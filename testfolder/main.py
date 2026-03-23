from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import json
from typing import Dict, List

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# 방(Room)별로 접속한 사람들의 통신망을 관리하는 매니저
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.room_state: Dict[str, dict] = {} 

    async def connect(self, websocket: WebSocket, room_name: str):
        await websocket.accept()
        if room_name not in self.active_connections:
            self.active_connections[room_name] = []
            self.room_state[room_name] = {'o_count': 0, 'x_count': 0, 'short_answers': [], 'total_answers': 0}
        self.active_connections[room_name].append(websocket)

    def disconnect(self, websocket: WebSocket, room_name: str):
        if room_name in self.active_connections:
            self.active_connections[room_name].remove(websocket)
            if not self.active_connections[room_name]:
                del self.active_connections[room_name]
                if room_name in self.room_state:
                    del self.room_state[room_name]

    async def broadcast(self, room_name: str, message: dict):
        if room_name in self.active_connections:
            for connection in self.active_connections[room_name]:
                await connection.send_json(message)

manager = ConnectionManager()

@app.get("/api/data")
async def get_quiz_data():
    with open("quiz_db.json", "r", encoding="utf-8") as f:
        return json.load(f)

@app.get("/")
async def get_home():
    with open("index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.websocket("/ws/{room_name}/{role}")
async def websocket_endpoint(websocket: WebSocket, room_name: str, role: str):
    await manager.connect(websocket, room_name)
    try:
        await manager.broadcast(room_name, {"type": "system", "msg": f"[{role}] 님이 입장했습니다!"})
        
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message['type'] == 'start_question':
                manager.room_state[room_name] = {'o_count': 0, 'x_count': 0, 'short_answers': [], 'total_answers': 0}
                await manager.broadcast(room_name, message)
                
            elif message['type'] == 'submit_answer':
                state = manager.room_state[room_name]
                state['total_answers'] += 1
                
                if message['question_type'] == 'ox':
                    if message['answer'] == 'O': state['o_count'] += 1
                    else: state['x_count'] += 1
                else:
                    state['short_answers'].append(message['answer'])
                    
                await manager.broadcast(room_name, {
                    'type': 'update_stats',
                    'state': state
                })
            
            # 🔥 핵심!! 누락되었던 부분입니다. 출제자가 정답 확인을 누르면 모두에게 쏴줍니다!
            elif message['type'] == 'show_answer':
                await manager.broadcast(room_name, message)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_name)
        await manager.broadcast(room_name, {"type": "system", "msg": f"[{role}] 님이 퇴장했습니다."})
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import json
from typing import Dict, List

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.room_state: Dict[str, dict] = {} 

    async def connect(self, websocket: WebSocket, room_name: str):
        await websocket.accept()
        if room_name not in self.active_connections:
            self.active_connections[room_name] = []
            
        if room_name not in self.room_state:
            self.room_state[room_name] = {
                'votes': {}, 
                'short_answers': {}, 
                'scores': {}, 
                'current_answer': None, 
                'is_scored': False      
            }
        self.active_connections[room_name].append(websocket)

    def disconnect(self, websocket: WebSocket, room_name: str):
        if room_name in self.active_connections:
            self.active_connections[room_name].remove(websocket)
            if not self.active_connections[room_name]:
                del self.active_connections[room_name]

    async def broadcast(self, room_name: str, message: dict):
        if room_name in self.active_connections:
            for connection in self.active_connections[room_name]:
                await connection.send_json(message)

manager = ConnectionManager()

@app.get("/api/data")
async def get_quiz_data():
    with open("quiz_db.json", "r", encoding="utf-8") as f:
        return json.load(f)

# 🌟 [수정됨] 모든 방의 점수 데이터를 한 번에 가져오는 종합 API!
@app.get("/api/scores")
async def get_all_scores():
    all_scores = {}
    for room, state in manager.room_state.items():
        if 'scores' in state:
            all_scores[room] = state['scores']
    return all_scores

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
            state = manager.room_state[room_name]
            
            if message['type'] == 'start_question':
                state['votes'] = {}
                state['short_answers'] = {}
                state['current_answer'] = message.get('answer') 
                state['is_scored'] = False 
                
                await manager.broadcast(room_name, message)
                
            elif message['type'] == 'submit_answer':
                user_id = message['user_id'] 
                ans = message['answer']
                q_type = message['question_type']
                
                if ans is None:
                    if q_type == 'ox' and user_id in state['votes']: del state['votes'][user_id]
                    elif q_type == 'short' and user_id in state['short_answers']: del state['short_answers'][user_id]
                else:
                    if q_type == 'ox': state['votes'][user_id] = ans
                    else: state['short_answers'][user_id] = ans
                
                o_count = list(state['votes'].values()).count('O')
                x_count = list(state['votes'].values()).count('X')
                total_ox = len(state['votes'])
                total_short = len(state['short_answers'])
                
                await manager.broadcast(room_name, {
                    'type': 'update_stats',
                    'question_type': q_type,
                    'state': {
                        'o_count': o_count,
                        'x_count': x_count,
                        'short_answers': list(state['short_answers'].values()),
                        'total_answers': total_ox if q_type == 'ox' else total_short,
                        'votes_detail': state['votes'],               
                        'short_answers_detail': state['short_answers'] 
                    }
                })
            
            elif message['type'] == 'show_answer':
                if not state['is_scored'] and state['current_answer']:
                    correct_ans = str(state['current_answer']).strip().lower() 
                    
                    for uid, u_ans in state['votes'].items():
                        if str(u_ans).strip().lower() == correct_ans:
                            state['scores'][uid] = state['scores'].get(uid, 0) + 1
                            
                    for uid, u_ans in state['short_answers'].items():
                        if str(u_ans).strip().lower() == correct_ans:
                            state['scores'][uid] = state['scores'].get(uid, 0) + 1
                            
                    state['is_scored'] = True 
                    
                await manager.broadcast(room_name, message)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_name)
        await manager.broadcast(room_name, {"type": "system", "msg": f"[{role}] 님이 퇴장했습니다."})
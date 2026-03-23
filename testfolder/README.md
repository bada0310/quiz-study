# 🚀 실시간 노션 퀴즈 쇼 (Real-time Notion Quiz)

스터디원들과 실시간으로 즐길 수 있는 웹소켓 기반의 퀴즈 웹사이트입니다.
노션(Notion)에 작성한 문제를 데이터베이스로 활용하여 자동으로 퀴즈를 생성합니다.

## 🛠️ 설치 및 실행 방법

1. **프로젝트 다운로드 및 라이브러리 설치**
   ```bash
   git clone [여기에_본인의_깃허브_주소_입력]
   cd testfolder
   pip install -r requirements.txt

   python update_notion.py

   uvicorn main:app --reload
# 실행 후 [http://127.0.0.1:8000](http://127.0.0.1:8000) 으로 접속하세요!

### ⚡ 4. (보너스) 원클릭 실행 파일 만들기 (`start.bat`)
윈도우를 쓰는 친구들이나 미래의 나를 위해, 위 과정조차 귀찮을 때 더블클릭 한 번으로 싹 켜지는 마법의 파일을 만들어 줄 수 있습니다.
`start.bat` 이라는 파일을 만들고 아래처럼 적어두세요.

```bat
@echo off
echo 필요한 라이브러리를 설치합니다...
pip install -r requirements.txt

echo.
echo 노션에서 최신 문제를 가져옵니다...
python update_notion.py

echo.
echo 실시간 퀴즈 서버를 시작합니다!
uvicorn main:app --reload
pause
import os
import requests
import json
from dotenv import load_dotenv
load_dotenv()

NOTION_TOKEN = os.environ.get("NOTION_TOKEN")  #  "secret_여기에_토큰_붙여넣기"
PAGE_ID = os.environ.get("NOTION_PAGE_ID") 

if not NOTION_TOKEN or not PAGE_ID:
    print("내 토큰 확인:", NOTION_TOKEN)
    print("🚨 .env 파일에 NOTION_TOKEN과 NOTION_PAGE_ID를 설정해주세요!")
    exit()

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def get_block_text(block):
    block_type = block["type"]
    if block_type in block and "rich_text" in block[block_type]:
        rich_texts = block[block_type]["rich_text"]
        if rich_texts:
            return "".join([rt["plain_text"] for rt in rich_texts])
    return ""

def get_answer_and_explanation(page_id):
    """문제 페이지 안으로 들어가서 답과 풀이를 찾아오는 함수"""
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    response = requests.get(url, headers=headers)
    
    result = {"answer": "", "explanation": ""}
    if response.status_code != 200:
        return result
        
    blocks = response.json().get("results", [])
    is_explanation_section = False
    explanation_lines = []
    
    for block in blocks:
        text = get_block_text(block).strip()
        if not text:
            continue
            
        if text.startswith("답") or "답 :" in text or "답:" in text:
            clean_answer = text.replace("답", "").replace(":", "").replace(" ", "").strip()
            result["answer"] = clean_answer
            
        elif text == "풀이" or text.startswith("풀이"):
            is_explanation_section = True
            clean_expl = text.replace("풀이", "").replace(":", "").strip()
            if clean_expl:
                explanation_lines.append(clean_expl)
                
        elif is_explanation_section:
            explanation_lines.append(text)
            
    result["explanation"] = "\n".join(explanation_lines)
    return result

def main():
    # 1. 메인 페이지에서 '데이터베이스(표)' 블록 찾기
    url = f"https://api.notion.com/v1/blocks/{PAGE_ID}/children"
    print("노션 페이지 분석 중...\n")
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"🚨 에러! 상태 코드: {response.status_code}")
        return

    quiz_data = {}
    blocks = response.json().get("results", [])

    for block in blocks:
        # 🔥 일반 페이지가 아닌 '데이터베이스' 블록인지 확인!
        if block["type"] == "child_database":
            db_title = block["child_database"]["title"]
            db_id = block["id"]
            print(f"🗂️ 출제자(데이터베이스) 발견: {db_title}")
            quiz_data[db_title] = []

            # 2. 해당 데이터베이스 안의 행(문제들) 긁어오기
            query_url = f"https://api.notion.com/v1/databases/{db_id}/query"
            db_response = requests.post(query_url, headers=headers)
            
            if db_response.status_code != 200:
                print(f"  🚨 DB 읽기 실패: {db_response.status_code}")
                continue
                
            pages = db_response.json().get("results", [])
            
            for page in pages:
                # 3. 데이터베이스 컬럼 중 '제목(title)' 속성 찾기 (이미지상의 'Aa 문제' 열)
                props = page["properties"]
                question_title = "제목 없음"
                
                for key, val in props.items():
                    if val["type"] == "title" and val["title"]:
                        question_title = val["title"][0]["plain_text"]
                        break
                
                if question_title == "제목 없음":
                    continue # 내용이 비어있는 빈 줄은 건너뛰기
                    
                print(f"  📄 문제 로드 중: {question_title[:20]}...")
                
                # 4. 문제 페이지 안으로 들어가서 답과 풀이 가져오기
                details = get_answer_and_explanation(page["id"])
                
                quiz_data[db_title].append({
                    "question": question_title,
                    "answer": details["answer"],
                    "explanation": details["explanation"]
                })
                print(f"     ✅ 정답: {details['answer']}")

    with open("quiz_db.json", "w", encoding="utf-8") as f:
        json.dump(quiz_data, f, ensure_ascii=False, indent=4)
    
    print("\n🎉 모든 데이터 추출 완료! 'quiz_db.json' 파일을 열어보세요.")

if __name__ == "__main__":
    main()
from fastapi import FastAPI
from core.database.database_config import test_connection
from core.domain.report.controller.report_controller import router as report_router

'''
서버 시작 명령어: fastapi dev main.py
'''

app = FastAPI(title="Channeling LLM API", version="1.0.0")

# 라우터 등록
app.include_router(report_router)

# 앱 시작 시 DB 연결 확인만
@app.on_event("startup")
async def on_startup():
    print("🚀 서버 시작 중...")
    
    # DB 연결 테스트만 수행
    if await test_connection():
        print("✅ DB에 연결 완료")
    else:
        print("❌ DB 연결 실패")

@app.get("/health")
async def health_check():
    """Docker 헬스체크용 엔드포인트"""
    return {"status": "UP"}


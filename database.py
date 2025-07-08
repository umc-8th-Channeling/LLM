from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
import os
from dotenv import load_dotenv
from sqlalchemy import text
'''
비동기 MySQL 데이터베이스를 설정합니다.
'''
# .env 파일 로드
load_dotenv()

# 환경변수에서 DB 설정 가져오기
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_DATABASE = os.getenv("DB_DATABASE")

# 비동기 MySQL 연결 URL
DATABASE_URL = f"mysql+aiomysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_DATABASE}"

# 비동기 엔진 생성
async_engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # SQL 쿼리 로그 출력 (개발용)
    pool_pre_ping=True,  # 연결 상태 체크
    pool_recycle=300,  # 연결 재사용 시간 (5분)
)

# 비동기 세션 팩토리
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
)

# 비동기 세션 의존성 (FastAPI용)
async def get_async_session():
    """비동기 세션 의존성 - FastAPI에서 사용"""
    async with AsyncSessionLocal() as session:
        yield session

# 연결 테스트 함수
async def test_connection():
    """비동기 DB 연결 테스트 및 테이블 목록 출력"""
    try:
        async with AsyncSessionLocal() as session:
            # 기본 연결 테스트
            result = await session.execute(text("SELECT 1"))
            print("✅ 데이터베이스 연결 성공!")
            
            # 데이터베이스 정보 조회
            db_info = await session.execute(text("SELECT DATABASE() as current_db"))
            current_db = db_info.fetchone()[0]
            print(f"📊 현재 데이터베이스: {current_db}")
            
            # 테이블 목록 조회
            tables_result = await session.execute(text("SHOW TABLES"))
            tables = tables_result.fetchall()
            
            if tables:
                print(f"📋 테이블 목록 ({len(tables)}개):")
                for i, table in enumerate(tables, 1):
                    print(f"   {i}. {table[0]}")
            else:
                print("📋 테이블이 없습니다.")
                
            return True
    except Exception as e:
        print(f"❌ 데이터베이스 연결 실패: {e}")
        return False


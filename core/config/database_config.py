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
# MySQL 설정
MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_PORT = os.getenv("MYSQL_PORT")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")

# PostgreSQL 설정
PG_HOST = os.getenv("PG_HOST")
PG_PORT = os.getenv("PG_PORT")
PG_USER = os.getenv("PG_USER")
PG_PASSWORD = os.getenv("PG_PASSWORD")
PG_DATABASE = os.getenv("PG_DATABASE")

# 비동기 MySQL 연결 URL
MYSQL_DATABASE_URL = f"mysql+aiomysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"

# 비동기 PostgreSQL 연결 URL
# 로컬 개발환경인지 확인 (localhost나 127.0.0.1이면 SSL 비활성화)
if PG_HOST in ['localhost', '127.0.0.1']:
    PG_DATABASE_URL = f"postgresql+asyncpg://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DATABASE}"
else:
    # RDS 등 프로덕션 환경에서는 SSL 사용
    PG_DATABASE_URL = f"postgresql+asyncpg://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DATABASE}?ssl=require"

# 비동기 엔진 생성
# MySQL 엔진
mysql_engine = create_async_engine(
    MYSQL_DATABASE_URL,
    echo=True,  # SQL 쿼리 로그 출력 (개발용)
    pool_pre_ping=True,  # 연결 상태 체크
    pool_recycle=300,  # 연결 재사용 시간 (5분)
)

# PostgreSQL 엔진
pg_engine = create_async_engine(
    PG_DATABASE_URL,
    echo=True,  # SQL 쿼리 로그 출력 (개발용)
    pool_pre_ping=True,  # 연결 상태 체크
    pool_recycle=300,  # 연결 재사용 시간 (5분)
)

# 비동기 세션 팩토리
# MySQL 세션 팩토리
MySQLSessionLocal = async_sessionmaker(
    bind=mysql_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
)

# PostgreSQL 세션 팩토리
PGSessionLocal = async_sessionmaker(
    bind=pg_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
)

# 비동기 세션 의존성 (FastAPI용)
async def get_mysql_session():
    """비동기 세션 의존성 - FastAPI에서 사용"""
    async with MySQLSessionLocal() as session:
        yield session

async def get_pg_session():
    """비동기 세션 의존성 - FastAPI에서 사용"""
    async with PGSessionLocal() as session:
        yield session

# 연결 테스트 함수
async def test_mysql_connection():
    """비동기 DB 연결 테스트 및 테이블 목록 출력"""
    try:
        async with MySQLSessionLocal() as session:
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

async def test_pg_connection():
    """비동기 PostgreSQL DB 연결 테스트 및 테이블 목록 출력"""
    try:
        async with PGSessionLocal() as session:
            # 기본 연결 테스트
            result = await session.execute(text("SELECT 1"))
            print("✅ PostgreSQL 데이터베이스 연결 성공!")
            
            # 데이터베이스 정보 조회
            db_info = await session.execute(text("SELECT current_database()"))
            current_db = db_info.fetchone()[0]
            print(f"📊 현재 데이터베이스: {current_db}")
            
            # 테이블 목록 조회
            tables_result = await session.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))
            tables = tables_result.fetchall()
            
            if tables:
                print(f"📋 테이블 목록 ({len(tables)}개):")
                for i, table in enumerate(tables, 1):
                    print(f"   {i}. {table[0]}")
            else:
                print("📋 테이블이 없습니다.")
                
            return True
    except Exception as e:
        print(f"❌ PostgreSQL 데이터베이스 연결 실패: {e}")
        return False


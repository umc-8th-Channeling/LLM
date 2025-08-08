# 멀티 스테이지 빌드 - 빌더 스테이지
FROM python:3.12-slim as builder

WORKDIR /app

# 빌드 의존성 설치
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치 (가상환경 사용)
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 런타임 스테이지
FROM python:3.12-slim

WORKDIR /app

# 런타임에 필요한 최소한의 패키지만 설치
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 빌더 스테이지에서 설치된 패키지 복사
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 애플리케이션 코드 복사
COPY . .

# 비특권 사용자 생성 및 전환
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

# 포트 노출
EXPOSE 8000

# 환경변수 설정
ENV PYTHONUNBUFFERED=1

# 애플리케이션 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
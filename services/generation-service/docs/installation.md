# Generation Service 설치 가이드

이 가이드는 Generation Service를 로컬 환경 또는 프로덕션 환경에 설치하는 방법을 설명합니다.

## 시스템 요구사항

### 최소 요구사항
- **OS**: Linux (Ubuntu 20.04+), macOS (10.15+), Windows 10+
- **CPU**: 2 cores (4 cores 권장)
- **RAM**: 4GB (8GB 권장)
- **디스크**: 10GB 여유 공간
- **네트워크**: 인터넷 연결 (AI API 사용)

### 권장 요구사항
- **OS**: Linux (Ubuntu 22.04 LTS)
- **CPU**: 4+ cores
- **RAM**: 16GB+
- **디스크**: 50GB+ SSD
- **네트워크**: 고속 인터넷 연결

## 의존성 설치

### 1. Docker 설치

#### Ubuntu/Debian
```bash
# Docker 공식 GPG 키 추가
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Docker 저장소 추가
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Docker 설치
sudo apt update
sudo apt install docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 사용자를 docker 그룹에 추가
sudo usermod -aG docker $USER
newgrp docker
```

#### macOS
```bash
# Homebrew를 사용한 설치
brew install --cask docker

# 또는 Docker Desktop 다운로드
# https://www.docker.com/products/docker-desktop
```

#### Windows
```bash
# Docker Desktop for Windows 다운로드 및 설치
# https://www.docker.com/products/docker-desktop
```

### 2. Python 환경 (선택사항 - 개발용)

#### Python 3.11 설치
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-pip python3.11-venv

# macOS (Homebrew)
brew install python@3.11

# Windows (Chocolatey)
choco install python311
```

#### 가상 환경 생성
```bash
python3.11 -m venv generation-service-env
source generation-service-env/bin/activate  # Linux/macOS
# generation-service-env\Scripts\activate  # Windows
```

## 소스 코드 다운로드

### Git을 사용한 다운로드
```bash
git clone https://github.com/your-org/ai-script-generator-v3.git
cd ai-script-generator-v3/services/generation-service
```

### 릴리스 패키지 다운로드
```bash
# 최신 릴리스 다운로드
curl -L https://github.com/your-org/ai-script-generator-v3/releases/latest/download/generation-service.tar.gz -o generation-service.tar.gz
tar -xzf generation-service.tar.gz
cd generation-service
```

## 환경 설정

### 1. 환경 변수 파일 생성
```bash
# 개발 환경
cp docker/.env.example docker/.env

# 환경 변수 편집
vim docker/.env
```

### 2. 필수 환경 변수 설정
```bash
# 기본 설정
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# Redis 설정
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=your_secure_redis_password  # pragma: allowlist secret

# 모니터링 설정
ENABLE_MONITORING=true
ENABLE_CACHING=true
ENABLE_PERFORMANCE_OPTIMIZATION=true

# Grafana 설정
GRAFANA_ADMIN_PASSWORD=your_secure_grafana_password  # pragma: allowlist secret
GRAFANA_SECRET_KEY=your_grafana_secret_key  # pragma: allowlist secret

# 성능 목표 설정
TARGET_WORKFLOW_EXECUTION_TIME=30
TARGET_CONCURRENT_WORKFLOWS=20
TARGET_API_RESPONSE_TIME_MS=100
TARGET_MEMORY_LIMIT_MB=2048
TARGET_CACHE_HIT_RATIO=0.7
TARGET_SUCCESS_RATE=0.95
```

### 3. AI API 키 설정 (필요시)
```bash
# OpenAI API
OPENAI_API_KEY=your_openai_api_key  # pragma: allowlist secret

# Anthropic API
ANTHROPIC_API_KEY=your_anthropic_api_key  # pragma: allowlist secret
```

## 설치 방법

### 방법 1: Docker Compose (권장)

#### 개발 환경 설치
```bash
# 개발 환경 시작
docker-compose -f docker/docker-compose.yml up -d

# 로그 확인
docker-compose -f docker/docker-compose.yml logs -f generation-service

# 서비스 상태 확인
docker-compose -f docker/docker-compose.yml ps
```

#### 프로덕션 환경 설치
```bash
# 환경 변수 설정
export REDIS_PASSWORD="your_secure_password"  # pragma: allowlist secret
export GRAFANA_ADMIN_PASSWORD="your_grafana_password"  # pragma: allowlist secret
export GRAFANA_SECRET_KEY="your_grafana_secret"  # pragma: allowlist secret

# 프로덕션 환경 시작
docker-compose -f docker/docker-compose.prod.yml up -d

# 서비스 확인
curl -f http://localhost/api/monitoring/health
```

### 방법 2: Docker 단독 실행

#### 이미지 빌드
```bash
# 개발용 이미지 빌드
docker build -f docker/Dockerfile --target development -t generation-service:dev .

# 프로덕션용 이미지 빌드
docker build -f docker/Dockerfile --target production -t generation-service:prod .
```

#### 컨테이너 실행
```bash
# Redis 시작
docker run -d --name redis -p 6379:6379 redis:7-alpine

# Generation Service 시작
docker run -d --name generation-service \
  -p 8000:8000 \
  -e ENVIRONMENT=development \
  -e REDIS_HOST=host.docker.internal \
  --link redis:redis \
  generation-service:dev
```

### 방법 3: 로컬 Python 환경

#### 의존성 설치
```bash
# 가상 환경 활성화
source generation-service-env/bin/activate

# 의존성 설치
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 패키지 설치
pip install -e .
```

#### Redis 시작 (별도)
```bash
# Docker로 Redis 시작
docker run -d --name redis -p 6379:6379 redis:7-alpine

# 또는 로컬 Redis 설치 및 시작
sudo apt install redis-server
sudo systemctl start redis-server
```

#### 서비스 시작
```bash
# 환경 변수 설정
export PYTHONPATH=/path/to/generation-service/src
export ENVIRONMENT=development
export REDIS_HOST=localhost
export REDIS_PORT=6379

# 서비스 시작
uvicorn src.generation_service.main:app --host 0.0.0.0 --port 8000 --reload
```

## 설치 확인

### 1. 헬스체크 확인
```bash
# 기본 헬스체크
curl http://localhost:8000/api/monitoring/health

# 응답 예시
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "overall_status": "healthy",
  "components": {
    "cache": "healthy",
    "redis": "healthy",
    "memory": "healthy"
  },
  "uptime": 3600,
  "version": "1.0.0"
}
```

### 2. 모니터링 대시보드 접속
```bash
# Grafana 대시보드
http://localhost:3000
# 로그인: admin / your_grafana_password

# Prometheus 메트릭
http://localhost:9090
```

### 3. API 문서 확인
```bash
# OpenAPI 문서 (Swagger UI)
http://localhost:8000/docs

# ReDoc 문서
http://localhost:8000/redoc
```

### 4. 테스트 실행
```bash
# 통합 테스트 실행
docker exec generation-service pytest tests/integration/ -v

# 성능 테스트 실행
docker exec generation-service python -c "
import asyncio
from tests.performance.performance_validator import run_performance_validation
asyncio.run(run_performance_validation())
"
```

## 초기 설정

### 1. 캐시 워밍
```bash
# 캐시 시스템 초기화
curl -X POST http://localhost:8000/api/cache/warm \
  -H "Content-Type: application/json" \
  -d '{"cache_types": ["prompt_result", "model_info"]}'
```

### 2. 모니터링 설정
```bash
# 알림 설정 확인
curl http://localhost:8000/api/monitoring/alerts/config

# 메트릭 수집 시작
curl -X POST http://localhost:8000/api/monitoring/metrics/start
```

### 3. 성능 최적화 활성화
```bash
# 성능 최적화 시작
curl -X POST http://localhost:8000/api/performance/optimize \
  -H "Content-Type: application/json" \
  -d '{"optimization_type": "all", "force": false}'
```

## 문제 해결

### 1. 일반적인 문제

#### 컨테이너 시작 실패
```bash
# 로그 확인
docker logs generation-service

# 상세 디버그 로그
docker run --rm -e DEBUG=true -e LOG_LEVEL=DEBUG generation-service:dev
```

#### Redis 연결 실패
```bash
# Redis 상태 확인
docker exec redis redis-cli ping

# 네트워크 연결 확인
docker exec generation-service nc -zv redis 6379
```

#### 메모리 부족
```bash
# 메모리 사용량 확인
docker stats

# 메모리 제한 증가
docker run --memory=4g generation-service:prod
```

### 2. 성능 문제

#### 느린 응답 시간
```bash
# 성능 메트릭 확인
curl http://localhost:8000/api/performance/status

# 캐시 상태 확인
curl http://localhost:8000/api/cache/status
```

#### 높은 CPU 사용률
```bash
# 리소스 사용량 확인
curl http://localhost:8000/api/performance/resources

# 최적화 실행
curl -X POST http://localhost:8000/api/performance/optimize \
  -H "Content-Type: application/json" \
  -d '{"optimization_type": "cpu"}'
```

### 3. 로그 분석

#### 로그 위치
```bash
# Docker 컨테이너 로그
docker logs generation-service

# 볼륨 마운트된 로그
ls -la ./logs/

# 로그 레벨 변경
docker exec generation-service \
  curl -X POST http://localhost:8000/api/monitoring/logging/level \
  -H "Content-Type: application/json" \
  -d '{"level": "DEBUG"}'
```

## 업그레이드

### 1. Docker 이미지 업그레이드
```bash
# 최신 이미지 다운로드
docker pull ghcr.io/your-org/generation-service:latest

# 서비스 재시작
docker-compose -f docker/docker-compose.yml down
docker-compose -f docker/docker-compose.yml up -d
```

### 2. 설정 마이그레이션
```bash
# 설정 백업
cp docker/.env docker/.env.backup

# 새 설정 템플릿 복사
cp docker/.env.example docker/.env.new

# 설정 병합 (수동)
diff docker/.env.backup docker/.env.new
```

### 3. 데이터 마이그레이션
```bash
# 캐시 데이터 백업
docker exec redis redis-cli BGSAVE

# 볼륨 백업
docker run --rm -v generation_redis-data:/data -v $(pwd):/backup alpine tar czf /backup/redis-backup.tar.gz /data
```

## 보안 설정

### 1. 방화벽 설정
```bash
# Ubuntu UFW
sudo ufw allow 8000/tcp  # API 포트
sudo ufw allow 3000/tcp  # Grafana (내부 네트워크만)
sudo ufw deny 6379/tcp   # Redis (외부 접근 차단)
```

### 2. SSL/TLS 설정
```bash
# 인증서 생성 (개발용)
openssl req -x509 -newkey rsa:4096 -keyout docker/nginx/ssl/key.pem -out docker/nginx/ssl/cert.pem -days 365 -nodes

# Let's Encrypt (프로덕션용)
sudo certbot --nginx -d your-domain.com
```

### 3. 액세스 제어
```bash
# API 키 설정
export API_KEY="your_secure_api_key"  # pragma: allowlist secret

# IP 화이트리스트 설정 (Nginx)
# /etc/nginx/conf.d/whitelist.conf
```

이제 Generation Service가 성공적으로 설치되었습니다. 다음 단계로 [배포 가이드](deployment.md)를 참조하여 프로덕션 환경 배포를 진행하세요.
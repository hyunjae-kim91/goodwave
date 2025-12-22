# SSH 터널을 통한 로컬 개발 환경 설정 가이드

로컬 개발 환경에서 SSH 터널을 통해 AWS RDS PostgreSQL 데이터베이스에 접근하는 방법입니다.

## ⚠️ 중요: Docker 환경에서는 SSH 터널이 필요하지 않습니다

**Docker 컨테이너 환경에서는 SSH 터널이 자동으로 비활성화됩니다.** 
- Docker 컨테이너가 EC2 인스턴스나 같은 VPC 내에서 실행되면 RDS에 직접 접근할 수 있습니다.
- `docker-compose.yml`에서 `USE_SSH_TUNNEL=false`로 자동 설정됩니다.
- 이 가이드는 **로컬 개발 환경에서만** 필요합니다.

## 설정 방법

### 1. SSH Private Key 준비

SSH private key 파일을 프로젝트 디렉토리 또는 안전한 위치에 저장합니다.

예: `~/.ssh/goodwave-key.pem` 또는 `backend/keys/goodwave-key.pem`

**중요**: `.gitignore`에 private key 파일이 포함되어 있는지 확인하세요!

### 2. 환경 변수 설정

`backend/.env` 파일에 다음 설정을 추가합니다:

```env
# 데이터베이스 URL (RDS 엔드포인트 사용)
DATABASE_URL=postgresql://DB_USER:DB_PASSWORD@fitfluence.cb622266qvje.ap-northeast-2.rds.amazonaws.com:5432/DB_NAME

# SSH 터널 설정
USE_SSH_TUNNEL=true
SSH_HOST=43.201.111.225
SSH_USER=ubuntu
SSH_PORT=22
SSH_PEM_KEY_PATH=~/.ssh/goodwave-key.pem  # 또는 절대 경로: C:\Users\yourname\.ssh\goodwave-key.pem
RDS_HOST=fitfluence.cb622266qvje.ap-northeast-2.rds.amazonaws.com
RDS_PORT=5432
LOCAL_TUNNEL_PORT=5433
```

### 3. Windows에서 경로 설정

Windows에서는 SSH key 경로를 절대 경로로 지정하거나, 상대 경로를 사용할 수 있습니다:

```env
# 절대 경로 (권장)
SSH_PEM_KEY_PATH=C:\Users\kim_hyunjae04\.ssh\goodwave-key.pem

# 또는 상대 경로 (프로젝트 루트 기준)
SSH_PEM_KEY_PATH=backend/keys/goodwave-key.pem
```

### 4. 애플리케이션 실행

애플리케이션을 실행하면 자동으로 SSH 터널이 시작됩니다:

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

로그에서 다음과 같은 메시지를 확인할 수 있습니다:

```
Starting SSH tunnel...
SSH tunnel established on localhost:5433
```

## 동작 원리

1. 애플리케이션 시작 시 `USE_SSH_TUNNEL=true`이면 SSH 터널을 자동으로 시작합니다.
2. SSH 터널은 로컬 포트 `5433`을 통해 RDS 데이터베이스에 연결합니다.
3. 데이터베이스 연결은 `localhost:5433`을 통해 이루어집니다.
4. 애플리케이션 종료 시 SSH 터널이 자동으로 종료됩니다.

## 문제 해결

### SSH 터널이 시작되지 않는 경우

1. **SSH Key 권한 확인** (Linux/Mac):
   ```bash
   chmod 600 ~/.ssh/goodwave-key.pem
   ```

2. **SSH 연결 테스트**:
   ```bash
   ssh -i ~/.ssh/goodwave-key.pem ubuntu@43.201.111.225
   ```

3. **환경 변수 확인**:
   - `USE_SSH_TUNNEL=true`로 설정되어 있는지 확인
   - `SSH_PEM_KEY_PATH`가 올바른 경로인지 확인
   - 모든 필수 설정이 있는지 확인

### 연결 타임아웃 오류

- EC2 인스턴스의 보안 그룹에서 SSH(22번 포트) 접근이 허용되어 있는지 확인
- RDS 보안 그룹에서 EC2 인스턴스로부터의 접근이 허용되어 있는지 확인

### 포트 충돌

`LOCAL_TUNNEL_PORT=5433`이 이미 사용 중인 경우 다른 포트로 변경:

```env
LOCAL_TUNNEL_PORT=5434
```

## SSH 터널 비활성화

### 로컬 환경에서 비활성화

프로덕션 환경이나 직접 연결이 가능한 경우:

```env
USE_SSH_TUNNEL=false
```

또는 환경 변수를 제거하면 기본값(`false`)이 사용됩니다.

### Docker 환경

Docker 환경에서는 **자동으로 비활성화**됩니다:
- Docker 컨테이너 내부에서는 `.dockerenv` 파일이나 `DOCKER_CONTAINER` 환경 변수를 통해 자동 감지됩니다.
- `docker-compose.yml`에 `USE_SSH_TUNNEL=false`가 명시적으로 설정되어 있습니다.
- 별도 설정 없이도 SSH 터널 없이 직접 RDS에 연결됩니다.


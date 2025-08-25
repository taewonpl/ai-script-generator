# Generation Service 배포 가이드

이 가이드는 Generation Service를 다양한 프로덕션 환경에 배포하는 방법을 설명합니다.

## 배포 환경 개요

### 지원하는 배포 방식
- **Docker Compose**: 단일 서버 배포
- **Kubernetes**: 컨테이너 오케스트레이션
- **AWS ECS**: Amazon 컨테이너 서비스
- **Azure Container Instances**: Microsoft 컨테이너 서비스
- **Google Cloud Run**: Google 서버리스 컨테이너

### 환경별 특징
| 환경 | 복잡도 | 확장성 | 비용 | 권장 용도 |
|------|--------|--------|------|-----------|
| Docker Compose | 낮음 | 낮음 | 낮음 | 개발/테스트 |
| Kubernetes | 높음 | 높음 | 중간 | 대규모 프로덕션 |
| AWS ECS | 중간 | 높음 | 중간 | AWS 기반 서비스 |
| Azure ACI | 낮음 | 중간 | 중간 | Azure 기반 서비스 |
| Google Cloud Run | 낮음 | 높음 | 낮음 | 서버리스 선호 |

## 사전 준비

### 1. 환경 변수 준비
```bash
# 프로덕션 환경 변수 파일 생성
cat > .env.prod << EOF
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Redis 설정
REDIS_HOST=redis.example.com
REDIS_PORT=6379
REDIS_PASSWORD=\${REDIS_PASSWORD}

# 보안 설정
JWT_SECRET_KEY=\${JWT_SECRET_KEY}
ENCRYPTION_KEY=\${ENCRYPTION_KEY}

# 성능 설정
MAX_WORKERS=4
WORKER_CONNECTIONS=1000
KEEP_ALIVE=2

# 모니터링 설정
ENABLE_MONITORING=true
ENABLE_CACHING=true
ENABLE_PERFORMANCE_OPTIMIZATION=true

# 외부 서비스 (필요시)
OPENAI_API_KEY=\${OPENAI_API_KEY}
ANTHROPIC_API_KEY=\${ANTHROPIC_API_KEY}
EOF
```

### 2. 보안 자격증명 관리
```bash
# 비밀번호 생성
export REDIS_PASSWORD=$(openssl rand -base64 32)
export JWT_SECRET_KEY=$(openssl rand -base64 64)
export ENCRYPTION_KEY=$(openssl rand -base64 32)
export GRAFANA_ADMIN_PASSWORD=$(openssl rand -base64 16)
export GRAFANA_SECRET_KEY=$(openssl rand -base64 32)

# 자격증명 파일 생성
cat > secrets.env << EOF
REDIS_PASSWORD=${REDIS_PASSWORD}
JWT_SECRET_KEY=${JWT_SECRET_KEY}
ENCRYPTION_KEY=${ENCRYPTION_KEY}
GRAFANA_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}
GRAFANA_SECRET_KEY=${GRAFANA_SECRET_KEY}
EOF

# 파일 권한 설정
chmod 600 secrets.env
```

### 3. SSL 인증서 준비
```bash
# Let's Encrypt 인증서 (권장)
sudo certbot certonly --standalone -d api.yourdomain.com

# 또는 자체 서명 인증서 (테스트용)
mkdir -p ssl
openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem -days 365 -nodes \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=api.yourdomain.com"
```

## Docker Compose 배포

### 1. 프로덕션 구성 파일 준비
```bash
# 프로덕션용 docker-compose 파일 복사
cp docker/docker-compose.prod.yml docker-compose.prod.yml

# 환경별 설정 수정
vim docker-compose.prod.yml
```

### 2. 배포 스크립트 작성
```bash
cat > deploy.sh << 'EOF'
#!/bin/bash
set -e

echo "🚀 Generation Service 프로덕션 배포 시작..."

# 환경 변수 로드
source .env.prod
source secrets.env

# 최신 이미지 다운로드
echo "📦 최신 이미지 다운로드 중..."
docker-compose -f docker-compose.prod.yml pull

# 기존 서비스 중지
echo "⏹️ 기존 서비스 중지 중..."
docker-compose -f docker-compose.prod.yml down

# 새 서비스 시작
echo "▶️ 새 서비스 시작 중..."
docker-compose -f docker-compose.prod.yml up -d

# 헬스체크 대기
echo "🏥 서비스 헬스체크 중..."
timeout 60 bash -c 'until curl -f http://localhost/api/monitoring/health; do sleep 5; done'

echo "✅ 배포 완료!"
EOF

chmod +x deploy.sh
```

### 3. 배포 실행
```bash
# 배포 실행
./deploy.sh

# 서비스 상태 확인
docker-compose -f docker-compose.prod.yml ps

# 로그 확인
docker-compose -f docker-compose.prod.yml logs -f generation-service
```

## Kubernetes 배포

### 1. Kubernetes 매니페스트 생성

#### Namespace 생성
```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: generation-service
  labels:
    app: generation-service
    environment: production
```

#### ConfigMap 생성
```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: generation-service-config
  namespace: generation-service
data:
  ENVIRONMENT: "production"
  DEBUG: "false"
  LOG_LEVEL: "INFO"
  REDIS_HOST: "redis-service"
  REDIS_PORT: "6379"
  ENABLE_MONITORING: "true"
  ENABLE_CACHING: "true"
  ENABLE_PERFORMANCE_OPTIMIZATION: "true"
  MAX_WORKERS: "4"
  WORKER_CONNECTIONS: "1000"
```

#### Secret 생성
```yaml
# k8s/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: generation-service-secret
  namespace: generation-service
type: Opaque
data:
  REDIS_PASSWORD: <base64-encoded-password>
  JWT_SECRET_KEY: <base64-encoded-key>
  ENCRYPTION_KEY: <base64-encoded-key>
  OPENAI_API_KEY: <base64-encoded-key>
```

#### Deployment 생성
```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: generation-service
  namespace: generation-service
  labels:
    app: generation-service
    version: v1.0.0
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
      maxSurge: 1
  selector:
    matchLabels:
      app: generation-service
  template:
    metadata:
      labels:
        app: generation-service
        version: v1.0.0
    spec:
      containers:
      - name: generation-service
        image: ghcr.io/your-org/generation-service:latest
        ports:
        - containerPort: 8000
          name: http
        envFrom:
        - configMapRef:
            name: generation-service-config
        - secretRef:
            name: generation-service-secret
        livenessProbe:
          httpGet:
            path: /api/monitoring/health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /api/monitoring/health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          successThreshold: 1
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        securityContext:
          runAsNonRoot: true
          runAsUser: 1000
          readOnlyRootFilesystem: true
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        - name: logs
          mountPath: /app/logs
      volumes:
      - name: tmp
        emptyDir: {}
      - name: logs
        emptyDir: {}
```

#### Service 생성
```yaml
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: generation-service
  namespace: generation-service
  labels:
    app: generation-service
spec:
  type: ClusterIP
  ports:
  - port: 80
    targetPort: 8000
    protocol: TCP
    name: http
  selector:
    app: generation-service
```

#### Ingress 생성
```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: generation-service
  namespace: generation-service
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"
spec:
  tls:
  - hosts:
    - api.yourdomain.com
    secretName: generation-service-tls
  rules:
  - host: api.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: generation-service
            port:
              number: 80
```

### 2. Redis 배포
```yaml
# k8s/redis.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: generation-service
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        env:
        - name: REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: generation-service-secret
              key: REDIS_PASSWORD
        command:
        - redis-server
        - --requirepass
        - $(REDIS_PASSWORD)
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        volumeMounts:
        - name: redis-data
          mountPath: /data
      volumes:
      - name: redis-data
        persistentVolumeClaim:
          claimName: redis-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: redis-service
  namespace: generation-service
spec:
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: redis-pvc
  namespace: generation-service
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```

### 3. Kubernetes 배포 실행
```bash
# 네임스페이스 생성
kubectl apply -f k8s/namespace.yaml

# Secret 생성 (base64 인코딩 필요)
kubectl create secret generic generation-service-secret \
  --from-literal=REDIS_PASSWORD=${REDIS_PASSWORD} \
  --from-literal=JWT_SECRET_KEY=${JWT_SECRET_KEY} \
  --from-literal=ENCRYPTION_KEY=${ENCRYPTION_KEY} \
  --from-literal=OPENAI_API_KEY=${OPENAI_API_KEY} \
  -n generation-service

# 모든 리소스 배포
kubectl apply -f k8s/

# 배포 상태 확인
kubectl get all -n generation-service

# 서비스 로그 확인
kubectl logs -f deployment/generation-service -n generation-service
```

## AWS ECS 배포

### 1. ECS 클러스터 생성
```bash
# AWS CLI로 클러스터 생성
aws ecs create-cluster --cluster-name generation-service-cluster

# 또는 Terraform 사용
cat > ecs-cluster.tf << EOF
resource "aws_ecs_cluster" "generation_service" {
  name = "generation-service-cluster"
  
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}
EOF
```

### 2. 태스크 정의 생성
```json
{
  "family": "generation-service",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "generation-service",
      "image": "ghcr.io/your-org/generation-service:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "essential": true,
      "environment": [
        {"name": "ENVIRONMENT", "value": "production"},
        {"name": "DEBUG", "value": "false"},
        {"name": "LOG_LEVEL", "value": "INFO"}
      ],
      "secrets": [
        {
          "name": "REDIS_PASSWORD",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:redis-password"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/generation-service",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": [
          "CMD-SHELL",
          "curl -f http://localhost:8000/api/monitoring/health || exit 1"
        ],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    },
    {
      "name": "redis",
      "image": "redis:7-alpine",
      "portMappings": [
        {
          "containerPort": 6379,
          "protocol": "tcp"
        }
      ],
      "essential": true,
      "command": [
        "redis-server",
        "--requirepass",
        "${REDIS_PASSWORD}"
      ],
      "environment": [
        {"name": "REDIS_PASSWORD", "valueFrom": "arn:aws:secretsmanager:region:account:secret:redis-password"}
      ]
    }
  ]
}
```

### 3. ECS 서비스 생성
```bash
# 서비스 생성
aws ecs create-service \
  --cluster generation-service-cluster \
  --service-name generation-service \
  --task-definition generation-service:1 \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-12345,subnet-67890],securityGroups=[sg-12345],assignPublicIp=ENABLED}" \
  --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:region:account:targetgroup/generation-service/1234567890123456,containerName=generation-service,containerPort=8000"
```

## Azure Container Instances 배포

### 1. Azure CLI로 배포
```bash
# 리소스 그룹 생성
az group create --name generation-service-rg --location eastus

# 컨테이너 인스턴스 생성
az container create \
  --resource-group generation-service-rg \
  --name generation-service \
  --image ghcr.io/your-org/generation-service:latest \
  --dns-name-label generation-service-unique \
  --ports 8000 \
  --environment-variables \
    ENVIRONMENT=production \
    DEBUG=false \
    LOG_LEVEL=INFO \
  --secure-environment-variables \
    REDIS_PASSWORD=${REDIS_PASSWORD} \
    JWT_SECRET_KEY=${JWT_SECRET_KEY} \
  --cpu 2 \
  --memory 4
```

### 2. ARM 템플릿 사용
```json
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "containerName": {
      "type": "string",
      "defaultValue": "generation-service"
    }
  },
  "resources": [
    {
      "type": "Microsoft.ContainerInstance/containerGroups",
      "apiVersion": "2021-03-01",
      "name": "[parameters('containerName')]",
      "location": "[resourceGroup().location]",
      "properties": {
        "containers": [
          {
            "name": "generation-service",
            "properties": {
              "image": "ghcr.io/your-org/generation-service:latest",
              "ports": [
                {
                  "port": 8000,
                  "protocol": "TCP"
                }
              ],
              "environmentVariables": [
                {
                  "name": "ENVIRONMENT",
                  "value": "production"
                }
              ],
              "resources": {
                "requests": {
                  "cpu": 2,
                  "memoryInGB": 4
                }
              }
            }
          }
        ],
        "ipAddress": {
          "type": "Public",
          "ports": [
            {
              "port": 8000,
              "protocol": "TCP"
            }
          ]
        },
        "osType": "Linux"
      }
    }
  ]
}
```

## Google Cloud Run 배포

### 1. Cloud Run으로 배포
```bash
# Google Cloud 프로젝트 설정
gcloud config set project your-project-id

# 컨테이너 이미지 빌드 및 푸시
gcloud builds submit --tag gcr.io/your-project-id/generation-service

# Cloud Run 서비스 배포
gcloud run deploy generation-service \
  --image gcr.io/your-project-id/generation-service \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8000 \
  --memory 2Gi \
  --cpu 2 \
  --max-instances 10 \
  --set-env-vars ENVIRONMENT=production,DEBUG=false \
  --set-secrets REDIS_PASSWORD=redis-password:latest
```

### 2. Cloud Run YAML 설정
```yaml
# cloudrun.yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: generation-service
  annotations:
    run.googleapis.com/ingress: all
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/maxScale: "10"
        run.googleapis.com/cpu-throttling: "false"
    spec:
      containerConcurrency: 100
      timeoutSeconds: 300
      containers:
      - image: gcr.io/your-project-id/generation-service
        ports:
        - containerPort: 8000
        env:
        - name: ENVIRONMENT
          value: production
        - name: DEBUG
          value: "false"
        - name: LOG_LEVEL
          value: INFO
        - name: REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: redis-password
              key: latest
        resources:
          limits:
            cpu: "2"
            memory: "2Gi"
        livenessProbe:
          httpGet:
            path: /api/monitoring/health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
```

## 모니터링 설정

### 1. Prometheus + Grafana 배포
```bash
# Helm을 사용한 모니터링 스택 설치
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Prometheus 설치
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --set grafana.adminPassword=${GRAFANA_ADMIN_PASSWORD}
```

### 2. 로그 집계 설정
```bash
# ELK Stack 또는 Fluentd 설정
# 로그 수집을 위한 설정 파일 생성
cat > logging-config.yaml << EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluentd-config
data:
  fluent.conf: |
    <source>
      @type tail
      path /var/log/containers/*generation-service*.log
      pos_file /var/log/fluentd-containers.log.pos
      tag kubernetes.*
      format json
    </source>
    
    <match kubernetes.**>
      @type elasticsearch
      host elasticsearch.logging.svc.cluster.local
      port 9200
      index_name generation-service
    </match>
EOF
```

## 백업 및 복구

### 1. 데이터 백업 전략
```bash
# Redis 데이터 백업
kubectl exec -n generation-service redis-deployment-xxx -- redis-cli BGSAVE

# 볼륨 백업 (Kubernetes)
kubectl create job --from=cronjob/backup-redis backup-redis-manual -n generation-service

# 설정 파일 백업
kubectl get configmap generation-service-config -o yaml > backup/configmap.yaml
kubectl get secret generation-service-secret -o yaml > backup/secret.yaml
```

### 2. 재해 복구 계획
```bash
# 복구 스크립트 생성
cat > disaster-recovery.sh << 'EOF'
#!/bin/bash
set -e

echo "🚨 재해 복구 프로세스 시작..."

# 1. 백업 데이터 확인
echo "📦 백업 데이터 확인 중..."
if [ ! -f "backup/redis-backup.tar.gz" ]; then
  echo "❌ Redis 백업 파일을 찾을 수 없습니다."
  exit 1
fi

# 2. 서비스 중지
echo "⏹️ 기존 서비스 중지 중..."
kubectl delete -f k8s/ --ignore-not-found=true

# 3. 데이터 복구
echo "🔄 데이터 복구 중..."
kubectl apply -f backup/

# 4. 서비스 재시작
echo "▶️ 서비스 재시작 중..."
kubectl apply -f k8s/

# 5. 헬스체크
echo "🏥 서비스 헬스체크 중..."
kubectl wait --for=condition=ready pod -l app=generation-service -n generation-service --timeout=300s

echo "✅ 재해 복구 완료!"
EOF

chmod +x disaster-recovery.sh
```

## 성능 튜닝

### 1. 리소스 최적화
```yaml
# 리소스 요청 및 제한 조정
resources:
  requests:
    memory: "1Gi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "1000m"
```

### 2. 오토스케일링 설정
```yaml
# Horizontal Pod Autoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: generation-service-hpa
  namespace: generation-service
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: generation-service
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### 3. 캐시 최적화
```bash
# Redis 성능 튜닝
kubectl patch configmap redis-config -n generation-service --patch '
data:
  redis.conf: |
    maxmemory 1gb
    maxmemory-policy allkeys-lru
    save 900 1
    save 300 10
    save 60 10000
'
```

## 보안 강화

### 1. 네트워크 정책
```yaml
# Network Policy
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: generation-service-netpol
  namespace: generation-service
spec:
  podSelector:
    matchLabels:
      app: generation-service
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
```

### 2. Pod Security Policy
```yaml
# Pod Security Policy
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: generation-service-psp
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  runAsUser:
    rule: 'MustRunAsNonRoot'
  seLinux:
    rule: 'RunAsAny'
  fsGroup:
    rule: 'RunAsAny'
  volumes:
    - 'configMap'
    - 'emptyDir'
    - 'projected'
    - 'secret'
    - 'downwardAPI'
    - 'persistentVolumeClaim'
```

이제 Generation Service가 다양한 프로덕션 환경에 배포할 준비가 완료되었습니다. 환경에 맞는 배포 방식을 선택하여 진행하세요.
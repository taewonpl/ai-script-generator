#!/bin/bash
echo "🔍 AI Script Generator v3.0 보안 검증 시작..."

# 1. 하드코딩된 인증정보 스캔
echo "1. 민감 정보 하드코딩 스캔..."
FOUND_SECRETS=$(rg "sk-[A-Za-z0-9_-]{20,}|postgresql://[^:]+:[^@]+@|password.*[=:]['\"][^'\"]{8,}" \
  --type py --type js --type ts --type json --count 2>/dev/null || echo "0")

if [ "$FOUND_SECRETS" -gt 0 ]; then
  echo "❌ 하드코딩된 민감정보 발견! 수정 후 재검사 필요"
  rg "sk-[A-Za-z0-9_-]{20,}|postgresql://[^:]+:[^@]+@|password.*[=:]['\"][^'\"]{8,}" \
    --type py --type js --type ts --type json -n
  exit 1
else
  echo "✅ 하드코딩된 민감정보 없음"
fi

# 2. .env 파일 Git 포함 여부 확인
echo "2. .env 파일 Git 추적 여부 확인..."
ENV_FILES=$(git ls-files 2>/dev/null | grep -E "\.env$|\.env\.[^e]|\.env\.l|\.env\.d|\.env\.p|\.env\.t" || true)
if [ -n "$ENV_FILES" ]; then
  echo "❌ .env 파일이 Git에 포함됨: $ENV_FILES"
  exit 1
else
  echo "✅ .env 파일 제외됨"
fi

# 3. .env.example 파일 존재 확인
echo "3. .env.example 파일 존재 확인..."
REQUIRED_ENV_FILES=(
  ".env.example"
  "services/generation-service/.env.example"
  "services/project-service/.env.example"
  "frontend/.env.example"
)

for file in "${REQUIRED_ENV_FILES[@]}"; do
  if [ ! -f "$file" ]; then
    echo "❌ 필수 .env.example 파일 없음: $file"
    exit 1
  fi
done
echo "✅ 모든 .env.example 파일 존재"

# 4. 보안 문서 존재 확인
echo "4. 보안 문서 확인..."
if [ ! -f "SECURITY_BEST_PRACTICES.md" ]; then
  echo "❌ SECURITY_BEST_PRACTICES.md 파일 없음"
  exit 1
fi
if [ ! -f "GITHUB_UPLOAD_CHECKLIST.md" ]; then
  echo "❌ GITHUB_UPLOAD_CHECKLIST.md 파일 없음"
  exit 1
fi
echo "✅ 보안 문서 존재"

# 5. 추가 패턴 검사
echo "5. 추가 보안 패턴 검사..."
ADDITIONAL_PATTERNS=$(rg "aws_access_key|aws_secret|private_key.*[=:]|BEGIN (RSA|PRIVATE) KEY" \
  --type py --type js --type ts --type json --count 2>/dev/null || echo "0")

if [ "$ADDITIONAL_PATTERNS" -gt 0 ]; then
  echo "⚠️ 추가 민감정보 패턴 발견:"
  rg "aws_access_key|aws_secret|private_key.*[=:]|BEGIN (RSA|PRIVATE) KEY" \
    --type py --type js --type ts --type json -n
  echo "확인 후 필요시 제거하세요."
fi

echo "🎉 모든 보안 검증 통과! GitHub 업로드 준비 완료"

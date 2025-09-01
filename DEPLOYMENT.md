# 포트폴리오 관리자 배포 가이드

## 🚀 Streamlit Cloud 배포

### 1. GitHub 저장소 생성
1. GitHub에서 새 저장소 생성
2. 저장소 이름: `portfolio-manager` (또는 원하는 이름)
3. Public 또는 Private 선택

### 2. 로컬 저장소를 GitHub에 연결
```bash
git remote add origin https://github.com/gmdtjr/portfolio-manager.git
git branch -M main
git push -u origin main
```

### 3. Streamlit Cloud 배포
1. [Streamlit Cloud](https://share.streamlit.io/) 접속
2. GitHub 계정으로 로그인
3. "New app" 클릭
4. 저장소 선택: `gmdtjr/portfolio-manager`
5. Main file path: `streamlit_portfolio.py`
6. "Deploy!" 클릭

### 4. 환경변수 설정
Streamlit Cloud 대시보드에서 다음 환경변수들을 설정:

#### 필수 환경변수:
- `KOREA_INVESTMENT_ACC_NO_DOMESTIC`
- `KOREA_INVESTMENT_API_KEY_DOMESTIC`
- `KOREA_INVESTMENT_API_SECRET_DOMESTIC`
- `KOREA_INVESTMENT_ACC_NO_PENSION`
- `KOREA_INVESTMENT_API_KEY_PENSION`
- `KOREA_INVESTMENT_API_SECRET_PENSION`
- `KOREA_INVESTMENT_ACC_NO_OVERSEAS`
- `KOREA_INVESTMENT_API_KEY_OVERSEAS`
- `KOREA_INVESTMENT_API_SECRET_OVERSEAS`
- `GOOGLE_SPREADSHEET_ID`

#### 선택사항:
- `DISCORD_WEBHOOK_URL`

### 5. Google Service Account 설정
1. Google Cloud Console에서 서비스 계정 생성
2. 서비스 계정 키 JSON 파일 다운로드
3. Streamlit Cloud에서 `GOOGLE_APPLICATION_CREDENTIALS` 환경변수로 JSON 내용 설정

## 🔧 로컬 개발 환경

### 1. 환경변수 설정
```bash
cp env.example .env
# .env 파일을 편집하여 실제 값들로 변경
```

### 2. 의존성 설치
```bash
pip install -r requirements.txt
```

### 3. 앱 실행
```bash
streamlit run streamlit_portfolio.py
```

## 📝 주의사항

1. **보안**: API 키와 시크릿은 절대 코드에 하드코딩하지 마세요
2. **환경변수**: 모든 민감한 정보는 환경변수로 관리
3. **서비스 계정**: Google Sheets 접근을 위한 서비스 계정 키는 안전하게 관리
4. **API 제한**: 한국투자증권 API 호출 제한을 고려하여 사용

## 🐛 문제 해결

### 일반적인 문제들:
1. **환경변수 누락**: 모든 필수 환경변수가 설정되었는지 확인
2. **API 키 오류**: 한국투자증권 API 키가 올바른지 확인
3. **Google Sheets 접근 오류**: 서비스 계정 권한 확인
4. **포트폴리오 조회 실패**: 계좌번호와 API 키가 일치하는지 확인

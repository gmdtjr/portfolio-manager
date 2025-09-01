# Gemini Deep Research

구글 제미나이 2.5 Pro를 활용한 딥리서치 도구입니다. 주제에 대해 반복적인 분석을 통해 깊이 있는 연구 결과를 생성합니다.

## 🚀 주요 기능

- **다단계 연구**: 여러 번의 반복을 통한 점진적 깊이 분석
- **연구 깊이 조절**: shallow, medium, deep 레벨 선택 가능
- **자동 요약**: 모든 연구 결과를 종합한 최종 요약 생성
- **결과 저장**: JSON 형태로 연구 결과 저장 및 로드
- **한글 지원**: 한국어 주제 및 결과 처리

## 📋 설치 방법

1. 필요한 패키지 설치:
```bash
pip install -r requirements.txt
```

2. Google AI Studio에서 API 키 발급:
   - [Google AI Studio](https://aistudio.google.com/) 방문
   - API 키 생성 및 복사

3. 환경변수 설정:
```bash
export GOOGLE_API_KEY="AIzaSyBFxIuI9McwkzSC5jWOnVEQxz8Af7tqxhY"
```

또는 `.env` 파일 생성:
```
GOOGLE_API_KEY=your_api_key_here
```

## 🔧 사용 방법

### 기본 사용법

```python
from deep_research import GeminiDeepResearch

# Deep Research 인스턴스 생성
researcher = GeminiDeepResearch()

# 딥리서치 실행
results = researcher.research_topic(
    topic="인공지능의 윤리적 문제와 해결 방안",
    depth="deep",
    max_iterations=3
)

# 결과 저장
filename = researcher.save_research_results(results)

# 결과 요약 출력
researcher.print_research_summary(results)
```

### 직접 실행

```bash
python deep_research.py
```

## 📊 연구 깊이 옵션

- **shallow**: 기본적인 정보와 핵심 개념
- **medium**: 상세한 분석과 예시 포함
- **deep**: 매우 상세한 분석, 다양한 관점, 구체적 예시

## 🔄 연구 프로세스

1. **초기 분석**: 주제에 대한 기본 구조화된 분석
2. **반복 심화**: 이전 결과를 바탕으로 더 깊이 있는 분석
3. **최종 요약**: 모든 반복 결과를 종합한 요약 생성

## 💾 결과 저장

연구 결과는 JSON 파일로 저장되며 다음 정보를 포함합니다:
- 연구 주제 및 설정
- 각 반복별 상세 결과
- 최종 요약
- 타임스탬프

## ⚠️ 주의사항

- Google AI API 사용량 및 비용을 고려하여 적절한 반복 횟수 설정
- API 키는 안전하게 보관하고 공개 저장소에 업로드하지 않음
- 긴 주제나 복잡한 질문의 경우 토큰 제한에 주의

## 🛠️ 커스터마이징

`GeminiDeepResearch` 클래스를 상속받아 프롬프트나 분석 로직을 수정할 수 있습니다:

```python
class CustomResearch(GeminiDeepResearch):
    def custom_analysis(self, topic):
        # 커스텀 분석 로직 구현
        pass
```

## 📞 지원

문제가 발생하거나 개선 사항이 있으면 이슈를 등록해주세요.

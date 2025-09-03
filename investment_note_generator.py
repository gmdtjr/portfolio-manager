import os
import json
import pandas as pd
from datetime import datetime
from google import genai
from google.genai import types
from google.oauth2 import service_account
from typing import Dict, Optional, List
from investment_notes_manager import InvestmentNotesManager

class InvestmentNoteGenerator:
    """기업 보고서를 분석하여 투자 노트 초안을 자동 생성하는 클래스"""
    
    def __init__(self, spreadsheet_id: str):
        self.spreadsheet_id = spreadsheet_id
        self.notes_manager = InvestmentNotesManager(spreadsheet_id)
        self.client = None
        self.model_name = "gemini-2.5-pro"
        self.gemini_api_key = os.getenv('GOOGLE_API_KEY')
        if not self.gemini_api_key:
            raise ValueError("GOOGLE_API_KEY 환경변수가 설정되지 않았습니다.")
        self._setup_gemini()
    
    def _setup_gemini(self):
        """Gemini API 설정"""
        try:
            # Google AI 클라이언트 초기화
            self.client = genai.Client(api_key=self.gemini_api_key)
            print("✅ Gemini API 설정이 완료되었습니다.")
            
        except Exception as e:
            print(f"❌ Gemini API 설정 실패: {e}")
            raise
    
    def generate_investment_note_from_report(self, company_name: str, stock_code: str, report_content: str) -> Dict:
        """기업 보고서를 분석하여 투자 노트 초안 생성"""
        max_retries = 3
        retry_delay = 2  # 초
        
        for attempt in range(max_retries):
            try:
                print(f"🤖 AI 분석 시도 {attempt + 1}/{max_retries}...")
                
                # 메타 프롬프트 생성
                meta_prompt = self._create_analysis_prompt(company_name, stock_code, report_content)
                
                # AI 분석 요청
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=meta_prompt
                )
                
                # 응답 파싱
                try:
                    response_text = response.text
                    if response_text:
                        analysis_result = self._parse_ai_response(response_text)
                    else:
                        raise ValueError("AI 응답이 비어있습니다.")
                except Exception as text_error:
                    print(f"⚠️ response.text 실패, fallback 방법 시도: {str(text_error)}")
                    
                    # 새로운 API의 fallback 방법 시도
                    if hasattr(response, 'candidates') and response.candidates:
                        candidate = response.candidates[0]
                        if hasattr(candidate, 'content') and candidate.content:
                            if hasattr(candidate.content, 'parts') and candidate.content.parts:
                                part = candidate.content.parts[0]
                                if hasattr(part, 'text'):
                                    response_text = part.text
                                    if response_text:
                                        analysis_result = self._parse_ai_response(response_text)
                                    else:
                                        raise ValueError("AI 응답이 비어있습니다.")
                                else:
                                    raise ValueError("AI 응답에서 텍스트를 추출할 수 없습니다.")
                            else:
                                raise ValueError("AI 응답에서 parts를 찾을 수 없습니다.")
                        else:
                            raise ValueError("AI 응답에서 content를 찾을 수 없습니다.")
                    else:
                        raise ValueError("AI 응답에서 candidates를 찾을 수 없습니다.")
                
                # 투자 노트 데이터 구조화
                investment_note = self._structure_investment_note(company_name, stock_code, analysis_result)
                
                print(f"✅ AI 분석 성공 (시도 {attempt + 1})")
                return investment_note
                
            except Exception as e:
                error_msg = str(e)
                print(f"❌ AI 분석 실패 (시도 {attempt + 1}): {error_msg}")
                
                # 503 오류인 경우 재시도
                if "503" in error_msg or "UNAVAILABLE" in error_msg:
                    if attempt < max_retries - 1:
                        print(f"⏳ {retry_delay}초 후 재시도합니다...")
                        import time
                        time.sleep(retry_delay)
                        retry_delay *= 2  # 지수 백오프
                        continue
                    else:
                        print("❌ 최대 재시도 횟수 초과. 서버가 과부하 상태입니다.")
                        raise e
                else:
                    # 다른 오류는 즉시 실패
                    raise e
        
        # 모든 재시도 실패
        raise Exception("AI 분석에 실패했습니다.")
    
    def _create_analysis_prompt(self, company_name: str, stock_code: str, report_content: str) -> str:
        """AI 분석을 위한 메타 프롬프트 생성"""
        return f"""당신은 전문 투자 분석가입니다. 주어진 기업 보고서를 분석하여 투자 노트를 작성해주세요.

## 분석 대상
- 기업명: {company_name}
- 종목코드: {stock_code}
- 보고서 내용: {report_content}

## 투자 노트 작성 가이드

### 1. 투자 아이디어 (Thesis) 작성
- 이 기업에 투자하는 가장 핵심적인 이유를 1-2줄로 요약
- 기업의 핵심 경쟁력과 성장 동력 중심으로 작성
- 구체적이고 실현 가능한 투자 논리 제시

### 2. 투자 확신도 (Conviction) 평가
다음 기준으로 평가:
- **상 (High)**: 강력한 경쟁력, 명확한 성장 동력, 낮은 리스크
- **중 (Medium)**: 양호한 경쟁력, 적당한 성장 동력, 보통 수준의 리스크
- **하 (Low)**: 불확실한 경쟁력, 모호한 성장 동력, 높은 리스크

### 3. 섹터/산업 (Sector/Industry) 분류
계층적 분류로 작성 (예: IT > 반도체 > HBM, 헬스케어 > 바이오 > 면역항암제)

### 4. 투자 유형 (Asset Type) 분류
다음 중 하나로 분류:
- **성장주 (Growth)**: 높은 성장률, 낮은 배당
- **가치주 (Value)**: 낮은 PER, 높은 배당률
- **배당주 (Dividend)**: 안정적 배당, 성장보다 수익성
- **경기순환주 (Cyclical)**: 경기 변동에 민감한 업종

### 5. 핵심 촉매 (Catalysts) 식별
주가 상승을 이끌 수 있는 구체적인 이벤트나 성과 (3개 이내):
- 신제품/서비스 출시
- 시장 진출/확장
- 실적 개선
- 정책 혜택
- 기술 혁신

### 6. 핵심 리스크 (Risks) 분석
주가 하락을 야기할 수 있는 주요 위험 요인 (3개 이내):
- 경쟁 심화
- 규제 변화
- 경기 침체
- 기술 변화
- 원자재 가격 변동

### 7. 핵심 모니터링 지표 (KPIs) 설정
투자 아이디어 유효성을 확인할 수 있는 핵심 지표 (3개 이내):
- 매출 성장률
- 영업이익률
- 시장 점유율
- 신규 고객 수
- R&D 투자 비중

### 8. 투자 기간 (Horizon) 설정
예상 투자 기간:
- **단기 (1년 이하)**: 단기 이벤트나 성과 기대
- **중기 (1-2년)**: 중간 정도의 성장 기대
- **중장기 (2-3년)**: 상당한 성장 기대
- **장기 (3년 이상)**: 장기적 성장 동력 기대

### 9. 목표 주가 (Target) 설정
1차, 2차 목표 주가와 근거:
- 밸류에이션 방법 (PER, PBR, DCF 등)
- 시장 상황 고려
- 리스크 프리미엄 반영

### 10. 매도 조건 (Exit Plan) 수립
구체적인 매도 전략:
- **수익 실현**: 목표 주가 도달 시 분할 매도 계획
- **손절**: 투자 아이디어 훼손 시 즉시 매도 조건

## 출력 형식
다음 JSON 형식으로 응답해주세요:

```json
{{
    "thesis": "투자 아이디어 요약",
    "conviction": "상/중/하",
    "sector": "섹터 > 산업 > 세부산업",
    "asset_type": "성장주/가치주/배당주/경기순환주",
    "catalysts": "1. 첫 번째 촉매\\n2. 두 번째 촉매\\n3. 세 번째 촉매",
    "risks": "1. 첫 번째 리스크\\n2. 두 번째 리스크\\n3. 세 번째 리스크",
    "kpis": "1. 첫 번째 지표\\n2. 두 번째 지표\\n3. 세 번째 지표",
    "horizon": "단기/중기/중장기/장기",
    "target": "1차: 목표주가 (근거)\\n2차: 목표주가 (근거)",
    "exit_plan": "수익 실현: 조건\\n손절: 조건"
}}
```

보고서 내용을 바탕으로 객관적이고 실용적인 투자 노트를 작성해주세요."""
    
    def _parse_ai_response(self, response_text: str) -> Dict:
        """AI 응답을 파싱하여 구조화된 데이터로 변환"""
        try:
            # JSON 부분 추출
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("JSON 형식을 찾을 수 없습니다.")
            
            json_str = response_text[json_start:json_end]
            analysis_result = json.loads(json_str)
            
            return analysis_result
            
        except Exception as e:
            print(f"❌ AI 응답 파싱 실패: {e}")
            # 기본 템플릿 반환
            return {
                "thesis": "AI 분석 실패로 인한 기본 템플릿",
                "conviction": "중",
                "sector": "미분류",
                "asset_type": "성장주",
                "catalysts": "1. 추가 분석 필요\n2. 추가 분석 필요\n3. 추가 분석 필요",
                "risks": "1. 추가 분석 필요\n2. 추가 분석 필요\n3. 추가 분석 필요",
                "kpis": "1. 추가 분석 필요\n2. 추가 분석 필요\n3. 추가 분석 필요",
                "horizon": "중기",
                "target": "1차: 분석 필요\n2차: 분석 필요",
                "exit_plan": "수익 실현: 분석 필요\n손절: 분석 필요"
            }
    
    def _structure_investment_note(self, company_name: str, stock_code: str, analysis_result: Dict) -> Dict:
        """분석 결과를 투자 노트 형식으로 구조화"""
        return {
            '종목코드': stock_code,
            '종목명': company_name,
            '투자 아이디어 (Thesis)': analysis_result.get('thesis', ''),
            '투자 확신도 (Conviction)': analysis_result.get('conviction', '중'),
            '섹터/산업 (Sector/Industry)': analysis_result.get('sector', '미분류'),
            '투자 유형 (Asset Type)': analysis_result.get('asset_type', '성장주'),
            '핵심 촉매 (Catalysts)': analysis_result.get('catalysts', ''),
            '핵심 리스크 (Risks)': analysis_result.get('risks', ''),
            '핵심 모니터링 지표 (KPIs)': analysis_result.get('kpis', ''),
            '투자 기간 (Horizon)': analysis_result.get('horizon', '중기'),
            '목표 주가 (Target)': analysis_result.get('target', ''),
            '매도 조건 (Exit Plan)': analysis_result.get('exit_plan', ''),
            '포트폴리오_상태': '',  # 빈 값으로 시작 (포트폴리오 동기화 시 채워짐)
            '최초_매수일': '',  # 빈 값으로 시작 (포트폴리오 동기화 시 채워짐)
            '최종_매도일': '',  # 빈 값으로 시작 (포트폴리오 동기화 시 채워짐)
            '마지막_수정일': datetime.now().strftime('%Y-%m-%d')
        }
    
    def create_and_save_note(self, company_name: str, stock_code: str, report_content: str) -> bool:
        """투자 노트 생성 및 DB 저장"""
        try:
            print(f"📝 {company_name} ({stock_code}) 투자 노트 생성 중...")
            
            # 기존 데이터 마이그레이션 확인
            print("🔄 마이그레이션 확인 중...")
            self.notes_manager.migrate_existing_notes()
            
            # AI 분석을 통한 투자 노트 생성
            print("🤖 AI 분석 중...")
            investment_note = self.generate_investment_note_from_report(company_name, stock_code, report_content)
            
            # 기존 노트 확인
            print("🔍 기존 노트 확인 중...")
            existing_note = self.notes_manager.get_note_by_stock_code(stock_code)
            
            if existing_note:
                # 기존 노트 업데이트
                print(f"📝 기존 투자 노트가 발견되어 업데이트합니다.")
                success = self.notes_manager.update_investment_note(stock_code, investment_note)
                if success:
                    print(f"✅ {company_name} ({stock_code}) 투자 노트가 업데이트되었습니다.")
                else:
                    print(f"❌ {company_name} ({stock_code}) 투자 노트 업데이트 실패")
                    return False
            else:
                # 새 노트 추가
                print(f"📝 새로운 투자 노트를 추가합니다.")
                success = self.notes_manager.add_investment_note(investment_note)
                if success:
                    print(f"✅ {company_name} ({stock_code}) 투자 노트가 생성되었습니다.")
                else:
                    print(f"❌ {company_name} ({stock_code}) 투자 노트 생성 실패")
                    return False
            
            return True
            
        except Exception as e:
            print(f"❌ 투자 노트 생성 및 저장 실패: {e}")
            import traceback
            print(f"상세 오류: {traceback.format_exc()}")
            return False
    
    def preview_note(self, company_name: str, stock_code: str, report_content: str) -> Dict:
        """투자 노트 미리보기 (저장하지 않고 생성만)"""
        try:
            print(f"👀 {company_name} ({stock_code}) 투자 노트 미리보기 생성 중...")
            
            investment_note = self.generate_investment_note_from_report(company_name, stock_code, report_content)
            
            print(f"✅ {company_name} ({stock_code}) 투자 노트 미리보기 완료")
            return investment_note
            
        except Exception as e:
            print(f"❌ 투자 노트 미리보기 실패: {e}")
            return {}

def main():
    """테스트 함수"""
    import os
    from dotenv import load_dotenv
    
    # 환경변수 로드
    load_dotenv()
    
    spreadsheet_id = os.getenv('GOOGLE_SPREADSHEET_ID')
    
    if not spreadsheet_id:
        print("❌ GOOGLE_SPREADSHEET_ID가 설정되지 않았습니다.")
        return
    
    try:
        # 투자 노트 생성기 초기화
        generator = InvestmentNoteGenerator(spreadsheet_id)
        
        # 테스트용 기업 보고서 (삼성전자 예시)
        test_company = "삼성전자"
        test_stock_code = "005930"
        test_report = """
        삼성전자 2024년 3분기 실적 발표:
        
        매출: 67조원 (전년 동기 대비 12% 증가)
        영업이익: 10조원 (전년 동기 대비 279% 증가)
        
        주요 성과:
        - HBM3 시장 점유율 50% 이상 유지
        - AI 반도체 수요 급증으로 메모리 사업 호조
        - 파운드리 3나노 공정 수율 안정화
        - 모바일 사업 수익성 개선
        
        전망:
        - 2024년 4분기 AI 반도체 수요 지속 전망
        - HBM4 양산 준비 중
        - 파운드리 신규 고객 확보 기대
        """
        
        print("🧪 투자 노트 자동 생성 테스트")
        print("=" * 50)
        
        # 미리보기 생성
        preview_note = generator.preview_note(test_company, test_stock_code, test_report)
        
        if preview_note:
            print("\n📋 생성된 투자 노트 미리보기:")
            for key, value in preview_note.items():
                print(f"{key}: {value}")
            
            # 사용자 확인
            user_input = input("\n이 투자 노트를 DB에 저장하시겠습니까? (y/n): ")
            
            if user_input.lower() == 'y':
                success = generator.create_and_save_note(test_company, test_stock_code, test_report)
                if success:
                    print("✅ 투자 노트가 성공적으로 저장되었습니다!")
                else:
                    print("❌ 투자 노트 저장에 실패했습니다.")
            else:
                print("📝 투자 노트 저장을 취소했습니다.")
        
        print("\n✅ 테스트가 완료되었습니다!")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        print(f"상세 오류: {traceback.format_exc()}")

if __name__ == "__main__":
    main()

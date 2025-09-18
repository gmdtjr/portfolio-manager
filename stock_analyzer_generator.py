"""
종목 상세 분석기 모듈
사용자가 입력한 종목명을 받아 DB 정보 유무에 따라 맞춤형 또는 일반적인 심층 분석용 Deep Research 프롬프트를 생성합니다.
"""

import os
import json
import pandas as pd
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build


class StockAnalyzerGenerator:
    """종목 상세 분석 프롬프트 생성기 (투자 노트 연동)"""
    
    def __init__(self, spreadsheet_id: str = None):
        """
        초기화
        
        Args:
            spreadsheet_id (str): Google Spreadsheet ID
        """
        self.spreadsheet_id = spreadsheet_id
        self.sheets_service = None
        
        if spreadsheet_id:
            self._setup_google_sheets()
    
    def _setup_google_sheets(self):
        """Google Sheets API 설정"""
        try:
            # 환경변수에서 서비스 계정 정보 가져오기
            service_account_json_str = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
            if not service_account_json_str:
                print("⚠️ GOOGLE_APPLICATION_CREDENTIALS_JSON 환경변수가 설정되지 않았습니다.")
                return
            
            service_account_info = json.loads(service_account_json_str)
            credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
            )
            self.sheets_service = build('sheets', 'v4', credentials=credentials)
            print("✅ Google Sheets API 설정 완료")
            
        except Exception as e:
            print(f"❌ Google Sheets API 설정 실패: {e}")
            self.sheets_service = None
    
    def get_investment_notes(self) -> pd.DataFrame:
        """투자 노트 시트에서 데이터를 읽어 DataFrame으로 반환"""
        if not self.sheets_service or not self.spreadsheet_id:
            print("⚠️ Google Sheets 서비스가 설정되지 않았습니다.")
            return pd.DataFrame()
        
        try:
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id, 
                range="투자_노트"
            ).execute()
            values = result.get('values', [])
            
            if not values or len(values) < 2:
                print("⚠️ 투자_노트 시트에 데이터가 없습니다.")
                return pd.DataFrame()
            
            df = pd.DataFrame(values[1:], columns=values[0])
            print(f"✅ 투자_노트 DB 로드 완료: {len(df)}개 종목")
            return df
            
        except Exception as e:
            print(f"⚠️ 투자_노트 시트 읽기 실패: {e}")
            return pd.DataFrame()
    
    def find_stock_note(self, stock_name: str) -> pd.Series:
        """
        투자 노트에서 해당 종목의 정보를 찾습니다.
        
        Args:
            stock_name (str): 검색할 종목명 또는 코드
            
        Returns:
            pd.Series: 해당 종목의 투자 노트 정보 (없으면 빈 Series)
        """
        notes_df = self.get_investment_notes()
        
        if notes_df.empty:
            return pd.Series(dtype=object)
        
        # 종목명 또는 종목코드로 검색
        mask = (
            notes_df['종목명'].str.contains(stock_name, case=False, na=False) |
            (notes_df['종목코드'] == stock_name)
        )
        
        if mask.any():
            return notes_df[mask].iloc[0]
        
        return pd.Series(dtype=object)
    
    def generate_contextual_deep_dive_prompt(self, stock_name: str, stock_note: pd.Series) -> str:
        """
        (투자 노트가 있을 때) 사용자의 기존 노트를 기준으로 'Bull vs. Bear' 관점의 균형 잡힌 검증 프롬프트를 생성합니다.
        """
        thesis = stock_note.get('투자 아이디어 (Thesis)', '내용 없음')
        catalysts = stock_note.get('핵심 촉매 (Catalysts)', '내용 없음')
        risks = stock_note.get('핵심 리스크 (Risks)', '내용 없음')
        conviction = stock_note.get('투자 확신도 (Conviction)', '내용 없음')
        sector = stock_note.get('섹터/산업 (Sector/Industry)', '내용 없음')
        today = datetime.now().strftime('%Y년 %m월 %d일')

        return f"""# {stock_name} 균형 분석 및 투자 노트 검증 보고서 ({today})

## [중요 지시사항]
- **역할 부여:** 당신은 나의 최종 의사결정을 돕기 위해, **객관적인 데이터에 기반한 찬성론(Bull Case)과 반대론(Bear Case)을 모두 제시하는 '균형 분석가'**입니다. 당신의 임무는 결론을 내리는 것이 아니라, 내가 최상의 결정을 내릴 수 있도록 양질의 재료(양면적 분석)를 제공하는 것입니다.
- **언어:** 모든 결과물은 반드시 **한글**로만 작성해주세요.

## 분석 목표:
아래 제시된 **[나의 기존 투자 노트]**를 기준으로, 최신 정보를 활용하여 {stock_name}에 대한 **균형 잡힌 찬반 분석**을 수행하고, 나의 기존 투자 아이디어의 강점과 약점을 객관적으로 평가하시오.

## [나의 기존 투자 노트]
- 나의 투자 아이디어: {thesis}
- 내가 기대하는 핵심 촉매: {catalysts}
- 내가 우려하는 핵심 리스크: {risks}

---
## 분석 목차:
*아래 목차에 따라, 모든 항목에 대해 **찬성론과 반대론을 함께 제시**해주십시오.*

**1. 투자 아이디어 (Investment Thesis):**
   - **찬성론 (Bull Case):** 나의 투자 아이디어를 뒷받침하는 가장 강력한 최신 데이터나 근거는 무엇인가?
   - **반대론 (Bear Case):** 나의 투자 아이디어를 반박할 수 있는 가장 강력한 논리나 데이터는 무엇인가?

**2. 경제적 해자 (Economic Moat):**
   - **찬성론 (Bull Case):** 나의 노트에 기록된 해자 관점을 뒷받침하는 가장 강력한 증거는 무엇인가?
   - **반대론 (Bear Case):** 나의 해자 가설이 과대평가되었거나 미래에 훼손될 수 있는 가장 큰 이유는 무엇인가?

**3. 성장 동력 및 촉매 (Growth Drivers & Catalysts):**
   - **찬성론 (Bull Case):** 내가 기대하는 '촉매'들이 실현될 긍정적인 신호는 무엇인가?
   - **반대론 (Bear Case):** 이 성장 스토리가 실현되지 않을 수 있는 가장 큰 장애물(Headwind)은 무엇인가?

**4. 리스크 분석 (Risk Analysis):**
   - 내가 우려하는 '핵심 리스크' 외에, 현재 시장에서 새롭게 부상하고 있는 잠재적 리스크는 무엇인가? 각 리스크의 발생 가능성과 예상 파급 효과를 분석하시오.

**5. 밸류에이션 (Valuation):**
   - **찬성론 (Bull Case):** 현재 주가가 왜 여전히 매력적인 진입점이라고 할 수 있는가?
   - **반대론 (Bear Case):** 현재 주가가 왜 이미 고평가되었거나 '밸류에이션 함정'일 수 있는가?

**6. 최종 의사결정을 위한 핵심 질문 (Key Questions for Decision):**
   - **지시사항:** 위 모든 찬반 분석을 종합하여, 내가 최종적으로 투자를 '결정'하기 위해 스스로에게 던져야 할 가장 중요한 질문 3가지를 제시해주시오.
   - (예시) "단기적인 밸류에이션 부담에도 불구하고, 장기적인 기술적 해자를 더 높게 평가할 것인가?"

**7. 투자 노트 DB 동기화를 위한 요약 (For DB Sync):**
   - **투자 아이디어:** [가장 핵심적인 찬성 논리 요약]
   - **핵심 촉매:** [가장 중요한 긍정적 이벤트 3가지]
   - **핵심 리스크:** [가장 중요한 부정적 위험 요인 3가지]
   - **핵심 모니터링 지표:** [찬성/반대 논리 중 어느 쪽이 현실화되는지 판단할 수 있는 핵심 지표 3가지]
"""

    def generate_generic_deep_dive_prompt(self, stock_name: str) -> str:
        """
        (투자 노트에 정보가 없을 때) 'Bull vs. Bear' 관점의 균형 잡힌 분석 프롬프트를 생성합니다.
        """
        today = datetime.now().strftime('%Y년 %m월 %d일')

        return f"""# {stock_name} 균형 분석 보고서 (Bull vs. Bear) ({today})

## [중요 지시사항]
- **역할 부여:** 당신은 특정 종목에 대해 **낙관론(Bull Case)과 비관론(Bear Case)을 모두 제시**하는 객관적이고 균형 잡힌 시각의 애널리스트입니다. 당신의 임무는 결론을 내리는 것이 아니라, 내가 최상의 결정을 내릴 수 있도록 양질의 재료(양면적 분석)를 제공하는 것입니다.
- **언어:** 모든 결과물은 반드시 **한글**로만 작성해주세요.

## 분석 목표:
{stock_name}에 대한 종합적인 분석을 통해, 이 기업에 대한 **가장 강력한 투자 찬성 논거(Bull Case)**와 **가장 강력한 투자 반대 논거(Bear Case)**를 모두 제시하여, 내가 합리적인 투자 결정을 내릴 수 있도록 지원하시오.

## 분석 목차:
*아래 목차 순서와 항목을 반드시 준수하여, 모든 항목에 대해 찬성/반대 논리를 함께 분석해주십시오.*

**1. 핵심 투자 논쟁 (The Key Debate):**
   - 현재 시장에서 {stock_name}을 둘러싼 가장 큰 의견 대립은 무엇인가?

**2. 경제적 해자 (Economic Moat):**
   - **찬성론 (Bull Case):** 이 기업의 해자가 왜 강력하고 지속 가능한가?
   - **반대론 (Bear Case):** 이 해자가 보기보다 약하거나 미래에 훼손될 수 있는 이유는 무엇인가?

**3. 성장 동력 (Growth Drivers):**
   - **찬성론 (Bull Case):** 향후 성장을 이끌 명확하고 강력한 촉매는 무엇인가?
   - **반대론 (Bear Case):** 이 성장 스토리가 실현되지 않을 수 있는 가장 큰 장애물(Headwind)은 무엇인가?

**4. 리스크 분석 (Risk Analysis):**
   - 투자자들이 가장 주목해야 할 핵심 리스크 요인들을 분석하고, 각 리스크가 현실화될 가능성을 평가하시오.

**5. 밸류에이션 (Valuation):**
   - **찬성론 (Bull Case):** 현재 주가가 왜 여전히 매력적인 진입점이라고 할 수 있는가?
   - **반대론 (Bear Case):** 현재 주가가 왜 이미 고평가되었거나 '밸류에이션 함정'일 수 있는가?

**6. 최종 의사결정을 위한 핵심 질문 (Key Questions for Decision):**
   - **지시사항:** 위 모든 찬반 분석을 종합하여, 내가 최종적으로 투자를 '결정'하기 위해 스스로에게 던져야 할 가장 중요한 질문 3가지를 제시해주시오.

**7. 투자 노트 DB 생성을 위한 요약 (For DB Sync):**
   - **지시사항:** 위 분석을 종합하여, 내가 이 종목에 대한 '투자 노트'를 새로 작성할 수 있도록 아래 형식에 맞춰 핵심 내용을 요약해주십시오.
   - **투자 아이디어 (Thesis):** [가장 핵심적인 투자 찬성 논리를 1~2줄로 요약]
   - **핵심 촉매 (Catalysts):** [가장 중요한 긍정적 이벤트 3가지]
   - **핵심 리스크 (Risks):** [가장 중요한 부정적 위험 요인 3가지]
   - **핵심 모니터링 지표 (KPIs):** [이 투자의 성패를 가늠할 가장 중요한 데이터 지표 3가지]
"""
    
    def generate_deep_dive_prompt(self, stock_name: str) -> tuple[str, bool]:
        """
        종목명을 받아 투자 노트 정보 유무에 따라 적절한 프롬프트를 생성합니다.
        
        Args:
            stock_name (str): 분석할 종목명 또는 코드
            
        Returns:
            tuple[str, bool]: (생성된 프롬프트, 투자 노트에서 정보를 찾았는지 여부)
        """
        sanitized_stock_name = stock_name.strip()
        
        # 투자 노트에서 해당 종목 정보 검색
        stock_note = self.find_stock_note(sanitized_stock_name)
        
        # 노트 유무에 따라 다른 프롬프트 생성
        if not stock_note.empty:
            final_prompt = self.generate_contextual_deep_dive_prompt(sanitized_stock_name, stock_note)
            return final_prompt, True
        else:
            final_prompt = self.generate_generic_deep_dive_prompt(sanitized_stock_name)
            return final_prompt, False


def main():
    """테스트용 메인 함수"""
    print("🧪 종목 상세 분석기 테스트")
    print("=" * 50)
    
    # 환경변수 확인
    spreadsheet_id = os.getenv('GOOGLE_SPREADSHEET_ID')
    if not spreadsheet_id:
        print("⚠️ GOOGLE_SPREADSHEET_ID 환경변수가 설정되지 않았습니다.")
        print("📝 일반 분석 프롬프트만 테스트합니다.")
        generator = StockAnalyzerGenerator()
    else:
        print(f"✅ Google Spreadsheet ID: {spreadsheet_id}")
        generator = StockAnalyzerGenerator(spreadsheet_id)
    
    # 테스트 종목들
    test_stocks = ["엔비디아", "ASML", "005930", "삼성전자"]
    
    for stock in test_stocks:
        print(f"\n📊 {stock} 분석 프롬프트 생성 중...")
        prompt, found_in_db = generator.generate_deep_dive_prompt(stock)
        
        if found_in_db:
            print(f"✅ DB에서 정보 발견! 맞춤형 검증 프롬프트 생성 완료 (길이: {len(prompt)}자)")
        else:
            print(f"ℹ️ DB에 정보 없음. 표준 분석 프롬프트 생성 완료 (길이: {len(prompt)}자)")
        
        print(f"📝 프롬프트 미리보기:\n{prompt[:200]}...")
    
    print("\n✅ 테스트가 완료되었습니다!")


if __name__ == "__main__":
    main()
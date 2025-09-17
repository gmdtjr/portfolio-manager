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
        (투자 노트에 정보가 있을 때) 투자 노트를 '스트레스 테스트'하는 비판적 검증 프롬프트를 생성합니다.
        """
        thesis = stock_note.get('투자 아이디어 (Thesis)', '내용 없음')
        catalysts = stock_note.get('핵심 촉매 (Catalysts)', '내용 없음')
        risks = stock_note.get('핵심 리스크 (Risks)', '내용 없음')
        conviction = stock_note.get('투자 확신도 (Conviction)', '내용 없음')
        sector = stock_note.get('섹터/산업 (Sector/Industry)', '내용 없음')
        today = datetime.now().strftime('%Y년 %m월 %d일')

        return f"""# {stock_name} 투자 아이디어 스트레스 테스트 보고서 ({today})

## **[중요 지시사항]**
- **역할 부여:** 당신은 나의 투자 아이디어를 검증하는 **'악마의 변호인(Devil's Advocate)'**입니다. 나의 가설을 긍정하기보다는, **가장 강력한 반론과 비판적인 데이터**를 찾아 제시하는 것이 당신의 핵심 임무입니다.
- **언어:** 모든 결과물은 반드시 **한글**로만 작성해주세요.

## **분석 목표:**
아래 제시된 **[나의 기존 투자 노트]**의 각 항목에 대해, 최신 시장 정보를 바탕으로 **가장 강력한 반론(Counter-Argument)을 제기**하고, 나의 투자 아이디어가 가진 잠재적 맹점을 파헤쳐 **스트레스 테스트(Stress Test)**를 수행하시오.

## **[나의 기존 투자 노트]**
- **섹터/산업:** {sector}
- **나의 투자 아이디어:** {thesis}
- **내가 기대하는 핵심 촉매:** {catalysts}
- **내가 우려하는 핵심 리스크:** {risks}
- **나의 투자 확신도:** {conviction}

---
## **분석 및 검증 목차:**
*아래 목차에 따라, 나의 투자 노트 각 항목을 비판적으로 검증해주십시오.*

**1. 투자 아이디어에 대한 반론 (Counter-Thesis):**
   - 나의 핵심 투자 아이디어를 반박할 수 있는 가장 강력한 논리는 무엇인가?
   - 시장이 나의 생각과 다르게 움직일 수 있는 가장 큰 이유는 무엇인가?

**2. 경제적 해자의 취약점 (Moat Vulnerability):**
   - 내가 생각하는 이 기업의 경제적 해자가 실제로는 과대평가되었거나, 미래에 약화될 수 있는 가장 큰 이유는 무엇인가?

**3. 성장 동력의 이면 (Growth Headwinds):**
   - 내가 '핵심 촉매'로 기대하는 것들이 실현되지 않을 가능성은 없는가?
   - 겉으로 보이는 성장 동력 이면에 숨겨진, 성장을 저해할 수 있는 가장 큰 역풍(Headwind)은 무엇인가?

**4. 숨겨진 리스크 (Hidden Risks):**
   - 내가 '핵심 리스크'로 인지하고 있는 것 외에, 내가 미처 파악하지 못했을 가능성이 있는 **'알려지지 않은 리스크(Unknown Unknowns)'**는 무엇인가?

**5. 밸류에이션 함정 (Valuation Trap):**
   - 현재 밸류에이션이 합리적으로 보이지만, 실제로는 성장에 대한 과도한 기대로 인한 **'밸류에이션 함정'**일 가능성은 없는가?

**6. 종합 결론 (Stress Test Result):**
   - 위 스트레스 테스트 결과를 종합했을 때, 나의 투자 아이디어가 여전히 방어 가능한가?
   - 나의 '투자 확신도({conviction})'를 **하향 조정**해야 한다면, 그 이유는 무엇인가?

**7. 투자 노트 DB 동기화를 위한 요약 (For DB Sync):**
   - **지시사항:** 위 비판적 분석을 종합하여, 나의 '투자 노트' DB를 업데이트할 수 있도록 **균형 잡힌 시각**으로 아래 내용을 요약해주십시오.
   - **투자 아이디어 (Thesis):** [기존 아이디어를 유지/수정/폐기해야 하는 최종 결론 요약]
   - **핵심 촉매 (Catalysts):** [가장 실현 가능성이 높은 긍정적 이벤트 3가지]
   - **핵심 리스크 (Risks):** [분석을 통해 새롭게 부각된 가장 중요한 위험 요인 3가지]
   - **핵심 모니터링 지표 (KPIs):** [나의 가설이 틀렸음을 감지할 수 있는 가장 중요한 '경고 지표' 3가지]
"""

    def generate_generic_deep_dive_prompt(self, stock_name: str) -> str:
        """
        (투자 노트에 정보가 없을 때) 'Bull vs. Bear' 관점의 균형 잡힌 분석 프롬프트를 생성합니다.
        """
        today = datetime.now().strftime('%Y년 %m월 %d일')

        return f"""# {stock_name} 균형 분석 보고서 (Bull vs. Bear) ({today})

## **[중요 지시사항]**
- **역할 부여:** 당신은 특정 종목에 대해 **낙관론(Bull Case)과 비관론(Bear Case)을 모두 제시**하는 객관적이고 균형 잡힌 시각의 애널리스트입니다.
- **언어:** 모든 결과물은 반드시 **한글**로만 작성해주세요.

## **분석 목표:**
{stock_name}에 대한 종합적인 분석을 통해, 이 기업에 대한 **가장 강력한 투자 찬성 논거(Bull Case)**와 **가장 강력한 투자 반대 논거(Bear Case)**를 모두 제시하고, 최종적으로 투자 매력도를 평가하시오.

## **분석 목차:**
*아래 목차 순서와 항목을 반드시 준수하여, 모든 항목에 대해 찬성/반대 논리를 함께 분석해주십시오.*

**1. 핵심 투자 논쟁 (The Key Debate):**
   - 현재 시장에서 {stock_name}을 둘러싼 가장 큰 의견 대립은 무엇인가?

**2. 경제적 해자 (Economic Moat):**
   - **Bull Case:** 이 기업의 해자가 왜 강력하고 지속 가능한가?
   - **Bear Case:** 이 해자가 보기보다 약하거나 미래에 훼손될 수 있는 이유는 무엇인가?

**3. 성장 동력 (Growth Drivers):**
   - **Bull Case:** 향후 성장을 이끌 명확하고 강력한 촉매는 무엇인가?
   - **Bear Case:** 이 성장 스토리가 실현되지 않을 수 있는 가장 큰 장애물은 무엇인가?

**4. 핵심 리스크 (Key Risks):**
   - 투자자들이 가장 주목해야 할 핵심 리스크 요인들을 분석하고, 각 리스크가 현실화될 가능성을 평가하시오.

**5. 밸류에이션 (Valuation):**
   - **Bull Case:** 현재 주가가 왜 여전히 매력적인 진입점이라고 할 수 있는가?
   - **Bear Case:** 현재 주가가 왜 이미 고평가되었거나 '밸류에이션 함정'일 수 있는가?

**6. 종합 결론 및 투자의견:**
   - 위 모든 찬반 논쟁을 종합했을 때, 어느 쪽의 논리가 더 설득력 있는가?
   - 최종적으로, 위험 대비 기대수익률 관점에서 이 종목에 대한 투자의견(예: 긍정적/중립적/부정적)과 그 핵심 근거를 제시하시오.

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
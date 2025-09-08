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
    """종목 상세 분석 프롬프트 생성기 (DB 연동)"""
    
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
        (DB에 정보가 있을 때) 투자 노트를 기반으로 한 맞춤형 검증 프롬프트를 생성합니다.
        
        Args:
            stock_name (str): 종목명
            stock_note (pd.Series): 투자 노트 정보
            
        Returns:
            str: 생성된 맞춤형 프롬프트
        """
        thesis = stock_note.get('투자 아이디어 (Thesis)', '내용 없음')
        catalysts = stock_note.get('핵심 촉매 (Catalysts)', '내용 없음')
        risks = stock_note.get('핵심 리스크 (Risks)', '내용 없음')
        conviction = stock_note.get('투자 확신도 (Conviction)', '내용 없음')
        sector = stock_note.get('섹터/산업 (Sector/Industry)', '내용 없음')
        
        today = datetime.now().strftime('%Y년 %m월 %d일')
        
        return f"""# {stock_name} 투자 아이디어 심층 검증 보고서 ({today})

## **[중요 지시사항]**
- **모든 결과물은 반드시 한글로만 작성해주세요.**
- 영문 용어는 필요한 경우에만 괄호 안에 병기하고, 그 외 모든 서술은 한글로 해야 합니다.

## **분석 목표:**
아래 제시된 나의 기존 투자 노트를 바탕으로, 최신 시장 정보와 데이터를 활용하여 나의 투자 아이디어가 여전히 유효한지 **검증(Validation)**하고, 종합적인 투자 매력도를 재평가하시오.

## **[나의 기존 투자 노트]**
- **섹터/산업:** {sector}
- **나의 투자 아이디어:** {thesis}
- **내가 기대하는 핵심 촉매:** {catalysts}
- **내가 우려하는 핵심 리스크:** {risks}
- **나의 투자 확신도:** {conviction}

## **핵심 검증 항목:**
*아래 3가지 관점을 중심으로 나의 기존 투자 노트를 심층적으로 검증해주십시오.*

**1. 투자 아이디어의 현실성 검증:**
   - 나의 핵심 투자 아이디어가 현재 시장 상황, 경쟁 구도, 기술 트렌드에 비추어볼 때 여전히 타당한가?
   - 나의 가설을 반박할 수 있는 새로운 데이터나 이벤트는 없었는가?
   - 내가 놓친 중요한 시장 변화나 경쟁사 동향은 없는가?

**2. 촉매 및 리스크 발생 현황 분석:**
   - 내가 기대했던 '핵심 촉매'들이 실제로 발생할 조짐이 보이는가? 아니면 지연되거나 무산될 가능성이 있는가?
   - 내가 우려했던 '핵심 리스크'들이 현실화되고 있는가? 혹은 내가 미처 파악하지 못했던 새로운 리스크는 없는가?
   - 최근 6개월간 해당 섹터에서 발생한 주요 이벤트들이 내 투자 논리에 어떤 영향을 미치는가?

**3. 종합 재평가 및 결론:**
   - 위 검증 내용을 바탕으로, {stock_name}에 대한 나의 기존 투자 아이디어를 계속 유지해야 하는가, 수정해야 하는가, 아니면 폐기해야 하는가?
   - 내가 설정한 투자 확신도({conviction})가 여전히 적절한가? 아니면 조정이 필요한가?
   - 최종적으로, 지금 시점에서 이 종목에 대한 투자 매력도를 A(매우 높음) ~ D(매우 낮음) 등급으로 평가하고 그 이유를 제시하시오.
   - 구체적인 액션 아이템(매수/보유/매도, 비중 조절 등)을 제안해주세요.
"""
    
    def generate_generic_deep_dive_prompt(self, stock_name: str) -> str:
        """
        (DB에 정보가 없을 때) 일반적인 종목 분석 프롬프트를 생성합니다.
        
        Args:
            stock_name (str): 종목명
            
        Returns:
            str: 생성된 일반 분석 프롬프트
        """
        today = datetime.now().strftime('%Y년 %m월 %d일')
        
        return f"""# {stock_name} 기업 심층 분석 보고서 ({today})

## **[중요 지시사항]**
- **모든 결과물은 반드시 한글로만 작성해주세요.**
- 영문 용어는 필요한 경우에만 괄호 안에 병기하고, 그 외 모든 서술은 한글로 해야 합니다.

## **분석 목표:**
{stock_name}에 대한 종합적인 분석을 통해, 이 기업의 장기 투자 매력도를 평가하고 핵심 투자 포인트를 도출하시오.

## **분석 목차:**
*아래 목차 순서와 항목을 반드시 준수하여 보고서를 작성해주십시오.*

**1. 기업 개요 (Business Overview):**
   - 주요 비즈니스 모델과 핵심 제품/서비스의 역할은 무엇인가?
   - 전체 매출에서 각 사업 부문이 차지하는 비중은 어떻게 되는가?

**2. 산업 분석 (Industry Analysis):**
   - {stock_name}이 속한 산업의 구조와 전반적인 성장 전망은 어떠한가?
   - 주요 경쟁사는 누구이며, 경쟁 환경은 어떠한가?

**3. 경제적 해자 (Economic Moat):**
   - {stock_name}이 가진 가장 강력한 경쟁 우위는 무엇인가? (예: 독점적 기술력, 브랜드 가치, 네트워크 효과, 높은 전환 비용 등)
   - 이 해자는 얼마나 오랫동안 지속 가능할 것으로 보는가?

**4. 성장 동력 (Growth Drivers):**
   - 향후 3~5년간 {stock_name}의 성장을 이끌 핵심 동력은 무엇인가?
   - AI, 클라우드 컴퓨팅, 인구 변화 등 거시적 트렌드가 이 기업에 미치는 긍정적 영향은 무엇인가?

**5. 핵심 리스크 (Key Risks):**
   - {stock_name}의 투자 아이디어를 훼손할 수 있는 가장 큰 내부/외부 리스크는 무엇인가? (최소 3가지 이상)
   - (예: 지정학적 리스크, 기술 변화 리스크, 규제 리스크, 경기 순환 리스크 등)

**6. 재무 분석 (Financial Analysis):**
   - 최근 3년간의 핵심 재무 지표(매출, 영업이익률, 순이익, 현금 흐름)를 분석하고, 재무 건전성을 평가하시오.

**7. 밸류에이션 (Valuation):**
   - 동종 업계 경쟁사(Peer Group)와 비교했을 때, 현재 {stock_name}의 주가 수준은 고평가인가, 저평가인가?
   - (PER, PBR, EV/EBITDA 등 다양한 지표를 활용하여 분석)

**8. 종합 결론 및 투자의견:**
   - 위 모든 분석을 종합하여, {stock_name}에 대한 최종 투자의견(예: 매수/보유/매도)과 그 핵심 근거를 제시하시오.
"""
    
    def generate_deep_dive_prompt(self, stock_name: str) -> tuple[str, bool]:
        """
        종목명을 받아 DB 정보 유무에 따라 적절한 프롬프트를 생성합니다.
        
        Args:
            stock_name (str): 분석할 종목명 또는 코드
            
        Returns:
            tuple[str, bool]: (생성된 프롬프트, DB에서 정보를 찾았는지 여부)
        """
        sanitized_stock_name = stock_name.strip()
        
        # DB에서 해당 종목 노트 검색
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
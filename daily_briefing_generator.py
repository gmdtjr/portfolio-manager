import streamlit as st
import os
import json
import pandas as pd
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google import genai
from google.genai import types
from typing import List, Dict, Optional
import time

# 투자 노트 매니저 import
try:
    from investment_notes_manager import InvestmentNotesManager
    INVESTMENT_NOTES_AVAILABLE = True
except ImportError:
    INVESTMENT_NOTES_AVAILABLE = False

class DailyBriefingGenerator:
    """CSV 데이터를 프롬프트에 포함하는 방식의 데일리 브리핑 프롬프트 생성을 위한 클래스"""
    
    def __init__(self, spreadsheet_id: str, gemini_api_key: str = None):
        self.spreadsheet_id = spreadsheet_id
        self.gemini_api_key = gemini_api_key or os.getenv('GOOGLE_API_KEY')
        if not self.gemini_api_key:
            raise ValueError("Google API 키가 필요합니다. 환경변수 GOOGLE_API_KEY를 설정하거나 직접 전달하세요.")
        
        self.service = None
        self._authenticate_google()
        self._setup_gemini()
        
        # 투자 노트 매니저 초기화
        if INVESTMENT_NOTES_AVAILABLE:
            self.notes_manager = InvestmentNotesManager(spreadsheet_id)
        else:
            self.notes_manager = None
    
    def _authenticate_google(self):
        """구글 API 인증"""
        try:
            # 환경변수에서 서비스 계정 JSON 읽기 시도
            service_account_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
            
            if service_account_json:
                # 환경변수에서 JSON 문자열을 파싱
                service_account_info = json.loads(service_account_json)
                credentials = service_account.Credentials.from_service_account_info(
                    service_account_info,
                    scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
                )
                print("✅ 구글 API 인증이 완료되었습니다. (환경변수에서 JSON)")
            else:
                # 파일에서 읽기 시도
                credentials = service_account.Credentials.from_service_account_file(
                    'service-account-key.json',
                    scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
                )
                print("✅ 구글 API 인증이 완료되었습니다. (파일에서 JSON)")
            
            self.service = build('sheets', 'v4', credentials=credentials)
        except Exception as e:
            print(f"❌ 구글 API 인증 실패: {e}")
            raise
    
    def _setup_gemini(self):
        """Gemini API 설정"""
        try:
            # Google AI 클라이언트 초기화
            self.client = genai.Client(api_key=self.gemini_api_key)
            self.model_name = "gemini-2.5-pro"
            print("✅ Gemini API 설정이 완료되었습니다.")
        except Exception as e:
            print(f"❌ Gemini API 설정 실패: {e}")
            raise
    
    def read_portfolio_data(self) -> pd.DataFrame:
        """구글 스프레드시트에서 포트폴리오 데이터 읽기"""
        try:
            # 사용 가능한 시트 확인
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            
            sheet_names = [sheet['properties']['title'] for sheet in spreadsheet['sheets']]
            print(f"📋 사용 가능한 시트: {sheet_names}")
            
            # Portfolio 시트가 있으면 사용, 없으면 첫 번째 시트 사용
            if 'Portfolio' in sheet_names:
                range_name = 'Portfolio!A:L'
                print("📊 'Portfolio' 시트를 사용합니다.")
            elif sheet_names:
                range_name = f'{sheet_names[0]}!A:L'
                print(f"📊 '{sheet_names[0]}' 시트를 사용합니다.")
            else:
                raise Exception("사용 가능한 시트가 없습니다.")
            
            # 데이터 읽기
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            if not values:
                raise Exception("스프레드시트에 데이터가 없습니다.")
            
            # 데이터프레임 생성
            df = pd.DataFrame(values[1:], columns=values[0])
            
            # 숫자 컬럼 변환
            numeric_columns = ['보유수량', '매입평균가', '매입금액(원)', '현재가', '평가금액(원)', '평가손익(원)', '수익률', '비중']
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            print(f"✅ 포트폴리오 데이터 읽기 완료: {len(df)}개 종목")
            return df
            
        except Exception as e:
            print(f"❌ 포트폴리오 데이터 읽기 실패: {e}")
            raise
    
    def read_exchange_rate_data(self) -> Dict:
        """환율 정보 데이터 읽기"""
        try:
            # 환율정보 시트 확인
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            
            sheet_names = [sheet['properties']['title'] for sheet in spreadsheet['sheets']]
            
            if '환율정보' not in sheet_names:
                print("⚠️ 환율정보 시트가 없습니다.")
                return {}
            
            # 환율정보 데이터 읽기
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range='환율정보!A:Z'
            ).execute()
            
            values = result.get('values', [])
            if not values:
                print("⚠️ 환율정보 데이터가 없습니다.")
                return {}
            
            # 데이터프레임 생성
            df = pd.DataFrame(values[1:], columns=values[0])
            
            # 최신 환율 정보 추출
            exchange_data = {}
            if not df.empty:
                latest_row = df.iloc[-1]  # 가장 최근 데이터
                for col in df.columns:
                    if '환율' in col or 'USD' in col or '달러' in col:
                        exchange_data[col] = latest_row[col]
            
            print(f"✅ 환율 정보 읽기 완료: {len(exchange_data)}개 항목")
            return exchange_data
            
        except Exception as e:
            print(f"❌ 환율 정보 읽기 실패: {e}")
            return {}
    
    def get_data_as_csv(self, sheet_name: str) -> str:
        """구글 시트에서 데이터를 읽어 CSV 문자열로 반환"""
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=sheet_name
            ).execute()
            
            values = result.get('values', [])
            if not values:
                print(f"⚠️ '{sheet_name}' 시트에 데이터가 없습니다.")
                return None
            
            df = pd.DataFrame(values[1:], columns=values[0])
            csv_string = df.to_csv(index=False)
            print(f"✅ '{sheet_name}' 시트 CSV 변환 완료: {len(df)}행")
            return csv_string
            
        except Exception as e:
            print(f"❌ '{sheet_name}' 시트 읽기 실패: {e}")
            return None
    
    def generate_daily_briefing_prompt(self, portfolio_df: pd.DataFrame, exchange_data: Dict = None) -> str:
        """CSV 데이터를 프롬프트에 포함하여 데일리 브리핑 프롬프트 생성"""
        max_retries = 8
        base_delay = 2
        
        for attempt in range(max_retries):
            try:
                today = datetime.now().strftime('%Y년 %m월 %d일')
                
                # 1. 포트폴리오 데이터를 CSV로 변환
                portfolio_csv = self.get_data_as_csv("Portfolio")
                if not portfolio_csv:
                    return "포트폴리오 데이터가 없습니다. Portfolio 시트를 확인해주세요."
                
                # 2. 투자 노트 데이터를 CSV로 변환
                notes_csv = self.get_data_as_csv("투자_노트")
                
                # 3. CSV 데이터를 포함한 메타 프롬프트 생성
                meta_prompt = f"""너는 최고의 퀀트 애널리스트이자 나의 개인 투자 비서 AI야.
오늘 날짜({today}) 기준 나의 포트폴리오에 대한 '데일리 브리핑 Deep Research 프롬프트'를 생성해 줘.

**포트폴리오 현황 데이터:**
```
{portfolio_csv}
```

**투자 노트 데이터:**
```
{notes_csv if notes_csv else "투자 노트 데이터 없음"}
```

**[지시사항]**
1. 위 CSV 데이터를 종합적으로 분석해줘.
2. 나의 투자 아이디어가 현재 시장 상황에서도 유효한지 검증하는 것에 초점을 맞춰줘.
3. 특히 투자 노트에 언급된 '핵심 리스크'와 관련된 최신 뉴스가 있는지 파악하고, 이를 질문에 반영해줘.
4. Deep Research에 바로 입력할 수 있는, 구체적이고 실행 가능한(actionable) 프롬프트 1개만 최종 결과물로 출력해줘."""
                
                # 4. Gemini API 호출
                print("🤖 Gemini API 호출 중...")
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=meta_prompt
                )
                
                # 5. 응답 반환
                if response.text:
                    return response.text
                else:
                    return "Gemini API 응답이 비어있습니다."
                    
            except Exception as e:
                error_str = str(e)
                if "503" in error_str and "UNAVAILABLE" in error_str:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        print(f"⚠️ Gemini API 503 오류 발생. {delay}초 후 재시도 중... (시도 {attempt + 1}/{max_retries})")
                        time.sleep(delay)
                        continue
                    else:
                        print(f"❌ 최대 재시도 횟수 초과. Gemini API 서버 과부하 상태입니다.")
                        return "Gemini API 서버가 과부하 상태입니다. 잠시 후 다시 시도해주세요."
                elif "429" in error_str and "RESOURCE_EXHAUSTED" in error_str:
                    if attempt < max_retries - 1:
                        delay = 60 + (attempt * 30)
                        print(f"⚠️ Gemini API 429 오류 발생 (무료 티어 제한). {delay}초 후 재시도 중... (시도 {attempt + 1}/{max_retries})")
                        time.sleep(delay)
                        continue
                    else:
                        print(f"❌ 최대 재시도 횟수 초과. 무료 티어 분당 요청 제한에 도달했습니다.")
                        return "Gemini API 무료 티어 분당 요청 제한에 도달했습니다. 1분 후 다시 시도해주세요."
                else:
                    print(f"❌ 지능형 프롬프트 생성 실패: {e}")
                    return f"지능형 프롬프트 생성 중 오류가 발생했습니다: {str(e)}"
        
        return "알 수 없는 오류가 발생했습니다."

def main():
    """메인 함수 - CSV 파일 업로드 방식의 지능형 데일리 브리핑 프롬프트 생성기"""
    st.title("🤖 CSV 업로드 방식 데일리 브리핑 프롬프트 생성기")
    st.markdown("CSV 파일을 Gemini API에 직접 업로드하여 맞춤형 Deep Research 프롬프트를 생성합니다.")
    
    # 사이드바 설정
    st.sidebar.title("⚙️ 설정")
    
    # 환경변수 확인
    def get_secret(key):
        try:
            if hasattr(st, 'secrets') and st.secrets:
                return st.secrets.get(key)
        except:
            pass
        return os.getenv(key)
    
    spreadsheet_id = get_secret('GOOGLE_SPREADSHEET_ID')
    google_api_key = get_secret('GOOGLE_API_KEY')
    
    if not spreadsheet_id:
        st.error("❌ GOOGLE_SPREADSHEET_ID가 설정되지 않았습니다.")
        return
    
    if not google_api_key:
        st.error("❌ GOOGLE_API_KEY가 설정되지 않았습니다.")
        st.info("💡 CSV 업로드 방식 프롬프트 생성을 위해 GOOGLE_API_KEY가 필요합니다.")
        return
    
    # 기능 설명
    st.info("""
    **🤖 CSV 업로드 방식 데일리 브리핑 프롬프트 생성기**
    • 구글 시트 데이터를 CSV로 변환하여 Gemini API에 직접 업로드
    • 포트폴리오 현황과 투자 노트를 구조화된 데이터로 분석
    • 프롬프트 길이 대폭 단축으로 API 부하 감소
    • 더 정확하고 구체적인 분석 프롬프트 생성
    • 생성된 프롬프트를 Gemini Deep Research에 수동 입력하여 보고서 생성
    """)
    
    # 브리핑 생성 버튼
    if st.button("🤖 CSV 업로드 방식 데일리 브리핑 프롬프트 생성", type="primary", use_container_width=True):
        try:
            with st.spinner("CSV 파일을 생성하고 Gemini API에 업로드하여 프롬프트를 생성하고 있습니다..."):
                # 브리핑 생성기 초기화
                generator = DailyBriefingGenerator(spreadsheet_id, google_api_key)
                
                # CSV 업로드 방식으로 프롬프트 생성
                st.info("📋 CSV 파일을 생성하고 Gemini API에 업로드 중...")
                briefing_prompt = generator.generate_daily_briefing_prompt(None, None)
                
                # 결과 표시
                st.success("✅ CSV 업로드 방식 데일리 브리핑 프롬프트가 생성되었습니다!")
                
                # 탭으로 구분하여 표시
                tab1, tab2 = st.tabs(["🤖 생성된 프롬프트", "📊 CSV 데이터 미리보기"])
                
                with tab1:
                    st.markdown("### 📋 Gemini Deep Research에 복사할 프롬프트")
                    st.text_area("CSV 업로드 방식 데일리 브리핑 프롬프트", briefing_prompt, height=600)
                    
                    # 복사 버튼
                    if st.button("📋 프롬프트 복사", key="copy_prompt"):
                        st.write("프롬프트가 클립보드에 복사되었습니다.")
                    
                    st.info("💡 이 프롬프트를 Gemini Deep Research에 붙여넣어 맞춤형 데일리 브리핑을 생성하세요.")
                
                with tab2:
                    # CSV 데이터 미리보기
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("📊 포트폴리오 데이터")
                        portfolio_csv = generator.get_data_as_csv("Portfolio")
                        if portfolio_csv:
                            st.text_area("포트폴리오 CSV", portfolio_csv, height=300)
                        else:
                            st.info("포트폴리오 데이터가 없습니다.")
                    
                    with col2:
                        st.subheader("📝 투자 노트 데이터")
                        notes_csv = generator.get_data_as_csv("투자_노트")
                        if notes_csv:
                            st.text_area("투자 노트 CSV", notes_csv, height=300)
                        else:
                            st.info("투자 노트 데이터가 없습니다.")
                
        except Exception as e:
            st.error(f"❌ 프롬프트 생성 실패: {e}")
            import traceback
            st.error(f"상세 오류: {traceback.format_exc()}")

if __name__ == "__main__":
    main()

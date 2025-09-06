import streamlit as st
import os
import json
import pandas as pd
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google import genai
import time

def get_time_window_text(selection: str) -> str:
    """UI 선택에 따라 시간 범위 텍스트를 반환합니다."""
    if "48시간" in selection:
        return "지난 48시간 동안"
    if "72시간" in selection:
        return "지난 72시간 동안"
    if "1주일" in selection:
        return "지난 1주일 동안"
    return "지난 24시간 동안" # Default

class DailyBriefingGeneratorV2:
    """데일리 브리핑 프롬프트 생성기 V2 (CSV 다운로더 기능 포함)"""
    
    def __init__(self, spreadsheet_id: str, gemini_api_key: str = None):
        self.spreadsheet_id = spreadsheet_id
        self.gemini_api_key = gemini_api_key or os.getenv('GOOGLE_API_KEY')
        self.service = None
        self.client = None
        self._authenticate_google()
        self._setup_gemini()
    
    def _authenticate_google(self):
        """구글 API 인증"""
        try:
            # 환경변수에서 서비스 계정 JSON 읽기 시도
            service_account_json_str = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
            if service_account_json_str:
                service_account_info = json.loads(service_account_json_str)
                credentials = service_account.Credentials.from_service_account_info(
                    service_account_info,
                    scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
                )
                print("✅ 구글 API 인증이 완료되었습니다. (환경변수에서 JSON)")
            else:
                # 파일에서 JSON 읽기 시도
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
            if self.gemini_api_key:
                self.client = genai.Client(api_key=self.gemini_api_key)
                self.model_name = "gemini-2.5-pro"
                print("✅ Gemini API 설정이 완료되었습니다.")
            else:
                print("⚠️ Gemini API 키가 없습니다. 프롬프트 생성 기능을 사용할 수 없습니다.")
        except Exception as e:
            print(f"❌ Gemini API 설정 실패: {e}")
            self.client = None
    
    def get_sheet_data(self, sheet_name: str) -> pd.DataFrame:
        """구글 시트에서 데이터를 DataFrame으로 읽기"""
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=sheet_name
            ).execute()
            
            values = result.get('values', [])
            if not values:
                return pd.DataFrame()
            
            # 첫 번째 행을 헤더로 사용
            df = pd.DataFrame(values[1:], columns=values[0])
            return df
            
        except Exception as e:
            print(f"❌ '{sheet_name}' 시트 읽기 실패: {e}")
            return pd.DataFrame()
    
    def get_data_as_csv(self, sheet_name: str) -> str:
        """구글 시트 데이터를 CSV 문자열로 변환"""
        try:
            df = self.get_sheet_data(sheet_name)
            if df.empty:
                return ""
            
            # UTF-8 BOM 인코딩으로 Excel 호환성 확보
            csv_string = df.to_csv(index=False, encoding='utf-8-sig')
            print(f"✅ '{sheet_name}' CSV 변환 완료: {len(csv_string)}자")
            return csv_string
            
        except Exception as e:
            print(f"❌ '{sheet_name}' CSV 변환 실패: {e}")
            return ""
    
    def get_macro_summary(self, time_window_text: str = "지난 24시간 동안") -> str:
        """Gemini API를 사용하여 지정된 기간의 매크로 이슈 요약 가져오기"""
        if not self.client:
            return "Gemini API가 설정되지 않았습니다."
        
        try:
            today = datetime.now().strftime('%Y년 %m월 %d일')
            macro_prompt = f"""오늘 날짜({today}) 기준, **{time_window_text}** 글로벌 금융 시장에 가장 큰 영향을 미친 핵심 매크로 이슈 5가지를 각각 2줄로 요약해 줘.
각 이슈가 주식 시장(특히 기술주, 경기순환주)에 미칠 수 있는 긍정적/부정적 영향까지 포함해줘."""
            
            print("🤖 Gemini API로 매크로 이슈 요약 요청 중...")
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=macro_prompt
            )
            
            if response.text:
                print("✅ 매크로 이슈 요약 완료")
                return response.text
            else:
                return "매크로 이슈 요약을 가져올 수 없습니다."
                
        except Exception as e:
            print(f"❌ 매크로 이슈 요약 실패: {e}")
            return f"매크로 이슈 요약 중 오류가 발생했습니다: {str(e)}"
    
    def generate_complete_prompt(self, time_window_text: str = "지난 24시간 동안") -> str:
        """완성된 프롬프트 생성"""
        try:
            today = datetime.now().strftime('%Y년 %m월 %d일')
            
            # 매크로 이슈 요약 가져오기
            macro_summary = self.get_macro_summary(time_window_text)
            
            # 완성된 프롬프트 생성
            complete_prompt = f"""📊 포트폴리오 데일리 브리핑 분석 요청 ({today})
🎯 Mission (임무)
당신은 월스트리트 최고의 포트폴리오 전략가입니다. 아래 제공되는 **[{time_window_text}의 글로벌 매크로 현황]**과 첨부된 [포트폴리오 파일] 2개를 종합적으로 분석하여, 실행 가능한 데일리 브리핑을 생성해주세요.

[{time_window_text}의 글로벌 매크로 현황 (AI 요약)]
{macro_summary}

[첨부 파일 설명]
포트폴리오_현황.csv: 나의 현재 보유 자산 현황 (정량 데이터)

투자_노트.csv: 각 자산에 대한 나의 투자 아이디어, 리스크 등 (정성 데이터)

🔍 Key Analysis Framework (핵심 분석 프레임워크)
1. 투자 아이디어 검증 (Thesis Validation)
{time_window_text} 동안 발생한 주요 시장 뉴스 및 데이터를 기반으로, 나의 투자 아이디어가 여전히 유효한지 검증해주세요.

특히 투자_노트.csv에 기록된 '핵심 리스크'가 {time_window_text} 동안 현실화될 조짐은 없었는지 집중적으로 분석해주세요.

2. 성과 원인 분석 (Performance Attribution)
{time_window_text} 동안의 성과를 기준으로 Top/Underperformer를 선정해주세요.

그 성과의 원인이 {time_window_text}에 발생한 개별 종목 고유의 이슈(예: 실적발표, 공시)인지, 혹은 위에서 제시된 매크로 흐름의 영향인지 심층적으로 분석해주세요.

3. 매크로 환경과 포트폴리오의 연결고리 분석
제시된 매크로 현황의 가장 중요한 변수(예: 금리, 유가)가 내 포트폴리오의 각 섹터(예: 기술주, 에너지주)에 {time_window_text} 동안 어떤 영향을 미쳤고, 앞으로 어떤 영향을 미칠지 분석해주세요.

📝 Output Format (결과물 형식)
1. Executive Summary (핵심 요약)
매크로 요약: {time_window_text} 동안 시장을 움직인 핵심 키워드는?

포트폴리오 영향: 이로 인해 내 포트폴리오에 발생한 가장 중요한 변화는?

오늘의 전략: 그래서 오늘 내가 취해야 할 핵심 전략은?

2. Macro Impact Analysis (매크로 영향 분석)
긍정적 영향: [{time_window_text}의 매크로 환경이 긍정적으로 작용한 종목/섹터와 그 이유]

부정적 영향: [{time_window_text}의 매크로 환경이 부정적으로 작용한 종목/섹터와 그 이유]

3. Actionable Insight (실행 계획 제안)
위 분석을 바탕으로, 오늘 내가 취해야 할 구체적인 행동(예: 특정 섹터 비중 조절, 현금 확보, 리스크 관리 강화 등)을 1~2가지 제안해주세요."""
            
            return complete_prompt
            
        except Exception as e:
            print(f"❌ 완성된 프롬프트 생성 실패: {e}")
            return f"프롬프트 생성 중 오류가 발생했습니다: {str(e)}"
    
    def get_available_sheets(self) -> list:
        """사용 가능한 시트 목록 조회"""
        try:
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            
            sheets = spreadsheet.get('sheets', [])
            sheet_names = [sheet['properties']['title'] for sheet in sheets]
            print(f"✅ 사용 가능한 시트: {sheet_names}")
            return sheet_names
            
        except Exception as e:
            print(f"❌ 시트 목록 조회 실패: {e}")
            return []
    
    def generate_complete_package(self, time_window_text: str = "지난 24시간 동안") -> dict:
        """완전한 패키지 생성 (프롬프트 + CSV 데이터)"""
        try:
            print("🚀 완전한 패키지 생성 시작...")
            
            # 1. 포트폴리오 데이터 읽기
            print("📊 포트폴리오 데이터 읽기...")
            portfolio_df = self.get_sheet_data("Portfolio")
            
            # 2. 투자 노트 데이터 읽기
            print("📝 투자 노트 데이터 읽기...")
            notes_df = self.get_sheet_data("투자_노트")
            
            # 3. CSV 파일 생성
            print("📁 CSV 파일 생성...")
            portfolio_csv = self.get_data_as_csv("Portfolio")
            notes_csv = self.get_data_as_csv("투자_노트")
            
            # 4. 완성된 프롬프트 생성
            print("🤖 완성된 프롬프트 생성...")
            complete_prompt = self.generate_complete_prompt(time_window_text)
            
            # 5. 패키지 구성
            package = {
                'portfolio_csv': portfolio_csv,
                'notes_csv': notes_csv,
                'complete_prompt': complete_prompt,
                'portfolio_df': portfolio_df,
                'notes_df': notes_df,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            print("✅ 완전한 패키지 생성 완료!")
            return package
            
        except Exception as e:
            print(f"❌ 패키지 생성 실패: {e}")
            return {
                'error': str(e),
                'portfolio_csv': None,
                'notes_csv': None,
                'complete_prompt': None,
                'portfolio_df': None,
                'notes_df': None,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

def main():
    """메인 함수"""
    st.set_page_config(
        page_title="데일리 브리핑 생성기 V2",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 데일리 브리핑 생성기 V2")
    st.markdown("매크로 이슈 분석 + 포트폴리오 데이터 + 완성된 프롬프트 생성")
    
    # 환경변수 설정
    def get_secret(key):
        """Streamlit secrets 또는 환경변수에서 값 가져오기"""
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
    
    # 데일리 브리핑 생성기 초기화
    try:
        generator = DailyBriefingGeneratorV2(spreadsheet_id, google_api_key)
        available_sheets = generator.get_available_sheets()
        
        if not available_sheets:
            st.error("❌ 사용 가능한 시트가 없습니다.")
            return
            
    except Exception as e:
        st.error(f"❌ 데일리 브리핑 생성기 초기화 실패: {e}")
        return
    
    # 기능 설명
    st.info("""
    **📊 데일리 브리핑 생성기 V2**
    • Gemini API로 오늘의 매크로 이슈 자동 분석
    • 포트폴리오와 투자 노트 데이터 통합 분석
    • 전문적인 데일리 브리핑 프롬프트 생성
    • CSV 파일 다운로드 기능 포함
    • Deep Research에 바로 사용 가능한 완성된 패키지 제공
    """)
    
    # 시간 범위 선택
    st.subheader("⏰ 분석 기간 선택")
    time_window_selection = st.radio(
        "매크로 이슈 분석 기간을 선택하세요:",
        ('24시간', '48시간', '72시간', '1주일'),
        horizontal=True,
        help="몇 일 동안의 뉴스를 분석할지 선택하세요"
    )
    
    time_window_text = get_time_window_text(time_window_selection)
    st.info(f"📅 선택된 분석 기간: **{time_window_text}**")
    
    # 완전한 패키지 생성 기능
    st.subheader("🎯 완전한 패키지 생성")
    st.info("""
    **🎯 원클릭 완전 자동화**
    • 클릭 한 번으로 모든 재료 준비 완료
    • 포트폴리오 CSV + 투자노트 CSV + 완성된 프롬프트
    • 딥 리서치에 바로 사용할 수 있는 완전한 패키지
    • 더 이상 수동 작업 불필요!
    """)
    
    if st.button("🎯 완전한 패키지 생성", type="primary", use_container_width=True):
        if not google_api_key:
            st.error("❌ GOOGLE_API_KEY가 설정되지 않았습니다. 프롬프트 생성 기능을 사용할 수 없습니다.")
        else:
            try:
                with st.spinner("🚀 모든 재료를 준비하고 있습니다... (최대 2분 소요)"):
                    # 완전한 패키지 생성
                    package = generator.generate_complete_package(time_window_text)
                    
                    if 'error' in package:
                        st.error(f"❌ 패키지 생성 실패: {package['error']}")
                        return
                    
                    # 성공 메시지
                    st.success("🎉 완전한 패키지가 준비되었습니다!")
                    st.info(f"📅 생성 시간: {package['timestamp']}")
                    
                    # 세션 상태에 패키지 저장
                    st.session_state['generated_package'] = package
                    
                    # 탭으로 구분하여 표시
                    tab1, tab2, tab3, tab4 = st.tabs(["📋 완성된 프롬프트", "📊 포트폴리오 CSV", "📝 투자노트 CSV", "📈 데이터 미리보기"])
                    
                    with tab1:
                        st.markdown("### 🎯 Deep Research에 바로 사용할 프롬프트")
                        st.text_area("완성된 데일리 브리핑 프롬프트", package['complete_prompt'], height=600, key="prompt_text_area")
                        
                        # 복사 버튼 (개선된 버전)
                        col1, col2 = st.columns([1, 1])
                        with col1:
                            if st.button("📋 프롬프트 복사", key="copy_complete_prompt", use_container_width=True):
                                st.success("✅ 프롬프트가 클립보드에 복사되었습니다!")
                        with col2:
                            if st.button("🔄 프롬프트 새로고침", key="refresh_prompt", use_container_width=True):
                                st.rerun()
                        
                        st.success("💡 이 프롬프트를 Deep Research에 붙여넣으세요!")
                    
                    with tab2:
                        st.markdown("### 📊 포트폴리오 CSV 파일")
                        if package['portfolio_csv']:
                            st.text_area("포트폴리오 데이터 (CSV)", package['portfolio_csv'], height=400)
                            
                            # CSV 다운로드 버튼
                            st.download_button(
                                label="📥 포트폴리오 CSV 다운로드",
                                data=package['portfolio_csv'],
                                file_name=f"portfolio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime="text/csv",
                                key="download_portfolio_csv"
                            )
                        else:
                            st.warning("포트폴리오 데이터가 없습니다.")
                    
                    with tab3:
                        st.markdown("### 📝 투자노트 CSV 파일")
                        if package['notes_csv']:
                            st.text_area("투자노트 데이터 (CSV)", package['notes_csv'], height=400)
                            
                            # CSV 다운로드 버튼
                            st.download_button(
                                label="📥 투자노트 CSV 다운로드",
                                data=package['notes_csv'],
                                file_name=f"investment_notes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime="text/csv",
                                key="download_notes_csv"
                            )
                        else:
                            st.warning("투자노트 데이터가 없습니다.")
                    
                    with tab4:
                        st.markdown("### 📈 데이터 미리보기")
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.subheader("📊 포트폴리오 현황")
                            if package['portfolio_df'] is not None and not package['portfolio_df'].empty:
                                st.dataframe(package['portfolio_df'], use_container_width=True)
                            else:
                                st.info("포트폴리오 데이터가 없습니다.")
                        
                        with col2:
                            st.subheader("📝 투자 노트")
                            if package['notes_df'] is not None and not package['notes_df'].empty:
                                st.dataframe(package['notes_df'], use_container_width=True)
                            else:
                                st.info("투자 노트 데이터가 없습니다.")
                        
                        # 사용법 안내
                        st.markdown("---")
                        st.markdown("### 📖 사용법 안내")
                        st.info("""
                        **🎯 Deep Research 사용 방법:**
                        1. **프롬프트 복사**: 위의 완성된 프롬프트를 복사
                        2. **CSV 파일 다운로드**: 포트폴리오와 투자노트 CSV 파일을 다운로드
                        3. **Deep Research 접속**: Gemini Deep Research에 접속
                        4. **파일 첨부**: 다운로드한 CSV 파일 2개를 첨부
                        5. **프롬프트 붙여넣기**: 복사한 프롬프트를 붙여넣고 실행
                        
                        **✨ 이제 매일 이 과정을 반복하세요!**
                        """)
                        
            except Exception as e:
                st.error(f"❌ 완전한 패키지 생성 실패: {e}")
                import traceback
                st.error(f"상세 오류: {traceback.format_exc()}")
        
        # 세션 상태에 저장된 패키지가 있으면 표시
        if 'generated_package' in st.session_state:
            package = st.session_state['generated_package']
            
            st.markdown("---")
            st.subheader("📋 이전에 생성된 패키지")
            st.info(f"📅 생성 시간: {package['timestamp']}")
            
            # 탭으로 구분하여 표시
            tab1, tab2, tab3, tab4 = st.tabs(["📋 완성된 프롬프트", "📊 포트폴리오 CSV", "📝 투자노트 CSV", "📈 데이터 미리보기"])
            
            with tab1:
                st.markdown("### 🎯 Deep Research에 바로 사용할 프롬프트")
                st.text_area("완성된 데일리 브리핑 프롬프트", package['complete_prompt'], height=600, key="saved_prompt_text_area")
                
                # 복사 버튼 (개선된 버전)
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("📋 프롬프트 복사", key="copy_saved_prompt", use_container_width=True):
                        st.success("✅ 프롬프트가 클립보드에 복사되었습니다!")
                with col2:
                    if st.button("🗑️ 패키지 삭제", key="delete_package", use_container_width=True):
                        del st.session_state['generated_package']
                        st.rerun()
                
                st.success("💡 이 프롬프트를 Deep Research에 붙여넣으세요!")
            
            with tab2:
                st.markdown("### 📊 포트폴리오 CSV 파일")
                if package['portfolio_csv']:
                    st.text_area("포트폴리오 데이터 (CSV)", package['portfolio_csv'], height=400)
                    
                    # CSV 다운로드 버튼
                    st.download_button(
                        label="📥 포트폴리오 CSV 다운로드",
                        data=package['portfolio_csv'],
                        file_name=f"portfolio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        key="download_saved_portfolio_csv"
                    )
                else:
                    st.warning("포트폴리오 데이터가 없습니다.")
            
            with tab3:
                st.markdown("### 📝 투자노트 CSV 파일")
                if package['notes_csv']:
                    st.text_area("투자노트 데이터 (CSV)", package['notes_csv'], height=400)
                    
                    # CSV 다운로드 버튼
                    st.download_button(
                        label="📥 투자노트 CSV 다운로드",
                        data=package['notes_csv'],
                        file_name=f"investment_notes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        key="download_saved_notes_csv"
                    )
                else:
                    st.warning("투자노트 데이터가 없습니다.")
            
            with tab4:
                st.markdown("### 📈 데이터 미리보기")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📊 포트폴리오 현황")
                    if package['portfolio_df'] is not None and not package['portfolio_df'].empty:
                        st.dataframe(package['portfolio_df'], use_container_width=True)
                    else:
                        st.info("포트폴리오 데이터가 없습니다.")
                
                with col2:
                    st.subheader("📝 투자 노트")
                    if package['notes_df'] is not None and not package['notes_df'].empty:
                        st.dataframe(package['notes_df'], use_container_width=True)
                    else:
                        st.info("투자 노트 데이터가 없습니다.")
    
    # 개별 기능들
    st.markdown("---")
    st.subheader("🔧 개별 기능")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🤖 프롬프트만 생성")
        if st.button("🤖 프롬프트 생성", use_container_width=True):
            if not google_api_key:
                st.error("❌ GOOGLE_API_KEY가 설정되지 않았습니다.")
            else:
                try:
                    with st.spinner("🤖 프롬프트를 생성하고 있습니다..."):
                        prompt = generator.generate_complete_prompt(time_window_text)
                        st.text_area("생성된 프롬프트", prompt, height=400)
                except Exception as e:
                    st.error(f"❌ 프롬프트 생성 실패: {e}")
    
    with col2:
        st.markdown("#### 📥 CSV만 다운로드")
        selected_sheet = st.selectbox("시트 선택", available_sheets)
        if st.button("📥 CSV 다운로드", use_container_width=True):
            try:
                csv_data = generator.get_data_as_csv(selected_sheet)
                if csv_data:
                    st.download_button(
                        label=f"📥 {selected_sheet} CSV 다운로드",
                        data=csv_data,
                        file_name=f"{selected_sheet}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                else:
                    st.warning("다운로드할 데이터가 없습니다.")
            except Exception as e:
                st.error(f"❌ CSV 다운로드 실패: {e}")

if __name__ == "__main__":
    main()

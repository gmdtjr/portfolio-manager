import streamlit as st
import os
import json
import pandas as pd
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build

def get_time_window_text(selection: str) -> str:
    """UI 선택에 따라 시간 범위 텍스트를 반환합니다."""
    if "48시간" in selection:
        return "지난 48시간 동안"
    if "72시간" in selection:
        return "지난 72시간 동안"
    if "1주일" in selection:
        return "지난 1주일 동안"
    return "지난 24시간 동안" # Default

class DailyBriefingGenerator:
    """데일리 브리핑 프롬프트 생성기 (CSV 다운로더 기능 포함)"""
    
    def __init__(self, spreadsheet_id: str):
        self.spreadsheet_id = spreadsheet_id
        self.service = None
        self._authenticate_google()
    
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
    
    
    def generate_complete_prompt(self, time_window_text: str = "지난 24시간 동안") -> str:
        """완성된 프롬프트 생성"""
        try:
            today = datetime.now().strftime('%Y년 %m월 %d일')
            
            # 완성된 프롬프트 생성
            complete_prompt = f"""📊 포트폴리오 및 관심 종목 종합 브리핑 ({today})
🎯 Mission (임무)
당신은 월스트리트 최고의 포트폴리오 전략가이자, **냉철한 리스크 관리자(Risk Manager)**입니다. 당신의 핵심 임무는 나의 기존 투자 아이디어를 긍정하는 것이 아니라, 객관적인 데이터와 비판적인 분석을 통해 잠재적인 맹점을 찾아내고 최악의 시나리오에 대비하도록 돕는 것입니다.

먼저, {time_window_text} 동안의 글로벌 매크로 환경을 스스로 리서치한 후, 그 내용을 바탕으로 첨부된 [포트폴리오 파일] 2개를 종합 분석하여 균형 잡힌 시각의 데일리 브리핑을 생성해주세요.

[중요 지시사항]
모든 결과물은 반드시 한글로만 작성해주세요. 영문 용어는 필요한 경우에만 괄호 안에 병기하고, 그 외의 모든 서술은 한글로 해야 합니다.

항상 긍정론(Bull Case)과 부정론(Bear Case)을 함께 제시해야 합니다.

[첨부 파일 설명]
포트폴리오_현황.csv: 나의 현재 보유 자산 현황 (정량 데이터)

투자_노트.csv: 모든 관심 자산에 대한 나의 투자 아이디어, 리스크 등 (정성 데이터)

🔍 Key Analysis Framework (핵심 분석 프레임워크)
1. 글로벌 매크로 환경 리서치 (Self-Research)
{time_window_text} 동안 발표된 주요 경제 지표, 중앙은행의 통화 정책, 원자재/환율 변동, 지정학적 이벤트 등을 리서치하고, 이것이 시장에 미칠 긍정적 영향과 부정적 영향을 모두 요약해주세요.

2. 투자 아이디어 스트레스 테스트 (Thesis Stress Test)
위에서 리서치한 매크로 환경을 바탕으로, 투자_노트.csv에 기록된 나의 투자 아이디어에 대한 **가장 강력한 반론(Strongest Counter-Argument)**은 무엇인지 분석해주세요.

특히 노트에 기록된 '핵심 리스크'가 현실화될 가능성이 얼마나 높아졌는지 집중적으로 점검하고, 내가 인지하지 못했을 새로운 리스크는 없는지 파악해주세요.

3. 성과 원인 분석 (Performance Attribution)
{time_window_text} 동안의 성과를 기준으로 Top/Underperformer를 선정하고, 그 원인이 나의 투자 아이디어가 적중한 결과(Skill)인지, 아니면 단순히 시장 전반의 흐름에 편승한 결과(Luck)인지 비판적으로 분석해주세요.

📝 Output Format (결과물 형식)
1. Executive Summary (핵심 요약)
시장 요약: {time_window_text} 동안 시장을 움직인 핵심 키워드와 투자 심리는? (예: 금리 인상 우려로 인한 위험 회피 심리 강화)

포트폴리오 영향: 이로 인해 내 포트폴리오에 발생한 가장 중요한 변화와 오늘 주목해야 할 가장 큰 위협은?

오늘의 핵심 고려사항: 그래서 오늘 내가 신중하게 고려해야 할 가장 중요한 의사결정 포인트는?

2. 보유 포트폴리오 분석 (Holdings Analysis)
이 섹션에서는 포트폴리오_현황.csv에 있는 모든 종목을 아래 형식에 맞춰 하나씩 분석해주세요.

[종목명 1]

핵심 코멘트: {time_window_text} 동안의 주요 이슈 및 주가 변동 요약.

투자노트 스트레스 테스트:

긍정론 (Bull Case): 나의 투자 아이디어를 지지하는 최신 근거는 무엇인가?

부정론 (Bear Case): 나의 투자 아이디어에 대한 가장 강력한 반론 또는 새롭게 부상한 리스크는 무엇인가?

의사결정 지원 (Decision Support):

추천 행동: 비중 유지/확대/축소 등

재검토 조건: 어떤 상황이 발생하면 이 추천 행동을 재검토해야 하는가?

(...모든 보유 종목에 대해 반복...)

3. 관심 종목 분석 (Watchlist Analysis)
이 섹션에서는 투자_노트.csv에만 있는 '관심 종목'들을 아래 형식에 맞춰 하나씩 분석해주세요.

[관심 종목명 1]

핵심 코멘트: {time_window_text} 동안의 주요 뉴스 및 데이터 변화 요약.

투자 매력도 검증:

기회 요인 (Opportunity): 나의 투자 아이디어를 뒷받침하는 긍정적 신호는 무엇인가?

위험 요인 (Threat): 신규 진입을 망설이게 만드는 가장 큰 리스크는 무엇인가?

의사결정 지원 (Decision Support):

추천 행동: 지속 관찰 / 신규 매수 고려 / 관심 목록 제외 등

매수 고려 조건: 어떤 조건이 충족되면 신규 매수를 긍정적으로 검토할 수 있는가?

(...모든 관심 종목에 대해 반복...)"""
            
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
        page_title="데일리 브리핑 생성기",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 데일리 브리핑 생성기")
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
    
    if not spreadsheet_id:
        st.error("❌ GOOGLE_SPREADSHEET_ID가 설정되지 않았습니다.")
        return
    
    # 데일리 브리핑 생성기 초기화
    try:
        generator = DailyBriefingGenerator(spreadsheet_id)
        available_sheets = generator.get_available_sheets()
        
        if not available_sheets:
            st.error("❌ 사용 가능한 시트가 없습니다.")
            return
            
    except Exception as e:
        st.error(f"❌ 데일리 브리핑 생성기 초기화 실패: {e}")
        return
    
    # 기능 설명
    st.info("""
    **📊 데일리 브리핑 생성기**
    • 포트폴리오와 투자 노트 데이터 통합 분석
    • 전문적인 데일리 브리핑 프롬프트 생성
    • CSV 파일 다운로드 기능 포함
    • Deep Research에 바로 사용 가능한 완성된 패키지 제공
    """)
    
    # 시간 범위 선택
    st.subheader("⏰ 분석 기간 선택")
    time_window_selection = st.radio(
        "분석 기간을 선택하세요:",
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
        try:
            with st.spinner("🚀 모든 재료를 준비하고 있습니다..."):
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
                    st.markdown("### 📋 프롬프트 복사 방법")
                    st.info("""
                    **💡 프롬프트 복사 방법:**
                    1. 위 텍스트 박스에서 전체 텍스트를 선택 (Ctrl+A 또는 Cmd+A)
                    2. 복사 (Ctrl+C 또는 Cmd+C)
                    3. Deep Research에 붙여넣기 (Ctrl+V 또는 Cmd+V)
                    """)
                    
                    # 프롬프트를 별도로 표시 (선택하기 쉬운 형태)
                    st.markdown("### 📄 복사용 프롬프트")
                    st.code(package['complete_prompt'], language="text")
                    
                    # 새로고침 버튼
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
            st.markdown("### 📋 프롬프트 복사 방법")
            st.info("""
            **💡 프롬프트 복사 방법:**
            1. 아래 코드 박스에서 전체 텍스트를 선택 (Ctrl+A 또는 Cmd+A)
            2. 복사 (Ctrl+C 또는 Cmd+C)
            3. Deep Research에 붙여넣기 (Ctrl+V 또는 Cmd+V)
            """)
            
            # 프롬프트를 별도로 표시 (선택하기 쉬운 형태)
            st.markdown("### 📄 복사용 프롬프트")
            st.code(package['complete_prompt'], language="text")
            
            # 버튼들
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("🔄 프롬프트 새로고침", key="refresh_saved_prompt", use_container_width=True):
                    st.rerun()
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

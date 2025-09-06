import streamlit as st
import os
import sys
import json
import pandas as pd
from datetime import datetime
from portfolio_manager import KoreaInvestmentAPI, GoogleSheetsManager, Account, ExchangeRateAPI

def get_time_window_text(selection: str) -> str:
    """UI 선택에 따라 시간 범위 텍스트를 반환합니다."""
    if "48시간" in selection:
        return "지난 48시간 동안"
    if "72시간" in selection:
        return "지난 72시간 동안"
    if "1주일" in selection:
        return "지난 1주일 동안"
    return "지난 24시간 동안" # Default


# 투자 노트 생성기 import
try:
    from investment_note_generator import InvestmentNoteGenerator
    INVESTMENT_NOTE_GENERATOR_AVAILABLE = True
except ImportError:
    INVESTMENT_NOTE_GENERATOR_AVAILABLE = False

# 페이지 설정
st.set_page_config(
    page_title="AI 포트폴리오 관리 시스템",
    page_icon="📊",
    layout="wide"
)

# 세션 상태 초기화
if 'api' not in st.session_state:
    st.session_state.api = None
if 'sheets_manager' not in st.session_state:
    st.session_state.sheets_manager = None
if 'accounts' not in st.session_state:
    st.session_state.accounts = None

def initialize_components():
    """API 컴포넌트 초기화"""
    if st.session_state.api is None:
        st.session_state.api = KoreaInvestmentAPI()
    if st.session_state.sheets_manager is None:
        st.session_state.sheets_manager = GoogleSheetsManager()

def load_accounts():
    """계좌 정보 로드"""
    # Streamlit Cloud에서는 st.secrets를 사용, 로컬에서는 os.getenv 사용
    def get_secret(key):
        # Streamlit Cloud에서 secrets 접근 시도
        try:
            if hasattr(st, 'secrets') and st.secrets:
                value = st.secrets.get(key)
                if value:
                    # Google Service Account JSON은 너무 길어서 표시하지 않음
                    if key == 'GOOGLE_APPLICATION_CREDENTIALS_JSON':
                        st.sidebar.success(f"✅ {key}: Google Service Account JSON 설정됨")
                    else:
                        st.sidebar.success(f"✅ {key}: {str(value)[:10]}...")
                    return value
        except Exception as e:
            st.sidebar.error(f"❌ {key}: secrets 접근 오류 - {str(e)}")
        
        # 로컬에서 환경변수 접근
        value = os.getenv(key)
        if value:
            if key == 'GOOGLE_APPLICATION_CREDENTIALS_JSON':
                st.sidebar.info(f"🔧 {key}: Google Service Account JSON 설정됨")
            else:
                st.sidebar.info(f"🔧 {key}: {str(value)[:10]}...")
        else:
            st.sidebar.warning(f"❌ {key}: 설정되지 않음")
        return value
    
    required_env_vars = [
        'KOREA_INVESTMENT_ACC_NO_DOMESTIC', 'KOREA_INVESTMENT_API_KEY_DOMESTIC', 'KOREA_INVESTMENT_API_SECRET_DOMESTIC',
        'KOREA_INVESTMENT_ACC_NO_PENSION', 'KOREA_INVESTMENT_API_KEY_PENSION', 'KOREA_INVESTMENT_API_SECRET_PENSION',
        'KOREA_INVESTMENT_ACC_NO_OVERSEAS', 'KOREA_INVESTMENT_API_KEY_OVERSEAS', 'KOREA_INVESTMENT_API_SECRET_OVERSEAS',
        'GOOGLE_SPREADSHEET_ID'
    ]
    
    missing_vars = []
    for var in required_env_vars:
        if not get_secret(var):
            missing_vars.append(var)
    
    if missing_vars:
        st.warning(f"⚠️ 다음 환경변수가 설정되지 않았습니다: {', '.join(missing_vars)}")
        st.info("📝 Streamlit Cloud 대시보드에서 환경변수를 설정해주세요.")
        st.info("🔧 또는 로컬에서 .env 파일에 다음 변수들을 추가해주세요:")
        for var in missing_vars:
            st.code(f"{var}=your_value")
        return None
    
    accounts = [
        Account(
            name="국내주식",
            acc_no=get_secret('KOREA_INVESTMENT_ACC_NO_DOMESTIC'),
            api_key=get_secret('KOREA_INVESTMENT_API_KEY_DOMESTIC'),
            api_secret=get_secret('KOREA_INVESTMENT_API_SECRET_DOMESTIC'),
            account_type="domestic_stock"
        ),
        Account(
            name="국내연금",
            acc_no=get_secret('KOREA_INVESTMENT_ACC_NO_PENSION'),
            api_key=get_secret('KOREA_INVESTMENT_API_KEY_PENSION'),
            api_secret=get_secret('KOREA_INVESTMENT_API_SECRET_PENSION'),
            account_type="pension"
        ),
        Account(
            name="해외주식",
            acc_no=get_secret('KOREA_INVESTMENT_ACC_NO_OVERSEAS'),
            api_key=get_secret('KOREA_INVESTMENT_API_KEY_OVERSEAS'),
            api_secret=get_secret('KOREA_INVESTMENT_API_SECRET_OVERSEAS'),
            account_type="overseas"
        )
    ]
    
    return accounts

def sync_investment_notes():
    """투자 노트와 포트폴리오 상태 동기화"""
    try:
        if not INVESTMENT_NOTE_GENERATOR_AVAILABLE:
            st.error("❌ 투자 노트 동기화 기능을 사용할 수 없습니다.")
            st.info("💡 필요한 모듈이 설치되지 않았습니다.")
            return
        
        # 환경변수 확인
        def get_secret(key):
            try:
                return st.secrets[key]
            except:
                return os.getenv(key)
        
        spreadsheet_id = get_secret('GOOGLE_SPREADSHEET_ID')
        
        if not spreadsheet_id:
            st.error("❌ GOOGLE_SPREADSHEET_ID가 설정되지 않았습니다.")
            return
        
        with st.spinner("투자 노트와 포트폴리오 상태를 동기화하고 있습니다..."):
            # 투자 노트 매니저 초기화
            from investment_notes_manager import InvestmentNotesManager
            notes_manager = InvestmentNotesManager(spreadsheet_id)
            
            # 기존 데이터 마이그레이션 확인
            notes_manager.migrate_existing_notes()
            
            # 포트폴리오 데이터 읽기
            st.info("📋 포트폴리오 데이터를 읽고 있습니다...")
            generator = DailyBriefingGenerator(spreadsheet_id)
            portfolio_df = generator.read_portfolio_data()
            
            if portfolio_df.empty:
                st.warning("⚠️ 포트폴리오 데이터가 없습니다. 먼저 포트폴리오를 업데이트해주세요.")
                return
            
            # 투자 노트 상태 업데이트
            st.info("🔄 투자 노트 상태를 업데이트하고 있습니다...")
            success = notes_manager.update_portfolio_status(portfolio_df)
            
            if success:
                st.success("✅ 투자 노트 동기화가 완료되었습니다!")
                
                # 동기화 결과 표시
                portfolio_notes = notes_manager.get_portfolio_notes()
                watchlist_notes = notes_manager.get_watchlist_notes()
                sold_notes = notes_manager.get_sold_notes()
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("보유 종목", len(portfolio_notes))
                    if not portfolio_notes.empty:
                        st.write("**보유 종목들:**")
                        for _, note in portfolio_notes.iterrows():
                            st.write(f"• {note['종목명']} ({note['종목코드']})")
                
                with col2:
                    st.metric("관심 종목", len(watchlist_notes))
                    if not watchlist_notes.empty:
                        st.write("**관심 종목들:**")
                        for _, note in watchlist_notes.iterrows():
                            st.write(f"• {note['종목명']} ({note['종목코드']})")
                
                with col3:
                    st.metric("매도 완료", len(sold_notes))
                    if not sold_notes.empty:
                        st.write("**매도 완료 종목들:**")
                        for _, note in sold_notes.iterrows():
                            st.write(f"• {note['종목명']} ({note['종목코드']})")
            else:
                st.error("❌ 투자 노트 동기화에 실패했습니다.")
                
    except Exception as e:
        st.error(f"❌ 투자 노트 동기화 실패: {e}")
        import traceback
        st.error(f"상세 오류: {traceback.format_exc()}")

def update_portfolio():
    """포트폴리오 업데이트 실행"""
    try:
        initialize_components()
        accounts = load_accounts()
        
        if accounts is None:
            return
        
        # 진행 상황 표시
        progress_bar = st.progress(0.0)  # 0.0으로 초기화
        status_text = st.empty()
        
        # 전체 포트폴리오 수집
        all_portfolio = []
        total_cash = 0
        exchange_rate = None
        exchange_source = None
        
        status_text.text("🔍 포트폴리오 조회 중...")
        
        for i, account in enumerate(accounts):
            progress = (i / len(accounts))  # 0.0 ~ 1.0 사이의 값으로 변경
            progress_bar.progress(progress)
            status_text.text(f"🔍 {account.name} 계좌 조회 중...")
            
            # 주식 포트폴리오 조회
            if account.account_type == "overseas":
                portfolio = st.session_state.api.get_overseas_portfolio(account)
                # 환율 정보 저장
                if st.session_state.api.exchange_rate:
                    exchange_rate = st.session_state.api.exchange_rate
                    exchange_source = st.session_state.api.exchange_rate_source
            else:
                portfolio = st.session_state.api.get_domestic_portfolio(account)
            
            if portfolio:
                all_portfolio.extend(portfolio)
            
            # 현금 잔고 조회 및 누적
            if account.account_type == "overseas":
                cash = st.session_state.api.get_overseas_cash(account)
            else:
                cash = st.session_state.api.get_domestic_cash(account)
            
            total_cash += cash
        
        progress_bar.progress(1.0)  # 완료 시 1.0으로 설정
        status_text.text("📊 구글 스프레드시트 업데이트 중...")
        
        if all_portfolio or total_cash > 0:
            # 구글 스프레드시트에 업데이트
            st.session_state.sheets_manager.update_portfolio(
                all_portfolio, total_cash, exchange_rate, exchange_source
            )
            
            # 결과 표시
            st.success("✅ 포트폴리오 업데이트가 완료되었습니다!")
            st.info("💡 투자 노트 상태를 동기화하려면 '📝 투자 노트 동기화' 버튼을 클릭하세요.")
            
            # 포트폴리오 요약 표시
            display_portfolio_summary(all_portfolio, total_cash, exchange_rate)
            
        else:
            st.warning("❌ 조회된 포트폴리오가 없습니다.")
            
    except Exception as e:
        st.error(f"❌ 포트폴리오 처리 실패: {e}")

def display_portfolio_summary(portfolio, total_cash, exchange_rate):
    """포트폴리오 요약 정보 표시"""
    if not portfolio:
        return
    
    st.subheader("📊 포트폴리오 요약")
    
    # 전체 포트폴리오 가치 계산
    total_value = sum(item['평가금액'] for item in portfolio) + total_cash
    
    # 메트릭 표시
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("총 포트폴리오 가치", f"{total_value:,.0f}원")
    
    with col2:
        st.metric("현금", f"{total_cash:,.0f}원")
    
    with col3:
        stock_value = sum(item['평가금액'] for item in portfolio)
        st.metric("주식 평가금액", f"{stock_value:,.0f}원")
    
    with col4:
        if exchange_rate:
            st.metric("현재 환율", f"{exchange_rate:,.2f}원")
    
    # 계좌별 비중
    st.subheader("🏦 계좌별 비중")
    
    account_data = {}
    for item in portfolio:
        account = item['계좌구분']
        if account not in account_data:
            account_data[account] = 0
        account_data[account] += item['평가금액']
    
    # 차트 데이터 준비
    labels = list(account_data.keys())
    values = list(account_data.values())
    
    if values:
        import plotly.express as px
        
        fig = px.pie(
            values=values, 
            names=labels, 
            title="계좌별 비중",
            hole=0.3
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # 포트폴리오 상세 테이블
    st.subheader("📋 포트폴리오 상세")
    
    if portfolio:
        import pandas as pd
        df = pd.DataFrame(portfolio)
        
        # 비중 계산
        df['비중'] = (df['평가금액'] / total_value * 100).round(2)
        
        # 테이블 표시
        st.dataframe(
            df[['종목명', '보유수량', '현재가', '평가금액', '평가손익', '수익률', '계좌구분', '비중']],
            use_container_width=True
        )

def main():
    """메인 Streamlit 앱"""
    st.title("📊 AI 포트폴리오 관리 시스템")
    st.markdown("DB 업데이트 + AI 투자 분석 + 자동화된 프롬프트 생성")
    
    # 페이지 선택을 상단으로 이동
    st.sidebar.title("🎯 AI 투자 도구")
    page = st.sidebar.selectbox(
        "원하는 기능을 선택하세요",
        ["🔄 포트폴리오 업데이트", "📝 투자 노트 자동 생성", "🎯 데일리 브리핑 생성기"],
        help="AI 기반 투자 분석 및 포트폴리오 관리 도구를 선택하세요"
    )
    
    # 사이드바 설정
    st.sidebar.title("⚙️ 시스템 설정")
    
    # 환경변수 상태 표시
    st.sidebar.subheader("🔧 환경변수 상태")
    
    def get_secret(key):
        try:
            return st.secrets[key]
        except:
            return os.getenv(key)
    
    env_status = {}
    env_vars = [
        'KOREA_INVESTMENT_ACC_NO_DOMESTIC', 'KOREA_INVESTMENT_API_KEY_DOMESTIC', 
        'KOREA_INVESTMENT_ACC_NO_PENSION', 'KOREA_INVESTMENT_API_KEY_PENSION',
        'KOREA_INVESTMENT_ACC_NO_OVERSEAS', 'KOREA_INVESTMENT_API_KEY_OVERSEAS',
        'GOOGLE_SPREADSHEET_ID', 'GOOGLE_API_KEY'
    ]
    
    for var in env_vars:
        env_status[var] = "✅" if get_secret(var) else "❌"
    
    for var, status in env_status.items():
        st.sidebar.text(f"{status} {var}")
    
    # 계좌 정보 표시
    accounts = load_accounts()
    if accounts:
        st.sidebar.subheader("🏦 연결된 계좌")
        for account in accounts:
            st.sidebar.text(f"• {account.name}: {account.acc_no[:8]}***")
    else:
        st.sidebar.subheader("🏦 연결된 계좌")
        st.sidebar.warning("⚠️ 환경변수가 설정되지 않았습니다")
    
    # 디버깅: secrets 확인 (개발용)
    if st.sidebar.checkbox("🔍 Secrets 디버깅 (개발용)", value=False):
        st.sidebar.subheader("🔍 Secrets 디버깅")
        try:
            if hasattr(st, 'secrets'):
                st.sidebar.write("✅ st.secrets 사용 가능")
                if st.secrets:
                    st.sidebar.write(f"📝 Secrets 개수: {len(st.secrets)}")
                    for key in st.secrets.keys():
                        st.sidebar.write(f"🔑 {key}: {str(st.secrets[key])[:20]}...")
                else:
                    st.sidebar.write("❌ st.secrets가 비어있음")
            else:
                st.sidebar.write("❌ st.secrets 사용 불가")
        except Exception as e:
            st.sidebar.write(f"❌ Secrets 오류: {str(e)}")
    
    # 최근 업데이트 정보
    if 'last_update' in st.session_state:
        st.sidebar.subheader("📅 최근 업데이트")
        st.sidebar.text(st.session_state.last_update)
    
    # 페이지별 컨텐츠
    if page == "🔄 포트폴리오 업데이트":
        # 메인 컨텐츠
        st.header("🔄 포트폴리오 업데이트")
        st.markdown("한국투자증권 API를 통해 포트폴리오를 조회하고 구글 스프레드시트에 업데이트합니다.")
        
        if accounts:
            # 주요 기능 버튼들
            st.subheader("🚀 주요 기능")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔄 포트폴리오 업데이트", type="primary", use_container_width=True):
                    update_portfolio()
            
            with col2:
                if st.button("📝 투자 노트 동기화", type="secondary", use_container_width=True):
                    sync_investment_notes()
            
            # 기능 설명
            st.subheader("💡 기능 설명")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.info("**🔄 포트폴리오 업데이트**")
                st.write("• 한국투자증권 API를 통해 실시간 포트폴리오 조회")
                st.write("• 구글 스프레드시트에 자동 업데이트")
                st.write("• 환율 정보 포함")
            
            with col2:
                st.info("**📝 투자 노트 동기화**")
                st.write("• 기존 투자 노트의 포트폴리오 상태 업데이트")
                st.write("• 보유중/관심종목/매도완료 상태 동기화")
                st.write("• 매수/매도 날짜 정보 추가")
        else:
            st.warning("⚠️ 환경변수를 설정한 후 포트폴리오 업데이트를 사용할 수 있습니다.")
            st.info("📝 Streamlit Cloud 대시보드에서 환경변수를 설정해주세요.")
    
    elif page == "📝 투자 노트 자동 생성":
        if not INVESTMENT_NOTE_GENERATOR_AVAILABLE:
            st.error("❌ 투자 노트 자동 생성 기능을 사용할 수 없습니다.")
            st.info("💡 필요한 모듈이 설치되지 않았습니다.")
            return
        
        st.header("📝 투자 노트 자동 생성")
        st.markdown("기업 보고서를 입력하면 AI가 자동으로 투자 노트 초안을 생성합니다.")
        
        # 환경변수 확인
        def get_secret(key):
            try:
                return st.secrets[key]
            except:
                return os.getenv(key)
        
        spreadsheet_id = get_secret('GOOGLE_SPREADSHEET_ID')
        google_api_key = get_secret('GOOGLE_API_KEY')
        
        if not spreadsheet_id:
            st.error("❌ GOOGLE_SPREADSHEET_ID가 설정되지 않았습니다.")
            return
        
        if not google_api_key:
            st.error("❌ GOOGLE_API_KEY가 설정되지 않았습니다.")
            st.info("💡 투자 노트 자동 생성을 위해 GOOGLE_API_KEY가 필요합니다.")
            return
        
        # 기능 설명
        st.subheader("💡 기능 설명")
        st.info("""
        **📝 투자 노트 자동 생성**
        • 기업 보고서 분석을 통한 투자 아이디어 추출
        • 투자 확신도, 섹터, 리스크 자동 분류
        • 목표 주가 및 매도 조건 제안
        • 구글 스프레드시트 자동 저장
        """)
        
        # 입력 폼
        st.subheader("📋 기업 정보 입력")
        with st.form("investment_note_form"):
            
            col1, col2 = st.columns(2)
            with col1:
                company_name = st.text_input("기업명", placeholder="예: 삼성전자")
            with col2:
                stock_code = st.text_input("종목코드", placeholder="예: 005930")
            
            st.subheader("📄 기업 보고서 내용")
            report_content = st.text_area(
                "보고서 내용을 입력하세요",
                placeholder="기업의 실적 발표, 전망, 주요 성과 등을 입력하세요...",
                height=200
            )
            
            col1, col2 = st.columns(2)
            with col1:
                preview_button = st.form_submit_button("👀 미리보기 생성", type="secondary")
            with col2:
                generate_button = st.form_submit_button("📝 투자 노트 생성", type="primary")
        
        # 미리보기 생성
        if preview_button and company_name and stock_code and report_content:
            try:
                with st.spinner("AI가 기업 보고서를 분석하여 투자 노트 미리보기를 생성하고 있습니다..."):
                    # 투자 노트 생성기 초기화
                    generator = InvestmentNoteGenerator(spreadsheet_id)
                    
                    # 미리보기 생성
                    preview_note = generator.preview_note(company_name, stock_code, report_content)
                    
                    if preview_note:
                        st.success("✅ 투자 노트 미리보기가 생성되었습니다!")
                        
                        # 미리보기 표시
                        st.subheader("📋 생성된 투자 노트 미리보기")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("**기본 정보**")
                            st.write(f"**기업명**: {preview_note['종목명']}")
                            st.write(f"**종목코드**: {preview_note['종목코드']}")
                            st.write(f"**투자 확신도**: {preview_note['투자 확신도 (Conviction)']}")
                            st.write(f"**섹터/산업**: {preview_note['섹터/산업 (Sector/Industry)']}")
                            st.write(f"**투자 유형**: {preview_note['투자 유형 (Asset Type)']}")
                            st.write(f"**투자 기간**: {preview_note['투자 기간 (Horizon)']}")
                        
                        with col2:
                            st.write("**투자 아이디어**")
                            st.write(preview_note['투자 아이디어 (Thesis)'])
                        
                        # 상세 정보를 탭으로 구분
                        tab1, tab2, tab3, tab4 = st.tabs(["🚀 촉매", "⚠️ 리스크", "📊 모니터링 지표", "💰 목표/매도"])
                        
                        with tab1:
                            st.write("**핵심 촉매**")
                            st.write(preview_note['핵심 촉매 (Catalysts)'])
                        
                        with tab2:
                            st.write("**핵심 리스크**")
                            st.write(preview_note['핵심 리스크 (Risks)'])
                        
                        with tab3:
                            st.write("**핵심 모니터링 지표**")
                            st.write(preview_note['핵심 모니터링 지표 (KPIs)'])
                        
                        with tab4:
                            st.write("**목표 주가**")
                            st.write(preview_note['목표 주가 (Target)'])
                            st.write("**매도 조건**")
                            st.write(preview_note['매도 조건 (Exit Plan)'])
                        
                        # 저장 확인
                        if st.button("💾 이 투자 노트를 DB에 저장", type="primary"):
                            success = generator.create_and_save_note(company_name, stock_code, report_content)
                            if success:
                                st.success("✅ 투자 노트가 성공적으로 저장되었습니다!")
                            else:
                                st.error("❌ 투자 노트 저장에 실패했습니다.")
                    else:
                        st.error("❌ 투자 노트 미리보기 생성에 실패했습니다.")
                        
            except Exception as e:
                st.error(f"❌ 미리보기 생성 실패: {e}")
                import traceback
                st.error(f"상세 오류: {traceback.format_exc()}")
        
        # 투자 노트 생성 및 저장
        elif generate_button and company_name and stock_code and report_content:
            try:
                with st.spinner("AI가 기업 보고서를 분석하여 투자 노트를 생성하고 있습니다..."):
                    # 투자 노트 생성기 초기화
                    generator = InvestmentNoteGenerator(spreadsheet_id)
                    
                    # 투자 노트 생성 및 저장
                    success = generator.create_and_save_note(company_name, stock_code, report_content)
                    
                    if success:
                        st.success("✅ 투자 노트가 성공적으로 생성되고 저장되었습니다!")
                        st.info("💡 생성된 투자 노트는 '투자_노트' 시트에서 확인할 수 있습니다.")
                    else:
                        st.error("❌ 투자 노트 생성 및 저장에 실패했습니다.")
                        
            except Exception as e:
                st.error(f"❌ 투자 노트 생성 실패: {e}")
                import traceback
                st.error(f"상세 오류: {traceback.format_exc()}")
        
        # 사용법 안내
        if not preview_button and not generate_button:
            st.subheader("📖 사용법 안내")
            st.info("💡 사용법:")
            st.write("1. 기업명과 종목코드를 입력하세요")
            st.write("2. 기업의 실적 발표, 전망, 주요 성과 등의 보고서 내용을 입력하세요")
            st.write("3. '미리보기 생성'으로 결과를 확인한 후 '투자 노트 생성'으로 저장하세요")
            st.write("4. 생성된 투자 노트는 Deep Research 질문 생성에서 활용됩니다")
            
            st.subheader("📝 예시 보고서")
            st.code("""
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
            """)
    
    # 데일리 브리핑 생성기 페이지
    elif page == "🎯 데일리 브리핑 생성기":
        st.subheader("🎯 데일리 브리핑 생성기")
        st.markdown("매크로 이슈 분석 + 포트폴리오 데이터 + 완성된 프롬프트 생성")
        
        # 환경변수 확인
        spreadsheet_id = get_secret('GOOGLE_SPREADSHEET_ID')
        google_api_key = get_secret('GOOGLE_API_KEY')
        
        if not spreadsheet_id:
            st.error("❌ GOOGLE_SPREADSHEET_ID가 설정되지 않았습니다.")
            return
        
        if not google_api_key:
            st.error("❌ GOOGLE_API_KEY가 설정되지 않았습니다. 프롬프트 생성 기능을 사용할 수 없습니다.")
            return
        
        # 데일리 브리핑 생성기 import
        try:
            from daily_briefing_generator import DailyBriefingGenerator
            DAILY_BRIEFING_AVAILABLE = True
        except ImportError as e:
            st.error(f"❌ 데일리 브리핑 생성기를 불러올 수 없습니다: {e}")
            DAILY_BRIEFING_AVAILABLE = False
        
        if DAILY_BRIEFING_AVAILABLE:
            try:
                # 데일리 브리핑 생성기 초기화
                generator = DailyBriefingGenerator(spreadsheet_id, google_api_key)
                
                # 기능 설명
                st.info("""
                **📊 데일리 브리핑 생성기**
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
                            
                            # 탭으로 구분하여 표시
                            tab1, tab2, tab3, tab4 = st.tabs(["📋 완성된 프롬프트", "📊 포트폴리오 CSV", "📝 투자노트 CSV", "📈 데이터 미리보기"])
                            
                            with tab1:
                                st.markdown("### 🎯 Deep Research에 바로 사용할 프롬프트")
                                st.text_area("완성된 데일리 브리핑 프롬프트", package['complete_prompt'], height=600)
                                
                                # 복사 방법 안내
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
                    available_sheets = generator.get_available_sheets()
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
                            
            except Exception as e:
                st.error(f"❌ 데일리 브리핑 생성기 V2 초기화 실패: {e}")
                import traceback
                st.error(f"상세 오류: {traceback.format_exc()}")

if __name__ == "__main__":
    main()

import streamlit as st
import os
import sys
from datetime import datetime
import time
from portfolio_manager import KoreaInvestmentAPI, GoogleSheetsManager, Account, ExchangeRateAPI

# 페이지 설정
st.set_page_config(
    page_title="포트폴리오 관리자",
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
                    st.sidebar.success(f"✅ {key}: {str(value)[:10]}...")
                    return value
        except Exception as e:
            st.sidebar.error(f"❌ {key}: secrets 접근 오류 - {str(e)}")
        
        # 로컬에서 환경변수 접근
        value = os.getenv(key)
        if value:
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
    st.title("📊 포트폴리오 관리자")
    st.markdown("한국투자증권 계좌 포트폴리오를 구글 스프레드시트에 업데이트합니다.")
    
    # 디버깅: secrets 확인
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
    
    # 사이드바
    st.sidebar.title("⚙️ 설정")
    
    # 계좌 정보 표시
    accounts = load_accounts()
    if accounts:
        st.sidebar.subheader("🏦 연결된 계좌")
        for account in accounts:
            st.sidebar.text(f"• {account.name}: {account.acc_no[:8]}***")
    else:
        st.sidebar.subheader("🏦 연결된 계좌")
        st.sidebar.warning("⚠️ 환경변수가 설정되지 않았습니다")
    
    # 메인 컨텐츠
    st.header("🔄 포트폴리오 업데이트")
    
    if accounts:
        col1, col2 = st.columns([1, 3])
        
        with col1:
            if st.button("🔄 포트폴리오 업데이트", type="primary", use_container_width=True):
                update_portfolio()
        
        with col2:
            st.info("💡 버튼을 클릭하면 한국투자증권 API를 통해 포트폴리오를 조회하고 구글 스프레드시트에 업데이트합니다.")
    else:
        st.warning("⚠️ 환경변수를 설정한 후 포트폴리오 업데이트를 사용할 수 있습니다.")
        st.info("📝 Streamlit Cloud 대시보드에서 환경변수를 설정해주세요.")
    
    # 최근 업데이트 시간 표시
    if 'last_update' in st.session_state:
        st.sidebar.subheader("📅 최근 업데이트")
        st.sidebar.text(st.session_state.last_update)
    
    # 환경변수 상태 표시
    st.sidebar.subheader("🔧 시스템 상태")
    
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
        'GOOGLE_SPREADSHEET_ID'
    ]
    
    for var in env_vars:
        env_status[var] = "✅" if get_secret(var) else "❌"
    
    for var, status in env_status.items():
        st.sidebar.text(f"{status} {var}")

if __name__ == "__main__":
    main()

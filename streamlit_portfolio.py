import streamlit as st
import os
import sys
import json
import pandas as pd
from datetime import datetime
import time
from portfolio_manager import KoreaInvestmentAPI, GoogleSheetsManager, Account, ExchangeRateAPI

# Deep Research 질문 생성기 import
try:
    from google import genai
    from google.genai import types
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    DEEP_RESEARCH_AVAILABLE = True
except ImportError:
    DEEP_RESEARCH_AVAILABLE = False

# 투자 노트 생성기 import
try:
    from investment_note_generator import InvestmentNoteGenerator
    INVESTMENT_NOTE_GENERATOR_AVAILABLE = True
except ImportError:
    INVESTMENT_NOTE_GENERATOR_AVAILABLE = False

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

class DeepResearchQuestionGenerator:
    """Deep Research를 위한 질문 생성을 위한 클래스"""
    
    def __init__(self, spreadsheet_id: str, gemini_api_key: str = None):
        self.spreadsheet_id = spreadsheet_id
        self.gemini_api_key = gemini_api_key or os.getenv('GOOGLE_API_KEY')
        if not self.gemini_api_key:
            raise ValueError("Google API 키가 필요합니다. 환경변수 GOOGLE_API_KEY를 설정하거나 직접 전달하세요.")
        
        self.service = None
        self._authenticate_google()
        self._setup_gemini()
    
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
    
    def generate_deep_research_questions(self, df: pd.DataFrame) -> str:
        """Deep Research를 위한 최적의 질문들을 생성하는 메타 프롬프트"""
        today = datetime.now().strftime('%Y년 %m월 %d일')
        
        # 포트폴리오 분석
        total_value = df['평가금액(원)'].sum() if '평가금액(원)' in df.columns else 0
        total_profit = df['평가손익(원)'].sum() if '평가손익(원)' in df.columns else 0
        total_profit_rate = (total_profit / (total_value - total_profit) * 100) if (total_value - total_profit) > 0 else 0
        
        # 계좌별 분석
        account_analysis = ""
        if '계좌구분' in df.columns and '평가금액(원)' in df.columns:
            account_stats = df.groupby('계좌구분').agg({
                '평가금액(원)': 'sum',
                '평가손익(원)': 'sum',
                '수익률': 'mean'
            }).round(2)
            
            account_analysis = "\n".join([
                f"- {account}: {stats['평가금액(원)']:,.0f}원 (손익: {stats['평가손익(원)']:+,.0f}원, 수익률: {stats['수익률']:+.2f}%)"
                for account, stats in account_stats.iterrows()
            ])
        
        # 상위/하위 종목 분석
        top_gainers = df.nlargest(3, '평가손익(원)')[['종목명', '평가손익(원)', '수익률']] if '평가손익(원)' in df.columns else pd.DataFrame()
        top_losers = df.nsmallest(3, '평가손익(원)')[['종목명', '평가손익(원)', '수익률']] if '평가손익(원)' in df.columns else pd.DataFrame()
        
        top_gainers_text = "\n".join([
            f"- {row['종목명']}: {row['평가손익(원)']:+,.0f}원 ({row['수익률']:+.2f}%)"
            for _, row in top_gainers.iterrows()
        ]) if not top_gainers.empty else "없음"
        
        top_losers_text = "\n".join([
            f"- {row['종목명']}: {row['평가손익(원)']:+,.0f}원 ({row['수익률']:+.2f}%)"
            for _, row in top_losers.iterrows()
        ]) if not top_losers.empty else "없음"
        
        # 보유 종목 목록
        portfolio_holdings = []
        for _, row in df.iterrows():
            if pd.notna(row['종목코드']) and pd.notna(row['종목명']):
                if str(row['종목코드']).startswith('A'):  # 해외주식
                    market = "나스닥" if "NASDAQ" in str(row['종목명']).upper() else "뉴욕거래소"
                    portfolio_holdings.append(f"* {row['종목명']} ({row['종목코드']}, {market})")
                else:  # 국내주식
                    market = "코스닥" if len(str(row['종목코드'])) == 6 else "코스피"
                    portfolio_holdings.append(f"* {row['종목명']} ({row['종목코드']}, {market})")
        
        portfolio_holdings_text = "\n".join(portfolio_holdings) if portfolio_holdings else "* [포트폴리오 데이터 없음]"
        
        prompt = f"""To: My Dedicated AI Research Assistant
From: Head of Portfolio Management
Subject: Deep Research Question Generation for My Portfolio (Date: {today})

## Mission Briefing
당신은 나의 포트폴리오를 위한 **'딥 리서치 질문 생성 전문가'**입니다. 나의 포트폴리오 데이터를 분석하여, Deep Research에 던질 최적의 질문들을 생성해주세요. 이 질문들은 단순한 정보 수집을 넘어, 나의 투자 결정에 직접적으로 도움이 되는 **전략적 인사이트**를 얻을 수 있어야 합니다.

## My Portfolio Context

### 📊 Portfolio Overview
- 총 평가금액: {total_value:,.0f}원
- 총 평가손익: {total_profit:+,.0f}원
- 전체 수익률: {total_profit_rate:+.2f}%

### 🏦 Account Analysis
{account_analysis}

### 📈 Top Performers
{top_gainers_text}

### 📉 Underperformers
{top_losers_text}

### 📋 Portfolio Holdings
{portfolio_holdings_text}

## Your Task: Generate Strategic Deep Research Questions

### 1. **Portfolio-Specific Questions (포트폴리오 특화 질문)**
내 보유 종목들에 대한 심층 분석 질문을 생성해주세요:

- **Top Performers Analysis**: 상위 수익 종목들의 성과 지속 가능성 분석
- **Risk Assessment**: 하위 수익 종목들의 리스크 요인과 회복 가능성
- **Sector Correlation**: 내 포트폴리오의 섹터별 분산도와 상관관계 분석
- **Valuation Check**: 현재 보유 종목들의 밸류에이션 수준과 적정가 분석

### 2. **Market Context Questions (시장 맥락 질문)**
현재 시장 상황과 내 포트폴리오의 연관성에 대한 질문:

- **Macro Impact**: 최근 금리, 환율, 원유가격 변화가 내 포트폴리오에 미치는 영향
- **Sector Rotation**: 현재 시장에서의 섹터 로테이션 트렌드와 내 포트폴리오 적합성
- **Geopolitical Risk**: 지정학적 리스크가 내 해외주식 포트폴리오에 미치는 영향
- **Economic Cycle**: 현재 경제 사이클에서 내 포트폴리오의 위치와 조정 필요성

### 3. **Strategic Action Questions (전략적 액션 질문)**
실행 가능한 투자 전략을 위한 질문:

- **Rebalancing**: 포트폴리오 리밸런싱이 필요한 종목과 타이밍
- **New Opportunities**: 현재 시장에서 추가 투자 고려 종목과 그 이유
- **Risk Management**: 포트폴리오 리스크를 줄이기 위한 헤지 전략
- **Exit Strategy**: 언제, 어떤 조건에서 종목을 매도해야 하는지

### 4. **Forward-Looking Questions (미래 지향 질문)**
장기적 관점에서의 질문:

- **Trend Analysis**: 내 보유 종목들이 속한 산업의 장기 트렌드
- **Disruption Risk**: 기술 변화나 시장 혁신이 내 포트폴리오에 미치는 영향
- **Regulatory Changes**: 규제 변화가 내 보유 종목들에 미칠 수 있는 영향
- **Global Competition**: 글로벌 경쟁 구도 변화와 내 포트폴리오 적응 방안

## Expected Output Format

각 질문은 다음 형식으로 생성해주세요:

### 🔍 Question Category: [카테고리명]
**Q1:** [구체적이고 전략적인 질문]
- **Why Important:** 이 질문이 왜 중요한지
- **Expected Insight:** 이 질문에서 기대할 수 있는 인사이트
- **Actionable:** 이 질문의 답변이 어떻게 투자 결정에 도움이 되는지

**Q2:** [다음 질문]
...

### 📊 Priority Ranking
생성된 질문들을 우선순위별로 정렬해주세요:
1. **High Priority:** 즉시 답변이 필요한 전략적 질문
2. **Medium Priority:** 중기적으로 고려해야 할 질문
3. **Low Priority:** 장기적 모니터링이 필요한 질문

## Success Criteria
- 각 질문이 구체적이고 실행 가능해야 함
- 내 포트폴리오의 현재 상황을 반영해야 함
- 단순한 정보 수집을 넘어 전략적 인사이트를 얻을 수 있어야 함
- Deep Research의 강력한 분석 능력을 최대한 활용할 수 있어야 함

이제 나의 포트폴리오 데이터를 바탕으로, Deep Research에 던질 최적의 질문들을 생성해주세요."""
        
        return prompt
    
    def generate_ai_research_questions(self, df: pd.DataFrame) -> str:
        """AI가 포트폴리오 데이터를 분석하여 Deep Research용 질문들을 생성"""
        try:
            meta_prompt = self.generate_deep_research_questions(df)
            
            # 새로운 API 사용
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=meta_prompt
            )
            
            # 응답 텍스트 안전하게 추출
            try:
                response_text = response.text
                if response_text:
                    return response_text
                else:
                    return "AI 질문 생성 중 오류가 발생했습니다."
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
                                    return response_text
                
                return "AI 질문 생성 중 오류가 발생했습니다."
                
        except Exception as e:
            print(f"❌ AI 질문 생성 실패: {e}")
            return f"AI 질문 생성 중 오류가 발생했습니다: {str(e)}"

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
    
    # 페이지 선택
    page = st.sidebar.selectbox(
        "📄 페이지 선택",
        ["🔄 포트폴리오 업데이트", "🤖 Deep Research 질문 생성", "📝 투자 노트 자동 생성"]
    )
    
    if page == "🔄 포트폴리오 업데이트":
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
    
    elif page == "🤖 Deep Research 질문 생성":
        if not DEEP_RESEARCH_AVAILABLE:
            st.error("❌ Deep Research 질문 생성 기능을 사용할 수 없습니다.")
            st.info("💡 필요한 모듈이 설치되지 않았습니다.")
            return
        
        st.header("🤖 Deep Research 질문 생성")
        st.markdown("포트폴리오 데이터를 분석하여 Deep Research에 던질 최적의 질문들을 생성합니다.")
        
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
            st.info("💡 Deep Research 질문 생성을 위해 GOOGLE_API_KEY가 필요합니다.")
            return
        
        # 질문 생성 버튼
        if st.button("🤖 Deep Research 질문 생성", type="primary"):
            try:
                with st.spinner("포트폴리오 데이터를 분석하고 질문들을 생성하고 있습니다..."):
                    # 질문 생성기 초기화
                    generator = DeepResearchQuestionGenerator(spreadsheet_id)
                    
                    # 포트폴리오 데이터 읽기
                    st.info("📋 포트폴리오 데이터를 읽고 있습니다...")
                    portfolio_df = generator.read_portfolio_data()
                    
                    # AI 질문 생성
                    st.info("🤖 Deep Research용 질문들을 생성하고 있습니다... (시간이 걸릴 수 있습니다)")
                    ai_questions = generator.generate_ai_research_questions(portfolio_df)
                    
                    # 결과 표시
                    st.success("✅ Deep Research용 질문들이 생성되었습니다!")
                    
                    # 탭으로 구분하여 표시
                    tab1, tab2, tab3 = st.tabs(["🤖 생성된 질문들", "📝 메타 프롬프트", "📊 포트폴리오 데이터"])
                    
                    with tab1:
                        st.markdown(ai_questions)
                        
                        # 복사 버튼
                        if st.button("📋 질문들 복사", key="copy_questions"):
                            st.write("질문들이 클립보드에 복사되었습니다.")
                    
                    with tab2:
                        meta_prompt = generator.generate_deep_research_questions(portfolio_df)
                        st.text_area("메타 프롬프트", meta_prompt, height=400)
                        
                        if st.button("📋 메타 프롬프트 복사", key="copy_meta_prompt"):
                            st.write("메타 프롬프트가 클립보드에 복사되었습니다.")
                    
                    with tab3:
                        st.dataframe(portfolio_df, use_container_width=True)
                    
            except Exception as e:
                st.error(f"❌ 질문 생성 실패: {e}")
                import traceback
                st.error(f"상세 오류: {traceback.format_exc()}")
    
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
        
        # 입력 폼
        with st.form("investment_note_form"):
            st.subheader("📋 기업 정보 입력")
            
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
        'GOOGLE_SPREADSHEET_ID', 'GOOGLE_API_KEY'
    ]
    
    for var in env_vars:
        env_status[var] = "✅" if get_secret(var) else "❌"
    
    for var, status in env_status.items():
        st.sidebar.text(f"{status} {var}")

if __name__ == "__main__":
    main()

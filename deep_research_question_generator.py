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

def main():
    """메인 함수"""
    st.title("🤖 Deep Research 질문 생성기")
    st.markdown("포트폴리오 데이터를 분석하여 Deep Research에 던질 최적의 질문들을 생성합니다.")
    
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
    
    if not spreadsheet_id:
        st.error("❌ GOOGLE_SPREADSHEET_ID가 설정되지 않았습니다.")
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

if __name__ == "__main__":
    main()

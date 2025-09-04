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

# 투자 노트 매니저 import
try:
    from investment_notes_manager import InvestmentNotesManager
    INVESTMENT_NOTES_AVAILABLE = True
except ImportError:
    INVESTMENT_NOTES_AVAILABLE = False

class DailyBriefingGenerator:
    """데일리 브리핑 프롬프트 생성을 위한 클래스"""
    
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
    
    def generate_daily_briefing_prompt(self, portfolio_df: pd.DataFrame, exchange_data: Dict = None) -> str:
        """Gemini API를 활용한 지능형 데일리 브리핑 프롬프트 생성"""
        try:
            today = datetime.now().strftime('%Y년 %m월 %d일')
            
            # 포트폴리오 분석
            total_value = portfolio_df['평가금액(원)'].sum() if '평가금액(원)' in portfolio_df.columns else 0
            total_profit = portfolio_df['평가손익(원)'].sum() if '평가손익(원)' in portfolio_df.columns else 0
            total_profit_rate = (total_profit / (total_value - total_profit) * 100) if (total_value - total_profit) > 0 else 0
            
            # 상위/하위 종목 분석
            top_gainers = portfolio_df.nlargest(3, '평가손익(원)')[['종목명', '평가손익(원)', '수익률']] if '평가손익(원)' in portfolio_df.columns else pd.DataFrame()
            top_losers = portfolio_df.nsmallest(3, '평가손익(원)')[['종목명', '평가손익(원)', '수익률']] if '평가손익(원)' in portfolio_df.columns else pd.DataFrame()
            
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
            for _, row in portfolio_df.iterrows():
                if pd.notna(row['종목코드']) and pd.notna(row['종목명']):
                    if str(row['종목코드']).startswith('A'):  # 해외주식
                        market = "나스닥" if "NASDAQ" in str(row['종목명']).upper() else "뉴욕거래소"
                        portfolio_holdings.append(f"* {row['종목명']} ({row['종목코드']}, {market})")
                    else:  # 국내주식
                        market = "코스닥" if len(str(row['종목코드'])) == 6 else "코스피"
                        portfolio_holdings.append(f"* {row['종목명']} ({row['종목코드']}, {market})")
            
            portfolio_holdings_text = "\n".join(portfolio_holdings) if portfolio_holdings else "* [포트폴리오 데이터 없음]"
            
            # 투자 노트 정보 (있는 경우)
            notes_summary = ""
            if self.notes_manager:
                try:
                    portfolio_notes = self.notes_manager.get_notes_by_portfolio(portfolio_df)
                    if not portfolio_notes.empty:
                        notes_summary = "\n### 📝 투자 노트 정보\n"
                        for _, note in portfolio_notes.iterrows():
                            conviction = note.get('투자 확신도 (Conviction)', '미설정')
                            sector = note.get('섹터/산업 (Sector/Industry)', '미설정')
                            thesis = note.get('투자 아이디어 (Thesis)', '미설정')
                            notes_summary += f"- {note['종목명']}: {conviction} 확신도, {sector}, {thesis}\n"
                except Exception as e:
                    print(f"⚠️ 투자 노트 읽기 실패: {e}")
            
            # 환율 정보
            exchange_info = ""
            if exchange_data:
                exchange_info = "\n".join([
                    f"- {key}: {value}"
                    for key, value in exchange_data.items()
                ])
            
            # Gemini API에 전달할 메타 프롬프트
            meta_prompt = f"""너는 최고의 퀀트 애널리스트이자 리서치 전문가야. 나의 개인 투자 비서로서, 아래 정보를 바탕으로 Google Deep Research에 사용할 가장 효과적인 데일리 브리핑 분석 프롬프트 1개를 생성해 줘.

## 📊 나의 현재 포트폴리오 현황 ({today})

### 📈 포트폴리오 개요
- 총 평가금액: {total_value:,.0f}원
- 총 평가손익: {total_profit:+,.0f}원
- 전체 수익률: {total_profit_rate:+.2f}%

### 📈 상위 수익 종목 (Top 3)
{top_gainers_text}

### 📉 하위 수익 종목 (Bottom 3)
{top_losers_text}

### 📋 보유 종목 목록
{portfolio_holdings_text}

### 💱 환율 정보
{exchange_info if exchange_info else "환율 정보 없음"}

{notes_summary}

## 🎯 지시사항

위 모든 정보를 종합적으로 고려하여, 현재 나에게 가장 필요하고 시의성 높은 주제로 **Google Deep Research용 데일리 브리핑 프롬프트**를 생성해 줘.

### 📋 프롬프트 생성 요구사항:

1. **포트폴리오 중심 분석**: 내 보유 종목들의 성과와 투자 아이디어 검증에 집중
2. **투자 노트 연계**: 투자 노트가 있는 종목들의 투자 확신도와 아이디어 유효성 검증
3. **시장 맥락 분석**: 현재 시장 상황과 내 포트폴리오의 연관성
4. **실행 가능한 인사이트**: 구체적인 투자 전략과 리스크 관리 방안 제시
5. **시의성**: 오늘의 주요 이벤트와 경제 지표 발표 고려

### 📝 출력 형식:

다음 형식으로 **Google Deep Research에 바로 입력할 수 있는 완성된 프롬프트**를 생성해줘:

```
# 📊 데일리 브리핑 분석 요청

## 🎯 분석 목적
[분석의 핵심 목적과 기대 효과]

## 📈 분석 대상
[분석할 주요 종목이나 섹터]

## 🔍 분석 관점
[어떤 관점에서 분석할지 명시]

## 📋 구체적 분석 요청사항
1. [첫 번째 분석 요청]
2. [두 번째 분석 요청]
3. [세 번째 분석 요청]

## 💡 기대 인사이트
[이 분석을 통해 얻고자 하는 인사이트]

## 📅 시의성 고려사항
[오늘의 주요 이벤트나 지표]
```

**중요**: 생성된 프롬프트는 Google Deep Research에 바로 복사해서 사용할 수 있어야 하며, 내 포트폴리오의 현재 상황과 투자 노트를 반영한 맞춤형 분석을 요청하는 내용이어야 해."""
            
            # Gemini API 호출
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
                    return "Gemini API 응답이 비어있습니다."
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
                
                return "Gemini API 응답 처리 중 오류가 발생했습니다."
                
        except Exception as e:
            print(f"❌ 지능형 프롬프트 생성 실패: {e}")
            return f"지능형 프롬프트 생성 중 오류가 발생했습니다: {str(e)}"
    
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
    
    def generate_advanced_deep_research_questions(self, df: pd.DataFrame) -> str:
        """투자 노트를 활용한 고급 Deep Research 질문 생성"""
        if not self.notes_manager:
            print("⚠️ 투자 노트 매니저를 사용할 수 없습니다. 기본 질문 생성으로 대체합니다.")
            return self.generate_deep_research_questions(df)
        
        try:
            # 포트폴리오 투자 노트 조회
            portfolio_notes = self.notes_manager.get_notes_by_portfolio(df)
            missing_notes = self.notes_manager.get_missing_notes(df)
            
            today = datetime.now().strftime('%Y년 %m월 %d일')
            
            # 포트폴리오 분석 (기존과 동일)
            total_value = df['평가금액(원)'].sum() if '평가금액(원)' in df.columns else 0
            total_profit = df['평가손익(원)'].sum() if '평가손익(원)' in df.columns else 0
            total_profit_rate = (total_profit / (total_value - total_profit) * 100) if (total_value - total_profit) > 0 else 0
            
            # 투자 노트가 있는 종목들의 상세 정보
            notes_summary = ""
            if not portfolio_notes.empty:
                notes_summary = "\n### 📝 투자 노트가 있는 종목들\n"
                for _, note in portfolio_notes.iterrows():
                    conviction = note.get('투자 확신도 (Conviction)', '미설정')
                    sector = note.get('섹터/산업 (Sector/Industry)', '미설정')
                    asset_type = note.get('투자 유형 (Asset Type)', '미설정')
                    kpis = note.get('핵심 모니터링 지표 (KPIs)', '미설정')
                    
                    notes_summary += f"""
**{note['종목명']} ({note['종목코드']})**
- **투자 확신도**: {conviction}
- **섹터/산업**: {sector}
- **투자 유형**: {asset_type}
- **투자 아이디어**: {note['투자 아이디어 (Thesis)']}
- **핵심 촉매**: {note['핵심 촉매 (Catalysts)']}
- **핵심 리스크**: {note['핵심 리스크 (Risks)']}
- **핵심 모니터링 지표**: {kpis}
- **투자 기간**: {note['투자 기간 (Horizon)']}
- **목표 주가**: {note['목표 주가 (Target)']}
- **매도 조건**: {note['매도 조건 (Exit Plan)']}
- **마지막 수정**: {note['마지막_수정일']}
"""
            
            # 투자 노트가 없는 종목들
            missing_notes_summary = ""
            if missing_notes:
                missing_notes_summary = f"\n### ⚠️ 투자 노트가 없는 종목들\n"
                missing_stocks = df[df['종목코드'].astype(str).isin(missing_notes)]
                for _, stock in missing_stocks.iterrows():
                    missing_notes_summary += f"- {stock['종목명']} ({stock['종목코드']})\n"
            
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
Subject: Advanced Deep Research Question Generation with Investment Notes (Date: {today})

## Mission Briefing
당신은 나의 포트폴리오를 위한 **'딥 리서치 질문 생성 전문가'**입니다. 나의 포트폴리오 데이터와 **투자 노트**를 종합적으로 분석하여, Deep Research에 던질 최적의 질문들을 생성해주세요. 이 질문들은 단순한 정보 수집을 넘어, 나의 **투자 아이디어와 리스크 관리**에 직접적으로 도움이 되는 **전략적 인사이트**를 얻을 수 있어야 합니다.

## My Portfolio Context

### 📊 Portfolio Overview
- 총 평가금액: {total_value:,.0f}원
- 총 평가손익: {total_profit:+,.0f}원
- 전체 수익률: {total_profit_rate:+.2f}%

### 📋 Portfolio Holdings
{portfolio_holdings_text}
{notes_summary}
{missing_notes_summary}

## Your Task: Generate Strategic Deep Research Questions

### 1. **Investment Thesis Validation Questions (투자 아이디어 검증 질문)**
내 투자 노트에 기록된 투자 아이디어들이 여전히 유효한지 검증하는 질문:

- **Thesis Strength Check**: 내 투자 아이디어의 핵심 가정들이 현재 시장 상황에서 여전히 타당한지
- **Catalyst Progress**: 내가 주목하는 촉매들이 예상대로 진행되고 있는지
- **Risk Materialization**: 내가 우려하는 리스크들이 현실화되고 있는지
- **Competitive Landscape**: 경쟁 구도가 내 투자 아이디어에 유리하게 변화하고 있는지
- **Conviction Level Review**: 내 투자 확신도가 현재 시장 상황에서 여전히 적절한지
- **KPI Performance**: 내 핵심 모니터링 지표들이 예상대로 움직이고 있는지

### 2. **Portfolio-Specific Deep Dive Questions (포트폴리오 특화 심층 질문)**
투자 노트를 기반으로 한 맞춤형 분석 질문:

- **High Conviction Analysis**: 투자 확신도 '상(High)' 종목들의 성과와 투자 아이디어 일치성
- **Sector Concentration Risk**: 섹터별 분산도와 투자 유형별 배분이 적절한지
- **Asset Type Performance**: 성장주/가치주/배당주/경기순환주별 성과 분석
- **Top Performers Analysis**: 상위 수익 종목들의 성과가 내 투자 아이디어와 일치하는지
- **Risk Assessment**: 하위 수익 종목들의 리스크가 내 투자 노트의 예상과 일치하는지
- **Valuation Check**: 현재 보유 종목들의 밸류에이션이 내 목표 주가 설정과 일치하는지

### 3. **Strategic Action Questions (전략적 액션 질문)**
투자 노트의 매도 조건과 연계된 실행 가능한 전략:

- **Exit Strategy Validation**: 내 매도 조건들이 현재 시장 상황에서 적절한지
- **Rebalancing Needs**: 포트폴리오 리밸런싱이 투자 아이디어에 부합하는지
- **New Opportunities**: 현재 시장에서 내 투자 아이디어와 일치하는 추가 투자 기회
- **Risk Management**: 투자 노트의 리스크 관리 방안이 현재 상황에 적합한지

### 4. **Forward-Looking Questions (미래 지향 질문)**
투자 기간과 목표를 고려한 장기적 관점:

- **Horizon Alignment**: 내 투자 기간 설정이 현재 시장 사이클과 일치하는지
- **Trend Analysis**: 내 보유 종목들이 속한 산업의 장기 트렌드가 투자 아이디어를 지지하는지
- **Disruption Risk**: 기술 변화나 시장 혁신이 내 투자 아이디어에 미치는 영향
- **Regulatory Changes**: 규제 변화가 내 보유 종목들과 투자 아이디어에 미칠 수 있는 영향

## Expected Output Format

각 질문은 다음 형식으로 생성해주세요:

### 🔍 Question Category: [카테고리명]
**Q1:** [구체적이고 전략적인 질문]
- **Why Important:** 이 질문이 왜 중요한지 (내 투자 아이디어와 연관성)
- **Expected Insight:** 이 질문에서 기대할 수 있는 인사이트
- **Actionable:** 이 질문의 답변이 어떻게 투자 결정에 도움이 되는지
- **Related Note:** 관련된 투자 노트 항목

**Q2:** [다음 질문]
...

### 📊 Priority Ranking
생성된 질문들을 우선순위별로 정렬해주세요:
1. **High Priority:** 즉시 답변이 필요한 전략적 질문 (투자 아이디어 검증 관련)
2. **Medium Priority:** 중기적으로 고려해야 할 질문 (포트폴리오 최적화 관련)
3. **Low Priority:** 장기적 모니터링이 필요한 질문 (시장 트렌드 관련)

### 💡 Special Focus Areas
다음 영역에 특별히 집중해주세요:
- **투자 확신도 '상(High)' 종목들**: 가장 확신하는 투자 아이디어의 검증에 집중
- **섹터별 집중도 분석**: 특정 섹터에 과도하게 집중된 리스크 평가
- **투자 유형별 성과**: 성장주/가치주/배당주/경기순환주별 성과와 투자 아이디어 일치성
- **핵심 모니터링 지표 추적**: 각 종목의 KPI 성과와 투자 아이디어 유효성 검증
- **투자 노트가 있는 종목들**: 내 투자 아이디어 검증에 집중
- **투자 노트가 없는 종목들**: 기본적인 투자 근거와 리스크 분석
- **상위/하위 수익 종목들**: 성과와 투자 아이디어의 일치성 검증

## Success Criteria
- 각 질문이 내 투자 노트의 내용을 반영해야 함
- 투자 확신도와 섹터/산업 분류를 고려한 우선순위 설정
- 투자 유형별 성과 분석과 포트폴리오 최적화 제안
- 핵심 모니터링 지표(KPI) 기반의 투자 아이디어 유효성 검증
- 투자 아이디어의 유효성을 검증할 수 있어야 함
- 실행 가능한 투자 전략을 제시할 수 있어야 함
- Deep Research의 강력한 분석 능력을 최대한 활용할 수 있어야 함

이제 나의 포트폴리오 데이터와 투자 노트를 바탕으로, Deep Research에 던질 최적의 질문들을 생성해주세요."""
            
            return prompt
            
        except Exception as e:
            print(f"❌ 고급 질문 생성 실패: {e}")
            return self.generate_deep_research_questions(df)  # 기본 질문 생성으로 fallback
    
    def generate_advanced_ai_research_questions(self, df: pd.DataFrame) -> str:
        """투자 노트를 활용한 고급 AI 질문 생성"""
        try:
            meta_prompt = self.generate_advanced_deep_research_questions(df)
            
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
                    return "고급 AI 질문 생성 중 오류가 발생했습니다."
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
                
                return "고급 AI 질문 생성 중 오류가 발생했습니다."
                
        except Exception as e:
            print(f"❌ 고급 AI 질문 생성 실패: {e}")
            return f"고급 AI 질문 생성 중 오류가 발생했습니다: {str(e)}"

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
    
    def generate_advanced_deep_research_questions(self, df: pd.DataFrame) -> str:
        """투자 노트를 활용한 고급 Deep Research 질문 생성"""
        if not self.notes_manager:
            print("⚠️ 투자 노트 매니저를 사용할 수 없습니다. 기본 질문 생성으로 대체합니다.")
            return self.generate_deep_research_questions(df)
        
        try:
            # 포트폴리오 투자 노트 조회
            portfolio_notes = self.notes_manager.get_notes_by_portfolio(df)
            missing_notes = self.notes_manager.get_missing_notes(df)
            
            today = datetime.now().strftime('%Y년 %m월 %d일')
            
            # 포트폴리오 분석 (기존과 동일)
            total_value = df['평가금액(원)'].sum() if '평가금액(원)' in df.columns else 0
            total_profit = df['평가손익(원)'].sum() if '평가손익(원)' in df.columns else 0
            total_profit_rate = (total_profit / (total_value - total_profit) * 100) if (total_value - total_profit) > 0 else 0
            
            # 투자 노트가 있는 종목들의 상세 정보
            notes_summary = ""
            if not portfolio_notes.empty:
                notes_summary = "\n### 📝 투자 노트가 있는 종목들\n"
                for _, note in portfolio_notes.iterrows():
                    conviction = note.get('투자 확신도 (Conviction)', '미설정')
                    sector = note.get('섹터/산업 (Sector/Industry)', '미설정')
                    asset_type = note.get('투자 유형 (Asset Type)', '미설정')
                    kpis = note.get('핵심 모니터링 지표 (KPIs)', '미설정')
                    
                    notes_summary += f"""
**{note['종목명']} ({note['종목코드']})**
- **투자 확신도**: {conviction}
- **섹터/산업**: {sector}
- **투자 유형**: {asset_type}
- **투자 아이디어**: {note['투자 아이디어 (Thesis)']}
- **핵심 촉매**: {note['핵심 촉매 (Catalysts)']}
- **핵심 리스크**: {note['핵심 리스크 (Risks)']}
- **핵심 모니터링 지표**: {kpis}
- **투자 기간**: {note['투자 기간 (Horizon)']}
- **목표 주가**: {note['목표 주가 (Target)']}
- **매도 조건**: {note['매도 조건 (Exit Plan)']}
- **마지막 수정**: {note['마지막_수정일']}
"""
            
            # 투자 노트가 없는 종목들
            missing_notes_summary = ""
            if missing_notes:
                missing_notes_summary = f"\n### ⚠️ 투자 노트가 없는 종목들\n"
                missing_stocks = df[df['종목코드'].astype(str).isin(missing_notes)]
                for _, stock in missing_stocks.iterrows():
                    missing_notes_summary += f"- {stock['종목명']} ({stock['종목코드']})\n"
            
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
Subject: Advanced Deep Research Question Generation with Investment Notes (Date: {today})

## Mission Briefing
당신은 나의 포트폴리오를 위한 **'딥 리서치 질문 생성 전문가'**입니다. 나의 포트폴리오 데이터와 **투자 노트**를 종합적으로 분석하여, Deep Research에 던질 최적의 질문들을 생성해주세요. 이 질문들은 단순한 정보 수집을 넘어, 나의 **투자 아이디어와 리스크 관리**에 직접적으로 도움이 되는 **전략적 인사이트**를 얻을 수 있어야 합니다.

## My Portfolio Context

### 📊 Portfolio Overview
- 총 평가금액: {total_value:,.0f}원
- 총 평가손익: {total_profit:+,.0f}원
- 전체 수익률: {total_profit_rate:+.2f}%

### 📋 Portfolio Holdings
{portfolio_holdings_text}
{notes_summary}
{missing_notes_summary}

## Your Task: Generate Strategic Deep Research Questions

### 1. **Investment Thesis Validation Questions (투자 아이디어 검증 질문)**
내 투자 노트에 기록된 투자 아이디어들이 여전히 유효한지 검증하는 질문:

- **Thesis Strength Check**: 내 투자 아이디어의 핵심 가정들이 현재 시장 상황에서 여전히 타당한지
- **Catalyst Progress**: 내가 주목하는 촉매들이 예상대로 진행되고 있는지
- **Risk Materialization**: 내가 우려하는 리스크들이 현실화되고 있는지
- **Competitive Landscape**: 경쟁 구도가 내 투자 아이디어에 유리하게 변화하고 있는지
- **Conviction Level Review**: 내 투자 확신도가 현재 시장 상황에서 여전히 적절한지
- **KPI Performance**: 내 핵심 모니터링 지표들이 예상대로 움직이고 있는지

### 2. **Portfolio-Specific Deep Dive Questions (포트폴리오 특화 심층 질문)**
투자 노트를 기반으로 한 맞춤형 분석 질문:

- **High Conviction Analysis**: 투자 확신도 '상(High)' 종목들의 성과와 투자 아이디어 일치성
- **Sector Concentration Risk**: 섹터별 분산도와 투자 유형별 배분이 적절한지
- **Asset Type Performance**: 성장주/가치주/배당주/경기순환주별 성과 분석
- **Top Performers Analysis**: 상위 수익 종목들의 성과가 내 투자 아이디어와 일치하는지
- **Risk Assessment**: 하위 수익 종목들의 리스크가 내 투자 노트의 예상과 일치하는지
- **Valuation Check**: 현재 보유 종목들의 밸류에이션이 내 목표 주가 설정과 일치하는지

### 3. **Strategic Action Questions (전략적 액션 질문)**
투자 노트의 매도 조건과 연계된 실행 가능한 전략:

- **Exit Strategy Validation**: 내 매도 조건들이 현재 시장 상황에서 적절한지
- **Rebalancing Needs**: 포트폴리오 리밸런싱이 투자 아이디어에 부합하는지
- **New Opportunities**: 현재 시장에서 내 투자 아이디어와 일치하는 추가 투자 기회
- **Risk Management**: 투자 노트의 리스크 관리 방안이 현재 상황에 적합한지

### 4. **Forward-Looking Questions (미래 지향 질문)**
투자 기간과 목표를 고려한 장기적 관점:

- **Horizon Alignment**: 내 투자 기간 설정이 현재 시장 사이클과 일치하는지
- **Trend Analysis**: 내 보유 종목들이 속한 산업의 장기 트렌드가 투자 아이디어를 지지하는지
- **Disruption Risk**: 기술 변화나 시장 혁신이 내 투자 아이디어에 미치는 영향
- **Regulatory Changes**: 규제 변화가 내 보유 종목들과 투자 아이디어에 미칠 수 있는 영향

## Expected Output Format

각 질문은 다음 형식으로 생성해주세요:

### 🔍 Question Category: [카테고리명]
**Q1:** [구체적이고 전략적인 질문]
- **Why Important:** 이 질문이 왜 중요한지 (내 투자 아이디어와 연관성)
- **Expected Insight:** 이 질문에서 기대할 수 있는 인사이트
- **Actionable:** 이 질문의 답변이 어떻게 투자 결정에 도움이 되는지
- **Related Note:** 관련된 투자 노트 항목

**Q2:** [다음 질문]
...

### 📊 Priority Ranking
생성된 질문들을 우선순위별로 정렬해주세요:
1. **High Priority:** 즉시 답변이 필요한 전략적 질문 (투자 아이디어 검증 관련)
2. **Medium Priority:** 중기적으로 고려해야 할 질문 (포트폴리오 최적화 관련)
3. **Low Priority:** 장기적 모니터링이 필요한 질문 (시장 트렌드 관련)

### 💡 Special Focus Areas
다음 영역에 특별히 집중해주세요:
- **투자 확신도 '상(High)' 종목들**: 가장 확신하는 투자 아이디어의 검증에 집중
- **섹터별 집중도 분석**: 특정 섹터에 과도하게 집중된 리스크 평가
- **투자 유형별 성과**: 성장주/가치주/배당주/경기순환주별 성과와 투자 아이디어 일치성
- **핵심 모니터링 지표 추적**: 각 종목의 KPI 성과와 투자 아이디어 유효성 검증
- **투자 노트가 있는 종목들**: 내 투자 아이디어 검증에 집중
- **투자 노트가 없는 종목들**: 기본적인 투자 근거와 리스크 분석
- **상위/하위 수익 종목들**: 성과와 투자 아이디어의 일치성 검증

## Success Criteria
- 각 질문이 내 투자 노트의 내용을 반영해야 함
- 투자 확신도와 섹터/산업 분류를 고려한 우선순위 설정
- 투자 유형별 성과 분석과 포트폴리오 최적화 제안
- 핵심 모니터링 지표(KPI) 기반의 투자 아이디어 유효성 검증
- 투자 아이디어의 유효성을 검증할 수 있어야 함
- 실행 가능한 투자 전략을 제시할 수 있어야 함
- Deep Research의 강력한 분석 능력을 최대한 활용할 수 있어야 함

이제 나의 포트폴리오 데이터와 투자 노트를 바탕으로, Deep Research에 던질 최적의 질문들을 생성해주세요."""
            
            return prompt
            
        except Exception as e:
            print(f"❌ 고급 질문 생성 실패: {e}")
            return self.generate_deep_research_questions(df)  # 기본 질문 생성으로 fallback
    
    def generate_advanced_ai_research_questions(self, df: pd.DataFrame) -> str:
        """투자 노트를 활용한 고급 AI 질문 생성"""
        try:
            meta_prompt = self.generate_advanced_deep_research_questions(df)
            
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
                    return "고급 AI 질문 생성 중 오류가 발생했습니다."
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
                
                return "고급 AI 질문 생성 중 오류가 발생했습니다."
                
        except Exception as e:
            print(f"❌ 고급 AI 질문 생성 실패: {e}")
            return f"고급 AI 질문 생성 중 오류가 발생했습니다: {str(e)}"

def main():
    """메인 함수 - Gemini API 기반 지능형 데일리 브리핑 프롬프트 생성기"""
    st.title("🤖 지능형 데일리 브리핑 프롬프트 생성기")
    st.markdown("Gemini API를 활용하여 포트폴리오 데이터를 분석하고 맞춤형 Deep Research 프롬프트를 생성합니다.")
    
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
        st.info("💡 지능형 프롬프트 생성을 위해 GOOGLE_API_KEY가 필요합니다.")
        return
    
    # 기능 설명
    st.info("""
    **🤖 지능형 데일리 브리핑 프롬프트 생성기**
    • Gemini API를 활용한 동적 프롬프트 생성
    • 포트폴리오 현황 분석 (수익률, 상위/하위 종목, 섹터별 분포)
    • 투자 노트 연계 분석 (투자 확신도, 아이디어 유효성)
    • 시의성 높은 맞춤형 분석 요청 프롬프트 생성
    • 생성된 프롬프트를 Gemini Deep Research에 수동 입력하여 보고서 생성
    """)
    
    # 브리핑 생성 버튼
    if st.button("🤖 지능형 데일리 브리핑 프롬프트 생성", type="primary", use_container_width=True):
        try:
            with st.spinner("Gemini API를 활용하여 지능형 데일리 브리핑 프롬프트를 생성하고 있습니다..."):
                # 브리핑 생성기 초기화
                generator = DailyBriefingGenerator(spreadsheet_id, google_api_key)
                
                # 포트폴리오 데이터 읽기
                st.info("📋 포트폴리오 데이터를 읽고 있습니다...")
                portfolio_df = generator.read_portfolio_data()
                
                # 환율 정보 읽기
                st.info("💱 환율 정보를 읽고 있습니다...")
                exchange_data = generator.read_exchange_rate_data()
                
                # Gemini API를 활용한 지능형 프롬프트 생성
                st.info("🤖 Gemini API를 활용하여 맞춤형 프롬프트를 생성하고 있습니다...")
                briefing_prompt = generator.generate_daily_briefing_prompt(portfolio_df, exchange_data)
                
                # 결과 표시
                st.success("✅ 지능형 데일리 브리핑 프롬프트가 생성되었습니다!")
                
                # 탭으로 구분하여 표시
                tab1, tab2, tab3 = st.tabs(["🤖 생성된 프롬프트", "📈 포트폴리오 데이터", "💱 환율 정보"])
                
                with tab1:
                    st.markdown("### 📋 Gemini Deep Research에 복사할 프롬프트")
                    st.text_area("지능형 데일리 브리핑 프롬프트", briefing_prompt, height=600)
                    
                    # 복사 버튼
                    if st.button("📋 프롬프트 복사", key="copy_prompt"):
                        st.write("프롬프트가 클립보드에 복사되었습니다.")
                    
                    st.info("💡 이 프롬프트를 Gemini Deep Research에 붙여넣어 맞춤형 데일리 브리핑을 생성하세요.")
                
                with tab2:
                    st.dataframe(portfolio_df, use_container_width=True)
                
                with tab3:
                    if exchange_data:
                        st.json(exchange_data)
                    else:
                        st.info("환율 정보가 없습니다.")
                
        except Exception as e:
            st.error(f"❌ 프롬프트 생성 실패: {e}")
            import traceback
            st.error(f"상세 오류: {traceback.format_exc()}")

if __name__ == "__main__":
    main()

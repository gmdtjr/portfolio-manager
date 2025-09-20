import streamlit as st

def generate_exploration_prompt(investment_idea: str, exclusions: str = "") -> str:
    """
    사용자의 투자 아이디어와 제외 조건을 받아,
    균형 잡힌 시각의 Deep Research 프롬프트를 생성합니다.
    """
    
    investment_theme = investment_idea.strip()
    
    exclusion_section = ""
    if exclusions.strip():
        exclusion_section = f"3.  **제외 조건:** {exclusions.strip()}과 같이 특정된 분야는 분석에서 제외할 것."

    # '균형 분석' 철학이 적용된 마스터 프롬프트 템플릿
    master_prompt_template = f"""# 유망 산업 및 종목 발굴을 위한 균형 분석 보고서

## [중요 지시사항]
- **역할 부여:** 당신은 나의 최종 의사결정을 돕기 위해, **객관적인 데이터에 기반한 찬성론(Bull Case)과 반대론(Bear Case)을 모두 제시하는 '균형 분석가'**입니다. 당신의 임무는 결론을 내리는 것이 아니라, 내가 최상의 결정을 내릴 수 있도록 양질의 재료(양면적 분석)를 제공하는 것입니다.
- **언어:** 모든 결과물은 반드시 **한글**로만 작성해주세요.

## 핵심 투자 테마:
{investment_theme}

## 분석 목표:
위 투자 테마와 관련하여, 향후 5년간 **가장 높은 '위험 조정 수익률(Risk-Adjusted Return)' 잠재력**을 가진 유망 산업 Top 3와, 각 산업 내 핵심 종목 1~2개를 발굴하시오. 모든 분석은 **찬성론과 반대론을 함께 제시**하여 내가 합리적인 결정을 내릴 수 있도록 지원해야 합니다.

## 세부 분석 요건:
1.  **산업 분석:** 각 유망 산업의 시장 규모(TAM), 성장률(CAGR), 성장 동력(Bull Case)을 분석함과 동시에, **해당 산업의 가장 큰 약점과 투자자들이 간과하는 치명적인 리스크(Bear Case)**는 무엇인지 반드시 분석할 것.
2.  **종목 분석:** 각 핵심 종목의 비즈니스 모델, 기술적 해자(Bull Case)를 분석함과 동시에, **가장 비관적인 시나리오(Worst-Case Scenario)와 현재 밸류에이션의 거품 가능성(Bear Case)**도 함께 분석할 것.
{exclusion_section}

---
## 결과물 형식:
*각 산업/종목에 대해 아래 내용을 반드시 포함하여 보고서를 작성해주십시오.*

### **[산업명 1]**
- **찬성론 (Bull Case):** 이 산업이 왜 매력적인가? (성장 동력, TAM 등)
- **반대론 (Bear Case):** 이 산업의 가장 큰 리스크와 약점은 무엇인가?

#### **- 핵심 발굴 종목 1: [종목명]**
  - **찬성론 (Pros):** 이 종목이 가진 강점과 기회 요인.
  - **반대론 (Cons):** 이 종목의 약점과 잠재적 리스크.

### **[산업명 2]**
... (위와 동일한 형식으로 반복) ...

---
### **최종 의사결정을 위한 핵심 질문 (Key Questions for Decision):**
- **지시사항:** 위 모든 분석을 종합하여, 내가 이 산업/종목들에 대한 최종 투자를 '결정'하기 위해 스스로에게 던져야 할 가장 중요한 질문 3가지를 제시해주시오.

### **투자 노트 DB 생성을 위한 요약 (For DB Sync):**
- **지시사항:** 위에서 발굴된 각 핵심 종목에 대해, 내가 '투자 노트'를 새로 작성할 수 있도록 아래 형식에 맞춰 종목별로 요약해주십시오.
- **[종목명 1]**
  - **투자 아이디어 (Thesis):**
  - **핵심 촉매 (Catalysts):**
  - **핵심 리스크 (Risks):**
  - **핵심 모니터링 지표 (KPIs):**
- **[종목명 2]**
  - ... (위와 동일한 형식으로 반복) ...
"""
    
    return master_prompt_template.strip()

def render_exploration_page():
    """유망 종목 탐색기 페이지 렌더링"""
    
    st.title("🧭 유망 산업 및 종목 탐색기 (균형 분석)")
    st.markdown("나의 투자 아이디어를 입력하면, Deep Research에 사용할 균형 잡힌 분석 프롬프트를 생성해줍니다.")

    # 1. 사용자 입력 필드
    st.subheader("1. 나의 투자 아이디어 입력")
    user_idea = st.text_area(
        "label",
        placeholder="예시: 저는 인구 고령화와 자동화 트렌드에 관심이 많습니다. 특히, 노동력 부족 문제를 해결할 수 있는 로봇 기술이나, 노년층의 삶의 질을 높여주는 헬스케어 기술에 장기 투자하고 싶습니다.",
        height=150,
        label_visibility="collapsed"
    )

    user_exclusions = st.text_input(
        "선택: 제외할 산업/종목이 있다면 입력하세요.",
        placeholder="예시: 변동성이 큰 바이오 신약 개발 기업"
    )

    # 2. 프롬프트 생성 버튼 및 결과 출력
    st.subheader("2. Deep Research 프롬프트 생성")

    if st.button("🤖 균형 분석 프롬프트 생성하기", type="primary"):
        if not user_idea.strip():
            st.warning("투자 아이디어를 먼저 입력해주세요.")
        else:
            # 템플릿 기반으로 프롬프트 즉시 생성
            final_prompt = generate_exploration_prompt(user_idea, user_exclusions)
            
            st.markdown("""
            <div style="background-color: #d4edda; padding: 1rem; border-radius: 8px; border-left: 4px solid #28a745; margin-bottom: 1rem;">
                <h4 style="color: #155724; margin: 0;">✅ 유망 종목 탐색 프롬프트</h4>
                <p style="color: #155724; margin: 0.5rem 0 0 0; font-size: 0.9rem;">균형 잡힌 시각의 산업 및 종목 발굴 프롬프트입니다</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.info("💡 아래 프롬프트를 복사하여 Deep Research에 사용하세요.")
            
            # 프롬프트 표시
            st.code(
                final_prompt,
                language="text",
                line_numbers=False
            )
            
            # 복사 안내
            st.markdown("""
            <div style="background-color: #fff3cd; padding: 1rem; border-radius: 8px; border-left: 4px solid #ffc107; margin: 1rem 0;">
                <h5 style="color: #856404; margin: 0;">📋 복사 방법</h5>
                <ol style="color: #856404; margin: 0.5rem 0 0 0; padding-left: 1.5rem;">
                    <li>위 프롬프트 박스를 클릭하여 전체 선택 (Ctrl+A 또는 Cmd+A)</li>
                    <li>복사 (Ctrl+C 또는 Cmd+C)</li>
                    <li>Deep Research에 붙여넣기 (Ctrl+V 또는 Cmd+V)</li>
                </ol>
            </div>
            """, unsafe_allow_html=True)
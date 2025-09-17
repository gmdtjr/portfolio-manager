import streamlit as st

def generate_exploration_prompt(investment_idea: str, exclusions: str = "") -> str:
    """
    사용자의 투자 아이디어와 제외 조건을 받아
    최적화된 Deep Research 프롬프트를 생성합니다.
    """
    
    # 사용자의 자유 서술형 아이디어를 프롬프트의 '핵심 투자 테마'로 그대로 사용합니다.
    investment_theme = investment_idea.strip()
    
    # 제외 조건이 있을 경우, 프롬프트에 해당 섹션을 추가합니다.
    exclusion_section = ""
    if exclusions.strip():
        exclusion_section = f"3.  **제외 조건:** {exclusions.strip()}과 같이 변동성이 매우 높거나 특정된 분야는 분석에서 제외할 것."

    # 마스터 프롬프트 템플릿
    master_prompt_template = f"""# 유망 산업 및 종목 발굴 보고서 (비판적 분석 포함)

## **[중요 지시사항]**
- **역할 부여:** 당신은 낙관적인 성장주 투자자와, 그 아이디어를 끊임없이 의심하는 **비판적인 리스크 분석가**, 두 가지 역할을 동시에 수행하는 AI입니다.
- **언어:** 모든 결과물은 반드시 **한글**로만 작성해주세요.

## **핵심 투자 테마:**
{investment_theme}

## **분석 목표:**
위 투자 테마와 관련하여, 향후 5년간 **가장 높은 '위험 조정 수익률(Risk-Adjusted Return)' 잠재력**을 가진 유망 산업 Top 3와, 각 산업 내 핵심 종목 1~2개를 발굴하시오. 단순히 성장성만 보는 것이 아니라, **잠재적 리스크 대비 보상이 매력적인지**를 기준으로 평가해야 합니다.

## **세부 분석 요건:**
1.  **산업 분석:** 각 유망 산업의 시장 규모(TAM), 성장률(CAGR), 성장 동력을 분석함과 동시에, **해당 산업의 가장 큰 약점과 투자자들이 간과하는 치명적인 리스크(Hidden Risk)**는 무엇인지 반드시 분석할 것.
2.  **종목 분석:** 각 핵심 종목의 비즈니스 모델, 기술적 해자, 재무 건전성을 분석함과 동시에, **가장 비관적인 시나리오(Worst-Case Scenario)를 가정**했을 때 예상되는 문제점과 **현재 밸류에이션의 거품(Bubble) 가능성**도 함께 분석할 것.
{exclusion_section}

## **결과물 형식:**
*각 산업/종목에 대해 아래 내용을 반드시 포함하여 보고서를 작성해주십시오.*

### **[산업명 1]**
- **기회 요인 (Bull Case):** 이 산업이 왜 매력적인가? (성장 동력, TAM 등)
- **위험 요인 (Bear Case):** 이 산업의 가장 큰 리스크와 약점은 무엇인가?
- **종합 의견:** 위험 요인에도 불구하고 투자가 유망하다고 판단하는 이유는?

#### **- 핵심 추천 종목 1: [종목명]**
  - **투자 매력도 (Pros):** 이 종목이 가진 강점과 기회.
  - **투자 유의점 (Cons):** 이 종목의 약점과 잠재적 리스크.
  - **최종 결론:** 'Cons'에도 불구하고 이 종목을 추천하는 핵심 논리.
"""
    
    return master_prompt_template.strip()

def render_exploration_page():
    """유망 종목 탐색기 페이지 렌더링"""
    
    # 페이지 헤더
    st.markdown("""
    <div style="text-align: center; padding: 1.5rem 0; background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); border-radius: 10px; margin-bottom: 2rem;">
        <h1 style="color: white; margin: 0; font-size: 2rem;">🧭 유망 산업 및 종목 탐색기</h1>
        <p style="color: #f0f0f0; margin: 0.5rem 0 0 0; font-size: 1rem;">나의 투자 아이디어를 입력하면 Deep Research에 사용할 최적의 분석 프롬프트를 생성합니다</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 기능 설명
    st.markdown("### 💡 기능 설명")
    st.markdown("""
    <div style="background-color: #e3f2fd; padding: 1.5rem; border-radius: 10px; border-left: 4px solid #2196f3; margin-bottom: 2rem;">
        <h4 style="color: #1976d2; margin: 0;">🧭 유망 종목 탐색기</h4>
        <ul style="color: #1976d2; margin: 0.5rem 0 0 0; padding-left: 1.5rem;">
            <li>투자 아이디어를 입력하면 최적화된 Deep Research 프롬프트 생성</li>
            <li>유망 산업 Top 3 및 핵심 종목 발굴을 위한 체계적 분석 프롬프트</li>
            <li>제외 조건 설정으로 원하는 분석 범위 조정 가능</li>
            <li>Deep Research에 바로 사용할 수 있는 완성된 프롬프트 제공</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    # 사용자 입력 필드
    st.markdown("### 📝 나의 투자 아이디어 입력")
    
    # 입력 안내
    st.markdown("""
    <div style="background-color: #f8f9fa; padding: 1.5rem; border-radius: 10px; border-left: 4px solid #667eea; margin-bottom: 1rem;">
        <p style="margin: 0; color: #495057; font-size: 0.95rem;">관심 있는 투자 테마나 아이디어를 자유롭게 서술해주세요</p>
    </div>
    """, unsafe_allow_html=True)
    
    user_idea = st.text_area(
        "투자 아이디어를 자유롭게 입력하세요",
        placeholder="예시: 저는 인구 고령화와 자동화 트렌드에 관심이 많습니다. 특히, 노동력 부족 문제를 해결할 수 있는 로봇 기술이나, 노년층의 삶의 질을 높여주는 헬스케어 기술에 장기 투자하고 싶습니다.",
        height=150,
        help="관심 있는 투자 테마나 아이디어를 자유롭게 서술해주세요."
    )
    
    user_exclusions = st.text_input(
        "선택: 제외할 산업/종목이 있다면 입력하세요",
        placeholder="예시: 변동성이 큰 바이오 신약 개발 기업",
        help="분석에서 제외하고 싶은 산업이나 종목 유형을 입력하세요."
    )
    
    # 프롬프트 생성 버튼 및 결과 출력
    st.markdown("### 🚀 Deep Research 프롬프트 생성")
    
    if st.button("🤖 최적 프롬프트 생성하기", type="primary", use_container_width=True):
        if not user_idea.strip():
            st.markdown("""
            <div style="background-color: #fff3cd; padding: 1rem; border-radius: 8px; border-left: 4px solid #ffc107; margin-bottom: 1rem;">
                <h4 style="color: #856404; margin: 0;">⚠️ 입력 필요</h4>
                <p style="color: #856404; margin: 0.5rem 0 0 0; font-size: 0.9rem;">투자 아이디어를 먼저 입력해주세요.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            # 템플릿 기반으로 프롬프트 즉시 생성
            final_prompt = generate_exploration_prompt(user_idea, user_exclusions)
            
            st.markdown("""
            <div style="background-color: #d4edda; padding: 1rem; border-radius: 8px; border-left: 4px solid #28a745; margin-bottom: 1rem;">
                <h4 style="color: #155724; margin: 0;">✅ 프롬프트 생성 완료</h4>
                <p style="color: #155724; margin: 0.5rem 0 0 0; font-size: 0.9rem;">아래 프롬프트를 복사하여 Deep Research에 사용하세요</p>
            </div>
            """, unsafe_allow_html=True)
            
            # 생성된 프롬프트 표시
            st.text_area(
                "생성된 Deep Research 프롬프트",
                value=final_prompt,
                height=400,
                help="이 프롬프트를 Deep Research에 붙여넣어 사용하세요."
            )
            
            # 복사 방법 안내
            st.markdown("""
            <div style="background-color: #fff3cd; padding: 1rem; border-radius: 8px; border-left: 4px solid #ffc107; margin: 1rem 0;">
                <h5 style="color: #856404; margin: 0;">📋 복사 방법</h5>
                <ol style="color: #856404; margin: 0.5rem 0 0 0; padding-left: 1.5rem;">
                    <li>위 텍스트 박스에서 전체 텍스트를 선택 (Ctrl+A 또는 Cmd+A)</li>
                    <li>복사 (Ctrl+C 또는 Cmd+C)</li>
                    <li>Deep Research에 붙여넣기 (Ctrl+V 또는 Cmd+V)</li>
                </ol>
            </div>
            """, unsafe_allow_html=True)
            
            # 프롬프트 미리보기
            st.markdown("### 📄 프롬프트 미리보기")
            st.code(final_prompt, language="markdown")
    
    # 예시 섹션
    st.markdown("---")
    st.markdown("### 💡 투자 아이디어 예시")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🌱 ESG 투자**")
        st.code("""
저는 지속가능한 발전에 관심이 많습니다. 
특히 친환경 에너지, 전기차, 
그리고 ESG 경영을 실천하는 기업들에 
장기 투자하고 싶습니다.
        """, language="text")
    
    with col2:
        st.markdown("**🤖 AI/디지털 전환**")
        st.code("""
인공지능과 디지털 전환이 
산업 전반에 미치는 영향을 보고 싶습니다.
특히 제조업, 금융업, 헬스케어에서 
AI를 활용하는 기업들에 관심이 있습니다.
        """, language="text")
    
    col3, col4 = st.columns(2)
    
    with col3:
        st.markdown("**🏥 헬스케어**")
        st.code("""
고령화 사회에서 헬스케어 산업의 
성장 가능성을 보고 싶습니다.
특히 디지털 헬스케어, 
바이오 기술, 의료기기 분야에 
투자하고 싶습니다.
        """, language="text")
    
    with col4:
        st.markdown("**🌐 글로벌 소비**")
        st.code("""
중국, 인도 등 신흥국의 
소비 증가 트렌드에 관심이 있습니다.
특히 프리미엄 브랜드, 
럭셔리 상품, 온라인 쇼핑 등에 
투자하고 싶습니다.
        """, language="text")
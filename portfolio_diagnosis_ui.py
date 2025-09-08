"""
포트폴리오 정밀 진단기 UI 모듈
Streamlit UI를 통해 포트폴리오 정밀 진단 프롬프트를 생성하는 인터페이스를 제공합니다.
"""

import streamlit as st
from portfolio_diagnosis_generator import PortfolioDiagnosisGenerator


def render_portfolio_diagnosis_page():
    """포트폴리오 정밀 진단기 페이지 렌더링"""
    
    st.title("⚖️ 포트폴리오 정밀 진단기")
    st.markdown("버튼을 클릭하면, Deep Research에 사용할 포트폴리오 종합 건강검진 프롬프트를 생성합니다.")
    
    # 분석기 초기화
    try:
        generator = PortfolioDiagnosisGenerator()
    except Exception as e:
        st.error(f"❌ 포트폴리오 정밀 진단기 초기화 실패: {e}")
        return
    
    # 사용 전 안내
    st.info("💡 이 기능을 사용하기 전, Deep Research에 `포트폴리오_현황.csv`와 `투자_노트.csv` 파일을 먼저 첨부해야 합니다.")
    
    # 프롬프트 생성 버튼 및 결과 출력
    st.subheader("포트폴리오 진단 프롬프트 생성")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("🩺 내 포트폴리오 정밀 진단 시작하기", type="primary", key="generate_diagnosis_btn", use_container_width=True):
            try:
                # 프롬프트 생성
                with st.spinner("포트폴리오 진단 프롬프트를 생성하고 있습니다..."):
                    final_prompt = generator.generate_diagnosis_prompt()
                
                # 세션 상태에 저장
                st.session_state['diagnosis_prompt'] = final_prompt
                
                st.success("✅ 포트폴리오 정밀 진단 프롬프트가 생성되었습니다!")
                
            except Exception as e:
                st.error(f"❌ 프롬프트 생성 실패: {e}")
    
    with col2:
        if st.button("🔄 새로고침", key="refresh_btn"):
            # 세션 상태 초기화
            if 'diagnosis_prompt' in st.session_state:
                del st.session_state['diagnosis_prompt']
            st.rerun()
    
    # 생성된 프롬프트 표시
    if 'diagnosis_prompt' in st.session_state and st.session_state['diagnosis_prompt']:
        st.subheader("생성된 포트폴리오 진단 프롬프트")
        
        st.success("🎯 **포트폴리오 정밀 진단 프롬프트** - 포트폴리오 전체의 구조적 건강 상태를 종합 분석하는 프롬프트입니다.")
        
        st.info("💡 아래 프롬프트를 복사하여 Deep Research에 사용하세요.")
        
        # 프롬프트 표시
        st.code(
            st.session_state['diagnosis_prompt'],
            language="text",
            line_numbers=False
        )
        
        # 복사 안내
        st.markdown("""
        **📋 복사 방법:**
        1. 위 프롬프트 박스를 클릭하여 전체 선택 (Ctrl+A 또는 Cmd+A)
        2. 복사 (Ctrl+C 또는 Cmd+C)
        3. Deep Research에 붙여넣기 (Ctrl+V 또는 Cmd+V)
        """)
        
        # 추가 기능들
        st.subheader("추가 기능")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📊 프롬프트 미리보기", key="preview_btn"):
                st.info("프롬프트가 위에 표시되어 있습니다.")
        
        with col2:
            if st.button("🗑️ 프롬프트 삭제", key="delete_btn"):
                if 'diagnosis_prompt' in st.session_state:
                    del st.session_state['diagnosis_prompt']
                st.rerun()
        
        with col3:
            if st.button("🔄 새 진단", key="new_diagnosis_btn"):
                if 'diagnosis_prompt' in st.session_state:
                    del st.session_state['diagnosis_prompt']
                st.rerun()
    
    # 사용법 안내
    with st.expander("📖 사용법 안내", expanded=False):
        st.markdown("""
        ### ⚖️ 포트폴리오 정밀 진단기 사용법
        
        **1단계: 파일 준비**
        - Deep Research에 `포트폴리오_현황.csv`와 `투자_노트.csv` 파일을 먼저 첨부하세요
        - 이 파일들은 포트폴리오의 정확한 진단을 위해 필요합니다
        
        **2단계: 진단 프롬프트 생성**
        - "내 포트폴리오 정밀 진단 시작하기" 버튼을 클릭하세요
        - 포트폴리오 전체의 구조적 건강 상태를 분석하는 프롬프트가 생성됩니다
        
        **3단계: Deep Research 활용**
        - 생성된 프롬프트를 복사하여 Deep Research에 붙여넣으세요
        - 포트폴리오 종합 건강검진 보고서를 받을 수 있습니다
        
        ### 🔍 진단 항목
        1. **자산 배분 분석** - 주식/현금 비중, 지역별 배분 적절성
        2. **섹터 집중도 분석** - 특정 섹터 편중 리스크, 소외 섹터 점검
        3. **종목 간 상관관계 분석** - 분산 효과 점검
        4. **투자 노트와 실제 포트폴리오 괴리 분석** - 신념과 비중의 불일치 점검
        
        ### 📊 결과물
        - **진단 결과**: 종합 건강 점수 (A/B/C/D) 및 항목별 진단
        - **개선 제안**: 구체적인 리밸런싱 전략 2~3가지
        - **모니터링 지표**: 향후 추적해야 할 핵심 지표 3가지
        
        ### 💡 팁
        - 정기적으로 사용하여 포트폴리오의 건강 상태를 점검하세요
        - 진단 결과를 바탕으로 리밸런싱을 고려해보세요
        - 생성된 프롬프트는 세션 동안 유지되므로 언제든지 복사할 수 있습니다
        """)


if __name__ == "__main__":
    # 테스트용 실행
    render_portfolio_diagnosis_page()

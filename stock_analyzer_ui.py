"""
종목 상세 분석기 UI 모듈
Streamlit UI를 통해 DB 연동 종목 상세 분석 프롬프트를 생성하는 인터페이스를 제공합니다.
"""

import streamlit as st
import os
from stock_analyzer_generator import StockAnalyzerGenerator


def get_secret(key):
    """Streamlit secrets 또는 환경변수에서 값 가져오기"""
    try:
        if hasattr(st, 'secrets') and st.secrets:
            return st.secrets.get(key)
    except Exception:
        pass
    return os.getenv(key)


def render_stock_analyzer_page():
    """종목 상세 분석기 페이지 렌더링"""
    
    st.title("🔬 종목 상세 분석기")
    st.markdown("분석할 종목을 입력하면, **투자 노트의 유무에 따라 맞춤형 분석 프롬프트**를 생성합니다.")
    
    # 설정값 확인
    spreadsheet_id = get_secret('GOOGLE_SPREADSHEET_ID')
    
    if not spreadsheet_id:
        st.error("❌ Secret 'GOOGLE_SPREADSHEET_ID'가 설정되지 않았습니다.")
        st.info("💡 환경변수 또는 Streamlit secrets에서 GOOGLE_SPREADSHEET_ID를 설정해주세요.")
        return
    
    # 분석기 초기화
    try:
        generator = StockAnalyzerGenerator(spreadsheet_id)
    except Exception as e:
        st.error(f"❌ 종목 상세 분석기 초기화 실패: {e}")
        return
    
    # 사용자 입력 필드
    st.subheader("1. 분석할 종목 입력")
    user_stock_name = st.text_input(
        "종목명 또는 코드",
        placeholder="예시: ASML, 엔비디아, 005930, 삼성전자",
        label_visibility="collapsed",
        key="stock_name_input"
    )
    
    # 프롬프트 생성 버튼 및 결과 출력
    st.subheader("2. Deep Research 프롬프트 생성")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("📄 상세 분석 프롬프트 생성하기", type="primary", key="generate_prompt_btn"):
            if not user_stock_name.strip():
                st.warning("⚠️ 분석할 종목의 이름이나 코드를 먼저 입력해주세요.")
            else:
                try:
                    # 프롬프트 생성
                    with st.spinner("프롬프트를 생성하고 있습니다..."):
                        final_prompt, found_in_db = generator.generate_deep_dive_prompt(user_stock_name)
                    
                    # 세션 상태에 저장
                    st.session_state['generated_prompt'] = final_prompt
                    st.session_state['analyzed_stock'] = user_stock_name.strip()
                    st.session_state['found_in_db'] = found_in_db
                    
                    if found_in_db:
                        st.success(f"✅ '{user_stock_name.strip()}' 정보를 투자 노트에서 찾았습니다! 맞춤형 검증 프롬프트가 생성되었습니다.")
                    else:
                        st.info(f"ℹ️ '{user_stock_name.strip()}' 정보가 투자 노트에 없습니다. 표준 분석 프롬프트가 생성되었습니다.")
                    
                except Exception as e:
                    st.error(f"❌ 프롬프트 생성 실패: {e}")
    
    with col2:
        if st.button("🔄 새로고침", key="refresh_btn"):
            # 세션 상태 초기화
            if 'generated_prompt' in st.session_state:
                del st.session_state['generated_prompt']
            if 'analyzed_stock' in st.session_state:
                del st.session_state['analyzed_stock']
            if 'found_in_db' in st.session_state:
                del st.session_state['found_in_db']
            st.rerun()
    
    # 생성된 프롬프트 표시
    if 'generated_prompt' in st.session_state and st.session_state['generated_prompt']:
        st.subheader(f"3. {st.session_state['analyzed_stock']} 분석 프롬프트")
        
        # 프롬프트 타입 표시
        if st.session_state.get('found_in_db', False):
            st.success("🎯 **맞춤형 검증 프롬프트** - 투자 노트 기반으로 생성된 개인화된 분석 프롬프트입니다.")
        else:
            st.info("📊 **표준 분석 프롬프트** - 일반적인 종목 분석 프롬프트입니다.")
        
        st.info("💡 아래 프롬프트를 복사하여 Deep Research에 사용하세요.")
        
        # 프롬프트 표시
        st.code(
            st.session_state['generated_prompt'],
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
        st.subheader("4. 추가 기능")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📊 프롬프트 미리보기", key="preview_btn"):
                st.info("프롬프트가 위에 표시되어 있습니다.")
        
        with col2:
            if st.button("🗑️ 프롬프트 삭제", key="delete_btn"):
                if 'generated_prompt' in st.session_state:
                    del st.session_state['generated_prompt']
                if 'analyzed_stock' in st.session_state:
                    del st.session_state['analyzed_stock']
                if 'found_in_db' in st.session_state:
                    del st.session_state['found_in_db']
                st.rerun()
        
        with col3:
            if st.button("📈 다른 종목 분석", key="new_analysis_btn"):
                if 'generated_prompt' in st.session_state:
                    del st.session_state['generated_prompt']
                if 'analyzed_stock' in st.session_state:
                    del st.session_state['analyzed_stock']
                if 'found_in_db' in st.session_state:
                    del st.session_state['found_in_db']
                st.rerun()
    
    # 사용법 안내
    with st.expander("📖 사용법 안내", expanded=False):
        st.markdown("""
        ### 🔬 종목 상세 분석기 사용법
        
        **1단계: 종목 입력**
        - 분석하고 싶은 종목의 이름이나 코드를 입력하세요
        - 예시: ASML, 엔비디아, 005930, 삼성전자, 애플 등
        
        **2단계: 프롬프트 생성**
        - "상세 분석 프롬프트 생성하기" 버튼을 클릭하세요
        - 시스템이 자동으로 투자 노트를 확인합니다
        
        **3단계: 맞춤형 분석**
        - **투자 노트에 정보가 있는 경우**: 나의 기존 투자 아이디어를 검증하는 맞춤형 프롬프트 생성
        - **투자 노트에 정보가 없는 경우**: 일반적인 종목 분석 프롬프트 생성
        
        **4단계: Deep Research 활용**
        - 생성된 프롬프트를 복사하여 Deep Research에 붙여넣으세요
        - 종합적인 기업 분석 보고서를 받을 수 있습니다
        
        ### 🎯 맞춤형 검증 프롬프트 (투자 노트 연동 시)
        1. **기업 개요** - 비즈니스 모델이 나의 투자 아이디어와 부합하는가?
        2. **산업 분석** - 산업 전망이 나의 투자 아이디어를 뒷받침하는가?
        3. **경제적 해자** - 나의 가설이 여전히 유효한가?
        4. **성장 동력** - 내가 기대한 촉매가 현실화될 조짐이 있는가?
        5. **핵심 리스크** - 내가 우려한 리스크가 현실화되고 있는가?
        6. **재무 분석** - 재무 데이터가 나의 기대감을 뒷받침하는가?
        7. **밸류에이션** - 현재 밸류에이션이 매력적인 진입점인가?
        8. **종합 결론** - 투자 아이디어 유지/수정/폐기 결정
        9. **투자 노트 동기화 요약** - 투자 노트 업데이트를 위한 핵심 내용 요약
        
        ### 📊 표준 분석 프롬프트 (투자 노트 없을 시)
        1. **기업 개요** - 비즈니스 모델과 핵심 제품/서비스
        2. **산업 분석** - 산업 구조와 성장 전망
        3. **경제적 해자** - 경쟁 우위와 지속 가능성
        4. **성장 동력** - 향후 성장을 이끌 핵심 동력
        5. **핵심 리스크** - 투자 아이디어를 훼손할 수 있는 리스크
        6. **재무 분석** - 핵심 재무 지표와 건전성 평가
        7. **밸류에이션** - 동종 업계 대비 주가 수준 평가
        8. **종합 결론** - 최종 투자의견과 핵심 근거
        
        ### 💡 팁
        - 투자 노트에 기록된 종목은 더욱 정교한 맞춤형 분석을 받을 수 있습니다
        - 정확한 종목명을 입력하면 더 정확한 분석을 받을 수 있습니다
        - 생성된 프롬프트는 세션 동안 유지되므로 언제든지 복사할 수 있습니다
        - 다른 종목을 분석하려면 "새로고침" 버튼을 사용하세요
        """)


if __name__ == "__main__":
    # 테스트용 실행
    render_stock_analyzer_page()

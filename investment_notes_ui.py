"""
투자 노트 UI 모듈
기업 보고서를 분석하여 투자 노트를 자동 생성하는 UI 기능을 제공합니다.
"""

import streamlit as st
import os
from investment_note_generator import InvestmentNoteGenerator


def get_secret(key):
    """환경변수 또는 Streamlit secrets에서 값을 가져옵니다."""
    try:
        return st.secrets[key]
    except:
        return os.getenv(key)


def render_investment_notes_page():
    """투자 노트 자동 생성 페이지를 렌더링합니다."""
    st.header("📝 투자 노트 자동 생성")
    st.markdown("기업 보고서를 입력하면 AI가 자동으로 투자 노트 초안을 생성합니다.")
    
    # 환경변수 확인
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

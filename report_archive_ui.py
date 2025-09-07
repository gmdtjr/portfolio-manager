"""
보고서 아카이브 UI 모듈
Deep Research 보고서를 저장, 조회, 검색하는 UI 기능을 제공합니다.
"""

import streamlit as st
import os
from report_archive_manager import ReportArchiveManager


def get_secret(key):
    """환경변수 또는 Streamlit secrets에서 값을 가져옵니다."""
    try:
        return st.secrets[key]
    except:
        return os.getenv(key)


def render_report_archive_page():
    """보고서 아카이브 페이지를 렌더링합니다."""
    # 환경변수 확인
    spreadsheet_id = get_secret('GOOGLE_SPREADSHEET_ID')
    google_api_key = get_secret('GOOGLE_API_KEY')
    
    if not spreadsheet_id:
        st.error("❌ GOOGLE_SPREADSHEET_ID가 설정되지 않았습니다.")
        return
    
    if not google_api_key:
        st.error("❌ GOOGLE_API_KEY가 설정되지 않았습니다.")
        st.info("💡 보고서 요약 생성 기능을 사용하려면 Gemini API 키가 필요합니다.")
        return
    
    try:
        # 보고서 아카이브 관리자 초기화
        archive_manager = ReportArchiveManager(spreadsheet_id, google_api_key)
        
        # 기능 설명
        st.info("""
        **📚 보고서 아카이브**
        • Deep Research에서 생성된 보고서를 체계적으로 저장
        • AI가 자동으로 보고서 요약 및 관련 종목 추출
        • 과거 보고서 검색 및 조회 기능
        • 투자 인사이트 누적 및 분석
        """)
        
        # 탭으로 기능 구분
        tab1, tab2, tab3 = st.tabs(["📝 보고서 저장", "📋 보고서 목록", "🔍 보고서 검색"])
        
        with tab1:
            st.subheader("📝 새로운 보고서 저장")
            
            # 사용된 프롬프트 입력
            used_prompt = st.text_area(
                "사용된 프롬프트 (선택사항)",
                height=100,
                help="Deep Research에서 사용한 프롬프트를 입력하세요. 비워두어도 됩니다."
            )
            
            # 보고서 원문 입력
            report_content = st.text_area(
                "보고서 원문",
                height=400,
                help="Deep Research에서 생성된 보고서 전체 내용을 붙여넣으세요."
            )
            
            if st.button("💾 보고서 저장", type="primary", use_container_width=True):
                if not report_content.strip():
                    st.error("❌ 보고서 원문을 입력해주세요.")
                else:
                    try:
                        with st.spinner("🤖 보고서를 분석하고 저장하고 있습니다..."):
                            result = archive_manager.save_report(report_content, used_prompt)
                            
                            if result['success']:
                                st.success(f"✅ {result['message']}")
                                
                                # 저장된 정보 표시
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.info(f"**보고서 ID:** {result['report_id']}")
                                    st.info(f"**생성일:** {result['creation_date']}")
                                with col2:
                                    st.info(f"**관련 종목:** {result['related_stocks']}")
                                
                                # 요약 표시
                                st.markdown("### 📄 생성된 요약")
                                st.write(result['summary'])
                                
                            else:
                                st.error(f"❌ {result['message']}")
                                
                    except Exception as e:
                        st.error(f"❌ 보고서 저장 실패: {e}")
                        import traceback
                        st.error(f"상세 오류: {traceback.format_exc()}")
        
        with tab2:
            st.subheader("📋 저장된 보고서 목록")
            
            if st.button("🔄 목록 새로고침", use_container_width=True):
                st.rerun()
            
            try:
                with st.spinner("📋 보고서 목록을 불러오고 있습니다..."):
                    reports_df = archive_manager.get_recent_reports(20)
                    
                    if reports_df.empty:
                        st.info("📭 저장된 보고서가 없습니다.")
                    else:
                        st.success(f"📊 총 {len(reports_df)}개의 보고서가 있습니다.")
                        
                        # 보고서 목록 표시
                        for idx, row in reports_df.iterrows():
                            with st.expander(f"📄 {row['보고서_ID']} - {row['생성일']} ({row['관련_종목']})"):
                                col1, col2 = st.columns([2, 1])
                                
                                with col1:
                                    st.markdown("**📄 요약:**")
                                    st.write(row['보고서_요약'])
                                    
                                    if row['사용된_프롬프트']:
                                        st.markdown("**🎯 사용된 프롬프트:**")
                                        st.code(row['사용된_프롬프트'], language="text")
                                
                                with col2:
                                    st.markdown("**📊 정보:**")
                                    st.write(f"**ID:** {row['보고서_ID']}")
                                    st.write(f"**생성일:** {row['생성일']}")
                                    st.write(f"**관련 종목:** {row['관련_종목']}")
                                    
                                    # 원문 보기 버튼
                                    if st.button(f"📖 원문 보기", key=f"view_{row['보고서_ID']}"):
                                        st.text_area("보고서 원문", row['보고서_원문'], height=300, key=f"content_{row['보고서_ID']}")
                        
            except Exception as e:
                st.error(f"❌ 보고서 목록 조회 실패: {e}")
        
        with tab3:
            st.subheader("🔍 보고서 검색")
            
            # 검색 키워드 입력
            search_keyword = st.text_input(
                "검색 키워드",
                help="종목명, 키워드, 내용 등을 입력하여 보고서를 검색하세요."
            )
            
            if st.button("🔍 검색", use_container_width=True):
                if not search_keyword.strip():
                    st.error("❌ 검색 키워드를 입력해주세요.")
                else:
                    try:
                        with st.spinner("🔍 보고서를 검색하고 있습니다..."):
                            search_results = archive_manager.search_reports(search_keyword)
                            
                            if search_results.empty:
                                st.info(f"📭 '{search_keyword}'와 관련된 보고서를 찾을 수 없습니다.")
                            else:
                                st.success(f"📊 '{search_keyword}' 관련 보고서 {len(search_results)}개를 찾았습니다.")
                                
                                # 검색 결과 표시
                                for idx, row in search_results.iterrows():
                                    with st.expander(f"📄 {row['보고서_ID']} - {row['생성일']} ({row['관련_종목']})"):
                                        col1, col2 = st.columns([2, 1])
                                        
                                        with col1:
                                            st.markdown("**📄 요약:**")
                                            st.write(row['보고서_요약'])
                                        
                                        with col2:
                                            st.markdown("**📊 정보:**")
                                            st.write(f"**ID:** {row['보고서_ID']}")
                                            st.write(f"**생성일:** {row['생성일']}")
                                            st.write(f"**관련 종목:** {row['관련_종목']}")
                                        
                                        # 원문 보기 버튼
                                        if st.button(f"📖 원문 보기", key=f"search_view_{row['보고서_ID']}"):
                                            st.text_area("보고서 원문", row['보고서_원문'], height=300, key=f"search_content_{row['보고서_ID']}")
                            
                    except Exception as e:
                        st.error(f"❌ 보고서 검색 실패: {e}")
        
    except Exception as e:
        st.error(f"❌ 보고서 아카이브 초기화 실패: {e}")
        import traceback
        st.error(f"상세 오류: {traceback.format_exc()}")

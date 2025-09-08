"""
데일리 브리핑 UI 모듈
포트폴리오 데이터와 투자 노트를 기반으로 데일리 브리핑 프롬프트를 생성하는 UI 기능을 제공합니다.
"""

import streamlit as st
import os
from datetime import datetime
from daily_briefing_generator import DailyBriefingGenerator


def get_secret(key):
    """환경변수 또는 Streamlit secrets에서 값을 가져옵니다."""
    try:
        return st.secrets[key]
    except:
        return os.getenv(key)


def get_time_window_text(selection: str) -> str:
    """UI 선택에 따라 시간 범위 텍스트를 반환합니다."""
    if "48시간" in selection:
        return "지난 48시간 동안"
    if "72시간" in selection:
        return "지난 72시간 동안"
    if "1주일" in selection:
        return "지난 1주일 동안"
    return "지난 24시간 동안" # Default


def render_daily_briefing_page():
    """데일리 브리핑 생성기 페이지를 렌더링합니다."""
    
    # 페이지 헤더
    st.markdown("""
    <div style="text-align: center; padding: 1.5rem 0; background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); border-radius: 10px; margin-bottom: 2rem;">
        <h1 style="color: white; margin: 0; font-size: 2rem;">🎯 데일리 브리핑 생성기</h1>
        <p style="color: #f0f0f0; margin: 0.5rem 0 0 0; font-size: 1rem;">매크로 이슈 분석 + 포트폴리오 데이터 + 완성된 프롬프트 생성</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 환경변수 확인
    spreadsheet_id = get_secret('GOOGLE_SPREADSHEET_ID')
    google_api_key = get_secret('GOOGLE_API_KEY')
    
    if not spreadsheet_id:
        st.markdown("""
        <div style="background-color: #f8d7da; padding: 1rem; border-radius: 8px; border-left: 4px solid #dc3545; margin-bottom: 1rem;">
            <h4 style="color: #721c24; margin: 0;">❌ 설정 오류</h4>
            <p style="color: #721c24; margin: 0.5rem 0 0 0; font-size: 0.9rem;">GOOGLE_SPREADSHEET_ID가 설정되지 않았습니다.</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    if not google_api_key:
        st.markdown("""
        <div style="background-color: #f8d7da; padding: 1rem; border-radius: 8px; border-left: 4px solid #dc3545; margin-bottom: 1rem;">
            <h4 style="color: #721c24; margin: 0;">❌ 설정 오류</h4>
            <p style="color: #721c24; margin: 0.5rem 0 0 0; font-size: 0.9rem;">GOOGLE_API_KEY가 설정되지 않았습니다. 프롬프트 생성 기능을 사용할 수 없습니다.</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # 데일리 브리핑 생성기 import
    try:
        from daily_briefing_generator import DailyBriefingGenerator
        DAILY_BRIEFING_AVAILABLE = True
    except ImportError as e:
        st.error(f"❌ 데일리 브리핑 생성기를 불러올 수 없습니다: {e}")
        DAILY_BRIEFING_AVAILABLE = False
    
    if DAILY_BRIEFING_AVAILABLE:
        try:
            # 데일리 브리핑 생성기 초기화
            generator = DailyBriefingGenerator(spreadsheet_id)
            
            # 기능 설명
            st.info("""
            **📊 데일리 브리핑 생성기**
            • 포트폴리오와 투자 노트 데이터 통합 분석
            • 전문적인 데일리 브리핑 프롬프트 생성
            • CSV 파일 다운로드 기능 포함
            • Deep Research에 바로 사용 가능한 완성된 패키지 제공
            """)
            
            # 시간 범위 선택
            st.subheader("⏰ 분석 기간 선택")
            time_window_selection = st.radio(
                "분석 기간을 선택하세요:",
                ('24시간', '48시간', '72시간', '1주일'),
                horizontal=True,
                help="몇 일 동안의 뉴스를 분석할지 선택하세요"
            )
            
            time_window_text = get_time_window_text(time_window_selection)
            st.info(f"📅 선택된 분석 기간: **{time_window_text}**")
            
            # 완전한 패키지 생성 기능
            st.subheader("🎯 완전한 패키지 생성")
            st.info("""
            **🎯 원클릭 완전 자동화**
            • 클릭 한 번으로 모든 재료 준비 완료
            • 포트폴리오 CSV + 투자노트 CSV + 완성된 프롬프트
            • 딥 리서치에 바로 사용할 수 있는 완전한 패키지
            • 더 이상 수동 작업 불필요!
            """)
            
            if st.button("🎯 완전한 패키지 생성", type="primary", use_container_width=True):
                try:
                    with st.spinner("🚀 모든 재료를 준비하고 있습니다... (최대 2분 소요)"):
                        # 완전한 패키지 생성
                        package = generator.generate_complete_package(time_window_text)
                        
                        if 'error' in package:
                            st.error(f"❌ 패키지 생성 실패: {package['error']}")
                            return
                        
                        # 성공 메시지
                        st.success("🎉 완전한 패키지가 준비되었습니다!")
                        st.info(f"📅 생성 시간: {package['timestamp']}")
                        
                        # 탭으로 구분하여 표시
                        tab1, tab2, tab3, tab4 = st.tabs(["📋 완성된 프롬프트", "📊 포트폴리오 CSV", "📝 투자노트 CSV", "📈 데이터 미리보기"])
                        
                        with tab1:
                            st.markdown("### 🎯 Deep Research에 바로 사용할 프롬프트")
                            
                            # 프롬프트 타입 표시
                            st.markdown("""
                            <div style="background-color: #d4edda; padding: 1rem; border-radius: 8px; border-left: 4px solid #28a745; margin-bottom: 1rem;">
                                <h4 style="color: #155724; margin: 0;">🎯 데일리 브리핑 프롬프트</h4>
                                <p style="color: #155724; margin: 0.5rem 0 0 0; font-size: 0.9rem;">매크로 분석과 포트폴리오 데이터를 종합한 완성된 프롬프트입니다</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            st.text_area("완성된 데일리 브리핑 프롬프트", package['complete_prompt'], height=600)
                            
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
                            
                            # 프롬프트를 별도로 표시 (선택하기 쉬운 형태)
                            st.markdown("### 📄 복사용 프롬프트")
                            st.code(package['complete_prompt'], language="text")
                            
                            st.success("💡 이 프롬프트를 Deep Research에 붙여넣으세요!")
                        
                        with tab2:
                            st.markdown("### 📊 포트폴리오 CSV 파일")
                            if package['portfolio_csv']:
                                st.text_area("포트폴리오 데이터 (CSV)", package['portfolio_csv'], height=400)
                                
                                # CSV 다운로드 버튼
                                st.download_button(
                                    label="📥 포트폴리오 CSV 다운로드",
                                    data=package['portfolio_csv'],
                                    file_name=f"portfolio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                    mime="text/csv",
                                    key="download_portfolio_csv"
                                )
                            else:
                                st.warning("포트폴리오 데이터가 없습니다.")
                        
                        with tab3:
                            st.markdown("### 📝 투자노트 CSV 파일")
                            if package['notes_csv']:
                                st.text_area("투자노트 데이터 (CSV)", package['notes_csv'], height=400)
                                
                                # CSV 다운로드 버튼
                                st.download_button(
                                    label="📥 투자노트 CSV 다운로드",
                                    data=package['notes_csv'],
                                    file_name=f"investment_notes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                    mime="text/csv",
                                    key="download_notes_csv"
                                )
                            else:
                                st.warning("투자노트 데이터가 없습니다.")
                        
                        with tab4:
                            st.markdown("### 📈 데이터 미리보기")
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.subheader("📊 포트폴리오 현황")
                                if package['portfolio_df'] is not None and not package['portfolio_df'].empty:
                                    st.dataframe(package['portfolio_df'], use_container_width=True)
                                else:
                                    st.info("포트폴리오 데이터가 없습니다.")
                            
                            with col2:
                                st.subheader("📝 투자 노트")
                                if package['notes_df'] is not None and not package['notes_df'].empty:
                                    st.dataframe(package['notes_df'], use_container_width=True)
                                else:
                                    st.info("투자 노트 데이터가 없습니다.")
                            
                            # 사용법 안내
                            st.markdown("---")
                            st.markdown("### 📖 사용법 안내")
                            st.info("""
                            **🎯 Deep Research 사용 방법:**
                            1. **프롬프트 복사**: 위의 완성된 프롬프트를 복사
                            2. **CSV 파일 다운로드**: 포트폴리오와 투자노트 CSV 파일을 다운로드
                            3. **Deep Research 접속**: Gemini Deep Research에 접속
                            4. **파일 첨부**: 다운로드한 CSV 파일 2개를 첨부
                            5. **프롬프트 붙여넣기**: 복사한 프롬프트를 붙여넣고 실행
                            
                            **✨ 이제 매일 이 과정을 반복하세요!**
                            """)
                            
                except Exception as e:
                    st.error(f"❌ 완전한 패키지 생성 실패: {e}")
                    import traceback
                    st.error(f"상세 오류: {traceback.format_exc()}")
            
            # 개별 기능들
            st.markdown("---")
            st.subheader("🔧 개별 기능")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 🤖 프롬프트만 생성")
                if st.button("🤖 프롬프트 생성", use_container_width=True):
                    try:
                        with st.spinner("🤖 프롬프트를 생성하고 있습니다..."):
                            prompt = generator.generate_complete_prompt(time_window_text)
                            st.text_area("생성된 프롬프트", prompt, height=400)
                    except Exception as e:
                        st.error(f"❌ 프롬프트 생성 실패: {e}")
            
            with col2:
                st.markdown("#### 📥 CSV만 다운로드")
                available_sheets = generator.get_available_sheets()
                selected_sheet = st.selectbox("시트 선택", available_sheets)
                if st.button("📥 CSV 다운로드", use_container_width=True):
                    try:
                        csv_data = generator.get_data_as_csv(selected_sheet)
                        if csv_data:
                            st.download_button(
                                label=f"📥 {selected_sheet} CSV 다운로드",
                                data=csv_data,
                                file_name=f"{selected_sheet}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
                        else:
                            st.warning("다운로드할 데이터가 없습니다.")
                    except Exception as e:
                        st.error(f"❌ CSV 다운로드 실패: {e}")
                        
        except Exception as e:
            st.error(f"❌ 데일리 브리핑 생성기 V2 초기화 실패: {e}")
            import traceback
            st.error(f"상세 오류: {traceback.format_exc()}")

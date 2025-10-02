"""
Gemini 웹 자동화 통합 UI 모듈
Streamlit 앱에서 Gemini deep research를 자동화된 방식으로 실행할 수 있는 인터페이스 제공
"""

import streamlit as st
import os
import time
import threading
from datetime import datetime
from typing import Dict, Any, Optional

# Gemini 웹 자동화 모듈 import
try:
    from gemini_web_automation import GeminiWebAutomation
    AUTOMATION_AVAILABLE = True
except ImportError as e:
    AUTOMATION_AVAILABLE = False
    # Streamlit Cloud에서는 Selenium 사용 불가하므로 우회 방법 제공
    pass

def show_gemini_setup_guide():
    """Gemini 설정 가이드 표시"""
    if AUTOMATION_AVAILABLE:
        st.markdown("""
        <div style="background-color: #fff3cd; padding: 1.5rem; border-radius: 10px; border-left: 4px solid #ffc107; margin-bottom: 2rem;">
            <h4 style="color: #856404; margin: 0;">🚨 Gemini 자동화 사용 전 설정 필요</h4>
            <p style="color: #856404; margin: 0.5rem 0 0 0; font-size: 0.95rem;">
            Gemini 웹 자동화를 사용하려면 우선 수동으로 로그인해야 합니다.
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background-color: #e3f2fd; padding: 1.5rem; border-radius: 10px; border-left: 4px solid #2196f3; margin-bottom: 2rem;">
            <h4 style="color: #1976d2; margin: 0;">🌐 Streamlit Cloud 환경 - GeminI 프롬프트 관리</h4>
            <p style="color: #1976d2; margin: 0.5rem 0 0 0; font-size: 0.95rem;">
            Selenium 브라우저 자동화는 로컬 환경에서만 사용 가능합니다. 여기서는 생성된 프롬프트를 관리하고 수동 전송할 수 있습니다.
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("### 🔧 설정 가이드")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div style="background-color: #e3f2fd; padding: 1rem; border-radius: 8px; border-left: 4px solid #2196f3;">
            <h5 style="color: #1976d2; margin: 0;">1️⃣ 브라우저 설정</h5>
            <ul style="color: #1976d2; margin: 0.5rem 0 0 0; padding-left: 1.5rem; font-size: 0.9rem;">
                <li>Chrome 프로필 경로 지정</li>
                <li>자동 로그인 상태 유지</li>
                <li>헤드리스/헤드풀 모드 선택</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="background-color: #e8f5e8; padding: 1rem; border-radius: 8px; border-left: 4px solid #4caf50;">
            <h5 style="color: #2e7d32; margin: 0;">2️⃣ 테스트 단계</h5>
            <ul style="color: #2e7d32; margin: 0.5rem 0 0 0; padding-left: 1.5rem; font-size: 0.9rem;">
                <li>단순 프롬프트로 테스트</li>
                <li>응답 수집 확인</li>
                <li>전체 플로우 검증</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

def create_gemini_automation_form():
    """Gemini 자동화 설정 폼 생성"""
    if AUTOMATION_AVAILABLE:
        st.markdown("### 🤖 Gemini 자동화 설정")
        
        # 설정 폼
        with st.form("gemini_automation_config"):
            col1, col2 = st.columns(2)
            
            with col1:
                headless_mode = st.checkbox("헤드리스 모드", help="브라우저 창을 표시하지 않고 실행")
                
                chrome_profile_path = st.text_input(
                    "Chrome 프로필 경로",
                    value="/Users/$(whoami)/Library/Application Support/Google/Chrome/Default",
                    help="Chrome 프로필 디렉토리 경로 (로그인 상태 유지용)"
                )
            
            with col2:
                auto_login = st.checkbox("자동 로그인 시도", help="브라우저 시작 시 로그인 상태 확인")
                
                test_mode = st.checkbox("테스트 모드", help="간단한 프롬프트로 기능 테스트")
            
            # 제출 버튼
            submitted = st.form_submit_button("설정 저장", type="primary")
            
            if submitted:
                # 설정을 세션 상태에 저장
                st.session_state.gemini_config = {
                    "headless_mode": headless_mode,
                    "chrome_profile_path": chrome_profile_path,
                    "auto_login": auto_login,
                    "test_mode": test_mode
                }
                st.success("✅ Gemini 자동화 설정이 저장되었습니다!")
    else:
        st.markdown("### 🌐 프롬프트 관리 도구")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            <div style="background-color: #e3f2fd; padding: 1rem; border-radius: 8px; border-left: 4px solid #2196f3;">
                <h5 style="color: #1976d2; margin: 0;">📝 프롬프트 생성</h5>
                <p style="color: #1976d2; margin: 0.5rem 0 0 0; font-size: 0.85rem;">다른 도구에서 생성된 프롬프트들이 자동으로 저장됩니다.</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div style="background-color: #e8f5e8; padding: 1rem; border-radius: 8px; border-left: 4px solid #4caf50;">
                <h5 style="color: #2e7d32; margin: 0;">📋 복사/다운로드</h5>
                <p style="color: #2e7d32; margin: 0.5rem 0 0 0; font-size: 0.85rem;">수동으로 Gemini에 붙여넣을 수 있도록 텍스트 복사.</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div style="background-color: #fff3e0; padding: 1rem; border-radius: 8px; border-left: 4px solid #ff9800;">
                <h5 style="color: #e65100; margin: 0;">🔗 직접 링크</h5>
                <p style="color: #e65100; margin: 0.5rem 0 0 0; font-size: 0.85rem;">Gemini Deep Research 페이지로 바로 이동.</p>
            </div>
            """, unsafe_allow_html=True)

def show_existing_prompts():
    """기존 생성된 프롬프트들 표시"""
    st.markdown("### 📝 기존 프롬프트 목록")
    
    # 세션 상태에서 프롬프트들 가져오기
    if hasattr(st.session_state, 'generated_prompts') and st.session_state.generated_prompts:
        prompts = st.session_state.generated_prompts
        
        for i, prompt_data in enumerate(prompts):
            with st.expander(f"프롬프트 {i+1}: {prompt_data.get('title', 'Untitled')}"):
                st.markdown("**생성 시간:** " + prompt_data.get('timestamp', 'Unknown'))
                
                # 프롬프트 미리보기
                preview = prompt_data.get('content', '')
                if len(preview) > 200:
                    preview = preview[:200] + "..."
                st.text_area(
                    "프롬프트 내용",
                    value=preview,
                    disabled=True,
                    height=100
                )
                
                # Gemini 전송 버튼
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button(f"🚀 Gemini 전송", key=f"send_{i}"):
                        st.session_state.selected_prompt = prompt_data
                        st.session_state.gemini_mode = "send"
                
                with col2:
                    if st.button(f"✏️ 편집", key=f"edit_{i}"):
                        st.session_state.selected_prompt_index = i
                        st.session_state.gemini_mode = "edit"
                
                with col3:
                    if st.button(f"📋 복사", key=f"copy_{i}"):
                        st.code(prompt_data.get('content', ''))
    
    else:
        st.info("💡 아직 생성된 프롬프트가 없습니다. 다른 도구를 사용하여 프롬프트를 생성한 후 다시 시도하세요.")
        
        # 예시 프롬프트 생성
        if st.button("📝 예시 프롬프트 생성"):
            example_prompt = """
다음 투자 주제에 대해 상세한 분석을 수행해주세요:

주제: 기후 변화 관련 ESG 투자 트렌드 분석

다음 관점에서 연구해주세요:
1. 최근 ESG 투자 규모 및 성장률
2. 정부 정책 및 규제 동향
3. 주요 기업들의 ESG 전략 발표
4. 투자자들의 ESG 요구사항 변화
5. 향후 전망 및 투자 기회

구체적인 데이터, 통계, 그리고 실제 사례를 포함하여 답변해주세요.
            """
            
            st.session_state.generated_prompts = [{
                "title": "ESG 투자 트렌드 분석",
                "content": example_prompt.strip(),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "source": "example"
            }]
            st.success("✅ 예시 프롬프트가 생성되었습니다!")
            st.rerun()

def run_gemini_automation_task(prompt_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Gemini 자동화 작업을 백그라운드에서 실행"""
    
    def automation_task():
        try:
            # 페이지에 상태 업데이트
            progress_container = st.container()
            
            with progress_container:
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                status_text.text("🚀 Gemini 자동화를 시작합니다...")
                progress_bar.progress(10)
                
                # Gemini 자동화 인스턴스 생성
                automation = GeminiWebAutomation(
                    headless=config.get("headless_mode", False),
                    chrome_profile_path=config.get("chrome_profile_path", None)
                )
                
                status_text.text("🌐 브라우저를 시작합니다...")
                progress_bar.progress(20)
                
                automation.start_browser()
                
                status_text.text("🔍 Gemini 페이지로 이동 중...")
                progress_bar.progress(30)
                
                automation.navigate_to_gemini()
                
                status_text.text("🔐 로그인 상태를 확인합니다...")
                progress_bar.progress(40)
                
                if not automation.check_login_status():
                    automation.stop_browser()
                    st.session_state.gemini_result = {
                        "success": False,
                        "error": "로그인이 필요합니다. 브라우저에서 수동으로 로그인한 후 다시 시도하세요."
                    }
                    return
                
                status_text.text("📝 프롬프트를 전송합니다...")
                progress_bar.progress(50)
                
                prompt_content = prompt_data.get("content", "")
                if not automation.send_prompt(prompt_content):
                    automation.stop_browser()
                    st.session_state.gemini_result = {
                        "success": False,
                        "error": "프롬프트 전송에 실패했습니다."
                    }
                    return
                
                status_text.text("⏳ 응답 시작을 대기합니다...")
                progress_bar.progress(60)
                
                if not automation.wait_for_response_start():
                    automation.stop_browser()
                    st.session_state.gemini_result = {
                        "success": False,
                        "error": "응답 시작을 감지하지 못했습니다."
                    }
                    return
                
                status_text.text("📊 응답 생성을 기다립니다...")
                progress_bar.progress(80)
                
                if not automation.wait_for_response_completion(timeout=300):
                    automation.stop_browser()
                    st.session_state.gemini_result = {
                        "success": False,
                        "error": "응답 완료를 감지하지 못했습니다 (5분 타임아웃)."
                    }
                    return
                
                status_text.text("💾 응답을 수집합니다...")
                progress_bar.progress(90)
                
                response_text = automation.collect_response_text()
                
                status_text.text("✅ 응답을 저장합니다...")
                progress_bar.progress(100)
                
                # 결과 저장
                saved_file = automation.save_response(
                    prompt_content, 
                    response_text,
                    f"gemini_research_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                )
                
                automation.stop_browser()
                
                # 결과를 세션 상태에 저장
                st.session_state.gemini_result = {
                    "success": True,
                    "prompt_title": prompt_data.get("title", "Unknown"),
                    "prompt_content": prompt_content,
                    "response_text": response_text,
                    "response_length": len(response_text),
                    "saved_file": saved_file,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                status_text.text("🎉 Gemini 연구가 완료되었습니다!")
                
        except Exception as e:
            st.session_state.gemini_result = {
                "success": False,
                "error": f"Gemini 자동화 실행 중 오류: {str(e)}"
            }
    
    # 백그라운드 스레드에서 실행
    thread = threading.Thread(target=automation_task)
    thread.daemon = True
    thread.start()
    
    # 실행 중임을 표시
    st.session_state.gemini_running = True
    
    return {"status": "started", "thread": thread}

def show_gemini_results():
    """Gemini 연구 결과 표시"""
    st.markdown("### 📊 Gemini 연구 결과")
    
    if hasattr(st.session_state, 'gemini_result') and st.session_state.gemini_result:
        result = st.session_state.gemini_result
        
        if result["success"]:
            st.success("✅ Gemini 연구가 성공적으로 완료되었습니다!")
            
            # 결과 요약
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("프롬프트 제목", result["prompt_title"])
            
            with col2:
                st.metric("응답 길이", f"{result['response_length']:,}자")
            
            with col3:
                st.metric("생성 시간", result["timestamp"])
            
            # 저장된 파일 정보
            if result.get("saved_file"):
                st.success(f"💾 응답이 파일에 저장되었습니다: `{result['saved_file']}`")
            
            # 응답 내용 표시
            st.markdown("### 📝 Gemini 응답 내용")
            
            # 응답 길이가 길면 탭으로 구분
            response_text = result["response_text"]
            
            if len(response_text) > 2000:
                # 응답을 여러 섹션으로 나누기
                parts = []
                current_part = ""
                sentences = response_text.split('. ')
                
                for sentence in sentences:
                    if sentence != sentences[-1]:
                        sentence += '. '
                    
                    if len(current_part) + len(sentence) <= 2000:
                        current_part += sentence
                    else:
                        if current_part.strip():
                            parts.append(current_part.strip())
                        current_part = sentence
                
                if current_part.strip():
                    parts.append(current_part.strip())
                
                # 탭으로 표시
                tab_names = [f"섹션 {i+1}" for i in range(len(parts))]
                tabs = st.tabs(tab_names)
                
                for i, tab in enumerate(tabs):
                    with tab:
                        st.markdown(parts[i])
            else:
                st.markdown(response_text)
            
            # 다운로드 버튼
            if result.get("saved_file") and os.path.exists(result["saved_file"]):
                with open(result["saved_file"], "r", encoding="utf-8") as f:
                    file_content = f.read()
                
                st.download_button(
                    label="📥 응답 결과 다운로드",
                    data=file_content,
                    file_name=result["saved_file"],
                    mime="text/plain"
                )
        
        else:
            st.error("❌ Gemini 연구 실행 실패:")
            st.error(result["error"])
    
    else:
        st.info("💡 아직 실행된 Gemini 연구가 없습니다. 위에서 프롬프트를 선택하여 연구를 시작하세요.")

def render_gemini_automation_page():
    """Gemini 자동화 페이지 렌더링"""
    
    # 페이지 헤더
    st.markdown("""
    <div style="text-align: center; padding: 1.5rem 0; background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); border-radius: 10px; margin-bottom: 2rem;">
        <h1 style="color: white; margin: 0; font-size: 2rem;">🤖 Gemini 웹 자동화</h1>
        <p style="color: #f0f0f0; margin: 0.5rem 0 0 0; font-size: 1rem;">생성된 프롬프트를 Gemini deep research에 자동 전송</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 모듈 사용 가능성 확인
    if not AUTOMATION_AVAILABLE:
        st.error("❌ Gemini 웹 자동화 모듈을 사용할 수 없습니다.")
        st.info("💡 필요한 패키지가 설치되지 않았습니다. 먼저 `pip install -r requirements.txt`를 실행하세요.")
        return
    
    # 설정 가이드 표시
    show_gemini_setup_guide()
    
    # 설정 폼
    create_gemini_automation_form()
    
    st.divider()
    
    # 기존 프롬프트 목록
    show_existing_prompts()
    
    # 프롬프트 선택 시 처리
    if hasattr(st.session_state, 'selected_prompt') and hasattr(st.session_state, 'gemini_mode'):
        selected_prompt = st.session_state.selected_prompt
        mode = st.session_state.gemini_mode
        
        st.markdown("---")
        st.markdown("### 🚀 선택된 프롬프트")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown(f"**제목:** {selected_prompt.get('title', 'Untitled')}")
            st.markdown(f"**생성 시간:** {selected_prompt.get('timestamp', 'Unknown')}")
            
            # 프롬프트 미리보기
            preview = selected_prompt.get('content', '')
            if len(preview) > 300:
                preview = preview[:300] + "..."
            st.text_area(
                "프롬프트 내용",
                value=preview,
                disabled=True,
                height=150
            )
        
        with col2:
            if mode == "send":
                if hasattr(st.session_state, 'gemini_config'):
                    config = st.session_state.gemini_config
                    
                    if AUTOMATION_AVAILABLE:
                        if st.button("🚀 Gemini에 전송하여 연구 시작", type="primary", use_container_width=True):
                            # 자동화 작업 시작
                            run_gemini_automation_task(selected_prompt, config)
                            
                            # 진행 상황 표시
                            with st.spinner("Gemini 자동화가 실행 중입니다. 잠시만 기다려주세요..."):
                                # 백그라운드 작업 완료 대기
                                time.sleep(1)
                                
                            st.success("Gemini 자동화가 시작되었습니다! 결과를 확인하려면 페이지를 새로고침하세요.")
                            st.rerun()
                    else:
                        st.warning("⚠️ Selenium이 설치되지 않았습니다. 로컬 환경에서 사용하세요.")
                else:
                    st.warning("⚠️ 먼저 위에서 Gemini 자동화 설정을 저장해주세요.")
                
                # Streamlit Cloud 환경을 위한 대안 제공
                if not AUTOMATION_AVAILABLE:
                    st.markdown("---")
                    st.markdown("#### 🌐 대안 방법 (수동 전송)")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if st.button("📋 프롬프트 복사", type="secondary", use_container_width=True):
                            st.session_state.copied_prompt = selected_prompt['content']
                            st.success("프롬프트가 클립보드에 복사되었습니다!")
                    
                    with col2:
                        if st.button("🔗 Gemini 링크 열기", use_container_width=True):
                            gemini_url = "https://gemini.google.com/app/topic"
                            st.write(f"🔗 [Gemini Deep Research 열기]({gemini_url})")
                            st.success("수동으로 Gemini에 접속하여 프롬프트를 붙여넣으세요!")
                    
                    with col3:
                        filename = f"prompt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                        st.download_button(
                            label="📥 프롬프트 다운로드",
                            data=selected_prompt['content'],
                            file_name=filename,
                            mime="text/plain",
                            use_container_width=True
                        )
            
            elif mode == "edit":
                # 프롬프트 편집 폼
                edited_content = st.text_area(
                    "프롬프트 편집",
                    value=selected_prompt.get('content', ''),
                    height=200
                )
                
                if st.button("💾 편집 저장", type="primary", use_container_width=True):
                    if hasattr(st.session_state, 'generated_prompts'):
                        prompt_index = st.session_state.get('selected_prompt_index', 0)
                        st.session_state.generated_prompts[prompt_index]['content'] = edited_content
                        st.session_state.generated_prompts[prompt_index]['last_modified'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        st.success("프롬프트가 업데이트되었습니다!")
                        st.rerun()
    
    # 실행 중 상태 표시
    if hasattr(st.session_state, 'gemini_running') and st.session_state.gemini_running:
        st.markdown("---")
        
        # 실행 진행 상황 표시
        progress_container = st.container()
        
        with progress_container:
            progress_bar = st.progress(0)
            status_placeholder = st.empty()
            
            # 진행 상황 업데이트 (간단한 애니메이션)
            for i in range(100):
                progress_bar.progress(i + 1)
                status_placeholder.text(f"Gemini 연구 진행 중... {i+1}%")
                time.sleep(0.1)
        
        # 상태 초기화
        st.session_state.gemini_running = False
    
    # Gemini 연구 결과 표시
    show_gemini_results()
    
    # 복사된 프롬프트 표시 (Streamlit Cloud 환경)
    if hasattr(st.session_state, 'copied_prompt'):
        st.markdown("---")
        st.markdown("### 📋 복사된 프롬프트")
        st.text_area(
            "Gemini Deep Research에 붙여넣을 프롬프트", 
            st.session_state.copied_prompt, 
            height=200,
            help="이 프롬프트를 복사하여 https://gemini.google.com/app/topic 에 붙여넣으세요."
        )
    
    # 실시간 업데이트를 위한 자동 새로고침
    if hasattr(st.session_state, 'gemini_running') and st.session_state.gemini_running:
        time.sleep(5)
        st.rerun()

def main():
    """테스트 실행 함수"""
    render_gemini_automation_page()

if __name__ == "__main__":
    main()

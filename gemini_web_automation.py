"""
Gemini 웹 인터페이스 자동화 모듈
Selenium을 사용하여 Gemini deep research에서 프롬프트를 전송하고 결과를 수집합니다.
"""

import os
import time
import json
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    StaleElementReferenceException,
    WebDriverException
)
from webdriver_manager.chrome import ChromeDriverManager

class GeminiWebAutomation:
    """Gemini 웹 인터페이스 자동화 클래스"""
    
    def __init__(self, headless: bool = False, chrome_profile_path: str = None):
        """
        GeminiWebAutomation 초기화
        
        Args:
            headless (bool): 헤드리스 모드 여부 (기본값: False)
            chrome_profile_path (str): Chrome 프로필 경로 (로그인 상태 유지용)
        """
        self.headless = headless
        self.chrome_profile_path = chrome_profile_path
        self.driver = None
        self.wait = None
        self.is_logged_in = False
        
        # 로깅 설정
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Gemini Deep Research URL
        self.gemini_url = "https://gemini.google.com/app/topic"
    
    def _setup_driver(self) -> webdriver.Chrome:
        """Chrome 드라이버 설정 및 초기화"""
        try:
            chrome_options = Options()
            
            if self.headless:
                chrome_options.add_argument("--headless")
            
            # 기본 Chrome 옵션 설정
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
            
            # Chrome 프로필 사용 (로그인 상태 유지)
            if self.chrome_profile_path:
                if Path(self.chrome_profile_path).exists():
                    chrome_options.add_argument(f"--user-data-dir={self.chrome_profile_path}")
                    self.logger.info(f"Chrome 프로필을 사용합니다: {self.chrome_profile_path}")
                else:
                    self.logger.warning(f"Chrome 프로필 경로가 존재하지 않습니다: {self.chrome_profile_path}")
            
            # ChromeDriver 자동 다운로드 및 설정
            service = Service(ChromeDriverManager().install())
            
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.implicitly_wait(10)
            
            self.logger.info("Chrome 드라이버가 성공적으로 설정되었습니다.")
            return driver
            
        except Exception as e:
            self.logger.error(f"Chrome 드라이버 설정 실패: {str(e)}")
            raise
    
    def start_browser(self):
        """브라우저 시작"""
        try:
            if self.driver is None:
                self.driver = self._setup_driver()
                self.wait = WebDriverWait(self.driver, 20)
                
            self.logger.info("브라우저가 시작되었습니다.")
            
        except Exception as e:
            self.logger.error(f"브라우저 시작 실패: {str(e)}")
            raise
    
    def stop_browser(self):
        """브라우저 종료"""
        try:
            if self.driver:
                self.driver.quit()
                self.driver = None
                self.wait = None
                self.logger.info("브라우저가 종료되었습니다.")
                
        except Exception as e:
            self.logger.error(f"브라우저 종료 중 오류: {str(e)}")
    
    def navigate_to_gemini(self):
        """Gemini Deep Research 페이지로 이동"""
        try:
            self.logger.info(f"Gemini 페이지로 이동 중: {self.gemini_url}")
            self.driver.get(self.gemini_url)
            
            # 페이지 로딩 대기
            time.sleep(3)
            
            # 현재 URL 확인
            current_url = self.driver.current_url
            self.logger.info(f"현재 페이지: {current_url}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Gemini 페이지 이동 실패: {str(e)}")
            raise
    
    def check_login_status(self) -> bool:
        """로그인 상태 확인"""
        try:
            # 로그인 관련 요소 확인
            login_indicators = [
                "//span[contains(text(), 'Sign in')]",
                "//button[contains(text(), 'Sign in')]",
                "//a[contains(text(), 'Sign in')]"
            ]
            
            for indicator in login_indicators:
                try:
                    element = self.driver.find_element(By.XPATH, indicator)
                    if element.is_displayed():
                        self.logger.warning("로그인이 필요합니다.")
                        self.is_logged_in = False
                        return False
                except NoSuchElementException:
                    continue
            
            # Google 계정 정보 확인 (선택적)
            try:
                account_elements = self.driver.find_elements(
                    By.XPATH, 
                    "//div[contains(@class, 'account') or contains(@class, 'profile') or contains(@class, 'user')]"
                )
                if account_elements:
                    self.logger.info("로그인 상태로 확인됩니다.")
                    self.is_logged_in = True
                    return True
            except NoSuchElementException:
                pass
            
            # 입력 필드가 있으면 로그인 가능성 체크
            try:
                input_field = self.driver.find_element(By.XPATH, "//textarea[@placeholder]")
                if input_field:
                    self.logger.info("입력 필드가 감지되어 로그인 상태로 추정됩니다.")
                    self.is_logged_in = True
                    return True
            except NoSuchElementException:
                pass
            
            self.is_logged_in = False
            self.logger.warning("로그인 상태를 확인할 수 없습니다.")
            return False
            
        except Exception as e:
            self.logger.error(f"로그인 상태 확인 실패: {str(e)}")
            return False
    
    def find_input_field(self) -> Optional[webdriver.Chrome.webelement.WebElement]:
        """텍스트 입력 필드 찾기"""
        try:
            # 다양한 입력 필드 선택자 시도
            input_selectors = [
                "//textarea[@placeholder]",
                "//textarea[contains(@class, 'input')]",
                "//textarea[contains(@class, 'prompt')]",
                "//input[@type='text']",
                "//div[@contenteditable='true']",
                "//textarea",
                "//input[@placeholder]"
            ]
            
            for selector in input_selectors:
                try:
                    element = self.driver.find_element(By.XPATH, selector)
                    if element.is_displayed() and element.is_enabled():
                        self.logger.info(f"입력 필드를 찾았습니다: {selector}")
                        return element
                except NoSuchElementException:
                    continue
            
            self.logger.warning("입력 필드를 찾을 수 없습니다.")
            return None
            
        except Exception as e:
            self.logger.error(f"입력 필드 검색 실패: {str(e)}")
            return None
    
    def send_prompt(self, prompt_text: str) -> bool:
        """
        프롬프트를 Gemini에 전송
        
        Args:
            prompt_text (str): 전송할 프롬프트 텍스트
            
        Returns:
            bool: 전송 성공 여부
        """
        try:
            self.logger.info("입력 필드를 찾는 중...")

            # 입력 필드 찾기 및 대기
            input_field = self.find_input_field()
            
            if not input_field:
                self.logger.error("입력 필드를 찾을 수 없습니다.")
                return False
            
            # 필드에 포커스 및 내용 지우기
            self.driver.execute_script("arguments[0].scrollIntoView(true);", input_field)
            input_field.click()
            time.sleep(1)
            
            # 기존 내용 지우기
            input_field.clear()
            
            # 프롬프트 입력
            self.logger.info(f"프롬프트 입력 중... (길이: {len(prompt_text)}자)")
            input_field.send_keys(prompt_text)
            
            # 전송 버튼 찾기 및 클릭
            send_buttons = [
                "//button[contains(text(), 'Send')]",
                "//button[contains(text(), 'Submit')]",
                "//button[@type='submit']",
                "//button[contains(@class, 'send')]",
                "//button[contains(@class, 'submit')]",
                "//button[contains(@aria-label, 'Send')]",
                "//button[contains(@aria-label, 'Submit')]"
            ]
            
            send_clicked = False
            for button_selector in send_buttons:
                try:
                    button = self.driver.find_element(By.XPATH, button_selector)
                    if button.is_displayed() and button.is_enabled():
                        self.driver.execute_script("arguments[0].send_keys('\n');", input_field)
                        send_clicked = True
                        self.logger.info(f"전송 버튼 클릭: {button_selector}")
                        break
                except NoSuchElementException:
                    continue
            
            # Enter 키로 실행
            if not send_clicked:
                self.driver.execute_script("arguments[0].send_keys('\n');", input_field)
                self.logger.info("Enter 키로 프롬프트 전송")
            
            time.sleep(2)  # 전송 시작 대기
            
            return True
            
        except Exception as e:
            self.logger.error(f"프롬프트 전송 실패: {str(e)}")
            return False
    
    def wait_for_response_start(self, timeout: int = 30) -> bool:
        """
        응답 시작 대기
        
        Args:
            timeout (int): 대기 시간 (초)
            
        Returns:
            bool: 응답 시작 감지 여부
        """
        try:
            self.logger.info("응답 시작을 대기 중...")
            
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                # 응답 관련 요소들 확인
                response_indicators = [
                    "//div[contains(@class, 'response')]",
                    "//div[contains(@class, 'answer')]",
                    "//div[contains(@class, 'content')]",
                    "//div[contains(@class, 'message')]",
                    "//div[contains(text(), '...')] or //span[contains(text(), '...')]"
                ]
                
                for indicator in response_indicators:
                    try:
                        elements = self.driver.find_elements(By.XPATH, indicator)
                        for element in elements:
                            if element.is_displayed():
                                element_text = element.text.strip()
                                if len(element_text) > 0:
                                    self.logger.info("응답이 시작되었습니다.")
                                    return True
                    except (NoSuchElementException, StaleElementReferenceException):
                        continue
                
                time.sleep(1)
            
            self.logger.warning(f"응답 시작을 {timeout}초 동안 감지하지 못했습니다.")
            return False
            
        except Exception as e:
            self.logger.error(f"응답 시작 대기 실패: {str(e)}")
            return False
    
    def wait_for_response_completion(self, timeout: int = 300) -> bool:
        """
        응답 완료 대기 (최대 5분)
        
        Args:
            timeout (int): 대기 시간 (초)
            
        Returns:
            bool: 응답 완료 감지 여부
        """
        try:
            self.logger.info("응답 완료를 대기 중...")
            
            start_time = time.time()
            last_response_length = 0
            stable_count = 0
            
            while time.time() - start_time < timeout:
                try:
                    # 응답 텍스트 수집
                    response_text = self.collect_response_text()
                    
                    current_length = len(response_text)
                    
                    # 응답 길이 변화 감지
                    if current_length > last_response_length:
                        last_response_length = current_length
                        stable_count = 0
                        self.logger.info(f"응답 진행 중... (길이: {current_length}자)")
                    else:
                        stable_count += 1
                    
                    # 응답이 안정화되었는지 확인 (5초 동안 길이 변화 없음)
                    if stable_count >= 5 and current_length > 0:
                        # 추가 응답 확인 (잠시 더 대기)
                        time.sleep(3)
                        final_response = self.collect_response_text()
                        if len(final_response) == current_length:
                            self.logger.info("응답이 완료되었습니다.")
                            return True
                    
                    time.sleep(1)
                    
                except Exception as e:
                    self.logger.warning(f"응답 상태 확인 중 오류: {str(e)}")
                    time.sleep(1)
                    continue
            
            self.logger.warning(f"응답 완료를 {timeout}초 동안 감지하지 못했습니다.")
            return False
            
        except Exception as e:
            self.logger.error(f"응답 완료 대기 실패: {str(e)}")
            return False
    
    def collect_response_text(self) -> str:
        """
        응답 텍스트 수집
        
        Returns:
            str: 수집된 응답 텍스트
        """
        try:
            response_selectors = [
                "//div[contains(@class, 'response')]",
                "//div[contains(@class, 'answer')]",
                "//div[contains(@class, 'content')]",
                "//div[contains(@class, 'message')]",
                "//div[contains(@class, 'output')]",
                "//article",
                "//main//p",
                "//div[@role='presentation']"
            ]
            
            response_text = ""
            
            for selector in response_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed():
                            element_text = element.text.strip()
                            if element_text and len(element_text) > len(response_text):
                                response_text = element_text
                except (NoSuchElementException, StaleElementReferenceException):
                    continue
            
            # 마지막 콘텐츠만 추출 (가장 긴 응답)
            if response_text:
                return response_text
            
            # 대체 방법: 모든 텍스트 노드 수집
            try:
                all_text = self.driver.find_element(By.TAG_NAME, "body").text
                return all_text
            except NoSuchElementException:
                pass
            
            return ""
            
        except Exception as e:
            self.logger.error(f"응답 텍스트 수집 실패: {str(e)}")
            return ""
    
    def save_response(self, prompt: str, response: str, filename: str = None) -> str:
        """
        프롬프트와 응답을 파일로 저장
        
        Args:
            prompt (str): 입력 프롬프트
            response (str): 수집된 응답
            filename (str): 저장할 파일명 (없으면 자동 생성)
            
        Returns:
            str: 저장된 파일 경로
        """
        try:
            # 파일명 자동 생성
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"gemini_response_{timestamp}.txt"
            
            # 저장 데이터 구성
            data = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "prompt": prompt,
                "response": response,
                "response_length": len(response)
            }
            
            # 텍스트 파일로 저장
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("=== Gemini 응답 결과 ===\n\n")
                f.write(f"시간: {data['timestamp']}\n")
                f.write(f"응답 길이: {data['response_length']}자\n\n")
                f.write("=== 입력 프롬프트 ===\n")
                f.write(prompt)
                f.write("\n\n=== Gemini 응답 ===\n")
                f.write(response)
                f.write("\n\n")
            
            self.logger.info(f"응답이 '{filename}'에 저장되었습니다.")
            return filename
            
        except Exception as e:
            self.logger.error(f"응답 저장 실패: {str(e)}")
            return ""
    
    def run_research(self, prompt_text: str, max_wait_time: int = 300) -> Dict[str, Any]:
        """
        전체 연구 프로세스 실행
        
        Args:
            prompt_text (str): 연구 프롬프트
            max_wait_time (int): 최대 대기 시간 (초)
            
        Returns:
            Dict[str, Any]: 연구 결과
        """
        result = {
            "success": False,
            "prompt": prompt_text,
            "response": "",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "error": None
        }
        
        try:
            # 브라우저 시작
            self.start_browser()
            
            # Gemini 페이지 이동
            self.navigate_to_gemini()
            
            # 로그인 상태 확인
            if not self.check_login_status():
                result["error"] = "로그인이 필요합니다. 브라우저에서 수동 로그인 후 다시 시도하세요."
                self.logger.error(result["error"])
                return result
            
            # 프롬프트 전송
            if not self.send_prompt(prompt_text):
                result["error"] = "프롬프트 전송에 실패했습니다."
                return result
            
            # 응답 시작 대기
            if not self.wait_for_response_start(timeout=30):
                result["error"] = "응답 시작을 감지하지 못했습니다."
                return result
            
            # 응답 완료 대기
            if not self.wait_for_response_completion(timeout=max_wait_time):
                result["error"] = "응답 완료를 감지하지 못했습니다."
                return result
            
            # 응답 수집
            response_text = self.collect_response_text()
            
            if not response_text:
                result["error"] = "응답을 수집할 수 없습니다."
                return result
            
            # 결과 저장
            result["success"] = True
            result["response"] = response_text
            result["response_length"] = len(response_text)
            
            # 파일로 저장
            saved_file = self.save_response(prompt_text, response_text)
            result["saved_file"] = saved_file
            
            self.logger.info(f"연구 완료! 응답 길이: {len(response_text)}자")
            
            return result
            
        except Exception as e:
            result["error"] = str(e)
            self.logger.error(f"연구 실행 중 오류: {str(e)}")
            return result
        
        finally:
            # 브라우저 정리는 사용자가 직접 처리하도록 함 (연속 작업 시 유용)
            pass


def main():
    """테스트 메인 함수"""
    print("🚀 Gemini 웹 자동화 테스트 시작")
    
    # 테스트 프롬프트
    test_prompt = """
    다음 주제에 대해 상세한 연구를 수행해주세요:
    
    주제: 테슬라 주식의 최근 성과와 전망
    
    다음 관점에서 분석해주세요:
    1. 최근 3개월간의 주가 동향
    2. 주요 실적 지표 분석
    3. 경쟁사 대비 평가
    4. 향후 전망 및 투자 전략
    
    구체적인 데이터와 근거를 포함하여 답변해주세요.
    """
    
    # 자동화 인스턴스 생성
    automation = GeminiWebAutomation()
    
    try:
        # 연구 실행
        result = automation.run_research(test_prompt, max_wait_time=300)
        
        if result["success"]:
            print(f"✅ 연구 성공!")
            print(f"📏 응답 길이: {result['response_length']}자")
            print(f"💾 저장 파일: {result.get('saved_file', 'N/A')}")
            print(f"\n=== 응답 미리보기 (처음 500자) ===")
            print(result["response"][:500] + "..." if len(result["response"]) > 500 else result["response"])
        else:
            print(f"❌ 연구 실패: {result['error']}")
    
    finally:
        # 브라우저 정리
        automation.stop_browser()


if __name__ == "__main__":
    main()

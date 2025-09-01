from google import genai
from google.genai import types
import os
from typing import List, Dict, Any
import json
import time

class GeminiDeepResearch:
    def __init__(self, api_key: str = None, use_google_search: bool = False):
        """
        Gemini Deep Research 클래스 초기화
        
        Args:
            api_key (str): Google AI API 키. 환경변수 GOOGLE_API_KEY에서도 읽을 수 있음
            use_google_search (bool): Google 검색 기능 사용 여부
        """
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY')
        if not self.api_key:
            raise ValueError("Google API 키가 필요합니다. 환경변수 GOOGLE_API_KEY를 설정하거나 직접 전달하세요.")
        
        # Google AI 클라이언트 초기화
        self.client = genai.Client(api_key=self.api_key)
        
        # Google 검색 기능 설정
        self.use_google_search = use_google_search
        if use_google_search:
            try:
                # Google 검색 도구 정의
                self.grounding_tool = types.Tool(
                    google_search=types.GoogleSearch()
                )
                
                # 생성 설정 구성
                self.config = types.GenerateContentConfig(
                    tools=[self.grounding_tool]
                )
                
                self.model_name = "gemini-2.5-pro"
                print("🔍 Google 검색 기능이 활성화되었습니다.")
                print("   💡 공식 Google 검색 도구를 사용합니다.")
            except Exception as e:
                print(f"⚠️ Google 검색 기능 초기화 실패, 기본 모델 사용: {str(e)}")
                print(f"   💡 Google 검색 기능이 현재 API 키에서 지원되지 않습니다.")
                print(f"   💡 Google AI Studio에서 검색 기능 권한을 확인하세요.")
                self.config = None
                self.model_name = "gemini-2.5-pro"
                self.use_google_search = False
        else:
            self.config = None
            self.model_name = "gemini-2.5-pro"
            print("📚 기본 모델로 실행됩니다.")
        
        self.last_request_time = 0  # 마지막 요청 시간 추적
        
    def _reset_model_session(self):
        """API 세션을 재설정하는 헬퍼 함수"""
        try:
            print("   🔄 API 세션 재설정 중...")
            # 새로운 API에서는 클라이언트 재생성이 필요할 수 있음
            self.client = genai.Client(api_key=self.api_key)
            time.sleep(2)  # 세션 재설정 후 잠시 대기
            print("   ✅ API 세션 재설정 완료")
        except Exception as e:
            print(f"   ❌ API 세션 재설정 실패: {str(e)}")
    
    def _ensure_request_interval(self):
        """요청 간 최소 간격을 보장하는 헬퍼 함수"""
        current_time = time.time()
        min_interval = 3  # 최소 3초 간격
        
        if current_time - self.last_request_time < min_interval:
            wait_time = min_interval - (current_time - self.last_request_time)
            print(f"   ⏳ 요청 간격 보장을 위해 {wait_time:.1f}초 대기...")
            time.sleep(wait_time)
        
        self.last_request_time = time.time()
    
    def research_topic(self, topic: str, depth: str = "deep", max_iterations: int = 3, use_search: bool = None) -> Dict[str, Any]:
        """
        주제에 대한 딥리서치 수행
        
        Args:
            topic (str): 연구할 주제
            depth (str): 연구 깊이 ("shallow", "medium", "deep") - 기본값: "deep"
            max_iterations (int): 최대 반복 횟수
            use_search (bool): Google 검색 사용 여부 (None이면 초기화 시 설정 사용)
            
        Returns:
            Dict[str, Any]: 연구 결과
        """
        print(f"🔍 '{topic}' 주제에 대한 딥리서치를 시작합니다...")
        
        # 검색 기능 사용 여부 결정
        search_enabled = use_search if use_search is not None else self.use_google_search
        if search_enabled:
            print("🔍 Google 검색을 활용한 실시간 정보 수집을 포함합니다.")
        
        # 요청 간격 보장
        self._ensure_request_interval()
        
        # 초기 프롬프트 설정
        depth_prompts = {
            "shallow": "간단하고 핵심적인 정보만 제공해주세요.",
            "medium": "중간 수준의 상세한 분석과 예시를 포함해주세요.",
            "deep": "매우 상세하고 깊이 있는 분석, 다양한 관점, 구체적인 예시를 포함해주세요."
        }
        
        # 검색 기능에 따른 프롬프트 조정
        if search_enabled:
            initial_prompt = f"""
            다음 주제에 대해 {depth_prompts.get(depth, depth_prompts["deep"])}
            
            주제: {topic}
            
            ⚠️ 실시간 정보 활용: Google 검색을 통해 최신 정보를 포함하여 답변해주세요.
            
            🔍 검색 요청: 이 주제에 대해 Google 검색을 실행하여 최신 정보를 수집하고, 
            현재 시점(2025년 8월 30일)의 최신 데이터를 포함하여 답변해주세요.
            
            다음 구조로 답변해주세요:
            1. 핵심 개념 및 정의
            2. 주요 특징 및 장단점
            3. 실제 적용 사례 (최신 사례 포함)
            4. 최신 동향 및 전망 (실시간 정보 활용)
            5. 추가 학습을 위한 참고 자료
            
            각 섹션을 명확하게 구분하여 답변해주세요.
            """
        else:
            initial_prompt = f"""
            다음 주제에 대해 {depth_prompts.get(depth, depth_prompts["deep"])}
            
            주제: {topic}
            
            ⚠️ 참고: 2024년 12월까지의 정보를 바탕으로 답변해주세요.
            최신 정보가 필요한 경우, 기본 원리와 과거 사례를 중심으로 설명해주세요.
            
            다음 구조로 답변해주세요:
            1. 핵심 개념 및 정의
            2. 주요 특징 및 장단점
            3. 실제 적용 사례 (2024년까지)
            4. 최신 동향 및 전망 (학습 데이터 기준)
            5. 추가 학습을 위한 참고 자료
            
            각 섹션을 명확하게 구분하여 답변해주세요.
            """
        
        research_results = {
            "topic": topic,
            "depth": depth,
            "use_google_search": search_enabled,
            "iterations": [],
            "final_summary": "",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        current_prompt = initial_prompt
        
        for iteration in range(max_iterations):
            print(f"📚 반복 {iteration + 1}/{max_iterations} 실행 중...")
            
            # 재시도 로직
            max_retries = 3
            retry_delay = 2  # 초기 대기 시간 (초)
            response_text = None  # 변수 초기화
            
            for retry in range(max_retries):
                try:
                    # 요청 간격 보장
                    self._ensure_request_interval()
                    
                    # 새로운 API 사용 (검색 기능 포함)
                    if search_enabled and self.config:
                        response = self.client.models.generate_content(
                            model=self.model_name,
                            contents=current_prompt,
                            config=self.config
                        )
                    else:
                        response = self.client.models.generate_content(
                            model=self.model_name,
                            contents=current_prompt
                        )
                    
                    # 응답 유효성 검증 추가
                    if not response:
                        print(f"❌ 반복 {iteration + 1}: 응답이 None")
                        continue
                    
                    # 응답 텍스트 안전하게 추출 - 새로운 API 구조
                    try:
                        # 새로운 API에서는 response.text 직접 사용
                        response_text = response.text
                        if response_text:
                            print(f"   ✅ response.text로 텍스트 추출 성공")
                            break  # 성공하면 재시도 루프 종료
                        else:
                            raise ValueError("응답 텍스트가 비어있음")
                    except Exception as text_error:
                        print(f"   ⚠️ response.text 실패, fallback 방법 시도: {str(text_error)}")
                        
                        # 응답 객체의 실제 구조 분석
                        print(f"   🔍 응답 객체 구조 분석:")
                        print(f"      response 타입: {type(response)}")
                        print(f"      response 속성: {[attr for attr in dir(response) if not attr.startswith('_')]}")
                        
                        # 새로운 API의 다른 접근 방법 시도
                        if hasattr(response, 'candidates') and response.candidates:
                            print(f"      candidates 발견: {len(response.candidates)}개")
                            for i, candidate in enumerate(response.candidates):
                                if hasattr(candidate, 'content') and candidate.content:
                                    if hasattr(candidate.content, 'parts') and candidate.content.parts:
                                        for j, part in enumerate(candidate.content.parts):
                                            if hasattr(part, 'text'):
                                                response_text = part.text
                                                if response_text:
                                                    print(f"   ✅ candidate.content.parts[{j}].text로 텍스트 추출 성공")
                                                    break
                        
                        if response_text:
                            break  # 성공하면 재시도 루프 종료
                        else:
                            print(f"   ❌ 모든 텍스트 추출 방법 실패")
                            if retry < max_retries - 1:
                                print(f"   🔄 재시도 {retry + 1}/{max_retries}...")
                                time.sleep(retry_delay)
                                retry_delay *= 2
                                
                                # 세 번째 재시도 시 API 세션 재설정
                                if retry == 1:
                                    self._reset_model_session()
                                
                                continue
                            else:
                                print(f"   ❌ 최대 재시도 횟수 초과")
                                break
                
                except Exception as e:
                    error_msg = str(e)
                    
                    # 500 오류인지 확인
                    if "500" in error_msg or "internal error" in error_msg.lower():
                        if retry < max_retries - 1:
                            print(f"⚠️ 반복 {iteration + 1} 재시도 {retry + 1}/{max_retries}: Google 서버 오류 (500)")
                            print(f"   {retry_delay}초 후 재시도합니다...")
                            time.sleep(retry_delay)
                            retry_delay *= 2  # 지수 백오프
                            
                            # 세 번째 재시도 시 API 세션 재설정
                            if retry == 1:
                                self._reset_model_session()
                            
                            continue
                        else:
                            print(f"❌ 반복 {iteration + 1}: 최대 재시도 횟수 초과 - Google 서버 오류")
                            break
                    else:
                        # 다른 오류인 경우
                        print(f"❌ 반복 {iteration + 1}에서 오류 발생: {error_msg}")
                        print(f"   오류 타입: {type(e)}")
                        if retry < max_retries - 1:
                            print(f"   🔄 재시도 {retry + 1}/{max_retries}...")
                            time.sleep(retry_delay)
                            retry_delay *= 2
                            
                            # 세 번째 재시도 시 API 세션 재설정
                            if retry == 1:
                                self._reset_model_session()
                            
                            continue
                        else:
                            break
            
            # 재시도 루프가 끝난 후 response_text가 있는지 확인
            if not response_text:
                print(f"❌ 반복 {iteration + 1}: 응답을 받지 못했습니다.")
                break
            
            iteration_result = {
                "iteration": iteration + 1,
                "prompt": current_prompt,
                "response": response_text,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            research_results["iterations"].append(iteration_result)
            
            # 다음 반복을 위한 프롬프트 생성 - response_text 사용
            if iteration < max_iterations - 1:
                current_prompt = f"""
                이전 답변을 바탕으로 더 깊이 있는 분석을 해주세요:
                
                주제: {topic}
                이전 답변: {response_text}
                
                다음 중 하나를 선택하여 더 자세히 분석해주세요:
                1. 이전 답변에서 언급된 구체적인 예시나 사례를 더 자세히 설명
                2. 반대 관점이나 대안적 시각 제시
                3. 실제 데이터나 통계를 활용한 분석
                4. 미래 전망이나 트렌드에 대한 예측
                
                선택한 방향으로 더 깊이 있는 분석을 제공해주세요.
                """
        
        # 최종 요약 생성
        if research_results["iterations"]:
            # 프롬프트 단순화 - 각 반복의 내용을 요약하여 길이 제한
            iteration_summaries = []
            for r in research_results['iterations']:
                # 각 반복의 응답을 100자로 제한하여 요약
                response_text = r['response']
                if len(response_text) > 100:
                    summary = response_text[:97] + "..."
                else:
                    summary = response_text
                iteration_summaries.append(f"반복 {r['iteration']}: {summary}")
            
            final_prompt = f"""
            다음 연구 결과들을 간단히 요약해주세요:
            
            주제: {topic}
            연구 결과들:
            {chr(10).join(iteration_summaries)}
            
            핵심 요약 (2-3문장)만 제공해주세요.
            """
            
            # 최종 요약 재시도 로직 추가
            max_summary_retries = 3
            summary_retry_delay = 2
            
            for summary_retry in range(max_summary_retries):
                try:
                    print(f"📝 최종 요약 생성 시도 {summary_retry + 1}/{max_summary_retries}...")
                    
                    # 최종 요약도 검색 기능 포함
                    if search_enabled and self.config:
                        final_response = self.client.models.generate_content(
                            model=self.model_name,
                            contents=final_prompt,
                            config=self.config
                        )
                    else:
                        final_response = self.client.models.generate_content(
                            model=self.model_name,
                            contents=final_prompt
                        )
                    
                    # 안전한 텍스트 추출
                    try:
                        final_summary_text = final_response.text
                        if final_summary_text:
                            print(f"   ✅ 최종 요약: response.text로 텍스트 추출 성공")
                            research_results["final_summary"] = final_summary_text
                            break
                        else:
                            raise ValueError("응답 텍스트가 비어있음")
                    except Exception as text_error:
                        print(f"   ⚠️ 최종 요약: response.text 실패, fallback 방법 시도: {str(text_error)}")
                        # 새로운 API의 fallback 방법 시도
                        if hasattr(final_response, 'candidates') and final_response.candidates:
                            candidate = final_response.candidates[0]
                            if hasattr(candidate, 'content') and candidate.content:
                                if hasattr(candidate.content, 'parts') and candidate.content.parts:
                                    part = candidate.content.parts[0]
                                    if hasattr(part, 'text'):
                                        final_summary_text = part.text
                                        if final_summary_text:
                                            print(f"   ✅ 최종 요약: candidates[0].content.parts[0].text로 텍스트 추출 성공")
                                            research_results["final_summary"] = final_summary_text
                                            break
                                        else:
                                            final_summary_text = "최종 요약 생성 실패"
                                    else:
                                        final_summary_text = "최종 요약 생성 실패"
                                else:
                                    final_summary_text = "최종 요약 생성 실패"
                            else:
                                final_summary_text = "최종 요약 생성 실패"
                        else:
                            final_summary_text = "최종 요약 생성 실패"
                        
                        if final_summary_text and final_summary_text != "최종 요약 생성 실패":
                            research_results["final_summary"] = final_summary_text
                            break
                        else:
                            if summary_retry < max_summary_retries - 1:
                                print(f"   🔄 최종 요약 재시도 {summary_retry + 1}/{max_summary_retries}...")
                                time.sleep(summary_retry_delay)
                                summary_retry_delay *= 2
                                continue
                            else:
                                research_results["final_summary"] = "최종 요약 생성 실패"
                                break
                
                except Exception as e:
                    error_msg = str(e)
                    
                    # 504 오류인지 확인
                    if "504" in error_msg or "deadline exceeded" in error_msg.lower():
                        if summary_retry < max_summary_retries - 1:
                            print(f"⚠️ 최종 요약 재시도 {summary_retry + 1}/{max_summary_retries}: 시간 초과 (504)")
                            print(f"   {summary_retry_delay}초 후 재시도합니다...")
                            time.sleep(summary_retry_delay)
                            summary_retry_delay *= 2
                            continue
                        else:
                            print(f"❌ 최종 요약: 최대 재시도 횟수 초과 - 시간 초과 (504)")
                            research_results["final_summary"] = "최종 요약 생성 실패 - 시간 초과"
                            break
                    else:
                        # 다른 오류인 경우
                        print(f"❌ 최종 요약 생성 중 오류 발생: {error_msg}")
                        if summary_retry < max_summary_retries - 1:
                            print(f"   🔄 최종 요약 재시도 {summary_retry + 1}/{max_summary_retries}...")
                            time.sleep(summary_retry_delay)
                            summary_retry_delay *= 2
                            continue
                        else:
                            research_results["final_summary"] = "최종 요약 생성 실패"
                            break
        
        print(f"✅ 딥리서치 완료! 총 {len(research_results['iterations'])}번의 반복을 수행했습니다.")
        return research_results
    
    def save_research_results(self, results: Dict[str, Any], filename: str = None) -> str:
        """
        연구 결과를 JSON 파일로 저장
        
        Args:
            results (Dict[str, Any]): 저장할 연구 결과
            filename (str): 저장할 파일명 (없으면 자동 생성)
            
        Returns:
            str: 저장된 파일 경로
        """
        if not filename:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            # 파일명 길이 제한 (최대 100자)
            safe_topic = results['topic'][:50].replace(' ', '_').replace('\n', '_').replace('\r', '_')
            # 특수문자 제거
            safe_topic = ''.join(c for c in safe_topic if c.isalnum() or c in '_')
            filename = f"research_{safe_topic}_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"💾 연구 결과가 '{filename}'에 저장되었습니다.")
        return filename
    
    def load_research_results(self, filename: str) -> Dict[str, Any]:
        """
        저장된 연구 결과를 JSON 파일에서 로드
        
        Args:
            filename (str): 로드할 파일명
            
        Returns:
            Dict[str, Any]: 로드된 연구 결과
        """
        with open(filename, 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        print(f"📂 연구 결과를 '{filename}'에서 로드했습니다.")
        return results
    
    def print_research_summary(self, results: Dict[str, Any]):
        """
        연구 결과를 보기 좋게 출력
        
        Args:
            results (Dict[str, Any]): 출력할 연구 결과
        """
        print("\n" + "="*60)
        print(f"🔬 딥리서치 결과: {results['topic']}")
        print("="*60)
        print(f"📅 연구 시간: {results['timestamp']}")
        print(f"🔍 연구 깊이: {results['depth']}")
        print(f"🔍 Google 검색 사용: {'예' if results.get('use_google_search', False) else '아니오'}")
        print(f"🔄 총 반복 횟수: {len(results['iterations'])}")
        
        print("\n📋 최종 요약:")
        print("-" * 40)
        print(results['final_summary'])
        
        print(f"\n📚 상세 결과는 총 {len(results['iterations'])}개의 반복에서 생성되었습니다.")
        print("전체 결과를 보려면 save_research_results()로 저장된 파일을 확인하세요.")


def main():
    """
    메인 실행 함수 - 예시 사용법
    """
    print("🚀 Gemini Deep Research 시작!")
    
    # API 키 설정 (환경변수에서 읽거나 직접 입력)
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        print("⚠️  GOOGLE_API_KEY 환경변수가 설정되지 않았습니다.")
        print("Google AI Studio에서 API 키를 발급받아 환경변수에 설정하세요.")
        return
    
    try:
        # Deep Research 인스턴스 생성 (Google 검색 기능 비활성화)
        researcher = GeminiDeepResearch(api_key, use_google_search=False)
        
        # 예시 연구 주제
        research_topic = "인공지능의 윤리적 문제와 해결 방안"
        
        # 딥리서치 실행
        results = researcher.research_topic(
            topic=research_topic,
            depth="deep",
            max_iterations=3
        )
        
        # 결과 저장
        filename = researcher.save_research_results(results)
        
        # 결과 요약 출력
        researcher.print_research_summary(results)
        
        print(f"\n🎉 연구 완료! 전체 결과는 '{filename}' 파일에서 확인할 수 있습니다.")
        
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")


if __name__ == "__main__":
    main()

import asyncio
from typing import Dict, Any
from deep_research import GeminiDeepResearch
import os

class ResearchManager:
    """Deep Research 실행을 관리하는 클래스"""
    
    def __init__(self, use_google_search: bool = False):
        self.researcher = None
        self.use_google_search = use_google_search
        self.initialize_researcher()
    
    def initialize_researcher(self):
        """Deep Research 인스턴스 초기화"""
        try:
            self.researcher = GeminiDeepResearch(use_google_search=self.use_google_search)
            print("✅ Deep Research 인스턴스가 초기화되었습니다.")
        except Exception as e:
            print(f"❌ Deep Research 초기화 실패: {str(e)}")
            self.researcher = None
    
    def is_research_request(self, message: str) -> bool:
        """메시지가 연구 요청인지 판단"""
        research_keywords = [
            "연구해줘", "분석해줘", "조사해줘", "알려줘", "설명해줘",
            "research", "analyze", "investigate", "explain", "tell me about"
        ]
        
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in research_keywords)
    
    def extract_topic(self, message: str) -> str:
        """메시지에서 연구 주제 추출"""
        # 간단한 주제 추출 로직
        # 실제로는 더 정교한 NLP 처리가 필요할 수 있음
        
        # 키워드 제거
        keywords_to_remove = [
            "연구해줘", "분석해줘", "조사해줘", "알려줘", "설명해줘",
            "research", "analyze", "investigate", "explain", "tell me about",
            "please", "해줘", "해주세요"
        ]
        
        topic = message
        for keyword in keywords_to_remove:
            topic = topic.replace(keyword, "").replace(keyword.upper(), "").replace(keyword.title(), "")
        
        return topic.strip()
    
    async def run_research(self, topic: str, depth: str = "deep", max_iterations: int = 3, use_search: bool = None) -> Dict[str, Any]:
        """비동기로 Deep Research 실행"""
        if not self.researcher:
            raise Exception("Deep Research 인스턴스가 초기화되지 않았습니다.")
        
        # 검색 기능 사용 여부 결정
        search_enabled = use_search if use_search is not None else self.use_google_search
        
        # 별도 스레드에서 실행하여 Discord 봇이 블록되지 않도록 함
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None, 
            self.researcher.research_topic, 
            topic, 
            depth, 
            max_iterations,
            search_enabled
        )
        
        # 결과 저장
        filename = self.researcher.save_research_results(results)
        results['filename'] = filename
        
        return results

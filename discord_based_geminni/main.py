import discord
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv
from deep_research import GeminiDeepResearch
from discord_handler import DiscordHandler
from research_manager import ResearchManager

# 환경변수 로드
load_dotenv()

class DeepResearchBot(commands.Bot):
    def __init__(self, use_google_search: bool = False):
        intents = discord.Intents.default()
        intents.message_content = True  # 메시지 내용 읽기 권한
        # intents.guilds = True  # 서버 정보 권한 (기본적으로 활성화됨)
        
        super().__init__(command_prefix='!', intents=intents)
        self.research_manager = ResearchManager(use_google_search=use_google_search)
        self.discord_handler = DiscordHandler()
        
    async def setup_hook(self):
        print("🤖 Deep Research Discord Bot이 시작되었습니다!")
        
    async def on_ready(self):
        print(f"✅ {self.user}로 로그인되었습니다!")
        print(f"🔗 서버 수: {len(self.guilds)}")
        
    async def on_message(self, message):
        if message.author == self.user:
            return
            
        # 봇 명령어 처리
        await self.process_commands(message)
        
        # 일반 메시지에서 연구 요청 감지
        if self.research_manager.is_research_request(message.content):
            await self.handle_research_request(message)

    async def handle_research_request(self, message):
        """연구 요청을 처리하는 메서드"""
        try:
            # Deep Research 상태 확인
            if not self.research_manager.researcher:
                await message.channel.send("❌ Deep Research가 초기화되지 않았습니다. Google API 키를 확인해주세요.")
                return
            
            # 사용자에게 처리 중임을 알림
            processing_msg = await message.channel.send("🔍 연구를 시작합니다... 잠시만 기다려주세요.")
            
            # Deep Research 실행
            topic = self.research_manager.extract_topic(message.content)
            results = await self.research_manager.run_research(topic)
            
            # 결과를 Discord로 전송
            await self.discord_handler.send_research_results(message.channel, results, processing_msg)
            
        except Exception as e:
            error_msg = f"❌ 오류가 발생했습니다: {str(e)}"
            print(error_msg)
            
            # 오류 메시지가 길면 분할하여 전송
            if len(error_msg) > 1900:
                # 메시지를 여러 부분으로 분할
                parts = []
                current_part = ""
                sentences = error_msg.split('. ')
                
                for sentence in sentences:
                    if sentence != sentences[-1]:
                        sentence += '. '
                    
                    if len(current_part) + len(sentence) <= 1900:
                        current_part += sentence
                    else:
                        if current_part.strip():
                            parts.append(current_part.strip())
                        current_part = sentence
                
                if current_part.strip():
                    parts.append(current_part.strip())
                
                for part in parts:
                    await message.channel.send(part)
            else:
                await message.channel.send(error_msg)

def main():
    """메인 실행 함수"""
    # Discord 봇 토큰 확인
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("❌ DISCORD_TOKEN 환경변수가 설정되지 않았습니다.")
        print("Discord Developer Portal에서 봇 토큰을 발급받아 .env 파일에 설정하세요.")
        return
    
    # Google API 키 확인
    google_api_key = os.getenv('GOOGLE_API_KEY')
    if not google_api_key:
        print("❌ GOOGLE_API_KEY 환경변수가 설정되지 않았습니다.")
        print("Google AI Studio에서 API 키를 발급받아 .env 파일에 설정하세요.")
        return
    
    # Google 검색 기능 사용 여부 설정
    use_google_search = os.getenv('USE_GOOGLE_SEARCH', 'false').lower() == 'true'
    
    # 봇 생성 및 실행
    bot = DeepResearchBot(use_google_search=use_google_search)
    
    try:
        bot.run(token)
    except Exception as e:
        print(f"❌ 봇 실행 중 오류 발생: {str(e)}")

if __name__ == "__main__":
    main()

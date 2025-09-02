import discord
from discord import Embed
from typing import Dict, Any, List
import asyncio

class DiscordHandler:
    """Discord로 연구 결과를 전송하는 클래스"""
    
    def __init__(self):
        self.max_message_length = 1900  # 안전 마진을 위해 1900자로 제한
        
    def split_text(self, text: str, max_length: int = None) -> List[str]:
        """긴 텍스트를 여러 부분으로 분할"""
        if max_length is None:
            max_length = self.max_message_length
        
        if len(text) <= max_length:
            return [text]
        
        parts = []
        current_part = ""
        
        # 문장 단위로 분할 (더 자연스러운 분할)
        sentences = text.split('. ')
        
        for sentence in sentences:
            # 마지막 문장이면 마침표 추가
            if sentence != sentences[-1]:
                sentence += '. '
            
            # 현재 부분에 문장을 추가할 수 있는지 확인
            if len(current_part) + len(sentence) <= max_length:
                current_part += sentence
            else:
                # 현재 부분이 비어있지 않으면 추가
                if current_part.strip():
                    parts.append(current_part.strip())
                current_part = sentence
        
        # 마지막 부분 추가
        if current_part.strip():
            parts.append(current_part.strip())
        
        return parts
    
    async def send_research_results(self, channel, results: Dict[str, Any], processing_msg):
        """연구 결과를 Discord로 전송"""
        try:
            # 처리 중 메시지 삭제
            try:
                await processing_msg.delete()
            except:
                pass
            
            # 결과 요약 전송
            topic = results.get('topic', '알 수 없는 주제')
            depth = results.get('depth', 'medium')
            iterations_count = len(results.get('iterations', []))
            
            # 기본 정보 전송
            summary_embed = Embed(
                title=f"🔬 딥리서치 완료: {topic}",
                description=f"연구 깊이: {depth} | 반복 횟수: {iterations_count}",
                color=0x00ff00
            )
            
            # 최종 요약 추가
            final_summary = results.get('final_summary', '요약 없음')
            if final_summary and final_summary != '요약 없음':
                # 요약이 길면 분할
                summary_parts = self.split_text(final_summary, 1000)
                for i, part in enumerate(summary_parts):
                    if i == 0:
                        summary_embed.add_field(
                            name="📋 최종 요약",
                            value=part,
                            inline=False
                        )
                    else:
                        summary_embed.add_field(
                            name=f"📋 요약 (계속)",
                            value=part,
                            inline=False
                        )
            
            # 파일 정보 추가
            filename = results.get('filename', '알 수 없음')
            summary_embed.add_field(
                name="💾 상세 결과",
                value=f"전체 결과는 `{filename}` 파일에서 확인할 수 있습니다.",
                inline=False
            )
            
            summary_embed.set_footer(text=f"연구 완료 시간: {results.get('timestamp', '알 수 없음')}")
            
            await channel.send(embed=summary_embed)
            
            # 상세 결과를 여러 메시지로 분할하여 전송
            iterations = results.get('iterations', [])
            if iterations:
                await channel.send("📚 **상세 연구 결과:**")
                
                for i, iteration in enumerate(iterations):
                    iteration_num = iteration.get('iteration', i + 1)
                    response_text = iteration.get('response', '')
                    
                    if response_text:
                        # 응답 텍스트를 여러 메시지로 분할
                        text_parts = self.split_text(response_text)
                        
                        for j, part in enumerate(text_parts):
                            if j == 0:
                                message_content = f"**반복 {iteration_num}/3:**\n{part}"
                            else:
                                message_content = f"**반복 {iteration_num}/3 (계속):**\n{part}"
                            
                            # 메시지가 너무 길면 임베드 사용
                            if len(message_content) > 1900:
                                embed = Embed(
                                    title=f"반복 {iteration_num}/3",
                                    description=part,
                                    color=0x0099ff
                                )
                                await channel.send(embed=embed)
                            else:
                                await channel.send(message_content)
                        
                        # 반복 간 구분선
                        if i < len(iterations) - 1:
                            await channel.send("─" * 50)
            
            print(f"✅ Discord로 연구 결과 전송 완료")
            
        except Exception as e:
            error_msg = f"❌ 결과 전송 중 오류 발생: {str(e)}"
            print(error_msg)
            
            # 오류 메시지가 길면 분할
            if len(error_msg) > 1900:
                error_parts = self.split_text(error_msg)
                for part in error_parts:
                    await channel.send(part)
            else:
                await channel.send(error_msg)

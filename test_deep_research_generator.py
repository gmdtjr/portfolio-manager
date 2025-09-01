#!/usr/bin/env python3
"""
일일 브리핑 생성기 테스트 스크립트
"""

import os
import pandas as pd
from dotenv import load_dotenv
from deep_research_question_generator import DeepResearchQuestionGenerator

def main():
    """Deep Research 질문 생성 테스트"""
    print("🤖 Deep Research 질문 생성기 테스트")
    print("=" * 50)
    
    # 환경변수 로드
    load_dotenv()
    
    # 필수 환경변수 확인
    spreadsheet_id = os.getenv('GOOGLE_SPREADSHEET_ID')
    google_api_key = os.getenv('GOOGLE_API_KEY')
    
    if not spreadsheet_id:
        print("❌ GOOGLE_SPREADSHEET_ID 환경변수가 설정되지 않았습니다.")
        return
    
    if not google_api_key:
        print("❌ GOOGLE_API_KEY 환경변수가 설정되지 않았습니다.")
        return
    
    try:
        # Deep Research 질문 생성기 초기화
        print("🔧 Deep Research 질문 생성기를 초기화하고 있습니다...")
        generator = DeepResearchQuestionGenerator(spreadsheet_id)
        print("✅ 초기화 완료")
        
        # 포트폴리오 데이터 읽기
        print("\n📋 포트폴리오 데이터를 읽고 있습니다...")
        portfolio_df = generator.read_portfolio_data()
        print(f"✅ 포트폴리오 데이터 읽기 완료: {len(portfolio_df)}개 종목")
        
        # Deep Research 질문 생성 프롬프트 생성
        print("\n📝 Deep Research 질문 생성 프롬프트 생성 중...")
        deep_research_prompt = generator.generate_deep_research_questions(portfolio_df)
        print("✅ Deep Research 질문 생성 프롬프트 생성 완료")
        print("\n" + "="*50)
        print("📝 Deep Research 질문 생성 메타 프롬프트:")
        print("="*50)
        print(deep_research_prompt)
        
        # AI 질문 생성 (선택사항)
        print("\n🤖 Deep Research용 질문들을 생성 중... (이 단계는 시간이 걸릴 수 있습니다)")
        user_input = input("AI 질문 생성을 진행하시겠습니까? (y/n): ")
        
        if user_input.lower() == 'y':
            ai_questions = generator.generate_ai_research_questions(portfolio_df)
            print("✅ Deep Research용 질문들 생성 완료")
            print("\n" + "="*50)
            print("🤖 Deep Research용 질문들:")
            print("="*50)
            print(ai_questions)
            
            # 질문들을 파일로 저장
            with open('deep_research_questions.txt', 'w', encoding='utf-8') as f:
                f.write(ai_questions)
            print("\n💾 Deep Research 질문들이 'deep_research_questions.txt' 파일로 저장되었습니다.")
        else:
            print("⏭️ AI 질문 생성을 건너뜁니다.")
        
        # 프롬프트들을 파일로 저장
        with open('deep_research_prompt.txt', 'w', encoding='utf-8') as f:
            f.write(deep_research_prompt)
        print("💾 Deep Research 질문 생성 프롬프트가 'deep_research_prompt.txt' 파일로 저장되었습니다.")
        
        print("\n✅ 모든 테스트가 완료되었습니다!")
        
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
        import traceback
        print(f"상세 오류: {traceback.format_exc()}")

if __name__ == "__main__":
    main()

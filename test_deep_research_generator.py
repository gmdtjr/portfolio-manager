#!/usr/bin/env python3
"""
일일 브리핑 생성기 테스트 스크립트
"""

import os
import pandas as pd
from dotenv import load_dotenv
from deep_research_question_generator import DeepResearchQuestionGenerator

# 투자 노트 매니저 import
try:
    from investment_notes_manager import InvestmentNotesManager
    INVESTMENT_NOTES_AVAILABLE = True
except ImportError:
    INVESTMENT_NOTES_AVAILABLE = False

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
        
        # 투자 노트 매니저 초기화 (선택사항)
        notes_manager = None
        if INVESTMENT_NOTES_AVAILABLE:
            print("🔧 투자 노트 매니저를 초기화하고 있습니다...")
            notes_manager = InvestmentNotesManager(spreadsheet_id)
            
            # 투자_노트 시트가 없으면 생성
            try:
                notes_df = notes_manager.read_investment_notes()
                print(f"📊 현재 투자 노트: {len(notes_df)}개 종목")
            except:
                print("📝 '투자_노트' 시트가 없습니다. 새로 생성합니다.")
                notes_manager.create_investment_notes_sheet()
                notes_df = notes_manager.read_investment_notes()
                print(f"📊 투자 노트 시트 생성 완료: {len(notes_df)}개 종목")
        else:
            print("⚠️ 투자 노트 매니저를 사용할 수 없습니다.")
        
        # 포트폴리오 데이터 읽기
        print("\n📋 포트폴리오 데이터를 읽고 있습니다...")
        portfolio_df = generator.read_portfolio_data()
        print(f"✅ 포트폴리오 데이터 읽기 완료: {len(portfolio_df)}개 종목")
        
        # 투자 노트가 있는 종목들 확인
        if notes_manager:
            portfolio_notes = notes_manager.get_notes_by_portfolio(portfolio_df)
            missing_notes = notes_manager.get_missing_notes(portfolio_df)
            
            print(f"\n📝 포트폴리오 투자 노트 현황:")
            print(f"- 투자 노트 있는 종목: {len(portfolio_notes)}개")
            print(f"- 투자 노트 없는 종목: {len(missing_notes)}개")
            
            if missing_notes:
                print(f"- 투자 노트가 필요한 종목들: {', '.join(missing_notes)}")
        
        # 기본 Deep Research 질문 생성 프롬프트 생성
        print("\n📝 기본 Deep Research 질문 생성 프롬프트 생성 중...")
        basic_prompt = generator.generate_deep_research_questions(portfolio_df)
        print("✅ 기본 프롬프트 생성 완료")
        
        # 고급 Deep Research 질문 생성 프롬프트 생성 (투자 노트 활용)
        if notes_manager:
            print("\n📝 고급 Deep Research 질문 생성 프롬프트 생성 중...")
            advanced_prompt = generator.generate_advanced_deep_research_questions(portfolio_df)
            print("✅ 고급 프롬프트 생성 완료")
        
        # AI 질문 생성 (선택사항)
        print("\n🤖 Deep Research용 질문들을 생성 중... (이 단계는 시간이 걸릴 수 있습니다)")
        user_input = input("AI 질문 생성을 진행하시겠습니까? (y/n): ")
        
        if user_input.lower() == 'y':
            # 기본 질문 생성
            print("\n🤖 기본 질문들을 생성 중...")
            basic_questions = generator.generate_ai_research_questions(portfolio_df)
            print("✅ 기본 질문들 생성 완료")
            
            # 고급 질문 생성 (투자 노트 활용)
            advanced_questions = None
            if notes_manager:
                print("\n🤖 고급 질문들을 생성 중...")
                advanced_questions = generator.generate_advanced_ai_research_questions(portfolio_df)
                print("✅ 고급 질문들 생성 완료")
            
            # 결과 저장
            with open('basic_deep_research_questions.txt', 'w', encoding='utf-8') as f:
                f.write(basic_questions)
            print("💾 기본 질문들이 'basic_deep_research_questions.txt' 파일로 저장되었습니다.")
            
            if advanced_questions:
                with open('advanced_deep_research_questions.txt', 'w', encoding='utf-8') as f:
                    f.write(advanced_questions)
                print("💾 고급 질문들이 'advanced_deep_research_questions.txt' 파일로 저장되었습니다.")
        else:
            print("⏭️ AI 질문 생성을 건너뜁니다.")
        
        # 프롬프트들을 파일로 저장
        with open('basic_deep_research_prompt.txt', 'w', encoding='utf-8') as f:
            f.write(basic_prompt)
        print("💾 기본 프롬프트가 'basic_deep_research_prompt.txt' 파일로 저장되었습니다.")
        
        if notes_manager:
            with open('advanced_deep_research_prompt.txt', 'w', encoding='utf-8') as f:
                f.write(advanced_prompt)
            print("💾 고급 프롬프트가 'advanced_deep_research_prompt.txt' 파일로 저장되었습니다.")
        
        print("\n✅ 모든 테스트가 완료되었습니다!")
        
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
        import traceback
        print(f"상세 오류: {traceback.format_exc()}")

if __name__ == "__main__":
    main()

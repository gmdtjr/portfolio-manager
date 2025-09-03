#!/usr/bin/env python3
"""
기존 투자 노트 데이터를 새로운 스키마로 마이그레이션하는 스크립트
"""

import os
from dotenv import load_dotenv
from investment_notes_manager import InvestmentNotesManager

def main():
    """마이그레이션 실행"""
    print("🔄 투자 노트 마이그레이션 시작")
    print("=" * 50)
    
    # 환경변수 로드
    load_dotenv()
    
    spreadsheet_id = os.getenv('GOOGLE_SPREADSHEET_ID')
    
    if not spreadsheet_id:
        print("❌ GOOGLE_SPREADSHEET_ID가 설정되지 않았습니다.")
        return
    
    try:
        # 투자 노트 매니저 초기화
        notes_manager = InvestmentNotesManager(spreadsheet_id)
        
        # 마이그레이션 실행
        success = notes_manager.migrate_existing_notes()
        
        if success:
            print("\n✅ 마이그레이션이 성공적으로 완료되었습니다!")
            print("💡 이제 투자 노트 자동 생성 기능을 사용할 수 있습니다.")
        else:
            print("\n❌ 마이그레이션에 실패했습니다.")
            
    except Exception as e:
        print(f"❌ 마이그레이션 실패: {e}")
        import traceback
        print(f"상세 오류: {traceback.format_exc()}")

if __name__ == "__main__":
    main()

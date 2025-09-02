import os
import pandas as pd
from dotenv import load_dotenv
from investment_notes_manager import InvestmentNotesManager
from deep_research_question_generator import DeepResearchQuestionGenerator

def check_portfolio_notes_status():
    """포트폴리오 종목들과 투자 노트 현황 확인"""
    print("📊 포트폴리오 종목과 투자 노트 현황 확인")
    print("=" * 60)
    
    # 환경변수 로드
    load_dotenv()
    
    spreadsheet_id = os.getenv('GOOGLE_SPREADSHEET_ID')
    
    if not spreadsheet_id:
        print("❌ GOOGLE_SPREADSHEET_ID가 설정되지 않았습니다.")
        return
    
    try:
        # 포트폴리오 데이터 읽기 (DeepResearchQuestionGenerator 사용)
        print("📋 포트폴리오 데이터를 읽고 있습니다...")
        generator = DeepResearchQuestionGenerator(spreadsheet_id)
        portfolio_df = generator.read_portfolio_data()
        print(f"✅ 포트폴리오 데이터 읽기 완료: {len(portfolio_df)}개 종목")
        
        # 투자 노트 데이터 읽기
        print("\n📝 투자 노트 데이터를 읽고 있습니다...")
        notes_manager = InvestmentNotesManager(spreadsheet_id)
        notes_df = notes_manager.read_investment_notes()
        print(f"✅ 투자 노트 데이터 읽기 완료: {len(notes_df)}개 종목")
        
        # 포트폴리오 종목 목록
        print("\n📋 포트폴리오 종목 목록:")
        for _, row in portfolio_df.iterrows():
            print(f"- {row['종목명']} ({row['종목코드']}) - {row['평가금액(원)']:,.0f}원")
        
        # 투자 노트가 있는 종목들
        portfolio_notes = notes_manager.get_notes_by_portfolio(portfolio_df)
        missing_notes = notes_manager.get_missing_notes(portfolio_df)
        
        print(f"\n📊 투자 노트 현황:")
        print(f"- 포트폴리오 종목 수: {len(portfolio_df)}개")
        print(f"- 투자 노트 있는 종목: {len(portfolio_notes)}개")
        print(f"- 투자 노트 없는 종목: {len(missing_notes)}개")
        
        if not portfolio_notes.empty:
            print(f"\n✅ 투자 노트가 있는 종목들:")
            for _, note in portfolio_notes.iterrows():
                print(f"- {note['종목명']} ({note['종목코드']}) - {note['마지막_수정일']}")
        
        if missing_notes:
            print(f"\n⚠️ 투자 노트가 필요한 종목들:")
            missing_stocks = portfolio_df[portfolio_df['종목코드'].astype(str).isin(missing_notes)]
            for _, stock in missing_stocks.iterrows():
                print(f"- {stock['종목명']} ({stock['종목코드']})")
        
        # 투자 노트 추가 여부 확인
        if missing_notes:
            print(f"\n🤔 투자 노트를 추가하시겠습니까?")
            user_input = input("샘플 투자 노트를 생성하시겠습니까? (y/n): ")
            
            if user_input.lower() == 'y':
                create_sample_notes(notes_manager, missing_stocks)
        
        print("\n✅ 현황 확인이 완료되었습니다!")
        
    except Exception as e:
        print(f"❌ 현황 확인 실패: {e}")
        import traceback
        print(f"상세 오류: {traceback.format_exc()}")

def create_sample_notes(notes_manager, missing_stocks):
    """누락된 종목들에 대한 샘플 투자 노트 생성"""
    print("\n📝 샘플 투자 노트를 생성합니다...")
    
    # 현재 포트폴리오에 있는 종목들에 대한 샘플 투자 노트 템플릿
    sample_notes = {
        '005490': {  # POSCO홀딩스
            '종목코드': '005490',
            '종목명': 'POSCO홀딩스',
            '투자 아이디어 (Thesis)': '글로벌 철강 산업의 리더로서, 친환경 철강 기술과 해외 사업 확장을 통한 성장.',
            '투자 확신도 (Conviction)': '중 (Medium)',
            '섹터/산업 (Sector/Industry)': '소재 > 철강 > 친환경철강',
            '투자 유형 (Asset Type)': '경기순환주 (Cyclical)',
            '핵심 촉매 (Catalysts)': '1. 친환경 철강 기술 개발 성과\n2. 해외 사업 확장 및 수익성 개선\n3. 원자재 가격 안정화',
            '핵심 리스크 (Risks)': '1. 글로벌 경기 침체로 인한 철강 수요 감소\n2. 원자재 가격 변동성\n3. 중국 철강 산업 과잉 공급',
            '핵심 모니터링 지표 (KPIs)': '1. 분기별 영업이익률\n2. 친환경 철강 매출 비중\n3. 해외 사업 매출 비중',
            '투자 기간 (Horizon)': '중장기 (2-3년)',
            '목표 주가 (Target)': '1차: 500,000원\n2차: 600,000원',
            '매도 조건 (Exit Plan)': '수익 실현: 1차 목표 주가 도달 시 30% 분할 매도\n손절: 철강 산업 구조적 악화 시 즉시 매도'
        },
        '006400': {  # 삼성SDI
            '종목코드': '006400',
            '종목명': '삼성SDI',
            '투자 아이디어 (Thesis)': '2차전지 산업의 글로벌 리더로서, 전기차 배터리 시장 확대와 에너지 저장장치(ESS) 사업 성장.',
            '투자 확신도 (Conviction)': '상 (High)',
            '섹터/산업 (Sector/Industry)': 'IT > 2차전지 > 전기차배터리',
            '투자 유형 (Asset Type)': '성장주 (Growth)',
            '핵심 촉매 (Catalysts)': '1. 전기차 배터리 공급 계약 확대\n2. ESS 시장 진출 성과\n3. 차세대 배터리 기술 개발',
            '핵심 리스크 (Risks)': '1. 중국 배터리 업체들의 가격 경쟁\n2. 원자재 가격 상승\n3. 전기차 보조금 정책 변화',
            '핵심 모니터링 지표 (KPIs)': '1. 전기차 배터리 매출 성장률\n2. ESS 사업 매출 비중\n3. 영업이익률',
            '투자 기간 (Horizon)': '장기 (3-5년)',
            '목표 주가 (Target)': '1차: 600,000원\n2차: 800,000원',
            '매도 조건 (Exit Plan)': '수익 실현: 1차 목표 주가 도달 시 30% 분할 매도\n손절: 배터리 기술 경쟁력 상실 시 즉시 매도'
        },
        '194480': {  # 데브시스터즈
            '종목코드': '194480',
            '종목명': '데브시스터즈',
            '투자 아이디어 (Thesis)': '모바일 게임 개발사로서, 글로벌 게임 시장 진출과 신작 성공을 통한 성장.',
            '투자 확신도 (Conviction)': '중 (Medium)',
            '섹터/산업 (Sector/Industry)': 'IT > 게임 > 모바일게임',
            '투자 유형 (Asset Type)': '성장주 (Growth)',
            '핵심 촉매 (Catalysts)': '1. 신작 게임 성공\n2. 글로벌 시장 진출 확대\n3. 게임 IP 라이센싱 수익 증가',
            '핵심 리스크 (Risks)': '1. 게임 시장 경쟁 심화\n2. 신작 실패 리스크\n3. 모바일 게임 시장 성장 둔화',
            '핵심 모니터링 지표 (KPIs)': '1. 신작 게임 매출 기여도\n2. 글로벌 매출 비중\n3. 영업이익률',
            '투자 기간 (Horizon)': '중기 (1-2년)',
            '목표 주가 (Target)': '1차: 200,000원\n2차: 250,000원',
            '매도 조건 (Exit Plan)': '수익 실현: 1차 목표 주가 도달 시 50% 매도\n손절: 신작 실패 시 즉시 매도'
        },
        'FSLR': {  # 퍼스트 솔라
            '종목코드': 'FSLR',
            '종목명': '퍼스트 솔라',
            '투자 아이디어 (Thesis)': '태양광 패널 제조업체로서, 재생에너지 시장 확대와 미국 IRA 정책 혜택.',
            '투자 확신도 (Conviction)': '상 (High)',
            '섹터/산업 (Sector/Industry)': '에너지 > 재생에너지 > 태양광',
            '투자 유형 (Asset Type)': '성장주 (Growth)',
            '핵심 촉매 (Catalysts)': '1. 미국 IRA 정책 혜택\n2. 태양광 설치량 증가\n3. 제조 능력 확대',
            '핵심 리스크 (Risks)': '1. 중국 태양광 업체들과의 가격 경쟁\n2. 정부 보조금 정책 변화\n3. 원자재 가격 상승',
            '핵심 모니터링 지표 (KPIs)': '1. 분기별 매출 성장률\n2. 제조 능력 활용률\n3. 영업이익률',
            '투자 기간 (Horizon)': '중장기 (2-3년)',
            '목표 주가 (Target)': '1차: $300\n2차: $400',
            '매도 조건 (Exit Plan)': '수익 실현: 1차 목표 주가 도달 시 30% 분할 매도\n손절: IRA 정책 변화 시 즉시 매도'
        },
        'GOOGL': {  # 알파벳 A
            '종목코드': 'GOOGL',
            '종목명': '알파벳 A',
            '투자 아이디어 (Thesis)': 'AI 기술 혁신을 통한 광고 사업 강화와 클라우드 사업 성장.',
            '투자 확신도 (Conviction)': '상 (High)',
            '섹터/산업 (Sector/Industry)': 'IT > 인터넷 > AI플랫폼',
            '투자 유형 (Asset Type)': '성장주 (Growth)',
            '핵심 촉매 (Catalysts)': '1. AI 기술 혁신 성과\n2. 클라우드 사업 성장\n3. 광고 시장 회복',
            '핵심 리스크 (Risks)': '1. 규제 환경 변화\n2. AI 경쟁 심화\n3. 광고 시장 침체',
            '핵심 모니터링 지표 (KPIs)': '1. 클라우드 사업 매출 성장률\n2. AI 서비스 사용자 수\n3. 광고 매출 성장률',
            '투자 기간 (Horizon)': '장기 (3-5년)',
            '목표 주가 (Target)': '1차: $200\n2차: $250',
            '매도 조건 (Exit Plan)': '수익 실현: 1차 목표 주가 도달 시 30% 분할 매도\n손절: AI 경쟁력 상실 시 즉시 매도'
        },
        'NVDA': {  # 엔비디아
            '종목코드': 'NVDA',
            '종목명': '엔비디아',
            '투자 아이디어 (Thesis)': 'AI 반도체 시장의 절대적 리더로서, AI 수요 증가와 데이터센터 사업 성장.',
            '투자 확신도 (Conviction)': '상 (High)',
            '섹터/산업 (Sector/Industry)': 'IT > 반도체 > AI반도체',
            '투자 유형 (Asset Type)': '성장주 (Growth)',
            '핵심 촉매 (Catalysts)': '1. AI 수요 증가\n2. 데이터센터 사업 성장\n3. 자율주행 기술 발전',
            '핵심 리스크 (Risks)': '1. 경쟁사들의 AI 반도체 개발\n2. 반도체 수요 감소\n3. 규제 환경 변화',
            '핵심 모니터링 지표 (KPIs)': '1. 데이터센터 매출 성장률\n2. AI 반도체 매출 비중\n3. 영업이익률',
            '투자 기간 (Horizon)': '장기 (3-5년)',
            '목표 주가 (Target)': '1차: $1,000\n2차: $1,200',
            '매도 조건 (Exit Plan)': '수익 실현: 1차 목표 주가 도달 시 30% 분할 매도\n손절: AI 반도체 경쟁력 상실 시 즉시 매도'
        }
    }
    
    created_count = 0
    for _, stock in missing_stocks.iterrows():
        stock_code = str(stock['종목코드'])
        stock_name = stock['종목명']
        
        # 샘플 노트가 있으면 사용, 없으면 기본 템플릿 생성
        if stock_code in sample_notes:
            note_data = sample_notes[stock_code]
        else:
            # 기본 템플릿 생성
            note_data = {
                '종목코드': stock_code,
                '종목명': stock_name,
                '투자 아이디어 (Thesis)': f'{stock_name}에 대한 투자 아이디어를 작성해주세요.',
                '투자 확신도 (Conviction)': '중 (Medium)',
                '섹터/산업 (Sector/Industry)': '섹터 > 산업 > 세부산업',
                '투자 유형 (Asset Type)': '성장주 (Growth)',
                '핵심 촉매 (Catalysts)': '1. 첫 번째 촉매\n2. 두 번째 촉매\n3. 세 번째 촉매',
                '핵심 리스크 (Risks)': '1. 첫 번째 리스크\n2. 두 번째 리스크\n3. 세 번째 리스크',
                '핵심 모니터링 지표 (KPIs)': '1. 첫 번째 지표\n2. 두 번째 지표\n3. 세 번째 지표',
                '투자 기간 (Horizon)': '중기 (1-2년)',
                '목표 주가 (Target)': '1차: 목표 주가 설정\n2차: 두 번째 목표 주가',
                '매도 조건 (Exit Plan)': '수익 실현: 목표 주가 도달 시 분할 매도\n손절: 투자 아이디어 훼손 시 즉시 매도'
            }
        
        # 투자 노트 추가
        if notes_manager.add_investment_note(note_data):
            created_count += 1
            print(f"✅ {stock_name} ({stock_code}) 투자 노트 생성 완료")
        else:
            print(f"⚠️ {stock_name} ({stock_code}) 투자 노트 생성 실패")
    
    print(f"\n📝 총 {created_count}개의 투자 노트가 생성되었습니다.")

def main():
    """메인 함수"""
    check_portfolio_notes_status()

if __name__ == "__main__":
    main()

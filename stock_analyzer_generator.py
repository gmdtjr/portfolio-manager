"""
종목 상세 분석기 모듈
사용자가 입력한 종목명을 받아 전문가 수준의 심층 분석용 Deep Research 프롬프트를 생성합니다.
"""

from datetime import datetime


class StockAnalyzerGenerator:
    """종목 상세 분석 프롬프트 생성기"""
    
    def __init__(self):
        """초기화"""
        pass
    
    def generate_deep_dive_prompt(self, stock_name: str) -> str:
        """
        사용자가 입력한 종목명을 받아,
        전문가 수준의 심층 분석용 Deep Research 프롬프트를 생성합니다.
        
        Args:
            stock_name (str): 분석할 종목명 또는 코드
            
        Returns:
            str: 생성된 Deep Research 프롬프트
        """
        
        # 사용자가 입력한 종목명을 프롬프트의 여러 위치에 삽입합니다.
        sanitized_stock_name = stock_name.strip()
        today = datetime.now().strftime('%Y년 %m월 %d일')
        
        # 마스터 프롬프트 템플릿
        master_prompt_template = f"""# {sanitized_stock_name} 기업 심층 분석 보고서 ({today})

## **[중요 지시사항]**
- **모든 결과물은 반드시 한글로만 작성해주세요.**
- 영문 용어는 필요한 경우에만 괄호 안에 병기하고(예: 경제적 해자(Economic Moat)), 그 외 모든 서술은 한글로 해야 합니다.

## **분석 목표:**
{sanitized_stock_name}에 대한 종합적인 분석을 통해, 이 기업의 장기 투자 매력도를 평가하고 핵심 투자 포인트를 도출하시오.

## **분석 목차:**
*아래 목차 순서와 항목을 반드시 준수하여 보고서를 작성해주십시오.*

**1. 기업 개요 (Business Overview):**
   - 주요 비즈니스 모델과 핵심 제품/서비스의 역할은 무엇인가?
   - 전체 매출에서 각 사업 부문이 차지하는 비중은 어떻게 되는가?

**2. 산업 분석 (Industry Analysis):**
   - {sanitized_stock_name}이 속한 산업의 구조와 전반적인 성장 전망은 어떠한가?
   - 주요 경쟁사는 누구이며, 경쟁 환경은 어떠한가?

**3. 경제적 해자 (Economic Moat):**
   - {sanitized_stock_name}이 가진 가장 강력한 경쟁 우위는 무엇인가? (예: 독점적 기술력, 브랜드 가치, 네트워크 효과, 높은 전환 비용 등)
   - 이 해자는 얼마나 오랫동안 지속 가능할 것으로 보는가?

**4. 성장 동력 (Growth Drivers):**
   - 향후 3~5년간 {sanitized_stock_name}의 성장을 이끌 핵심 동력은 무엇인가?
   - AI, 클라우드 컴퓨팅, 인구 변화 등 거시적 트렌드가 이 기업에 미치는 긍정적 영향은 무엇인가?

**5. 핵심 리스크 (Key Risks):**
   - {sanitized_stock_name}의 투자 아이디어를 훼손할 수 있는 가장 큰 내부/외부 리스크는 무엇인가? (최소 3가지 이상)
   - (예: 지정학적 리스크, 기술 변화 리스크, 규제 리스크, 경기 순환 리스크 등)

**6. 재무 분석 (Financial Analysis):**
   - 최근 3년간의 핵심 재무 지표(매출, 영업이익률, 순이익, 현금 흐름)를 분석하고, 재무 건전성을 평가하시오.

**7. 밸류에이션 (Valuation):**
   - 동종 업계 경쟁사(Peer Group)와 비교했을 때, 현재 {sanitized_stock_name}의 주가 수준은 고평가인가, 저평가인가?
   - (PER, PBR, EV/EBITDA 등 다양한 지표를 활용하여 분석)

**8. 종합 결론 및 투자의견:**
   - 위 모든 분석을 종합하여, {sanitized_stock_name}에 대한 최종 투자의견(예: 매수/보유/매도)과 그 핵심 근거를 제시하시오.
"""
        
        return master_prompt_template.strip()


def main():
    """테스트용 메인 함수"""
    print("🧪 종목 상세 분석기 테스트")
    print("=" * 50)
    
    generator = StockAnalyzerGenerator()
    
    # 테스트 종목들
    test_stocks = ["엔비디아", "ASML", "005930"]
    
    for stock in test_stocks:
        print(f"\n📊 {stock} 분석 프롬프트 생성 중...")
        prompt = generator.generate_deep_dive_prompt(stock)
        print(f"✅ 프롬프트 생성 완료 (길이: {len(prompt)}자)")
        print(f"📝 프롬프트 미리보기:\n{prompt[:200]}...")
    
    print("\n✅ 테스트가 완료되었습니다!")


if __name__ == "__main__":
    main()

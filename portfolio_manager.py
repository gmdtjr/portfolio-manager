import os
import requests
import json
import pandas as pd
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build  # pyright: ignore[reportMissingImports]
from dotenv import load_dotenv
import time
from dataclasses import dataclass
from typing import Optional, List, Dict

load_dotenv()

@dataclass
class RequestHeader:
    authorization: str
    appkey: str
    appsecret: str
    tr_id: str
    content_type: Optional[str] = None
    personalseckey: Optional[str] = None
    tr_cont: Optional[str] = None
    custtype: Optional[str] = None
    seq_no: Optional[str] = None
    mac_address: Optional[str] = None
    phone_number: Optional[str] = None
    ip_addr: Optional[str] = None
    hashkey: Optional[str] = None
    gt_uid: Optional[str] = None

@dataclass
class DomesticRequestQueryParam:
    CANO: str
    ACNT_PRDT_CD: str
    AFHR_FLPR_YN: str
    INQR_DVSN: str
    UNPR_DVSN: str
    FUND_STTL_ICLD_YN: str
    FNCG_AMT_AUTO_RDPT_YN: str
    PRCS_DVSN: str
    OFL_YN: Optional[str] = None
    CTX_AREA_FK100: Optional[str] = None
    CTX_AREA_NK100: Optional[str] = None

@dataclass
class OverseasRequestQueryParam:
    CANO: str
    ACNT_PRDT_CD: str
    OVRS_EXCG_CD: str
    TR_CRCY_CD: str
    CTX_AREA_FK200: Optional[str] = None
    CTX_AREA_NK200: Optional[str] = None

@dataclass
class DomesticCashRequestQueryParam:
    CANO: str
    ACNT_PRDT_CD: str
    PDNO: str
    ORD_UNPR: str
    ORD_DVSN: str
    CMA_EVLU_AMT_ICLD_YN: str
    OVRS_ICLD_YN: str

@dataclass
class OverseasCashRequestQueryParam:
    CANO: str
    ACNT_PRDT_CD: str
    OVRS_EXCG_CD: str
    OVRS_ORD_UNPR: str
    ITEM_CD: str

class Account:
    def __init__(self, name: str, acc_no: str, api_key: str, api_secret: str, account_type: str):
        self.name = name
        self.acc_no = acc_no
        self.api_key = api_key
        self.api_secret = api_secret
        self.account_type = account_type
        self.cano, self.acnt_prdt_cd = self._parse_account_number(acc_no)
    
    def _parse_account_number(self, acc_no: str) -> tuple[str, str]:
        """계좌번호를 CANO와 ACNT_PRDT_CD로 분리"""
        if not acc_no:
            raise ValueError("계좌번호가 설정되지 않았습니다.")
        
        if '-' in acc_no:
            parts = acc_no.split('-')
            if len(parts) == 2:
                return parts[0], parts[1]
        return acc_no, "01"

class ExchangeRateAPI:
    """환율 API 클래스"""
    
    @staticmethod
    def get_usd_krw_rate() -> tuple[float, str]:
        """달러/원 환율 조회 (여러 API 시도)"""
        apis = [
            ExchangeRateAPI._try_exchangerate_api,
            ExchangeRateAPI._try_fixer_api,
            ExchangeRateAPI._try_currency_api
        ]
        
        for api_func in apis:
            try:
                rate = api_func()
                if rate and rate > 0:
                    print(f"💰 현재 달러 환율: {rate:,.2f}원")
                    return rate, api_func.__name__
            except Exception as e:
                print(f"⚠️ 환율 API 실패 ({api_func.__name__}): {e}")
                continue
        
        # 모든 API 실패 시 기본값 사용
        print("⚠️ 모든 환율 API 실패, 기본값 1300원 사용")
        return 1300.0, "default"
    
    @staticmethod
    def _try_exchangerate_api() -> Optional[float]:
        """ExchangeRate-API.com 사용"""
        try:
            url = "https://api.exchangerate-api.com/v4/latest/USD"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return float(data['rates']['KRW'])
        except Exception:
            pass
        return None
    
    @staticmethod
    def _try_fixer_api() -> Optional[float]:
        """Fixer.io API 사용 (무료 버전)"""
        try:
            url = "http://data.fixer.io/api/latest?access_key=free&base=USD&symbols=KRW"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return float(data['rates']['KRW'])
        except Exception:
            pass
        return None
    
    @staticmethod
    def _try_currency_api() -> Optional[float]:
        """Currency API 사용"""
        try:
            url = "https://api.currencyapi.com/v3/latest?apikey=free&currencies=KRW&base_currency=USD"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return float(data['data']['KRW']['value'])
        except Exception:
            pass
        return None

class KoreaInvestmentAPI:
    """한국투자증권 API 클래스"""
    
    def __init__(self):
        self.base_url = "https://openapi.koreainvestment.com:9443"
        self.access_tokens = {}
        self.token_expiry = {}
        self.exchange_rate = None
        self.exchange_rate_source = None
    
    def get_access_token(self, account: Account) -> str:
        """접근 토큰 발급 (계좌별로 관리)"""
        # 토큰이 유효한 경우 재사용
        if (account.name in self.access_tokens and 
            account.name in self.token_expiry and 
            datetime.now() < self.token_expiry[account.name]):
            return self.access_tokens[account.name]
        
        # 토큰 발급 제한 방지를 위한 재시도 로직
        max_retries = 3
        for attempt in range(max_retries):
            try:
                headers = {"content-type": "application/json"}
                body = {
                    "grant_type": "client_credentials",
                    "appkey": account.api_key,
                    "appsecret": account.api_secret
                }
                url = f"{self.base_url}/oauth2/tokenP"
                response = requests.post(url, headers=headers, data=json.dumps(body))
                
                if response.status_code == 200:
                    token_data = response.json()
                    self.access_tokens[account.name] = token_data["access_token"]
                    # 토큰 만료 시간 설정 (23시간 후)
                    self.token_expiry[account.name] = datetime.now() + timedelta(hours=23)
                    print(f"✅ {account.name} 계좌 접근 토큰이 발급되었습니다.")
                    return self.access_tokens[account.name]
                else:
                    print(f"⚠️ {account.name} 계좌 토큰 발급 실패: {response.text}")
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 30
                        print(f"⏳ 토큰 발급 제한. {wait_time}초 후 재시도... ({attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                    
            except Exception as e:
                print(f"❌ {account.name} 계좌 토큰 발급 중 오류: {e}")
                if attempt < max_retries - 1:
                    time.sleep(30)
        
        raise Exception(f"{account.name} 계좌 토큰 발급 실패")
    
    def get_domestic_cash(self, account: Account) -> float:
        """국내 주식 계좌 현금 잔고 조회 (원화)"""
        try:
            access_token = self.get_access_token(account)
            
            # 국내 주식 매수 가능 금액 조회 API
            url = f"{self.base_url}/uapi/domestic-stock/v1/trading/inquire-psbl-order"
            
            headers = {
                "Content-Type": "application/json",
                "authorization": f"Bearer {access_token}",
                "appKey": account.api_key,
                "appSecret": account.api_secret,
                "tr_id": "TTTC8908R",
                "custtype": "P"
            }
            
            params = {
                "CANO": account.cano,
                "ACNT_PRDT_CD": account.acnt_prdt_cd,
                "PDNO": "005930",  # 삼성전자 (임의 종목)
                "ORD_UNPR": "65500",
                "ORD_DVSN": "01",
                "CMA_EVLU_AMT_ICLD_YN": "Y",
                "OVRS_ICLD_YN": "Y"
            }
            
            print(f"🔍 {account.name} 계좌 현금 잔고 조회 중...")
            
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("rt_cd") == "0":
                    cash_amount = int(data.get("output", {}).get("ord_psbl_cash", "0"))
                    print(f"💰 {account.name} 계좌 현금 잔고: {cash_amount:,}원")
                    return cash_amount
                else:
                    print(f"⚠️ {account.name} 계좌 현금 조회 실패: {data.get('msg1', '알 수 없는 오류')}")
                    return 0
            else:
                print(f"❌ {account.name} 계좌 현금 API 요청 실패: {response.status_code}")
                return 0
                
        except Exception as e:
            print(f"❌ {account.name} 계좌 현금 조회 중 오류: {e}")
            return 0
    
    def get_overseas_cash(self, account: Account) -> float:
        """해외 주식 계좌 현금 잔고 조회 (원화로 변환)"""
        try:
            access_token = self.get_access_token(account)
            
            # 해외 주식 매수 가능 금액 조회 API
            url = f"{self.base_url}/uapi/overseas-stock/v1/trading/inquire-psamount"
            
            headers = {
                "Content-Type": "application/json",
                "authorization": f"Bearer {access_token}",
                "appKey": account.api_key,
                "appSecret": account.api_secret,
                "tr_id": "TTTS3007R"
            }
            
            params = {
                "CANO": account.cano,
                "ACNT_PRDT_CD": account.acnt_prdt_cd,
                "OVRS_EXCG_CD": "NASD",
                "OVRS_ORD_UNPR": "100.00",
                "ITEM_CD": "AAPL"
            }
            
            print(f"🔍 {account.name} 계좌 현금 잔고 조회 중...")
            
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("rt_cd") == "0":
                    # 주문가능외화금액 사용
                    usd_cash = float(data.get("output", {}).get("ord_psbl_frcr_amt", "0"))
                    
                    # 환율이 설정되지 않은 경우 기본값 사용
                    exchange_rate = self.exchange_rate or 1300.0
                    krw_cash = usd_cash * exchange_rate
                    
                    print(f"💰 {account.name} 계좌 현금 잔고: ${usd_cash:,.2f} (₩{krw_cash:,.0f})")
                    return krw_cash
                else:
                    print(f"⚠️ {account.name} 계좌 현금 조회 실패: {data.get('msg1', '알 수 없는 오류')}")
                    return 0
            else:
                print(f"❌ {account.name} 계좌 현금 API 요청 실패: {response.status_code}")
                return 0
                
        except Exception as e:
            print(f"❌ {account.name} 계좌 현금 조회 중 오류: {e}")
            return 0
    
    def get_domestic_portfolio(self, account: Account) -> List[Dict]:
        """국내 주식 포트폴리오 조회"""
        try:
            access_token = self.get_access_token(account)
            
            # 국내 주식 잔고 조회 API (예전 코드와 동일한 tr_id 사용)
            url = f"{self.base_url}/uapi/domestic-stock/v1/trading/inquire-balance"
            
            # 헤더 설정 (예전 코드와 동일하게)
            headers = {
                "Content-Type": "application/json",
                "authorization": f"Bearer {access_token}",
                "appKey": account.api_key,
                "appSecret": account.api_secret,
                "tr_id": "TTTC8434R",  # 예전 코드와 동일한 tr_id
                "custtype": "P"  # 예전 코드와 동일한 custtype
            }
            
            # 쿼리 파라미터 설정 (예전 코드와 동일하게)
            params = {
                "CANO": account.cano,
                "ACNT_PRDT_CD": account.acnt_prdt_cd,
                "AFHR_FLPR_YN": "N",
                "OFL_YN": "",
                "INQR_DVSN": "02",
                "UNPR_DVSN": "01",
                "FUND_STTL_ICLD_YN": "N",
                "FNCG_AMT_AUTO_RDPT_YN": "N",
                "PRCS_DVSN": "01",
                "CTX_AREA_FK100": "",
                "CTX_AREA_NK100": ""
            }
            
            print(f"🔍 {account.name} 계좌 조회 중...")
            print(f"🔍 API 요청 URL: {url}")
            print(f"🔍 API 요청 파라미터: {params}")
            
            response = requests.get(url, headers=headers, params=params)
            print(f"🔍 API 응답: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("rt_cd") == "0":
                    output1 = data.get("output1", [])
                    if output1:
                        portfolio = []
                        for item in output1:
                            try:
                                # 보유수량이 0보다 큰 경우만 포함
                                if int(float(item.get("hldg_qty", "0"))) > 0:
                                    portfolio.append({
                                        "종목코드": item.get("pdno", ""),
                                        "종목명": item.get("prdt_name", ""),
                                        "보유수량": int(float(item.get("hldg_qty", "0"))),
                                        "매입평균가": float(item.get("pchs_avg_pric", "0")),
                                        "매입금액": int(float(item.get("pchs_amt", "0"))),
                                        "현재가": int(float(item.get("prpr", "0"))),
                                        "평가금액": int(float(item.get("evlu_amt", "0"))),
                                        "평가손익": int(float(item.get("evlu_pfls_amt", "0"))),
                                        "수익률": float(item.get("evlu_pfls_rt", "0")),
                                        "계좌구분": account.name,
                                        "통화": "KRW"
                                    })
                            except (ValueError, TypeError) as e:
                                print(f"⚠️ 데이터 변환 오류: {e}, 데이터: {item}")
                                continue
                        return portfolio
                    else:
                        print(f"📊 {account.name} 계좌에 보유 주식이 없습니다.")
                        return []
                else:
                    error_msg = data.get("msg1", "알 수 없는 오류")
                    print(f"⚠️ {account.name} 계좌 조회 실패: {error_msg}")
                    return []
            else:
                print(f"❌ {account.name} 계좌 API 요청 실패: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ {account.name} 계좌 조회 중 오류: {e}")
            return []
    
    def get_overseas_portfolio(self, account: Account) -> List[Dict]:
        """해외 주식 포트폴리오 조회"""
        try:
            access_token = self.get_access_token(account)
            
            # 환율 조회 (외부 API 사용)
            exchange_rate, exchange_source = ExchangeRateAPI.get_usd_krw_rate()
            self.exchange_rate = exchange_rate
            self.exchange_rate_source = exchange_source
            
            # 해외 주식 잔고 조회 API
            url = f"{self.base_url}/uapi/overseas-stock/v1/trading/inquire-balance"
            
            # 헤더 설정
            headers = {
                "Content-Type": "application/json",
                "authorization": f"Bearer {access_token}",
                "appKey": account.api_key,
                "appSecret": account.api_secret,
                "tr_id": "TTTS3012R"  # 실전 거래
            }
            
            # 쿼리 파라미터 설정
            params = {
                "CANO": account.cano,
                "ACNT_PRDT_CD": account.acnt_prdt_cd,
                "OVRS_EXCG_CD": "NASD",  # NASDAQ
                "TR_CRCY_CD": "USD",
                "CTX_AREA_FK200": "",
                "CTX_AREA_NK200": ""
            }
            
            print(f"🔍 {account.name} 계좌 조회 중...")
            print(f"🔍 API 요청 URL: {url}")
            print(f"🔍 API 요청 파라미터: {params}")
            
            response = requests.get(url, headers=headers, params=params)
            print(f"🔍 해외 주식 API 응답: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("rt_cd") == "0":
                    output1 = data.get("output1", [])
                    if output1:
                        portfolio = []
                        for item in output1:
                            try:
                                # 달러 금액을 원화로 변환
                                usd_evaluation = float(item.get("ovrs_stck_evlu_amt", "0"))
                                krw_evaluation = usd_evaluation * exchange_rate
                                
                                usd_purchase = float(item.get("frcr_pchs_amt1", "0"))
                                krw_purchase = usd_purchase * exchange_rate
                                
                                usd_profit = float(item.get("frcr_evlu_pfls_amt", "0"))
                                krw_profit = usd_profit * exchange_rate
                                
                                portfolio.append({
                                    "종목코드": item.get("ovrs_pdno", ""),
                                    "종목명": item.get("ovrs_item_name", ""),
                                    "보유수량": int(float(item.get("ovrs_cblc_qty", "0"))),
                                    "매입평균가": float(item.get("pchs_avg_pric", "0")),
                                    "매입금액": int(krw_purchase),
                                    "현재가": float(item.get("now_pric2", "0")),
                                    "평가금액": int(krw_evaluation),
                                    "평가손익": int(krw_profit),
                                    "수익률": float(item.get("evlu_pfls_rt", "0")),
                                    "계좌구분": account.name,
                                    "통화": "USD",
                                    "환율": exchange_rate
                                })
                            except (ValueError, TypeError) as e:
                                print(f"⚠️ 데이터 변환 오류: {e}, 데이터: {item}")
                                continue
                        return portfolio
                    else:
                        print(f"📊 {account.name} 계좌에 보유 주식이 없습니다.")
                        return []
                else:
                    error_msg = data.get("msg1", "알 수 없는 오류")
                    print(f"⚠️ {account.name} 계좌 조회 실패: {error_msg}")
                    return []
            else:
                print(f"❌ {account.name} 계좌 API 요청 실패: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ {account.name} 계좌 조회 중 오류: {e}")
            return []

class GoogleSheetsManager:
    """구글 스프레드시트 관리 클래스"""
    
    def __init__(self):
        self.spreadsheet_id = os.getenv('GOOGLE_SPREADSHEET_ID')
        self.credentials = None
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """구글 API 인증"""
        try:
            credentials = service_account.Credentials.from_service_account_file(
                'service-account-key.json',
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            self.service = build('sheets', 'v4', credentials=credentials)
            print("✅ 구글 API 인증이 완료되었습니다.")
        except Exception as e:
            print(f"❌ 구글 API 인증 실패: {e}")
            raise
    
    def get_sheet_names(self):
        """스프레드시트의 시트 이름 목록 가져오기"""
        try:
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            return [sheet['properties']['title'] for sheet in spreadsheet['sheets']]
        except Exception as e:
            print(f"❌ 시트 목록 조회 실패: {e}")
            return []
    
    def update_portfolio(self, portfolio_data: List[Dict], total_cash: float, exchange_rate: float = None, exchange_source: str = None):
        """포트폴리오 데이터를 스프레드시트에 업데이트"""
        try:
            # 현금 항목 추가
            if total_cash > 0:
                cash_item = {
                    "종목코드": "CASH",
                    "종목명": "현금",
                    "보유수량": 1,
                    "매입평균가": total_cash,
                    "매입금액": total_cash,
                    "현재가": total_cash,
                    "평가금액": total_cash,
                    "평가손익": 0,
                    "수익률": 0.0,
                    "계좌구분": "통합",
                    "통화": "KRW"
                }
                portfolio_data.append(cash_item)
            
            if not portfolio_data:
                print("❌ 업데이트할 포트폴리오 데이터가 없습니다.")
                return
            
            # 데이터프레임 생성
            df = pd.DataFrame(portfolio_data)
            
            # 전체 포트폴리오 가치 계산 (모든 금액이 원화로 통일됨)
            total_value = df['평가금액'].sum()
            df['비중'] = (df['평가금액'] / total_value * 100).round(2)
            
            # 계좌별 비중 계산 (현금 제외)
            stock_df = df[df['종목코드'] != 'CASH']
            account_weights = stock_df.groupby('계좌구분')['평가금액'].sum() / total_value * 100
            
            # 현금 비중 계산
            cash_weight = (total_cash / total_value * 100) if total_value > 0 else 0
            
            # 헤더 행 추가 (통화 정보 포함)
            headers = [['종목코드', '종목명', '보유수량', '매입평균가', '매입금액(원)', '현재가', '평가금액(원)', '평가손익(원)', '수익률', '계좌구분', '비중', '통화']]
            
            # 데이터 행들
            data_rows = []
            for _, row in df.iterrows():
                data_row = [
                    row['종목코드'], row['종목명'], row['보유수량'], 
                    row['매입평균가'], row['매입금액'], row['현재가'], 
                    row['평가금액'], row['평가손익'], row['수익률'], 
                    row['계좌구분'], row['비중'], row['통화']
                ]
                data_rows.append(data_row)
            
            # 전체 데이터
            all_data = headers + data_rows
            
            # 사용 가능한 시트 확인
            sheet_names = self.get_sheet_names()
            print(f"📋 사용 가능한 시트: {sheet_names}")
            
            # Portfolio 시트가 있으면 사용, 없으면 첫 번째 시트 사용
            if 'Portfolio' in sheet_names:
                range_name = 'Portfolio!A1:L1000'
                print("📊 'Portfolio' 시트를 사용합니다.")
            elif sheet_names:
                range_name = f'{sheet_names[0]}!A1:L1000'
                print(f"📊 '{sheet_names[0]}' 시트를 사용합니다.")
            else:
                print("❌ 사용 가능한 시트가 없습니다.")
                return
            
            try:
                # 기존 데이터 삭제
                self.service.spreadsheets().values().clear(
                    spreadsheetId=self.spreadsheet_id,
                    range=range_name
                ).execute()
                
                # 새 데이터 입력
                self.service.spreadsheets().values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range=range_name,
                    valueInputOption='RAW',
                    body={'values': all_data}
                ).execute()
                
                # 환율 정보를 별도 시트에 저장
                if exchange_rate and exchange_source:
                    self._update_exchange_rate_info(exchange_rate, exchange_source, total_value)
                
                print(f"✅ 포트폴리오 데이터가 구글 스프레드시트에 업데이트되었습니다.")
                print(f"💰 총 포트폴리오 가치: {total_value:,.0f}원")
                print(f"💰 현금 비중: {cash_weight:.2f}% ({total_cash:,.0f}원)")
                print(f"📊 계좌별 비중:")
                for account, weight in account_weights.items():
                    account_value = stock_df[stock_df['계좌구분'] == account]['평가금액'].sum()
                    print(f"  - {account}: {weight:.2f}% ({account_value:,.0f}원)")
                    
            except Exception as e:
                print(f"❌ 스프레드시트 업데이트 실패: {e}")
                print("📝 스프레드시트에 접근 권한이 있는지 확인해주세요.")
            
        except Exception as e:
            print(f"❌ 스프레드시트 업데이트 실패: {e}")
    
    def _update_exchange_rate_info(self, exchange_rate: float, exchange_source: str, total_value: float):
        """환율 정보를 별도 시트에 저장"""
        try:
            # 환율 정보 시트 생성 또는 업데이트
            sheet_name = '환율정보'
            
            # 시트가 있는지 확인
            sheet_names = self.get_sheet_names()
            if sheet_name not in sheet_names:
                # 새 시트 생성
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=self.spreadsheet_id,
                    body={
                        'requests': [{
                            'addSheet': {
                                'properties': {
                                    'title': sheet_name
                                }
                            }
                        }]
                    }
                ).execute()
                print(f"✅ '{sheet_name}' 시트가 생성되었습니다.")
            
            # 환율 정보 데이터 준비
            now = datetime.now()
            exchange_data = [
                ['업데이트 시간', '환율', '환율 출처', '총 포트폴리오 가치'],
                [now.strftime('%Y-%m-%d %H:%M:%S'), f"{exchange_rate:,.2f}원", exchange_source, f"{total_value:,.0f}원"]
            ]
            
            # 환율 정보 업데이트
            range_name = f'{sheet_name}!A1:D10'
            self.service.spreadsheets().values().clear(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body={'values': exchange_data}
            ).execute()
            
            print(f"✅ 환율 정보가 '{sheet_name}' 시트에 저장되었습니다.")
            
        except Exception as e:
            print(f"⚠️ 환율 정보 저장 실패: {e}")

def main():
    """메인 함수"""
    try:
        # 환경변수 확인
        required_env_vars = [
            'KOREA_INVESTMENT_ACC_NO_DOMESTIC', 'KOREA_INVESTMENT_API_KEY_DOMESTIC', 'KOREA_INVESTMENT_API_SECRET_DOMESTIC',
            'KOREA_INVESTMENT_ACC_NO_PENSION', 'KOREA_INVESTMENT_API_KEY_PENSION', 'KOREA_INVESTMENT_API_SECRET_PENSION',
            'KOREA_INVESTMENT_ACC_NO_OVERSEAS', 'KOREA_INVESTMENT_API_KEY_OVERSEAS', 'KOREA_INVESTMENT_API_SECRET_OVERSEAS',
            'GOOGLE_SPREADSHEET_ID'
        ]
        
        missing_vars = []
        for var in required_env_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"❌ 다음 환경변수가 설정되지 않았습니다: {', '.join(missing_vars)}")
            print("📝 .env 파일에 다음 변수들을 추가해주세요:")
            for var in missing_vars:
                print(f"  {var}=your_value")
            return
        
        # 계좌 설정
        accounts = [
            Account(
                name="국내주식",
                acc_no=os.getenv('KOREA_INVESTMENT_ACC_NO_DOMESTIC'),
                api_key=os.getenv('KOREA_INVESTMENT_API_KEY_DOMESTIC'),
                api_secret=os.getenv('KOREA_INVESTMENT_API_SECRET_DOMESTIC'),
                account_type="domestic_stock"
            ),
            Account(
                name="국내연금",
                acc_no=os.getenv('KOREA_INVESTMENT_ACC_NO_PENSION'),
                api_key=os.getenv('KOREA_INVESTMENT_API_KEY_PENSION'),
                api_secret=os.getenv('KOREA_INVESTMENT_API_SECRET_PENSION'),
                account_type="pension"
            ),
            Account(
                name="해외주식",
                acc_no=os.getenv('KOREA_INVESTMENT_ACC_NO_OVERSEAS'),
                api_key=os.getenv('KOREA_INVESTMENT_API_KEY_OVERSEAS'),
                api_secret=os.getenv('KOREA_INVESTMENT_API_SECRET_OVERSEAS'),
                account_type="overseas"
            )
        ]
        
        print(f"📋 총 {len(accounts)}개 계좌가 설정되었습니다.")
        for account in accounts:
            print(f"  - {account.name}: {account.acc_no} ({account.account_type})")
        
        # API 클래스 초기화
        api = KoreaInvestmentAPI()
        sheets_manager = GoogleSheetsManager()
        
        print("🔍 전체 포트폴리오 조회 중...")
        
        # 전체 포트폴리오 수집
        all_portfolio = []
        total_cash = 0
        exchange_rate = None
        exchange_source = None
        
        for account in accounts:
            # 주식 포트폴리오 조회
            if account.account_type == "overseas":
                portfolio = api.get_overseas_portfolio(account)
                # 환율 정보 저장
                if api.exchange_rate:
                    exchange_rate = api.exchange_rate
                    exchange_source = api.exchange_rate_source
            else:
                portfolio = api.get_domestic_portfolio(account)
            
            if portfolio:
                all_portfolio.extend(portfolio)
            
            # 현금 잔고 조회 및 누적
            if account.account_type == "overseas":
                cash = api.get_overseas_cash(account)
            else:
                cash = api.get_domestic_cash(account)
            
            total_cash += cash
        
        if all_portfolio or total_cash > 0:
            # 구글 스프레드시트에 업데이트 (환율 정보 포함)
            sheets_manager.update_portfolio(all_portfolio, total_cash, exchange_rate, exchange_source)
        else:
            print("❌ 조회된 포트폴리오가 없습니다.")
            
    except Exception as e:
        print(f"❌ 포트폴리오 처리 실패: {e}")

if __name__ == "__main__":
    main()

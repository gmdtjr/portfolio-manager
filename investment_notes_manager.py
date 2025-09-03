import os
import json
import pandas as pd
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from typing import List, Dict, Optional, Tuple

class InvestmentNotesManager:
    """투자 노트 관리를 위한 클래스"""
    
    def __init__(self, spreadsheet_id: str):
        self.spreadsheet_id = spreadsheet_id
        self.service = None
        self._authenticate_google()
    
    def _authenticate_google(self):
        """구글 API 인증"""
        try:
            # 환경변수에서 서비스 계정 JSON 읽기 시도
            service_account_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
            
            if service_account_json:
                # 환경변수에서 JSON 문자열을 파싱
                service_account_info = json.loads(service_account_json)
                credentials = service_account.Credentials.from_service_account_info(
                    service_account_info,
                    scopes=['https://www.googleapis.com/auth/spreadsheets']
                )
                print("✅ 구글 API 인증이 완료되었습니다. (환경변수에서 JSON)")
            else:
                # 파일에서 읽기 시도
                credentials = service_account.Credentials.from_service_account_file(
                    'service-account-key.json',
                    scopes=['https://www.googleapis.com/auth/spreadsheets']
                )
                print("✅ 구글 API 인증이 완료되었습니다. (파일에서 JSON)")
            
            self.service = build('sheets', 'v4', credentials=credentials)
        except Exception as e:
            print(f"❌ 구글 API 인증 실패: {e}")
            raise
    
    def read_investment_notes(self) -> pd.DataFrame:
        """투자_노트 시트에서 투자 노트 데이터 읽기"""
        try:
            # 투자_노트 시트 확인
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            
            sheet_names = [sheet['properties']['title'] for sheet in spreadsheet['sheets']]
            print(f"📋 사용 가능한 시트: {sheet_names}")
            
            # 투자_노트 시트가 있으면 사용
            if '투자_노트' in sheet_names:
                range_name = '투자_노트!A:M'  # A부터 M까지 (13개 컬럼)
                print("📊 '투자_노트' 시트를 사용합니다.")
            else:
                raise Exception("'투자_노트' 시트가 없습니다. 먼저 시트를 생성해주세요.")
            
            # 데이터 읽기
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            if not values:
                # 빈 시트인 경우 기본 헤더 생성
                return self._create_empty_notes_df()
            
            # 데이터프레임 생성
            df = pd.DataFrame(values[1:], columns=values[0])
            
            # 마지막_수정일 컬럼을 datetime으로 변환
            if '마지막_수정일' in df.columns:
                df['마지막_수정일'] = pd.to_datetime(df['마지막_수정일'], errors='coerce')
            
            print(f"✅ 투자 노트 데이터 읽기 완료: {len(df)}개 종목")
            return df
            
        except Exception as e:
            print(f"❌ 투자 노트 데이터 읽기 실패: {e}")
            raise
    
    def _create_empty_notes_df(self) -> pd.DataFrame:
        """빈 투자 노트 데이터프레임 생성"""
        columns = [
            '종목코드', '종목명', '투자 아이디어 (Thesis)', '투자 확신도 (Conviction)', 
            '섹터/산업 (Sector/Industry)', '투자 유형 (Asset Type)', '핵심 촉매 (Catalysts)', 
            '핵심 리스크 (Risks)', '핵심 모니터링 지표 (KPIs)', '투자 기간 (Horizon)', 
            '목표 주가 (Target)', '매도 조건 (Exit Plan)', '마지막_수정일'
        ]
        return pd.DataFrame(columns=columns)
    
    def create_investment_notes_sheet(self):
        """투자_노트 시트 생성 및 기본 헤더 설정"""
        try:
            # 시트 생성
            request = {
                'addSheet': {
                    'properties': {
                        'title': '투자_노트'
                    }
                }
            }
            
            body = {
                'requests': [request]
            }
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body=body
            ).execute()
            
            print("✅ '투자_노트' 시트가 생성되었습니다.")
            
            # 기본 헤더 설정
            headers = [
                '종목코드', '종목명', '투자 아이디어 (Thesis)', '투자 확신도 (Conviction)', 
                '섹터/산업 (Sector/Industry)', '투자 유형 (Asset Type)', '핵심 촉매 (Catalysts)', 
                '핵심 리스크 (Risks)', '핵심 모니터링 지표 (KPIs)', '투자 기간 (Horizon)', 
                '목표 주가 (Target)', '매도 조건 (Exit Plan)', '마지막_수정일'
            ]
            
            # 헤더 쓰기
            range_name = '투자_노트!A1:M1'
            body = {
                'values': [headers]
            }
            
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            print("✅ 기본 헤더가 설정되었습니다.")
            
        except Exception as e:
            print(f"❌ 투자_노트 시트 생성 실패: {e}")
            raise
    
    def add_investment_note(self, note_data: Dict) -> bool:
        """새로운 투자 노트 추가"""
        try:
            # 필수 필드 확인
            required_fields = ['종목코드', '종목명']
            for field in required_fields:
                if field not in note_data or not note_data[field]:
                    raise ValueError(f"필수 필드 '{field}'가 누락되었습니다.")
            
            # 현재 데이터 읽기
            current_df = self.read_investment_notes()
            
            # 중복 확인 (빈 데이터프레임이 아닌 경우에만)
            if not current_df.empty and note_data['종목코드'] in current_df['종목코드'].values:
                print(f"⚠️ 종목코드 {note_data['종목코드']}가 이미 존재합니다. 업데이트를 사용하세요.")
                return False
            
            # 새 노트 데이터 준비
            note_data['마지막_수정일'] = datetime.now().strftime('%Y-%m-%d')
            
            # 데이터프레임에 추가
            new_row = pd.DataFrame([note_data])
            
            if current_df.empty:
                # 빈 데이터프레임인 경우 새 데이터만 사용
                updated_df = new_row
                print(f"📝 빈 시트에 첫 번째 투자 노트를 추가합니다.")
            else:
                # 기존 데이터에 새 데이터 추가
                updated_df = pd.concat([current_df, new_row], ignore_index=True)
            
            # 시트에 쓰기
            self._write_notes_to_sheet(updated_df)
            
            print(f"✅ {note_data['종목명']} ({note_data['종목코드']}) 투자 노트가 추가되었습니다.")
            return True
            
        except Exception as e:
            print(f"❌ 투자 노트 추가 실패: {e}")
            return False
    
    def update_investment_note(self, stock_code: str, note_data: Dict) -> bool:
        """기존 투자 노트 업데이트"""
        try:
            # 현재 데이터 읽기
            current_df = self.read_investment_notes()
            
            if current_df.empty:
                print("❌ 업데이트할 투자 노트가 없습니다.")
                return False
            
            # 해당 종목 찾기
            mask = current_df['종목코드'] == stock_code
            if not mask.any():
                print(f"❌ 종목코드 {stock_code}를 찾을 수 없습니다.")
                return False
            
            # 업데이트할 데이터 준비
            note_data['마지막_수정일'] = datetime.now().strftime('%Y-%m-%d')
            
            # 데이터프레임 업데이트
            for key, value in note_data.items():
                if key in current_df.columns:
                    current_df.loc[mask, key] = value
            
            # 시트에 쓰기
            self._write_notes_to_sheet(current_df)
            
            print(f"✅ {stock_code} 투자 노트가 업데이트되었습니다.")
            return True
            
        except Exception as e:
            print(f"❌ 투자 노트 업데이트 실패: {e}")
            return False
    
    def delete_investment_note(self, stock_code: str) -> bool:
        """투자 노트 삭제"""
        try:
            # 현재 데이터 읽기
            current_df = self.read_investment_notes()
            
            if current_df.empty:
                print("❌ 삭제할 투자 노트가 없습니다.")
                return False
            
            # 해당 종목 찾기
            mask = current_df['종목코드'] == stock_code
            if not mask.any():
                print(f"❌ 종목코드 {stock_code}를 찾을 수 없습니다.")
                return False
            
            # 삭제
            updated_df = current_df[~mask].reset_index(drop=True)
            
            # 시트에 쓰기
            self._write_notes_to_sheet(updated_df)
            
            print(f"✅ {stock_code} 투자 노트가 삭제되었습니다.")
            return True
            
        except Exception as e:
            print(f"❌ 투자 노트 삭제 실패: {e}")
            return False
    
    def _write_notes_to_sheet(self, df: pd.DataFrame):
        """데이터프레임을 시트에 쓰기"""
        try:
            # 빈 데이터프레임인 경우 헤더만 쓰기
            if df.empty:
                headers = [
                    '종목코드', '종목명', '투자 아이디어 (Thesis)', '투자 확신도 (Conviction)', 
                    '섹터/산업 (Sector/Industry)', '투자 유형 (Asset Type)', '핵심 촉매 (Catalysts)', 
                    '핵심 리스크 (Risks)', '핵심 모니터링 지표 (KPIs)', '투자 기간 (Horizon)', 
                    '목표 주가 (Target)', '매도 조건 (Exit Plan)', '마지막_수정일'
                ]
                data = [headers]
                print("📝 빈 시트에 헤더만 작성합니다.")
            else:
                # Timestamp를 문자열로 변환 (안전하게 처리)
                df_copy = df.copy()
                if '마지막_수정일' in df_copy.columns:
                    # datetime 타입인 경우에만 strftime 적용
                    if pd.api.types.is_datetime64_any_dtype(df_copy['마지막_수정일']):
                        df_copy['마지막_수정일'] = df_copy['마지막_수정일'].dt.strftime('%Y-%m-%d')
                    elif df_copy['마지막_수정일'].dtype == 'object':
                        # 문자열이 아닌 경우만 변환
                        df_copy['마지막_수정일'] = df_copy['마지막_수정일'].apply(
                            lambda x: x.strftime('%Y-%m-%d') if hasattr(x, 'strftime') else str(x)
                        )
                
                # 헤더 포함하여 데이터 준비
                data = [df_copy.columns.tolist()] + df_copy.values.tolist()
            
            # 시트에 쓰기
            range_name = '투자_노트!A1'
            body = {
                'values': data
            }
            
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            print(f"✅ 시트 쓰기 완료: {len(data)-1 if len(data) > 1 else 0}개 행")
            
        except Exception as e:
            print(f"❌ 시트 쓰기 실패: {e}")
            raise
    
    def get_note_by_stock_code(self, stock_code: str) -> Optional[Dict]:
        """종목코드로 투자 노트 조회"""
        try:
            df = self.read_investment_notes()
            
            if df.empty:
                return None
            
            note = df[df['종목코드'] == stock_code]
            
            if note.empty:
                return None
            
            return note.iloc[0].to_dict()
            
        except Exception as e:
            print(f"❌ 투자 노트 조회 실패: {e}")
            return None
    
    def get_notes_by_portfolio(self, portfolio_df: pd.DataFrame) -> pd.DataFrame:
        """포트폴리오에 있는 종목들의 투자 노트만 조회"""
        try:
            notes_df = self.read_investment_notes()
            
            if notes_df.empty:
                return pd.DataFrame()
            
            # 포트폴리오의 종목코드들
            portfolio_codes = portfolio_df['종목코드'].astype(str).tolist()
            
            # 투자 노트에서 포트폴리오 종목들만 필터링
            portfolio_notes = notes_df[notes_df['종목코드'].astype(str).isin(portfolio_codes)]
            
            return portfolio_notes
            
        except Exception as e:
            print(f"❌ 포트폴리오 투자 노트 조회 실패: {e}")
            return pd.DataFrame()
    
    def get_missing_notes(self, portfolio_df: pd.DataFrame) -> List[str]:
        """포트폴리오에 있지만 투자 노트가 없는 종목들"""
        try:
            notes_df = self.read_investment_notes()
            
            if notes_df.empty:
                return portfolio_df['종목코드'].astype(str).tolist()
            
            # 포트폴리오의 종목코드들
            portfolio_codes = set(portfolio_df['종목코드'].astype(str))
            
            # 투자 노트가 있는 종목코드들
            note_codes = set(notes_df['종목코드'].astype(str))
            
            # 투자 노트가 없는 종목들
            missing_codes = portfolio_codes - note_codes
            
            return list(missing_codes)
            
        except Exception as e:
            print(f"❌ 누락된 투자 노트 조회 실패: {e}")
            return []

def main():
    """테스트 함수"""
    import os
    from dotenv import load_dotenv
    
    # 환경변수 로드
    load_dotenv()
    
    spreadsheet_id = os.getenv('GOOGLE_SPREADSHEET_ID')
    
    if not spreadsheet_id:
        print("❌ GOOGLE_SPREADSHEET_ID가 설정되지 않았습니다.")
        return
    
    try:
        # 투자 노트 매니저 초기화
        manager = InvestmentNotesManager(spreadsheet_id)
        
        # 투자_노트 시트가 없으면 생성
        try:
            notes_df = manager.read_investment_notes()
        except:
            print("📝 '투자_노트' 시트가 없습니다. 새로 생성합니다.")
            manager.create_investment_notes_sheet()
            notes_df = manager.read_investment_notes()
        
        print(f"📊 현재 투자 노트: {len(notes_df)}개 종목")
        
        if not notes_df.empty:
            print("\n📋 투자 노트 목록:")
            for _, row in notes_df.iterrows():
                print(f"- {row['종목명']} ({row['종목코드']}) - {row['마지막_수정일']}")
        else:
            print("\n📝 투자 노트가 비어있습니다. 삼성전자 예시 노트를 추가합니다.")
            # 샘플 투자 노트 추가 예시 (투자 노트가 완전히 비어있을 때만)
            sample_note = {
                '종목코드': '005930',
                '종목명': '삼성전자',
                '투자 아이디어 (Thesis)': 'HBM3 시장의 압도적 선두주자로서, AI 시대의 본격적인 성장에 따른 메모리 반도체 슈퍼 사이클의 최대 수혜주가 될 것이라 판단.',
                '투자 확신도 (Conviction)': '상 (High)',
                '섹터/산업 (Sector/Industry)': 'IT > 반도체 > HBM',
                '투자 유형 (Asset Type)': '성장주 (Growth)',
                '핵심 촉매 (Catalysts)': '1. 차세대 HBM4 양산 계획 발표\n2. 파운드리 3나노 공정 수율 안정화 및 대형 고객사 확보 뉴스\n3. 분기 실적 컨센서스 상회 (어닝 서프라이즈)',
                '핵심 리스크 (Risks)': '1. 경쟁사(SK하이닉스, 마이크론)의 HBM 기술 추격\n2. 글로벌 경기 침체로 인한 스마트폰, 가전 등 전방산업 수요 둔화\n3. 지정학적 리스크(미중 갈등)로 인한 공급망 문제',
                '핵심 모니터링 지표 (KPIs)': '1. 분기별 HBM 매출 성장률(YoY)\n2. 신규 파운드리 고객사 수\n3. 영업이익률',
                '투자 기간 (Horizon)': '장기 (3년 이상)',
                '목표 주가 (Target)': '1차: 100,000원 (PER 15배 적용)\n2차: 120,000원 (HBM 시장 지배력 강화 시)',
                '매도 조건 (Exit Plan)': '수익 실현: 1차 목표 주가 도달 시 30% 분할 매도\n손절: 투자 아이디어가 훼손되는 경우 (예: HBM 경쟁력 상실) 즉시 매도'
            }
            manager.add_investment_note(sample_note)
        
        print("\n✅ 테스트가 완료되었습니다!")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        print(f"상세 오류: {traceback.format_exc()}")

if __name__ == "__main__":
    main()

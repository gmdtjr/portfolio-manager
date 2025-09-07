import os
import json
import pandas as pd
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google import genai
import uuid

class ReportArchiveManager:
    """딥리서치 보고서 아카이브 관리자"""
    
    def __init__(self, spreadsheet_id: str, gemini_api_key: str = None):
        self.spreadsheet_id = spreadsheet_id
        self.gemini_api_key = gemini_api_key or os.getenv('GOOGLE_API_KEY')
        self.service = None
        self.client = None
        self.sheet_name = "보고서_아카이브"
        self._authenticate_google()
        self._setup_gemini()
    
    def _authenticate_google(self):
        """구글 API 인증"""
        try:
            # 환경변수에서 서비스 계정 JSON 읽기 시도
            service_account_json_str = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
            if service_account_json_str:
                service_account_info = json.loads(service_account_json_str)
                credentials = service_account.Credentials.from_service_account_info(
                    service_account_info,
                    scopes=['https://www.googleapis.com/auth/spreadsheets']
                )
                print("✅ 구글 API 인증이 완료되었습니다. (환경변수에서 JSON)")
            else:
                # 파일에서 JSON 읽기 시도
                credentials = service_account.Credentials.from_service_account_file(
                    'service-account-key.json',
                    scopes=['https://www.googleapis.com/auth/spreadsheets']
                )
                print("✅ 구글 API 인증이 완료되었습니다. (파일에서 JSON)")
            
            self.service = build('sheets', 'v4', credentials=credentials)
        except Exception as e:
            print(f"❌ 구글 API 인증 실패: {e}")
            raise
    
    def _setup_gemini(self):
        """Gemini API 설정"""
        try:
            if self.gemini_api_key:
                self.client = genai.Client(api_key=self.gemini_api_key)
                self.model_name = "gemini-2.5-pro"
                print("✅ Gemini API 설정이 완료되었습니다.")
            else:
                print("⚠️ Gemini API 키가 없습니다. 요약 생성 기능을 사용할 수 없습니다.")
        except Exception as e:
            print(f"❌ Gemini API 설정 실패: {e}")
            self.client = None
    
    def create_archive_sheet(self):
        """보고서 아카이브 시트 생성"""
        try:
            # 시트가 이미 존재하는지 확인
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            
            existing_sheets = [sheet['properties']['title'] for sheet in spreadsheet.get('sheets', [])]
            
            if self.sheet_name in existing_sheets:
                print(f"✅ '{self.sheet_name}' 시트가 이미 존재합니다.")
                return True
            
            # 새 시트 생성
            request_body = {
                'requests': [{
                    'addSheet': {
                        'properties': {
                            'title': self.sheet_name,
                            'gridProperties': {
                                'rowCount': 1000,
                                'columnCount': 6
                            }
                        }
                    }
                }]
            }
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body=request_body
            ).execute()
            
            # 헤더 추가
            headers = ['보고서_ID', '생성일', '관련_종목', '사용된_프롬프트', '보고서_요약', '보고서_원문']
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f'{self.sheet_name}!A1:F1',
                valueInputOption='RAW',
                body={'values': [headers]}
            ).execute()
            
            print(f"✅ '{self.sheet_name}' 시트가 생성되었습니다.")
            return True
            
        except Exception as e:
            print(f"❌ 시트 생성 실패: {e}")
            return False
    
    def generate_report_id(self) -> str:
        """보고서 ID 생성 (날짜 + UUID)"""
        today = datetime.now().strftime('%Y%m%d')
        unique_id = str(uuid.uuid4())[:8]
        return f"{today}_{unique_id}"
    
    def generate_summary(self, report_content: str) -> str:
        """Gemini API를 사용하여 보고서 요약 생성"""
        if not self.client:
            return "Gemini API가 설정되지 않았습니다."
        
        try:
            summary_prompt = f"""다음은 딥리서치에서 생성된 투자 분석 보고서입니다. 
이 보고서의 핵심 내용을 3-4줄로 요약해주세요.

보고서 내용:
{report_content}

요약 요구사항:
- 핵심 투자 인사이트와 결론을 중심으로 요약
- 구체적인 수치나 데이터가 있다면 포함
- 투자자 관점에서 가장 중요한 포인트 위주로 작성
- 간결하고 명확한 문장으로 작성"""
            
            print("🤖 Gemini API로 보고서 요약 생성 중...")
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=summary_prompt
            )
            
            if response.text:
                print("✅ 보고서 요약 생성 완료")
                return response.text.strip()
            else:
                return "요약을 생성할 수 없습니다."
                
        except Exception as e:
            print(f"❌ 보고서 요약 생성 실패: {e}")
            return f"요약 생성 중 오류가 발생했습니다: {str(e)}"
    
    def extract_related_stocks(self, report_content: str) -> str:
        """보고서에서 관련 종목 추출"""
        if not self.client:
            return "Gemini API가 설정되지 않았습니다."
        
        try:
            extract_prompt = f"""다음 보고서에서 언급된 주식 종목명들을 추출해주세요.
한국 종목은 한글명으로, 해외 종목은 영문명으로 추출하세요.

보고서 내용:
{report_content}

추출 요구사항:
- 보고서에서 직접 언급된 종목명만 추출
- 여러 종목이 있으면 쉼표로 구분
- 종목명이 없으면 "일반적 분석"으로 표시
- 최대 5개 종목까지만 추출

예시: 삼성전자, SK하이닉스, Apple, Microsoft"""
            
            print("🤖 Gemini API로 관련 종목 추출 중...")
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=extract_prompt
            )
            
            if response.text:
                print("✅ 관련 종목 추출 완료")
                return response.text.strip()
            else:
                return "일반적 분석"
                
        except Exception as e:
            print(f"❌ 관련 종목 추출 실패: {e}")
            return "일반적 분석"
    
    def save_report(self, report_content: str, used_prompt: str = "") -> dict:
        """보고서를 아카이브에 저장"""
        try:
            # 시트 생성 확인
            self.create_archive_sheet()
            
            # 보고서 ID 생성
            report_id = self.generate_report_id()
            creation_date = datetime.now().strftime('%Y-%m-%d')
            
            # 요약 및 관련 종목 생성
            summary = self.generate_summary(report_content)
            related_stocks = self.extract_related_stocks(report_content)
            
            # 데이터 준비
            report_data = [
                report_id,
                creation_date,
                related_stocks,
                used_prompt[:500] if used_prompt else "",  # 프롬프트는 500자로 제한
                summary,
                report_content
            ]
            
            # 시트에 데이터 추가
            self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=f'{self.sheet_name}!A:F',
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body={'values': [report_data]}
            ).execute()
            
            print(f"✅ 보고서가 저장되었습니다. ID: {report_id}")
            
            return {
                'success': True,
                'report_id': report_id,
                'creation_date': creation_date,
                'related_stocks': related_stocks,
                'summary': summary,
                'message': f"보고서가 성공적으로 저장되었습니다. (ID: {report_id})"
            }
            
        except Exception as e:
            print(f"❌ 보고서 저장 실패: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f"보고서 저장 중 오류가 발생했습니다: {str(e)}"
            }
    
    def get_recent_reports(self, limit: int = 10) -> pd.DataFrame:
        """최근 보고서 목록 조회"""
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f'{self.sheet_name}!A:F'
            ).execute()
            
            values = result.get('values', [])
            if len(values) <= 1:  # 헤더만 있는 경우
                return pd.DataFrame()
            
            # 헤더와 데이터 분리
            headers = values[0]
            data = values[1:]
            
            # DataFrame 생성
            df = pd.DataFrame(data, columns=headers)
            
            # 최근 순으로 정렬
            df = df.tail(limit)
            
            return df
            
        except Exception as e:
            print(f"❌ 보고서 목록 조회 실패: {e}")
            return pd.DataFrame()
    
    def search_reports(self, keyword: str) -> pd.DataFrame:
        """키워드로 보고서 검색"""
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f'{self.sheet_name}!A:F'
            ).execute()
            
            values = result.get('values', [])
            if len(values) <= 1:
                return pd.DataFrame()
            
            headers = values[0]
            data = values[1:]
            
            # 키워드가 포함된 행 필터링
            filtered_data = []
            for row in data:
                if any(keyword.lower() in str(cell).lower() for cell in row):
                    filtered_data.append(row)
            
            if not filtered_data:
                return pd.DataFrame()
            
            df = pd.DataFrame(filtered_data, columns=headers)
            return df
            
        except Exception as e:
            print(f"❌ 보고서 검색 실패: {e}")
            return pd.DataFrame()

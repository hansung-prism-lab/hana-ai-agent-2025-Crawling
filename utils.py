"""
HANA (Hansung AI for Notice & Assistance)
한성대학교 공지사항 크롤링 시스템 유틸리티 모듈

크롤링 시스템에서 사용되는 핵심 기능 제공
"""

import os
import json
import asyncio
import img2pdf
import requests
from datetime import datetime, timedelta
from openai import OpenAI
from pyzerox import zerox

from crawler_config import (
    CATEGORY_MAP,
    DB_TEXT_FILENAME, CRAWLED_ID_FILENAME,
    PDF_PATH, OCR_DELAY,
    OPENAI_API_KEY, MODEL, TEMPERATURE, MAX_TOKENS,
    FASTAPI_BASE_URL, FASTAPI_PORT, FASTAPI_PATH,
    PROMPT
)

# ============================================================================

# 카테고리 정규화
def normalize_category(category):
    """
    세부 카테고리를 대표 카테고리로 정규화
    
    Args:
        category (str): 원본 카테고리명
        
    Returns:
        str: 정규화된 카테고리명
    """
    return CATEGORY_MAP.get(category, category)

# ============================================================================

# AI 기반 데이터 추출
def get_application_period(content):
    """
    OpenAI API로 공지사항 본문에서 신청기간 추출
    
    Args:
        content (str): 공지사항 본문 내용
        
    Returns:
        tuple[str | None, str | None]: (시작일, 종료일)
    """
    if not content:
        return None, None
    
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # 프롬프트 생성
        prompt = PROMPT.format(content=content)

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS
        )

        # AI 응답 파싱
        ai_response = response.choices[0].message.content.strip()
        
        if not ai_response:
            print("AI 응답이 비어있습니다.")
            return None, None
        
        try:
            result = json.loads(ai_response)
            
            if result.get('has_period', False):
                start_date = result.get('start_date')
                end_date = result.get('end_date')
                return start_date, end_date
            else:
                return None, None
                
        except json.JSONDecodeError as e:
            print(f"JSON 형식 X: {e}")
            print(f"AI 응답: {ai_response}")
            return None, None
        except Exception as e:
            print(f"파싱 오류: {e}")
            return None, None
            
    except Exception as e:
        print(f"AI 신청기간 추출 실패: {e}")
        return None, None

# ============================================================================

# 이미지 및 OCR 처리

def images_to_pdf(image_urls):
    """
    이미지 URL들을 PDF로 변환
    
    Args:
        image_urls (list): 이미지 URL 리스트
        
    Returns:
        bool: 변환 성공 여부
    """
    try:
        # 출력 디렉토리 생성
        os.makedirs(os.path.dirname(PDF_PATH), exist_ok=True)
        
        image_list = []
        
        # 이미지 다운로드
        for url in image_urls:
            try:
                response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
                response.raise_for_status()
                image_list.append(response.content)
            except requests.RequestException as e:
                print(f"이미지 다운로드 실패: {url} - {e}")
                continue
        
        # PDF 생성
        if image_list:
            pdf_bytes = img2pdf.convert(image_list)
            with open(PDF_PATH, "wb") as f:
                f.write(pdf_bytes)
            return True
        else:
            print("다운로드된 이미지가 없습니다")
            return False
            
    except Exception as e:
        print(f"이미지 -> PDF 변환 중 오류 발생: {e}")
        return False

async def get_text_from_pdf(file_path):
    """
    PDF에서 zerox로 텍스트 추출
    
    Args:
        file_path (str): PDF 파일 경로
        
    Returns:
        str | None: 추출된 텍스트
    """
    try:
        result = await zerox(
            file_path=file_path,
            model=MODEL
        )
        
        content = ""
        for page in result.pages:
            content += page.content + "\n\n"
        
        return content
    
    except Exception as e:
        print(f"OCR 처리 실패: {e}")
        return None

async def image_urls_to_text(image_urls):
    """
    이미지 URL들에서 텍스트 추출 (PDF 변환 + OCR)
    
    Args:
        image_urls (list[str]): 이미지 URL 리스트
        
    Returns:
        str | None: 추출된 텍스트
    """
    try:
        # 이미지 -> PDF 변환
        if not images_to_pdf(image_urls):
            print("PDF 변환 실패")
            return None
            
        # API 호출 전 대기
        await asyncio.sleep(OCR_DELAY)
            
        # OCR 처리
        content = await get_text_from_pdf(PDF_PATH)
        if content:
            return content
        else:
            print("OCR 텍스트 추출 실패")
            return ""
                
    finally:
        # 임시 파일 정리
        try:
            if os.path.exists(PDF_PATH):
                os.remove(PDF_PATH)
        except OSError as e:
            print(f"임시 파일 삭제 실패: {e}")

# ============================================================================

# 크롤링 상태 관리

def is_initial_crawl():
    """
    초기 크롤링인지 확인
    
    Returns:
        bool: DB 파일이 없으면 True (초기 크롤링)
    """
    return not os.path.exists(DB_TEXT_FILENAME)

def is_stop(pub_date):
    """
    크롤링 중단 여부 확인 (1년 전 데이터는 중단)
    
    Args:
        pub_date (str): 공지사항 게시일 (예: "2025-09-16 14:30:00" 또는 "2025-09-16")
        
    Returns:
        bool: 크롤링 중단 여부
    """
    # 날짜 부분만 추출
    if ' ' in pub_date:
        pub_date = pub_date.split(' ')[0]
    
    # 1년 전 날짜 계산
    last_year_yesterday = datetime.now() - timedelta(days=365)
    target_date = last_year_yesterday.strftime("%Y-%m-%d")
    
    if pub_date < target_date:
        return True
        
    return False

def load_latest_crawled_id():
    """
    마지막 크롤링 ID 로드
    
    Returns:
        str | None: 마지막 크롤링 ID (파일이 없으면 None)
    """
    if os.path.exists(CRAWLED_ID_FILENAME):
        with open(CRAWLED_ID_FILENAME, "r", encoding="utf-8") as f:
            latest_id = f.read().strip()
            return latest_id if latest_id else None
    return None

def save_latest_crawled_id(notice_id):
    """
    마지막 크롤링 ID 저장
    
    Args:
        notice_id (str): 저장할 공지 ID
    """
    with open(CRAWLED_ID_FILENAME, "w", encoding="utf-8") as f:
        f.write(notice_id)

# ============================================================================

# 데이터베이스 파일 관리

def remove_notice_db():
    """
    DB 파일 삭제 (일일 크롤링용)
    """
    if os.path.exists(DB_TEXT_FILENAME):
        os.remove(DB_TEXT_FILENAME)

def reset_database():
    """
    DB 파일 초기화 (모든 크롤링 기록 삭제)
    """
    files_to_delete = [DB_TEXT_FILENAME, CRAWLED_ID_FILENAME]
    
    for filename in files_to_delete:
        if os.path.exists(filename):
            os.remove(filename)

# ============================================================================

# FastAPI 서버 연동

def send_to_file(file_path=None):
    """
    FastAPI 서버로 결과 파일 전송

    Args:
        file_path (str): 전송할 파일 경로 (기본값: DB_TEXT_FILENAME)

    Returns:
        bool: 전송 성공 여부
    """
    if file_path is None:
        file_path = DB_TEXT_FILENAME
    
    if not os.path.exists(file_path):
        print(f"전송할 파일이 없습니다: {file_path}")
        return False

    url = f"{FASTAPI_BASE_URL}:{FASTAPI_PORT}{FASTAPI_PATH}"
    try:
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, "text/plain")}
            resp = requests.post(url, files=files, timeout=30)
        if 200 <= resp.status_code < 300:
            print(f"FastAPI 업로드 성공: {url}")
            return True
        else:
            print(f"FastAPI 업로드 실패 {resp.status_code}: {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"FastAPI 전송 오류: {e}")
        return False

"""
HANA (Hansung AI for Notice & Assistance)
한성대학교 공지사항 크롤링 모듈

RSS 피드 및 HTML 페이지 크롤링을 통해 공지사항 데이터 수집
"""

import re
import asyncio
import requests
from bs4 import BeautifulSoup as bs
from markdownify import markdownify as md

from crawler_config import (
    RSS_URL, BASE_DOMAIN, HTML_CONTENT_CLASS, HTML_FILE_CLASS, NOTICE_ID_PATTERN,
    MIN_TEXT_LENGTH, AI_CALL_DELAY, ALLOWED_CATEGORIES
)
from utils import (
    normalize_category,
    get_application_period,
    image_urls_to_text,
    is_stop, load_latest_crawled_id, save_latest_crawled_id
)


# ============================================================================

# HTML 페이지 크롤링

def html_crawl(link, base_domain=BASE_DOMAIN):
    """
    공지사항 게시글에서 본문, 이미지, 첨부파일 수집
    
    Args:
        link (str): 공지사항 URL
        base_domain (str): 기본 도메인
        
    Returns:
        tuple[str | None, list[str], list[str]]: (본문, 이미지 URL 목록, 첨부파일 목록)
    """
    page = requests.get(link)
    soup = bs(page.text, 'html.parser')

    content, image_urls, attachments = None, [], []

    # 본문 내용 및 이미지 추출
    view_con_div = soup.find('div', class_=HTML_CONTENT_CLASS)
    if view_con_div:
        # HTML을 Markdown으로 변환
        content = md(str(view_con_div), strip=['a', 'img']).strip()
        
        # 이미지 URL 수집
        for img_tag in view_con_div.find_all('img', src=True):
            src = img_tag['src']
            # 상대 경로를 절대 경로로 변환
            if src.startswith('/'):
                src = f"{base_domain}{src}"
            image_urls.append(src)

    # 첨부파일 추출
    file_div = soup.find('div', class_=HTML_FILE_CLASS)
    if file_div:
        for a_tag in file_div.find_all('a', href=True):
            href = a_tag['href']
            # 다운로드 링크만 수집
            if "download.do" in href:
                if href.startswith('/'):
                    file_url = f"{base_domain}{href}"
                file_name = a_tag.get_text(strip=True)
                attachments.append(f"{file_name} | {file_url}")
    
    return content, image_urls, attachments

# ============================================================================

# RSS 피드 크롤링

async def rss_crawl(db, max_pages, initial=False, rss_url=RSS_URL, base_domain=BASE_DOMAIN):
    """
    RSS 피드를 순회하며 공지사항 수집 및 처리
    
    Args:
        db: 데이터베이스 객체
        max_pages (int): 최대 크롤링 페이지 수
        initial (bool): 초기 크롤링 여부 (True=초기, False=일일)
        rss_url (str): RSS URL 템플릿
        base_domain (str): 기본 도메인
    """
    saved_cnt = 0
    ocr_count = 0
    
    # 마지막 크롤링 ID 로드
    latest_crawled_id = load_latest_crawled_id()
    
    # 가장 최신 ID 저장용
    newest_id = None

    for page_number in range(1, max_pages + 1):
        url = rss_url.format(page_number)
        page = requests.get(url)
            
        soup = bs(page.text, 'xml')
        items = soup.find_all('item')

        if not items:
            break

        for item in items:
            # RSS 아이템에서 기본 정보 추출
            title = item.find('title').get_text(strip=True) if item.find('title') else ""
            link = item.find('link').get_text(strip=True) if item.find('link') else ""
            pub_date = item.find('pubDate').get_text(strip=True) if item.find('pubDate') else ""
            category = item.find('category').get_text(strip=True) if item.find('category') else ""

            # 카테고리 정규화 및 필터링
            category = normalize_category(category)
            if category not in ALLOWED_CATEGORIES:
                continue

            # 공지사항 ID 추출
            match = re.search(NOTICE_ID_PATTERN, link)
            notice_id = match.group(1) if match else "unknown"

            # 가장 최신 ID 저장 (첫 아이템)
            if newest_id is None:
                newest_id = notice_id

            # 초기 크롤링: 1년 전 데이터 도달 시 중단
            if initial and is_stop(pub_date):
                if newest_id:
                    save_latest_crawled_id(newest_id)
                    print(f"가장 최신 ID 저장: {newest_id}")
                return

            # 중복 체크: 마지막 크롤링 ID와 동일하면 중단
            if latest_crawled_id and notice_id == latest_crawled_id:
                if newest_id:
                    save_latest_crawled_id(newest_id)
                    print(f"가장 최신 ID 저장: {newest_id}")
                return

            # 상대 경로를 절대 경로로 변환
            if link.startswith("/"):
                link = f"{base_domain}{link}"

            # HTML 크롤링 (본문, 이미지, 첨부파일)
            content, image_urls, attachments = html_crawl(link)
            
            # API 호출 간격 대기
            await asyncio.sleep(AI_CALL_DELAY)
            
            # OCR 처리
            if not content and image_urls:
                # 텍스트가 없고 이미지만 있는 경우
                ocr_count += 1
                content = await image_urls_to_text(image_urls)
                
            elif content and len(content) < MIN_TEXT_LENGTH and image_urls:
                # 텍스트가 짧고 이미지가 있는 경우
                ocr_count += 1
                ocr_content = await image_urls_to_text(image_urls)
                
                # OCR 결과가 더 길면 대체
                if ocr_content and len(ocr_content) > len(content):
                    content = ocr_content
            
            # 신청기간 추출
            start_date, end_date = None, None
            if content:
                await asyncio.sleep(AI_CALL_DELAY)
                start_date, end_date = get_application_period(content)
                
                # 종료일만 있고 시작일이 없으면 게시일을 시작일로 사용
                if end_date and not start_date:
                    clean_pub_date = pub_date.split(' ')[0] if ' ' in pub_date else pub_date
                    start_date = clean_pub_date
                
            # DB에 저장
            db.save_notice(
                notice_id=notice_id,
                title=title,
                link=link,
                pub_date=pub_date,
                category=category,
                start_date=start_date,
                end_date=end_date,
                content=content,
                image_urls=image_urls,
                attachments=attachments
            )
            saved_cnt += 1
            
            await asyncio.sleep(AI_CALL_DELAY)
            
    print(f"총 {saved_cnt}개의 공지사항이 성공적으로 저장되었습니다!", flush=True)
    print(f"OCR을 실행한 공지는 총 {ocr_count}개입니다.", flush=True)

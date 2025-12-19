"""
HANA (Hansung AI for Notice & Assistance)
한성대학교 공지사항 크롤링 시스템 실행 파일

초기 크롤링 및 일일 크롤링 실행
"""

import asyncio
import sys
import time

from db import TextFileDB
from crawling import rss_crawl
from utils import (
    is_initial_crawl,
    remove_notice_db,
    reset_database,
    send_to_file
)


# ============================================================================

# 메인 실행 함수

def main():
    """
    크롤링 시스템 메인 실행 로직
    
    - 초기 크롤링: DB 파일이 없을 때 (1년치 데이터)
    - 일일 크롤링: DB 파일이 있을 때 (최신 데이터만)
    """
    # 명령행 인수 확인
    if len(sys.argv) > 1 and sys.argv[1] == "reset":
        reset_database()
        return

    # 초기 크롤링 여부 판단
    initial = is_initial_crawl()
    print("초기 크롤링" if initial else "일일 크롤링")

    # 크롤링 페이지 수 설정
    max_pages = 100 if initial else 2  # 초기: 100페이지, 일일: 2페이지

    # 일일 크롤링인 경우 기존 DB 삭제
    if not initial:
        remove_notice_db()

    # DB 인스턴스 생성
    db = TextFileDB()

    # 크롤링 시간 측정 시작
    start_ts = time.perf_counter()

    # 크롤링 실행
    print("HANA 크롤링 시스템 시작...\n")
    asyncio.run(rss_crawl(
        db=db,
        max_pages=max_pages,
        initial=initial
    ))
    print("크롤링 완료!\n")

    # 소요 시간 계산 및 출력
    elapsed = time.perf_counter() - start_ts
    hours = int(elapsed // 3600)
    minutes = int((elapsed % 3600) // 60)
    seconds = int(elapsed % 60)
    
    if hours:
        print(f"소요시간: {hours}시간 {minutes}분 {seconds}초, {elapsed:.2f}초")
    else:
        print(f"소요시간: {minutes}분 {seconds}초, {elapsed:.2f}초")

    # FastAPI 서버로 결과 파일 전송
    # send_to_file(DB_TEXT_FILENAME)  # 현재는 서버가 없으므로 주석 처리

# ============================================================================

if __name__ == "__main__":
    main()

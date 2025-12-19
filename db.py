"""
HANA (Hansung AI for Notice & Assistance)
한성대학교 공지사항 크롤링 시스템 데이터베이스 모듈

크롤링한 공지사항 데이터를 구조화된 형식으로 저장
"""

import os


class TextFileDB:
    """
    텍스트 파일 기반 데이터베이스 클래스
    
    공지사항 데이터를 .txt 파일 형식으로 저장
    각 공지사항은 구분선으로 분리되어 저장
    
    Attributes:
        filename (str): 데이터를 저장할 파일 경로
        format (str): 파일 형식 ("txt" 고정)
    """
    
    def __init__(self, filename="notice_db.txt"):
        """
        TextFileDB 초기화
        
        Args:
            filename (str): 저장할 파일명 (기본값: "notice_db.txt")
        """
        self.filename = filename
        self.format = "txt"
        
        # 파일이 존재하지 않으면 빈 파일 생성
        if not os.path.exists(self.filename):
            with open(self.filename, "w", encoding="utf-8") as f:
                pass
    
    def save_notice(self, notice_id, title, link, pub_date, category, 
                    start_date, end_date, content, image_urls=None, attachments=None):
        """
        공지사항 데이터를 파일에 추가 저장
        
        Args:
            notice_id (str): 공지사항 고유 ID
            title (str): 공지사항 제목
            link (str): 공지사항 URL
            pub_date (str): 게시 날짜
            category (str): 카테고리
            start_date (str or None): 신청 시작일 (없으면 None)
            end_date (str or None): 신청 종료일 (없으면 None)
            content (str): 공지사항 본문 내용
            image_urls (list, optional): 이미지 URL 리스트
            attachments (list, optional): 첨부파일 정보 리스트
        """
        # None 값을 빈 리스트로 변환
        image_urls = image_urls or []
        attachments = attachments or []
        
        # 파일에 추가 모드로 쓰기
        with open(self.filename, "a", encoding="utf-8") as f:
            # 기본 정보
            f.write(f"ID: {notice_id}\n")
            f.write(f"제목: {title}\n")
            f.write(f"링크: {link}?layout=unknown\n")
            f.write(f"게시 날짜: {pub_date}\n")
            f.write(f"카테고리: {category}\n")
            
            # 신청 기간 정보
            f.write(f"시작일: {start_date if start_date else '없음'}\n")
            f.write(f"종료일: {end_date if end_date else '없음'}\n")
            
            # 이미지 URL 정보
            if image_urls:
                f.write("이미지 URL:\n")
                for img in image_urls:
                    f.write(f"\t- {img}\n")
            else:
                f.write("이미지 URL: 없음\n")
            
            # 첨부파일 정보
            if attachments:
                f.write("첨부파일:\n")
                for att in attachments:
                    f.write(f"\t- {att}\n")
            else:
                f.write("첨부파일: 없음\n")
            
            # 본문 내용
            f.write(f"내용:\n{content}\n")
            
            # 구분선 (다음 공지사항과 구분)
            f.write("\n" + "-" * 50 + "\n\n")

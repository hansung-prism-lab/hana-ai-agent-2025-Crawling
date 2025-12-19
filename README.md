# HANA Crawler

HANA 는 한성대학교 AI 공지사항 및 도움 에이전트 서비스입니다.

<div align="center">

  https://github.com/user-attachments/assets/4b888521-15ca-4232-aa8e-5b8ff2564fb4

</div>

## Preview
<img width="4959" height="7016" alt="판넬_ver3" src="https://github.com/user-attachments/assets/d8e0ec60-ba6d-48f1-b4fa-ae27f590d939" />

### Members

<table width="50%" align="center">
    <tr>
        <td align="center"><b>FE</b></td>
        <td align="center"><b>BE</b></td>
        <td align="center"><b>AI</b></td>
        <td align="center"><b>AI</b></td>
    </tr>
    <tr>
        <td align="center"><img src="https://github.com/user-attachments/assets/b95eea07-c69a-4bbf-9a8f-eccda41c410e" style="width:220px; object-fit:cover;" /></td>
        <td align="center"><img src="https://github.com/user-attachments/assets/561672fc-71f6-49d3-b826-da55d6ace0c4" style="width:220px; object-fit:cover;" /></td>
        <td align="center"><img src="https://github.com/user-attachments/assets/c3b96a8f-2760-4bc3-8b9d-ff76f5dbcac4" style="width:220px; object-fit:cover;" /></td>
        <td align="center"><img src="https://github.com/user-attachments/assets/6d6ae01b-1cf0-411f-8d7c-ca9338cbe944" style="width:220px; object-fit:cover;" /></td>
    </tr>
    <tr>
        <td align="center"><b><a href="https://github.com/nyun-nye">윤예진</a></b></td>
        <td align="center"><b><a href="https://github.com/hardwoong">박세웅</a></b></td>
        <td align="center"><b><a href="https://github.com/jwon0523">이재원</a></b></td>
        <td align="center"><b><a href="https://github.com/ThreeeJ">정종진</a></b></td>
    </tr>
</table>

## Tech Stack

- **Python 3.11+** - 런타임
- **Requests, BeautifulSoup, lxml** - RSS/HTML 크롤링
- **img2pdf + py-zerox (zerox OCR)** - 이미지 → PDF → 텍스트 추출
- **OpenAI** - 기간 추출 및 카테고리 분류 보조
- **markdownify** - HTML → Markdown 변환
- **python-dotenv** - 환경 변수 관리
- **Poppler** - PDF 처리(zerox 내부 의존성)
- **Cron/작업 스케줄러** - 정기 실행

## Getting Started

### Installation

```bash
# 저장소 클론
git clone https://github.com/Hansung-AI-for-Notice-and-Assistance/Crawler.git
cd Crawler

# 가상환경 생성 및 활성화
python -m venv .venv
.\.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/macOS

# 의존성 설치
pip install -r requirements.txt
```

### Prerequisites

#### Windows
- [Poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases/) 다운로드 후 설치 경로의 `bin` 디렉터리를 PATH에 추가

#### Linux
```bash
sudo apt update && sudo apt install -y poppler-utils
```

### Environment Variables
```env
# OpenAI
OPENAI_API_KEY="your_openai_api_key"
```

참고: 업로드 대상 서버(FASTAPI)는 `hana_crawler_config.py`의 `FASTAPI_BASE_URL`, `FASTAPI_PORT`, `FASTAPI_PATH`에서 설정합니다.

### Run

```bash
# 데이터 초기화 후 초기 크롤링
python hana_start.py reset
python hana_start.py

# 일일(일반) 크롤링
python hana_start.py
```

### (Optional) Scheduling

Linux 예시(cron):

```bash
mkdir -p logs
crontab -e
```

```bash
# 매일 01:00 실행 예시
0 1 * * * cd /home/ubuntu/Crawling && .venv/bin/python hana_start.py >> logs/daily.log 2>&1
```

## Project Structure

```
.
├── db.py                      # 텍스트 파일 기반 간단 DB (notice_db.txt 저장)
├── hana_crawler_config.py     # 크롤러/AI/OCR/업로드 등 전역 설정
├── hana_crawling.py           # RSS/HTML 크롤링, OCR, 기간 추출 메인 로직
├── hana_start.py              # 실행 엔트리포인트(초기/일일 크롤링, 업로드 트리거)
├── hana_utils.py              # OCR·AI 호출, 파일/상태 관리 유틸
├── requirements.txt           # 의존성 목록
├── notice_db.txt              # 수집 결과(출력물)
└── crawled_id.txt             # 마지막으로 본 최신 공지 ID(중복 방지)
```

## Key Features
- **RSS/HTML 크롤링**: 한성대 공지 RSS를 순회하고 상세 페이지에서 본문/이미지/첨부 수집
- **OCR 기반 이미지 텍스트 추출**: `img2pdf` + `py-zerox`로 이미지 → PDF → 텍스트 변환
- **기간/카테고리 추출**: 본문에서 신청 기간(JSON)과 대표 카테고리 추출
- **중복/중단 로직**: `crawled_id.txt`로 중복 방지, 초기 적재 시 오래된 공지에서 자동 중단
- **카테고리 필터/정규화**: 불필요 카테고리 제외 및 대표 카테고리 맵핑
- **결과 저장/전송**: 구조화 텍스트를 `notice_db.txt`로 저장 후 FastAPI로 업로드

## Output Format
크롤링 결과는 `notice_db.txt`에 다음 형식으로 저장됩니다:

```text
ID: 271xxx
제목: ...
링크: https://www.hansung.ac.kr/bbs/hansung/143/271xxx/artclView.do?layout=unknown
게시 날짜: YYYY-MM-DD hh:mm:ss
카테고리: 한성공지 | 학사 | 비교과 | 진로 및 취·창업 | 장학 | 국제
시작일: YYYY-MM-DD 또는 없음
종료일: YYYY-MM-DD 또는 없음
이미지 URL:
  - https://...
첨부파일:
  - 파일명.pdf | https://.../download.do
내용:
...공지 본문 마크다운...
--------------------------------------------------
```

## Upload Endpoint

크롤링 완료 후 결과 파일을 FastAPI 서버로 업로드합니다.

- `POST {FASTAPI_BASE_URL}:{FASTAPI_PORT}{FASTAPI_PATH}`

- 기본값: `http://13.209.9.15:8000/send/file`

## Server Information

| 환경              | URL                        |
| ----------------- | -------------------------- |
| 업로드 대상(FastAPI) | http://13.209.9.15:8000     |

## License

이 프로젝트는 한성대학교 공학경진대회에서 진행되었습니다.

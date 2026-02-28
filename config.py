"""수업 스크래핑봇 설정"""

# 스크래핑 대상
TARGET_URL = "https://www.ssmdacademy.com/write"

# 이메일
EMAIL_SUBJECT = "[수업알림] {date} 상상마당 글쓰기 수업 모집 현황"

# Playwright
BROWSER_TIMEOUT_MS = 30_000
WAIT_AFTER_LOAD_MS = 5_000

# 재시도
MAX_RETRIES = 2
RETRY_DELAY_SEC = 5

# 모집 상태 판별 키워드
RECRUITING_KEYWORDS = ["모집중", "모집 중", "접수중", "접수 중", "신청가능"]
SOLD_OUT_KEYWORDS = ["마감", "sold out", "품절", "종료"]

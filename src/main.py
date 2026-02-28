"""수업 스크래핑봇 메인 파이프라인

매주 토요일 오전 8시(KST) 실행:
1. 상상마당 아카데미 글쓰기 페이지 스크래핑
2. 현재 모집 중인 수업 추출
3. Gmail로 결과 이메일 발송
"""

import sys
import os
import csv
import time
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USAGE_LOG_PATH = os.path.join(PROJECT_ROOT, "usage_log.csv")

from dotenv import load_dotenv

import config
from src.scraper import scrape_courses
from src.mailer import send_email


def _log_run(run_date: str, courses_found: int, email_sent: bool,
             duration_sec: float, note: str = ""):
    """실행 기록을 CSV에 저장한다."""
    write_header = not os.path.exists(USAGE_LOG_PATH)
    with open(USAGE_LOG_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow([
                "date", "courses_found", "email_sent",
                "duration_sec", "source", "note",
            ])
        writer.writerow([
            run_date, courses_found, email_sent,
            f"{duration_sec:.1f}", "bot", note,
        ])
    print(f"[Usage] 기록 저장: {USAGE_LOG_PATH}")


def run():
    load_dotenv()
    start_time = time.time()
    today = datetime.now(KST).strftime("%Y-%m-%d")

    print(f"=== 수업 스크래핑봇 실행 ({today}) ===\n")

    # 1. 스크래핑
    print("--- 1단계: 페이지 스크래핑 ---")
    try:
        courses = scrape_courses()
    except Exception as e:
        print(f"[Error] 스크래핑 실패: {e}")
        duration_sec = time.time() - start_time
        try:
            send_email(
                subject=f"[수업알림] {today} 스크래핑 실패",
                courses=[],
                error_message=str(e),
            )
            _log_run(today, 0, True, duration_sec, note=f"scrape-error: {e}")
        except Exception as mail_err:
            print(f"[Error] 에러 알림 이메일도 실패: {mail_err}")
            _log_run(today, 0, False, duration_sec,
                     note=f"scrape-error+mail-error: {e}")
        return

    recruiting = [c for c in courses if c.get("is_recruiting")]
    print(f"\n총 {len(courses)}개 수업 발견, 모집 중 {len(recruiting)}개\n")

    # 2. 이메일 발송
    print("--- 2단계: 이메일 발송 ---")
    subject = config.EMAIL_SUBJECT.format(date=today)
    email_sent = False
    try:
        send_email(subject=subject, courses=courses)
        email_sent = True
    except Exception as e:
        print(f"[Error] 이메일 발송 실패: {e}")

    # 3. 실행 기록
    duration_sec = time.time() - start_time
    _log_run(today, len(courses), email_sent, duration_sec)

    print(f"\n=== 수업 스크래핑봇 완료! ({duration_sec:.1f}초) ===")


if __name__ == "__main__":
    run()

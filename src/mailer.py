"""Gmail SMTP로 수업 알림 이메일을 발송하는 모듈"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def send_email(subject: str, courses: list[dict],
               error_message: str = "") -> None:
    """수업 목록을 이메일로 발송한다."""
    gmail_address = os.environ.get("GMAIL_ADDRESS")
    gmail_password = os.environ.get("GMAIL_APP_PASSWORD")
    recipient = os.environ.get("RECIPIENT_EMAIL")

    if not all([gmail_address, gmail_password, recipient]):
        print("[Mailer] GMAIL_ADDRESS, GMAIL_APP_PASSWORD, RECIPIENT_EMAIL 누락 - 건너뜀")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"수업알림봇 <{gmail_address}>"
    msg["To"] = recipient

    msg.attach(MIMEText(_build_plain_text(courses, error_message), "plain", "utf-8"))
    msg.attach(MIMEText(_build_html(courses, error_message), "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_address, gmail_password)
        server.sendmail(gmail_address, recipient, msg.as_string())

    print(f"[Mailer] 이메일 발송 완료 -> {recipient}")


def _build_plain_text(courses: list[dict], error_message: str) -> str:
    if error_message:
        return f"스크래핑 중 오류가 발생했습니다:\n{error_message}\n\n수동 확인: https://www.ssmdacademy.com/write"

    if not courses:
        return "현재 표시된 수업이 없습니다.\n\n확인: https://www.ssmdacademy.com/write"

    recruiting = [c for c in courses if c.get("is_recruiting")]
    closed = [c for c in courses if not c.get("is_recruiting")]

    lines = []
    if recruiting:
        lines.append(f"== 모집 중 ({len(recruiting)}개) ==\n")
        for c in recruiting:
            lines.append(f"- {c['name']}")
            if c.get("price"):
                lines.append(f"  가격: {c['price']}")
            if c.get("url"):
                lines.append(f"  링크: {c['url']}")
            lines.append("")

    if closed:
        lines.append(f"\n== 마감 ({len(closed)}개) ==\n")
        for c in closed:
            lines.append(f"- {c['name']} ({c.get('status', '')})")

    lines.append(f"\n페이지: https://www.ssmdacademy.com/write")
    return "\n".join(lines)


def _build_html(courses: list[dict], error_message: str) -> str:
    if error_message:
        content = f'''
        <div style="padding:20px;background:#fee;border-left:4px solid #e74c3c;border-radius:4px;margin:20px 0;">
            <strong>스크래핑 오류</strong><br>
            <p style="color:#666;">{error_message}</p>
            <a href="https://www.ssmdacademy.com/write" style="color:#3498db;">직접 확인하기</a>
        </div>'''
        return _wrap_html(content)

    if not courses:
        content = '''
        <div style="padding:20px;background:#fff3cd;border-left:4px solid #f0ad4e;border-radius:4px;margin:20px 0;">
            <strong>표시된 수업 없음</strong><br>
            <p style="color:#666;">현재 페이지에 수업이 표시되지 않습니다.</p>
            <a href="https://www.ssmdacademy.com/write" style="color:#3498db;">직접 확인하기</a>
        </div>'''
        return _wrap_html(content)

    recruiting = [c for c in courses if c.get("is_recruiting")]
    closed = [c for c in courses if not c.get("is_recruiting")]

    parts = []

    # 요약
    parts.append(f'''
    <div style="margin-bottom:20px;padding:12px 16px;background:#eef6ff;border-left:4px solid #3498db;border-radius:4px;font-size:14px;color:#555;">
        전체 {len(courses)}개 수업 | 모집 중 <strong>{len(recruiting)}개</strong> | 마감 {len(closed)}개
    </div>''')

    # 모집 중
    if recruiting:
        parts.append('<h2 style="color:#27ae60;border-bottom:2px solid #27ae60;padding-bottom:6px;">모집 중</h2>')
        for c in recruiting:
            parts.append(_course_card_html(c, recruiting=True))
    else:
        parts.append('''
        <div style="padding:15px;background:#f8f9fa;border-radius:8px;text-align:center;color:#888;">
            현재 모집 중인 수업이 없습니다.
        </div>''')

    # 마감
    if closed:
        parts.append(f'<h2 style="color:#999;border-bottom:1px solid #ddd;padding-bottom:6px;margin-top:30px;">마감 ({len(closed)}개)</h2>')
        for c in closed:
            parts.append(_course_card_html(c, recruiting=False))

    parts.append('''
    <div style="margin-top:20px;text-align:center;">
        <a href="https://www.ssmdacademy.com/write" style="display:inline-block;padding:10px 24px;background:#3498db;color:white;text-decoration:none;border-radius:6px;font-weight:bold;">페이지에서 직접 확인</a>
    </div>''')

    return _wrap_html("\n".join(parts))


def _course_card_html(course: dict, recruiting: bool) -> str:
    border_color = "#27ae60" if recruiting else "#ddd"
    bg = "#f0fff4" if recruiting else "#fafafa"
    opacity = "1" if recruiting else "0.7"

    parts = [f'''
    <div style="margin:10px 0;padding:15px;border-left:4px solid {border_color};background:{bg};border-radius:4px;opacity:{opacity};">
        <strong style="font-size:15px;">{course["name"]}</strong>''']

    if course.get("price"):
        parts.append(f'<br><span style="color:#e67e22;font-weight:bold;">{course["price"]}</span>')

    badge_color = "#27ae60" if recruiting else "#999"
    badge_bg = "#e8f5e9" if recruiting else "#f0f0f0"
    parts.append(f'<br><span style="display:inline-block;margin-top:5px;padding:2px 8px;background:{badge_bg};color:{badge_color};border-radius:3px;font-size:12px;">{course.get("status", "")}</span>')

    if course.get("url") and recruiting:
        parts.append(f'<br><a href="{course["url"]}" style="color:#3498db;font-size:13px;margin-top:5px;display:inline-block;">상세보기 &rarr;</a>')

    parts.append('</div>')
    return "\n".join(parts)


def _wrap_html(content: str) -> str:
    return f'''<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:'Apple SD Gothic Neo','Malgun Gothic',sans-serif;max-width:700px;margin:0 auto;padding:20px;line-height:1.8;color:#333;">
<div style="background:linear-gradient(135deg,#27ae60 0%,#2ecc71 100%);color:white;padding:20px 30px;border-radius:10px;margin-bottom:30px;">
    <h1 style="margin:0;font-size:24px;">상상마당 글쓰기 수업 알림</h1>
    <p style="margin:5px 0 0;opacity:0.9;">매주 자동으로 모집 현황을 확인합니다</p>
</div>
<div style="padding:0 10px;">
{content}
</div>
<div style="margin-top:40px;padding:15px;background:#f8f9fa;border-radius:8px;text-align:center;color:#888;font-size:13px;">
    수업알림봇이 자동으로 생성한 이메일입니다.
</div>
</body>
</html>'''

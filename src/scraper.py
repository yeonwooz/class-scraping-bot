"""상상마당 아카데미 글쓰기 페이지 스크래핑 모듈

imweb 기반 사이트로, Playwright로 JS 렌더링 후 BeautifulSoup으로 파싱한다.
"""

import os
import time
from dataclasses import dataclass, asdict

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup

import config


@dataclass
class Course:
    name: str
    status: str
    is_recruiting: bool
    url: str = ""
    price: str = ""
    thumbnail: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def scrape_courses() -> list[dict]:
    """페이지를 렌더링하고 수업 목록을 추출한다."""
    for attempt in range(1, config.MAX_RETRIES + 2):
        try:
            print(f"[Scraper] 시도 {attempt}/{config.MAX_RETRIES + 1}")
            return _do_scrape()
        except (PlaywrightTimeout, Exception) as e:
            if attempt <= config.MAX_RETRIES:
                print(f"[Scraper] 실패, {config.RETRY_DELAY_SEC}초 후 재시도: {e}")
                time.sleep(config.RETRY_DELAY_SEC)
            else:
                raise RuntimeError(
                    f"{config.MAX_RETRIES + 1}회 시도 후 스크래핑 실패: {e}"
                ) from e


def _do_scrape() -> list[dict]:
    """Playwright로 페이지 렌더링 후 파싱."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            locale="ko-KR",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        print(f"[Scraper] 페이지 로딩: {config.TARGET_URL}")
        page.goto(config.TARGET_URL, timeout=config.BROWSER_TIMEOUT_MS)

        # 수업 카드가 실제로 렌더링될 때까지 대기
        try:
            page.wait_for_selector(
                ".shop-item._shop_item",
                timeout=config.BROWSER_TIMEOUT_MS,
            )
            print("[Scraper] 수업 카드 로딩 확인")
        except PlaywrightTimeout:
            print("[Scraper] 경고: 수업 카드 로딩 타임아웃, 현재 상태로 진행")

        # 추가 렌더링 대기 (이미지, 가격 등)
        page.wait_for_timeout(config.WAIT_AFTER_LOAD_MS)

        html = page.content()
        browser.close()

    print(f"[Scraper] HTML 수신 완료 ({len(html):,}자)")
    return _parse_courses(html)


def _parse_courses(html: str) -> list[dict]:
    """렌더링된 HTML에서 수업 정보를 추출한다.

    imweb 쇼핑 위젯 구조:
    - .shop-item._shop_item 이 각 수업 카드
    - .item-detail 안의 h2.shop-title 이 수업명
    - .item-pay-detail p.pay 가 가격
    - .item-detail a[href] 가 상세 링크
    """
    soup = BeautifulSoup(html, "html.parser")
    courses = []

    product_cards = soup.select(".shop-item._shop_item")

    if not product_cards:
        print("[Scraper] 경고: 수업 카드를 찾지 못했습니다. HTML 구조 확인 필요.")
        _dump_debug_html(html)
        return []

    for card in product_cards:
        course = _extract_course_info(card)
        if course:
            courses.append(course.to_dict())

    print(f"[Scraper] {len(courses)}개 수업 추출 완료")
    return courses


def _extract_course_info(card) -> Course | None:
    """개별 상품 카드에서 수업 정보를 추출한다."""
    # 수업명: .item-detail 내의 h2.shop-title
    name_el = card.select_one(".item-detail h2.shop-title")
    if not name_el:
        name_el = card.select_one(".item-detail h2")
    name = name_el.get_text(strip=True) if name_el else ""
    if not name:
        return None

    # 상태: sold-out 클래스 또는 뱃지
    status_el = card.select_one(".sold-out, .badge, .status, .item-soldout")
    status = status_el.get_text(strip=True) if status_el else "모집중"

    is_recruiting = _check_recruiting(status, card)

    # 가격: .item-pay-detail p.pay
    price_el = card.select_one(".item-pay-detail p.pay")
    if not price_el:
        price_el = card.select_one("p.pay")
    price = price_el.get_text(strip=True) if price_el else ""

    # 링크: .item-detail a[href]
    link_el = card.select_one(".item-detail a[href]")
    if not link_el:
        link_el = card.select_one("a[href]")
    url = ""
    if link_el:
        href = link_el.get("href", "")
        if href.startswith("/"):
            url = f"https://www.ssmdacademy.com{href}"
        elif href.startswith("http"):
            url = href

    # 썸네일
    img_el = card.select_one("img")
    thumbnail = img_el.get("src", "") if img_el else ""

    return Course(
        name=name,
        status=status,
        is_recruiting=is_recruiting,
        url=url,
        price=price,
        thumbnail=thumbnail,
    )


def _check_recruiting(status_text: str, card) -> bool:
    """모집 중 여부를 판단한다."""
    text_lower = status_text.lower()

    for keyword in config.SOLD_OUT_KEYWORDS:
        if keyword in text_lower:
            return False

    for keyword in config.RECRUITING_KEYWORDS:
        if keyword in text_lower:
            return True

    # 카드 전체 텍스트에서도 확인
    full_text = card.get_text().lower()
    for keyword in config.SOLD_OUT_KEYWORDS:
        if keyword in full_text:
            return False

    # 불확실하면 모집중으로 처리 (누락보다 과잉 알림이 나음)
    return True


def _dump_debug_html(html: str):
    """디버깅용 HTML 저장."""
    debug_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "debug_page.html",
    )
    try:
        with open(debug_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"[Scraper] 디버그 HTML 저장: {debug_path}")
    except Exception:
        pass

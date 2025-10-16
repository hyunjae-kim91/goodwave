import re
import json
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout

# ===== 튜닝 가능한 상수 =====
NAV_TIMEOUT   = 12_000   # page.goto 타임아웃(ms)
WAIT_NUMERIC  = 6_000    # "숫자 등장" 대기(ms)
SEL_TIMEOUT   = 3_000    # 일반 selector 대기(ms)
INNER_TIMEOUT = 800      # inner_text/get_attribute(ms)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124 Safari/537.36")

POST_SELECTORS = [
    ".se-main-container", "#postViewArea", "#printPost1",
    ".se-text-paragraph", ".se-component", ".post-view", ".blog-content",
    "article", ".content", ".se-text", ".se-module", ".se-section", "body"
]

TITLE_CANDIDATES = [
    'meta[property="og:title"]',
    'h3.se_title, h2.se_title, .se-title-text',
    '#title_area, #post-title, .blog_title, .pcol1 h3',
    'meta[name="title"]',
]

DATE_CANDIDATES_META = [
    'meta[property="og:article:published_time"]',
    'meta[name="article:published_time"]',
    'meta[property="article:published_time"]',
    'meta[name="og:regDate"]',
]

DATE_CANDIDATES_DOM = [
    'time[datetime]',
    '.se_publishDate, .se_publish_date, .se_date',
    '#postViewArea .date, .post_header .date'
]

LIKE_CANDIDATES = [
    "em.u_cnt._count, em._count, span.u_cnt._count",
    "#sympathyArea em.u_cnt, .u_likeit_list_module .u_likeit_list_count._count",
    "button[aria-pressed] .u_likeit_list_count._count"
]

LIKE_STRICT = [
    ".btn_like_w .u_likeit_list_module em.u_cnt._count",
    ".section_t1 .btn_like_w .u_likeit_list_module em.u_cnt._count",
    ".u_likeit_list_module em.u_cnt._count",
    "em.u_cnt._count",
]

def clean_title(t: str) -> str:
    if not t:
        return "제목 없음"
    t = re.sub(r"\s*(?:\||:)\s*네이버\s*블로그\s*$", "", t.strip(), flags=re.I)
    return t or "제목 없음"

def format_date_kr(s: str) -> str:
    if not s:
        return "날짜 없음"
    s = s.strip()
    m = re.search(r"(\d{4}-\d{2}-\d{2})", s) or re.search(r"(\d{4}-\d{2}-\d{2})T", s)
    if m:
        return m.group(1)
    m = re.search(r"(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})", s)
    if m:
        y, mo, d = m.groups()
        return f"{y}-{int(mo):02d}-{int(d):02d}"
    return s

def to_mobile_url(url: str) -> str:
    if "m.blog.naver.com" in url:
        return url
    if "PostView.naver" in url:
        qs = parse_qs(urlparse(url).query)
        bid = qs.get("blogId", [None])[0]
        log = qs.get("logNo", [None])[0]
        if bid and log:
            return f"https://m.blog.naver.com/{bid}/{log}"
    m = re.search(r"blog\.naver\.com/([^/]+)/(\d+)", url)
    if m:
        return f"https://m.blog.naver.com/{m.group(1)}/{m.group(2)}"
    return url

def safe_goto(page, url: str, nav_timeout: int):
    """네이버는 networkidle이 잘 안 옴 → domcontentloaded 우선 + 폴백."""
    try:
        return page.goto(url, wait_until="domcontentloaded", timeout=nav_timeout)
    except Exception:
        pass
    try:
        return page.goto(url, wait_until="load", timeout=nav_timeout + 4000)
    except Exception:
        pass
    murl = to_mobile_url(url)
    if murl != url:
        try:
            return page.goto(murl, wait_until="domcontentloaded", timeout=nav_timeout)
        except Exception:
            pass
    # 마지막 폴백
    page.goto(url, timeout=nav_timeout)
    return None

def pick_text(ctx, selectors, attr=None, timeout=INNER_TIMEOUT):
    for sel in selectors:
        try:
            el = ctx.locator(sel).first
            el.wait_for(timeout=timeout)
            if attr == "content":
                v = el.get_attribute("content")
            elif attr:
                v = el.get_attribute(attr)
            else:
                v = el.inner_text(timeout=timeout)
            if v:
                return v.strip()
        except Exception:
            pass
    return None

def pick_text_both(primary_ctx, secondary_ctx, selectors, attr=None, timeout=INNER_TIMEOUT):
    v = pick_text(primary_ctx, selectors, attr=attr, timeout=timeout)
    if not v and secondary_ctx:
        v = pick_text(secondary_ctx, selectors, attr=attr, timeout=timeout)
    return (v or "").strip()

def wait_numeric_text(ctx, selectors, timeout_ms=WAIT_NUMERIC):
    """여러 selector 중 하나라도 숫자를 포함할 때까지 기다렸다가 숫자만 반환"""
    if isinstance(selectors, str):
        selectors = [selectors]
    for selector in selectors:
        try:
            ctx.wait_for_selector(selector, timeout=timeout_ms)
            ctx.wait_for_function(
                """([sel]) => {
                    const el = document.querySelector(sel);
                    if (!el) return false;
                    const t = (el.innerText || el.textContent || "").replace(/\\s+/g,"");
                    return /\\d/.test(t);
                }""",
                arg=selector,
                timeout=timeout_ms,
                polling=200
            )
            txt = ctx.locator(selector).first.inner_text(timeout=INNER_TIMEOUT)
            num = re.sub(r"[^\d]", "", txt or "")
            if num and num != "0":
                return num
        except Exception:
            continue
    return "0"

def trigger_lazy_loading(page):
    try:
        page.mouse.wheel(0, 600); page.wait_for_timeout(200)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)"); page.wait_for_timeout(300)
        page.evaluate("window.scrollTo(0, 0)"); page.wait_for_timeout(100)
    except Exception:
        pass

def read_likes_dom(page):
    """플로팅 메뉴 공감 카운터 DOM에서 읽기 (프레임 포함)"""
    for sel in [".btn_like_w", ".section_t1", "#sympathyArea", ".u_likeit_list_module"]:
        try:
            el = page.locator(sel).first
            el.wait_for(timeout=1500)
            el.scroll_into_view_if_needed(timeout=800)
            page.wait_for_timeout(300)
            break
        except Exception:
            pass

    ctxs = [page]
    mf = page.frame(name="mainFrame")
    if mf:
        ctxs.append(mf)
    for fr in page.frames:
        if fr not in ctxs:
            ctxs.append(fr)

    for ctx in ctxs:
        for sel in LIKE_STRICT:
            try:
                ctx.wait_for_selector(sel, state="attached", timeout=2000)
                txt = ctx.locator(sel).first.inner_text(timeout=INNER_TIMEOUT)
                num = re.sub(r"[^\d]", "", txt or "")
                if num and num != "0":
                    return num
            except Exception:
                continue
    return "0"



def extract_from_loaded_page(page, post_json=None):
    frame = page.frame(name="mainFrame")
    target = frame or page
    other  = page if frame else None

    for sel in POST_SELECTORS:
        try:
            (target or page).wait_for_selector(sel, timeout=SEL_TIMEOUT)
            break
        except PwTimeout:
            pass

    title = pick_text_both(target or page, other, TITLE_CANDIDATES, attr="content") \
         or pick_text_both(target or page, other, TITLE_CANDIDATES, timeout=SEL_TIMEOUT) \
         or page.title()
    title = clean_title(title)

    # 날짜
    date_raw = None
    # JSON-LD
    try:
        handles = (target or page).locator('script[type="application/ld+json"]').all()
        for h in handles:
            raw = (h.inner_text() or "")
            if '"datePublished"' in raw or '"uploadDate"' in raw:
                j = json.loads(raw)
                def collect(d, acc):
                    if isinstance(d, dict):
                        for k,v in d.items():
                            if k in ("datePublished","uploadDate","dateCreated"):
                                acc.append(str(v))
                            else:
                                collect(v, acc)
                    elif isinstance(d, list):
                        for x in d: collect(x, acc)
                acc = []; collect(j, acc)
                for c in acc:
                    m = re.search(r"\d{4}-\d{2}-\d{2}", c)
                    if m:
                        date_raw = m.group(0); break
        if not date_raw:
            date_raw = pick_text_both(target or page, other, DATE_CANDIDATES_META, attr="content", timeout=SEL_TIMEOUT)
    except Exception:
        pass
    if not date_raw and frame:
        try:
            frame.wait_for_function(
                """() => {
                    const t = document.body ? document.body.innerText : "";
                    return /(\\d{4})\\s*\\.\\s*(\\d{1,2})\\s*\\.\\s*(\\d{1,2})/.test(t) ||
                           /(\\d{4}-\\d{2}-\\d{2})/.test(t);
                }""",
                timeout=WAIT_NUMERIC
            )
        except Exception:
            pass
        date_raw = pick_text(frame, DATE_CANDIDATES_DOM, timeout=INNER_TIMEOUT)
    if not date_raw:
        date_raw = pick_text_both(target or page, other, DATE_CANDIDATES_DOM, timeout=SEL_TIMEOUT)
    post_date = format_date_kr(date_raw)

    # 공감: XHR 우선, DOM 보조, 폴백
    likes = "0"
    if post_json:
        cand = post_json.get("_like_candidates") or []
        if cand:
            likes = str(max(cand))
    if likes == "0":
        likes = read_likes_dom(page)
    if likes == "0":
        def read_likes_fallback(ctx):
            n = wait_numeric_text(ctx, LIKE_CANDIDATES, timeout_ms=WAIT_NUMERIC)
            if n != "0":
                return n
            try:
                txts = ctx.eval_on_selector_all(
                    "a[role='button'],button,span,div,em",
                    "els => els.map(e => e.textContent||'').filter(t=>/공감/.test(t)).join(' | ')"
                )
                nums = re.findall(r"\d+", txts or "")
                if nums:
                    return str(max(int(x) for x in nums))
            except Exception:
                pass
            return "0"
        likes = read_likes_fallback(page)
        if likes == "0" and frame:
            likes = read_likes_fallback(frame)

    # 댓글
    comments = wait_numeric_text(page,
        ["#commentCount", ".u_cbox_count", ".se_comment_count",
         "#cbox_module .u_cbox_count", ".comment_area .count"],
        timeout_ms=WAIT_NUMERIC
    )
    if comments == "0" and frame:
        tmp = wait_numeric_text(frame, [".u_cbox_count", ".se_comment_count"], timeout_ms=SEL_TIMEOUT)
        if tmp != "0":
            comments = tmp
        else:
            tmp2 = pick_text_both(page, frame, ["#commentCount", ".u_cbox_count", ".se_comment_count"], timeout=SEL_TIMEOUT)
            comments = re.sub(r"[^\d]", "", tmp2 or "0") or "0"

    return {
        "post_title": title,
        "post_date": post_date,
        "post_likes": likes,
        "post_comments": comments
    }

def load_and_extract(page, url: str):
    post_json = {}

    # XHR 수집 핸들러
    def handle_response(response):
        try:
            ctype = (response.headers.get("content-type", "") or "").lower()
            url_l = (response.url or "").lower()
            is_jsonish = ("json" in ctype) or ("javascript" in ctype)
            if is_jsonish and not any(ad in url_l for ad in ["veta.naver.com", "ssp-ad", "gfp"]) and any(
                k in url_l for k in [
                    "postview", "post-view", "common.like", "u_likeit", "sympathy", "/like/", "/likes",
                    "blogid", "logno", "blog.naver.com"
                ]
            ):
                data = response.json()
                # 평탄화
                acc = {}
                def merge(d):
                    if isinstance(d, dict):
                        for k, v in d.items():
                            if isinstance(v, (dict, list)):
                                merge(v)
                            else:
                                acc[k] = v
                    elif isinstance(d, list):
                        for x in d:
                            merge(x)
                merge(data)
                for k in ["totalCount", "likeCount", "sympathyCount", "sympathies", "count"]:
                    if k in acc:
                        try:
                            v = int(re.sub(r"[^\d]", "", str(acc[k])))
                            post_json.setdefault("_like_candidates", []).append(v)
                        except Exception:
                            pass
                post_json.update(data)
        except Exception:
            pass

    page.on("response", handle_response)

    # 페이지 열기
    safe_goto(page, url, NAV_TIMEOUT)

    # 지연 로딩 유도
    trigger_lazy_loading(page)
    page.wait_for_timeout(600)

    return extract_from_loaded_page(page, post_json)

def get_blog_info(post_url: str):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox","--disable-dev-shm-usage","--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            user_agent=UA,
            locale="ko-KR",
            timezone_id="Asia/Seoul",
            viewport={"width": 1280, "height": 800},
            extra_http_headers={"Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8"},
        )
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")

        page = context.new_page()
        page.set_default_navigation_timeout(NAV_TIMEOUT)
        page.set_default_timeout(SEL_TIMEOUT)

        # 이미지/폰트/미디어 + 대표 광고만 차단
        AD_HOSTS = ("veta.naver.com", "ssl.pstatic.net/ads", "doubleclick.net", "adservice.google.com")
        page.route("**/*", lambda route: (
            route.abort()
            if (route.request.resource_type in {"image","font","media"}
                or any(h in route.request.url for h in AD_HOSTS))
            else route.continue_()
        ))

        try:
            data = load_and_extract(page, post_url)
        finally:
            context.close(); browser.close()

        if not data:
            data = {"post_title": "제목 없음", "post_date": "날짜 없음", "post_likes": "0", "post_comments": "0"}
        data["url"] = post_url
        return data

# ---- 테스트 실행 ----
if __name__ == "__main__":
    url = "https://blog.naver.com/11010design/223727804470"
    info = get_blog_info(url)
    print(f"제목: {info['post_title']}")
    print(f"날짜: {info['post_date']}")
    print(f"댓글 수: {info['post_comments']}")
    print(f"좋아요 수: {info['post_likes']}")

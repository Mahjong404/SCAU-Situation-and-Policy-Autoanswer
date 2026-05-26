import json
import re
import sys
import os
import base64
from pathlib import Path
from playwright.async_api import Page

BASE_DIR = Path(__file__).parent
QUESTION_PATH = BASE_DIR / "data" / "questions.json"

_old_cwd = os.getcwd()
os.chdir(str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR))
from chaoxing_solution_of_font_confusion.glyfSearch import translate  # noqa: E402
os.chdir(_old_cwd)


def _extract_ttf_base64(html: str) -> str | None:
    for pattern in [
        r"font-ttf;charset=utf-8;base64,([^\'\")]+)",
        r"base64,([A-Za-z0-9+/=]{100,})",
        r"url\(data:font[^)]+base64,([A-Za-z0-9+/=]+)",
    ]:
        m = re.search(pattern, html)
        if m:
            return m.group(1)
    return None


def _build_decoder(table):
    src_chars, dst_chars = table
    mapping = dict(zip(src_chars, dst_chars))

    def decode_text(text: str) -> str:
        if not text or not mapping:
            return text
        for s, d in mapping.items():
            text = text.replace(s, d)
        return text

    return decode_text


def _normalize(s: str) -> str:
    s = re.sub(r"^\s*\d+[、.]\s*", "", s)
    s = re.sub(r"^\s*【(单选题|多选题|判断题)】\s*", "", s)
    s = s.replace("（", "(").replace("）", ")")
    s = re.sub(r"\s+", "", s)
    return s


async def answer(page: Page) -> None:
    with open(QUESTION_PATH, "r", encoding="utf-8") as f:
        question_bank = json.load(f)

    # 进入三层嵌套 iframe
    deep = (
        page
        .frame_locator("iframe").first
        .frame_locator("iframe").first
        .frame_locator("iframe").first
    )

    await deep.locator(".TiMu").first.wait_for(state="visible", timeout=15000)

    # 构建字体解码器
    ttf_b64 = None
    for frame in page.frames:
        try:
            html = await frame.evaluate("() => document.documentElement.outerHTML")
        except Exception:
            continue
        ttf_b64 = _extract_ttf_base64(html)
        if ttf_b64:
            break

    decoder = (lambda x: x)
    if ttf_b64:
        font_bytes = base64.b64decode(ttf_b64)
        decoder = _build_decoder(translate(font_bytes))

    # 取第一道题
    qb = deep.locator(".TiMu").first

    title_el = qb.locator(".font-cxsecret").first
    if await title_el.count() == 0:
        print("未找到题干")
        return

    question_raw = await title_el.text_content()
    if not question_raw:
        print("题干为空")
        return

    question_decoded = decoder(question_raw)
    q_key = _normalize(question_decoded)

    matched = None
    for q in question_bank:
        if _normalize(q.get("question", "")) == q_key:
            matched = q
            break

    if not matched:
        print(f"未匹配到题目: {question_decoded.strip()[:60]}...")
        return

    print(f"匹配成功: {matched['type']} answer={matched['answer']}")

    if matched["type"] == "判断题":
        ans = matched.get("answer", "")
        target_texts = {"对"} if ans == "√" else {"错"} if ans == "X" else set()
    else:
        letter_to_text = {}
        for opt in matched.get("options", []):
            m = re.match(r"\s*([A-D])[、.]?\s*(.+)", opt)
            if m:
                letter_to_text[m.group(1)] = m.group(2)

        target_letters = list(matched.get("answer", ""))
        target_texts = set(letter_to_text.get(l, "") for l in target_letters)

    target_texts = {t for t in target_texts if t}
    if not target_texts:
        print("无目标选项文本")
        return

    option_els = qb.locator("ul.Zy_ulTop li")
    count = await option_els.count()
    for i in range(count):
        li = option_els.nth(i)
        a_el = li.locator("a.fl.after")
        a_text_raw = await a_el.text_content() if await a_el.count() > 0 else await li.text_content()

        a_text_decoded = decoder(a_text_raw).strip()

        if a_text_decoded in target_texts:
            checked = await li.get_attribute("aria-checked")
            if checked != "true":
                await li.click()
                await page.wait_for_timeout(500)
                print(f"已点击: {a_text_decoded}")
            else:
                print(f"已选中(跳过): {a_text_decoded}")
            break

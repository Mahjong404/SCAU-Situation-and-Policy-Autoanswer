import json
import re
import sys
import os
import base64
from difflib import SequenceMatcher
from pathlib import Path
from playwright.async_api import Page

BASE_DIR = Path(__file__).parent
QUESTION_PATH = BASE_DIR / "data" / "questions.json"
FUZZY_LOG_PATH = BASE_DIR / "fuzzy_matches.txt"

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


def _match_question(question_bank: list, q_key: str) -> tuple:
    """返回 (题目, 是否模糊匹配, 相似度)"""
    best, best_ratio = None, 0
    for q in question_bank:
        q_norm = _normalize(q.get("question", ""))
        if q_norm == q_key:
            return q, False, 1.0
        ratio = SequenceMatcher(None, q_norm, q_key).ratio()
        if ratio > best_ratio:
            best_ratio, best = ratio, q
    if best_ratio >= 0.92:
        return best, True, best_ratio
    return None, False, best_ratio


def _get_target_texts(matched: dict) -> set[str]:
    if matched["type"] == "判断题":
        ans = matched.get("answer", "")
        return {"对"} if ans == "√" else {"错"} if ans == "X" else set()

    letter_to_text = {}
    for opt in matched.get("options", []):
        m = re.match(r"\s*([A-D])[、.]?\s*(.+)", opt)
        if m:
            letter_to_text[m.group(1)] = m.group(2)

    target_letters = list(matched.get("answer", ""))
    return {letter_to_text.get(l, "") for l in target_letters} - {""}


async def _click_correct_options(page: Page, qb, decoder,
                                  target_texts: set[str], multi: bool) -> int:
    """点击正确选项，multi=True 时点击全部匹配。返回点击数"""
    option_els = qb.locator("ul.Zy_ulTop li")
    count = await option_els.count()
    clicked = 0
    for i in range(count):
        li = option_els.nth(i)
        a_el = li.locator("a.fl.after")
        a_text_raw = await a_el.text_content() if await a_el.count() > 0 else await li.text_content()
        a_text_decoded = decoder(a_text_raw).strip()

        if a_text_decoded in target_texts:
            checked = await li.get_attribute("aria-checked")
            if checked != "true":
                await li.click()
                await page.wait_for_timeout(300)
                print(f"  已点击: {a_text_decoded}")
                clicked += 1
                if not multi:
                    return clicked
            else:
                print(f"  已选中(跳过): {a_text_decoded}")
                if not multi:
                    return clicked
                clicked += 1
    return clicked


async def answer(page: Page) -> None:
    with open(QUESTION_PATH, "r", encoding="utf-8") as f:
        question_bank = json.load(f)

    f1 = page.frame_locator("iframe").first
    await f1.locator("iframe").first.wait_for(state="attached", timeout=30000)

    f2 = f1.frame_locator("iframe").first
    await f2.locator("iframe").first.wait_for(state="attached", timeout=30000)

    deep = f2.frame_locator("iframe").first
    await deep.locator(".TiMu").first.wait_for(state="visible", timeout=30000)

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

    question_blocks = deep.locator(".TiMu")
    total = await question_blocks.count()
    print(f"共 {total} 道题\n")

    fuzzy_log = []
    answered = 0
    for i in range(total):
        qb = question_blocks.nth(i)

        title_el = qb.locator(".font-cxsecret").first
        if await title_el.count() == 0:
            continue

        question_raw = await title_el.text_content()
        if not question_raw:
            continue

        question_decoded = decoder(question_raw).strip()
        q_key = _normalize(question_decoded)

        matched, is_fuzzy, ratio = _match_question(question_bank, q_key)
        if not matched:
            preview = question_decoded[:60]
            print(f"[{i+1}] 未匹配: {preview}...")
            print("题库无此题，退出答题。")
            return

        if is_fuzzy:
            q_norm = _normalize(matched.get("question", ""))
            fuzzy_log.append(
                f"[{i+1}] {matched['type']} ratio={ratio:.3f}\n"
                f"  页面: {q_key}\n"
                f"  题库: {q_norm}\n"
            )

        print(f"[{i+1}] {matched['type']} answer={matched['answer']}")

        target_texts = _get_target_texts(matched)
        if not target_texts:
            print("  无目标选项")
            continue

        multi = matched["type"] == "多选题"
        clicked = await _click_correct_options(page, qb, decoder, target_texts, multi)
        answered += clicked

    print(f"\n已回答 {answered}/{total} 题")

    if fuzzy_log:
        with open(FUZZY_LOG_PATH, "w", encoding="utf-8") as f:
            f.write("=== 模糊匹配题目（请核验）===\n\n")
            f.write("\n".join(fuzzy_log))
        print(f"模糊匹配 {len(fuzzy_log)} 题，已写入 {FUZZY_LOG_PATH}")

    save_btn = deep.locator("#tempsave")
    if await save_btn.count() > 0:
        await save_btn.click()
        print("已点击: 暂时保存")
    else:
        print("未找到「暂时保存」按钮")

    print("\n答题完成。")

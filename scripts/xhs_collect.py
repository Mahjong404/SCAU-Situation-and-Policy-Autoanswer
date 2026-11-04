"""Collect complete XHS image carousels through the user's web-access browser."""
import argparse
import asyncio
import hashlib
import html
import json
import re
import urllib.request
from pathlib import Path

from PIL import Image
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
PROXY = "http://localhost:3456"


def proxy(route, body=None):
    request = urllib.request.Request(PROXY + route, data=body.encode() if body is not None else None)
    with urllib.request.urlopen(request, timeout=60) as response:
        result = json.load(response)
    if "error" in result:
        raise RuntimeError(result["error"])
    return result


def extract_urls(text):
    # Accept Markdown links, discovery/item, explore, xhslink, and pasted share text.
    text = html.unescape(re.sub(r"\\([:/._&?=\-])", r"\1", text))
    urls = re.findall(r"https?://(?:www\.)?(?:xiaohongshu\.com|xhslink\.com)/[^\s<>\]\)]+", text)
    return list(dict.fromkeys(urls))


async def collect(term, text, targets):
    if not re.fullmatch(r"\d{4}-\d{4}-[12]", term) or int(term[5:9]) != int(term[:4]) + 1:
        raise ValueError("学期格式必须为 yyyy-yyyy-1/2，学年连续")
    folder = ROOT / "question bank" / term
    folder.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("ws://127.0.0.1:9222/devtools/browser")
        for index, url in enumerate(extract_urls(text)):
            owned = index >= len(targets)
            target = proxy("/new", url)["targetId"] if owned else targets[index]
            session = None
            try:
                for context in browser.contexts:
                    for candidate in context.pages:
                        probe = await context.new_cdp_session(candidate)
                        info = await probe.send("Target.getTargetInfo")
                        if info["targetInfo"]["targetId"] == target:
                            page, session = candidate, probe
                            break
                        await probe.detach()
                    if session:
                        break
                if session is None:
                    raise RuntimeError("未找到本次创建的笔记标签页")
                await page.wait_for_selector(".note-detail-mask .note-slider-img img", timeout=30000)
                data = await page.evaluate("""() => {
                  const root = document.querySelector('.note-detail-mask');
                  return {title:document.title,url:location.href,text:root.innerText,
                    images:[...new Set([...root.querySelectorAll('.note-slider-img img')].map(i=>i.src))]};
                }""")
                note = re.search(r"/(?:explore|discovery/item)/([a-f0-9]{24})", data["url"])
                if not note:
                    raise ValueError("无法识别笔记ID")
                note_id = note[1]
                total = re.search(r"\b\d+/(\d+)\b", data["text"])
                if not total or int(total[1]) != len(data["images"]):
                    raise ValueError("轮播总数与正文图片数不符；停止以避免漏图")
                images_dir = folder / "images" / note_id
                images_dir.mkdir(parents=True, exist_ok=True)
                await session.send("Page.setDownloadBehavior", {"behavior":"allow", "downloadPath":str(images_dir)})
                files = []
                for number, image_url in enumerate(data["images"], 1):
                    filename = f"{number:03}.webp"
                    path = images_dir / filename
                    if not path.exists():
                        # Blob + anchor triggers a real browser download; destination is controlled above.
                        await page.evaluate("""async ({url,name}) => {
                          const response=await fetch(url);
                          if (!response.ok) throw new Error('图片HTTP '+response.status);
                          const blob=await response.blob(), link=document.createElement('a');
                          link.href=URL.createObjectURL(blob);link.download=name;
                          document.body.append(link);link.click();link.remove();
                          setTimeout(()=>URL.revokeObjectURL(link.href),30000);
                        }""", {"url":image_url,"name":filename})
                        for _ in range(120):
                            if path.exists() and not path.with_suffix(".webp.crdownload").exists():
                                break
                            await asyncio.sleep(0.25)
                    with Image.open(path) as image:
                        image.load()
                        width, height = image.size
                        image_format = image.format
                    if image_format != "WEBP":
                        new_path = path.with_suffix("." + image_format.lower().replace("jpeg", "jpg"))
                        path.rename(new_path)
                        path = new_path
                    files.append({"index":number,"file":path.relative_to(folder).as_posix(),
                        "url":image_url,"width":width,"height":height,
                        "sha256":hashlib.sha256(path.read_bytes()).hexdigest()})
                    print(f"{note_id}: {number}/{len(data['images'])} {width}x{height}", flush=True)
                data.update(note_id=note_id, term=term, download_method="browser_blob_download_Page.setDownloadBehavior",
                            image_count=len(files), files=files)
                # Store the note body and image provenance, excluding unrelated feed images.
                dest = folder / "sources" / f"{note_id}.json"
                dest.parent.mkdir(exist_ok=True)
                dest.write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
            finally:
                if session:
                    await session.send("Page.setDownloadBehavior", {"behavior":"default"})
                    await session.detach()
                if owned:
                    proxy("/close?target=" + target)
        # Disconnect only; never close the user's browser.


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--term", required=True)
    parser.add_argument("--input", type=Path, required=True, help="包含URL或分享文本的UTF-8文件")
    parser.add_argument("--targets", nargs="*", default=[], help=argparse.SUPPRESS)
    args = parser.parse_args()
    asyncio.run(collect(args.term, args.input.read_text(encoding="utf-8-sig"), args.targets))

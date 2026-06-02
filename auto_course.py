from playwright.async_api import Page, TimeoutError

import auto_video


def is_completed_status(text: str | None) -> bool:
    return (text or "").strip() == "已完成"


def is_completed_task_icon(aria_label: str | None) -> bool:
    label = (aria_label or "").strip()
    return "已完成" in label and "未完成" not in label


async def _find_unfinished_leaf_item(page: Page):
    items = page.locator("#coursetree li")
    count = await items.count()
    for i in range(count):
        item = items.nth(i)
        if not await item.is_visible():
            continue

        has_child_li = await item.evaluate(
            "el => el.querySelector('ul li, ol li') !== null"
        )
        if has_child_li:
            continue

        tips = item.locator("span.prevHoverTips")
        if await tips.count() == 0:
            continue

        status = await tips.last.text_content()
        if not is_completed_status(status):
            return item

    return None


async def find_next_unfinished_catalog_item(page: Page):
    tabs = page.locator("#selector li")
    tab_count = await tabs.count()
    if tab_count == 0:
        return await _find_unfinished_leaf_item(page)

    for i in range(tab_count):
        tab = tabs.nth(i)
        if not await tab.is_visible():
            continue

        await tab.click()
        await page.wait_for_timeout(500)

        item = await _find_unfinished_leaf_item(page)
        if item:
            return item

    return None


async def _complete_videos_in_frame(outer_frame, catalog_title: str,
                                    speed: float, mute: bool) -> int:
    blocks = outer_frame.locator("p:has(iframe)")
    count = await blocks.count()
    completed = 0

    for i in range(count):
        block = blocks.nth(i)
        icon = block.locator(".ans-job-icon").first
        aria_label = await icon.get_attribute("aria-label") if await icon.count() else None
        if is_completed_task_icon(aria_label):
            continue

        iframe = block.locator("iframe").first
        if await iframe.count() == 0:
            continue

        video_label = f"{catalog_title} 第{i + 1}个"
        if await auto_video.play_player(
            iframe.content_frame,
            label=video_label,
            speed=speed,
            mute=mute,
        ):
            completed += 1

    return completed


async def complete_videos_in_current_item(page: Page, catalog_title: str,
                                          speed: float, mute: bool) -> int:
    outer_iframes = page.locator("iframe")
    count = await outer_iframes.count()
    completed = 0

    for i in range(count):
        iframe = outer_iframes.nth(i)
        try:
            completed += await _complete_videos_in_frame(
                iframe.content_frame,
                catalog_title,
                speed,
                mute,
            )
        except TimeoutError:
            continue

    return completed


async def complete_course_videos(page: Page, speed: float = 2.0,
                                 mute: bool = True, max_rounds: int = 100) -> int:
    total_completed = 0

    for _ in range(max_rounds):
        item = await find_next_unfinished_catalog_item(page)
        if not item:
            print("课程目录任务均已完成")
            return total_completed

        title = (await item.inner_text()).strip().splitlines()[0]
        print(f"进入未完成目录: {title}")
        await item.scroll_into_view_if_needed()
        await item.click()
        await page.wait_for_timeout(2000)

        completed = await complete_videos_in_current_item(page, title, speed, mute)
        total_completed += completed

        if completed == 0:
            print("当前目录未发现可播放的未完成视频，停止视频遍历")
            return total_completed

    print("目录遍历达到上限，停止视频遍历")
    return total_completed

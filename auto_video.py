from playwright.async_api import Page, TimeoutError


async def video(page: Page) -> bool:
    """播放视频并跳转到下一节。返回 True 表示处理了视频页面。"""
    # 快速检查主页面是否包含视频播放器相关 iframe
    outer = page.frame_locator("iframe").first
    try:
        await outer.locator("iframe").first.wait_for(state="attached", timeout=5000)
    except TimeoutError:
        print("未检测到视频页面，直接答题")
        return False

    player = outer.frame_locator("iframe").first

    play_btn = player.locator(".vjs-big-play-button")
    ended = player.locator(".vjs-ended")

    try:
        await play_btn.first.wait_for(state="attached", timeout=3000)
        await play_btn.click()
        print("视频开始播放")

        play_ctrl = player.locator(".vjs-play-control")
        if await play_ctrl.count() > 0:
            await play_ctrl.hover()

        await ended.wait_for(state="attached", timeout=1_750_000)
        print("视频播放完成")

    except TimeoutError:
        try:
            await ended.first.wait_for(state="attached", timeout=3000)
            print("视频已完成")
        except TimeoutError:
            print("未检测到视频播放器，跳过")

    next_btn = page.locator("#prevNextFocusNext")
    if await next_btn.count() > 0 and await next_btn.is_visible():
        await next_btn.click()
        await page.wait_for_timeout(3000)
        print("已点击下一节")
        return True

    return False

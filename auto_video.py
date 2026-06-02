from playwright.async_api import Page, TimeoutError


def is_double_speed_text(text: str | None) -> bool:
    text = (text or "").strip().lower().replace(" ", "")
    return text in {"2x", "2.0x", "2倍", "2.0倍"}


def is_double_speed_rate(rate) -> bool:
    try:
        return float(rate) >= 1.95
    except (TypeError, ValueError):
        return False


def video_complete_message(label: str | None) -> str:
    label = (label or "").strip()
    return f"已完成{label}视频播放" if label else "已完成视频播放"


def is_note_tip_text(text: str | None) -> bool:
    return (text or "").strip() == "可边看边记，笔记会标记视频时间点"


async def _dismiss_note_tip(player) -> bool:
    boxes = player.locator("div.writeNote_vid_box")
    count = await boxes.count()
    for i in range(count):
        box = boxes.nth(i)
        tip = box.locator("div.writeNote_vid_text").first
        if await tip.count() == 0:
            continue

        tip_text = await tip.text_content()
        if not is_note_tip_text(tip_text):
            continue

        button = box.locator("a.writeNote_vid_blue", has_text="知道了").first
        if await button.count() == 0:
            continue

        try:
            await button.click(timeout=3000)
            print("已关闭: 记笔记提示")
            return True
        except TimeoutError:
            return False

    return False


async def _is_player_double_speed(player) -> bool:
    video = player.locator("video").first
    if await video.count() > 0:
        rate = await video.evaluate("el => el.playbackRate")
        if is_double_speed_rate(rate):
            return True

    speed_btn = player.locator("button.vjs-playback-rate, .vjs-playback-rate").first
    if await speed_btn.count() > 0:
        text = await speed_btn.text_content()
        if is_double_speed_text(text):
            return True

    return False


async def _set_double_speed(player) -> bool:
    if await _is_player_double_speed(player):
        print("已是2倍速")
        return True

    speed_btn = player.locator("button.vjs-playback-rate, .vjs-playback-rate").first
    try:
        await speed_btn.wait_for(state="visible", timeout=5000)
        await speed_btn.hover()
    except TimeoutError:
        print("未找到播放速度按钮")
        return False

    menu_items = player.locator(".vjs-menu-item, [role='menuitem'], [role='menuitemradio']")
    count = await menu_items.count()
    for i in range(count):
        item = menu_items.nth(i)
        text = await item.text_content()
        if is_double_speed_text(text):
            await item.click(timeout=3000)
            print("已设置: 2倍速")
            return True

    if await _is_player_double_speed(player):
        print("已是2倍速")
        return True

    video = player.locator("video").first
    if await video.count() > 0:
        await video.evaluate("el => el.playbackRate = 2")
        print("已设置: 2倍速")
        return True

    print("未找到2倍速选项")
    return False


async def _mute_player(player) -> bool:
    mute_btn = player.locator("button.vjs-mute-control").first
    try:
        await mute_btn.wait_for(state="visible", timeout=5000)
    except TimeoutError:
        print("未找到静音按钮")
        return False

    title = await mute_btn.get_attribute("title")
    class_name = await mute_btn.get_attribute("class")
    if title == "取消静音" or "vjs-vol-0" in (class_name or ""):
        print("已是静音状态")
        return True

    await mute_btn.click()
    print("已设置: 静音")
    return True


async def _configure_player(player) -> None:
    await _set_double_speed(player)
    await _mute_player(player)


async def play_player(player, timeout: int = 1_750_000, label: str | None = None) -> bool:
    """播放一个视频播放器 iframe。返回 True 表示检测到并处理了播放器。"""
    play_btn = player.locator(".vjs-big-play-button")
    ended = player.locator(".vjs-ended")

    try:
        await play_btn.first.wait_for(state="visible", timeout=5000)
        await _dismiss_note_tip(player)
        await play_btn.first.click()
        print("视频开始播放")
        await _configure_player(player)
    except TimeoutError:
        try:
            await ended.first.wait_for(state="attached", timeout=3000)
            print("视频已完成")
            return True
        except TimeoutError:
            print("未检测到视频播放器，跳过")
            return False

    play_ctrl = player.locator(".vjs-play-control")
    if await play_ctrl.count() > 0:
        await play_ctrl.first.hover()

    await ended.first.wait_for(state="attached", timeout=timeout)
    print(video_complete_message(label))
    return True


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

    handled = await play_player(player)

    next_btn = page.locator("#prevNextFocusNext")
    if await next_btn.count() > 0 and await next_btn.is_visible():
        await next_btn.click()
        await page.wait_for_timeout(3000)
        print("已点击下一节")
        return True

    return handled

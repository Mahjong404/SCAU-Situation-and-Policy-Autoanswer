import asyncio
from playwright.async_api import async_playwright
import setup
import auto_sign_in
import auto_course
import auto_answer


async def main():
    config = setup.run()
    account = config["account"]
    settings = config["settings"]

    async with async_playwright() as p:
        browser_name = settings["browser"]
        if browser_name == "chromium":
            browser = await p.chromium.launch(headless=False)
        else:
            browser = await p.chromium.launch(channel=browser_name, headless=False)
        context = await browser.new_context()

        page = await auto_sign_in.sign_in(context, account)

        try:
            await auto_course.complete_course_videos(
                page,
                speed=float(settings["speed"]),
                mute=bool(settings["mute"]),
            )
        except Exception as e:
            print(f"视频模块跳过: {e}")

        await auto_answer.answer(page)

        input("按回车键关闭浏览器...")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())

import asyncio
from playwright.async_api import async_playwright
import auto_sign_in
import auto_answer


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=False)
        context = await browser.new_context()

        page = await auto_sign_in.sign_in(context)
        await auto_answer.answer(page)

        input("按回车键关闭浏览器...")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())

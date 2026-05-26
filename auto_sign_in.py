import json
from pathlib import Path
from playwright.async_api import BrowserContext, Page


BASE_DIR = Path(__file__).parent
ACCOUNT_PATH = BASE_DIR / "real_data" / "account.json"


async def sign_in(context: BrowserContext) -> Page:
    with open(ACCOUNT_PATH, "r", encoding="utf-8") as f:
        account = json.load(f)

    page = await context.new_page()

    await page.add_init_script("""
        const nativeAdd = EventTarget.prototype.addEventListener;
        EventTarget.prototype.addEventListener = function(type, fn, opts) {
            if (type === 'mouseout') {
                console.log('[block] mouseout on', this);
                return;
            }
            nativeAdd.call(this, type, fn, opts);
        };
        Object.defineProperty(Element.prototype, 'onmouseout', {
            set: function(_) {},
            get: function() { return null; }
        });
    """)

    await page.goto(account["course"], wait_until="domcontentloaded")
    await page.wait_for_timeout(3000)

    phone_input = page.locator(".ipt-tel")
    if await phone_input.count() > 0:
        await phone_input.fill(str(account["phone"]))
        await page.locator(".ipt-pwd").fill(str(account["password"]))
        await page.locator("button").click()
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(3000)

    return page

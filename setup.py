import json
from pathlib import Path


BASE_DIR = Path(__file__).parent
REAL_DATA_DIR = BASE_DIR / "real_data"
ACCOUNT_PATH = REAL_DATA_DIR / "account.json"
SETTINGS_PATH = REAL_DATA_DIR / "settings.json"


def default_account() -> dict:
    return {"phone": "", "password": "", "course": ""}


def default_settings() -> dict:
    return {"browser": "msedge", "speed": 2.0, "mute": True}


def resolve_browser_choice(choice: str) -> str:
    choices = {
        "": "msedge",
        "1": "msedge",
        "edge": "msedge",
        "msedge": "msedge",
        "2": "chrome",
        "chrome": "chrome",
        "3": "chromium",
        "chromium": "chromium",
    }
    return choices.get((choice or "").strip().lower(), "msedge")


def parse_speed(value: str, current: float) -> float:
    if not value.strip():
        return current
    try:
        speed = float(value)
    except ValueError:
        return current
    return speed if speed > 0 else current


def parse_mute(value: str, current: bool) -> bool:
    value = (value or "").strip().lower()
    if not value:
        return current
    if value in {"y", "yes", "1", "true", "是"}:
        return True
    if value in {"n", "no", "0", "false", "否"}:
        return False
    return current


def mask_phone(phone: str) -> str:
    phone = str(phone or "")
    if len(phone) < 7:
        return phone
    return f"{phone[:3]}****{phone[-4:]}"


def is_account_complete(account: dict) -> bool:
    return all(str(account.get(key, "")).strip() for key in ("phone", "password", "course"))


def _read_json(path: Path, fallback: dict) -> dict:
    if not path.exists():
        return fallback.copy()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return fallback.copy()
    result = fallback.copy()
    result.update({k: data.get(k, v) for k, v in fallback.items()})
    return result


def _write_json(path: Path, data: dict) -> None:
    REAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _print_summary(account: dict, settings: dict) -> None:
    print("\n当前设置：")
    print(f"  账号: {mask_phone(account.get('phone', '')) or '(空)'}")
    print(f"  密码: {'***' if account.get('password') else '(空)'}")
    print(f"  课程URL: {account.get('course') or '(空)'}")
    print(f"  浏览器: {settings.get('browser', 'msedge')}")
    print(f"  倍速: {settings.get('speed', 2.0)}x")
    print(f"  静音: {'是' if settings.get('mute', True) else '否'}")


def _edit_account(account: dict) -> dict:
    print("\n修改账号/密码/url，直接回车保留当前值。")
    phone = input(f"phone [{mask_phone(account.get('phone', '')) or '空'}]: ").strip()
    password = input("password [***]: ").strip()
    course = input(f"url [{account.get('course') or '空'}]: ").strip()

    updated = account.copy()
    if phone:
        updated["phone"] = phone
    if password:
        updated["password"] = password
    if course:
        updated["course"] = course
    return updated


def _edit_settings(settings: dict) -> dict:
    updated = settings.copy()

    print("\n浏览器：[1] Edge  [2] Chrome  [3] Chromium")
    updated["browser"] = resolve_browser_choice(input("选择浏览器 [默认Edge]: "))

    speed = input(f"播放倍速 [{updated.get('speed', 2.0)}]: ")
    updated["speed"] = parse_speed(speed, float(updated.get("speed", 2.0)))

    mute = input(f"静音播放 [{'Y' if updated.get('mute', True) else 'n'}]: ")
    updated["mute"] = parse_mute(mute, bool(updated.get("mute", True)))

    return updated


def run() -> dict:
    REAL_DATA_DIR.mkdir(parents=True, exist_ok=True)

    account = _read_json(ACCOUNT_PATH, default_account())
    settings = _read_json(SETTINGS_PATH, default_settings())

    if not ACCOUNT_PATH.exists():
        _write_json(ACCOUNT_PATH, account)
    if not SETTINGS_PATH.exists():
        _write_json(SETTINGS_PATH, settings)

    _print_summary(account, settings)
    if input("\n修改设置？(y/N): ").strip().lower() == "y":
        account = _edit_account(account)
        settings = _edit_settings(settings)
        _write_json(ACCOUNT_PATH, account)
        _write_json(SETTINGS_PATH, settings)
        print("设置已保存。")

    if not is_account_complete(account):
        raise SystemExit("账号、密码或课程URL为空，请先修改设置。")

    return {"account": account, "settings": settings}

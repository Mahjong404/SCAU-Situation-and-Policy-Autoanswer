# Startup Settings Design

## Overview

启动前交互式设置，允许用户确认/修改账号凭据和播放偏好后再执行主流程。

## Files

### New: `setup.py`

启动前设置模块。职责：读取配置 → 打印摘要 → 询问是否修改 → 逐项交互 → 写入文件。

```
setup.run() -> dict
```

返回 `{"account": {...}, "settings": {...}}`，传递给后续模块。

### New: `real_data/settings.json`

```json
{
  "browser": "msedge",
  "speed": 2.0,
  "mute": true
}
```

首次运行自动生成。`real_data/` 已 gitignored。

### Modified: `real_data/account.json`

不变，仍是 `{"phone": "...", "password": "...", "course": "..."}`。`setup.py` 读取和修改此文件。

### Modified Files

| File | Change |
|------|--------|
| `main.py` | 开头调用 `setup.run()`，将结果传入各模块 |
| `auto_sign_in.py` | `sign_in(context, account, browser)` — 参数化 |
| `auto_video.py` | `play_player()` 接受 `speed` 和 `mute` 参数 |

`auto_course.py`、`auto_answer.py` — 无需改动。

## Flow

```
setup.run()
  ├─ 读取 real_data/account.json + real_data/settings.json
  │   首次运行：生成默认空/默认设置
  ├─ 打印摘要（密码脱敏）
  │   账号: 138****1234
  │   课程: https://...
  │   浏览器: Edge | 倍速: 2x | 静音: 是
  ├─ "修改设置？(y/N)"
  │   ├─ N/回车 → 跳过，返回配置
  │   └─ y →
  │     0. phone: [当前: xxx] > 输入 / 回车保留
  │        password: [当前: ***] >
  │        url: [当前: xxx] >
  │     1. 浏览器 [1]Edge [2]Chrome [3]Chromium >
  │     2. 倍速 >
  │     3. 静音 Y/n >
  │     → 写入文件 → 返回配置
  └─ 返回
```

## Speed Compatibility

倍速设置失败时已有三级回退：菜单点击 → 检测 playbackRate → `el.playbackRate = N`。自定义倍速值沿用此链路，不受影响。

## Edge Cases

- `real_data/` 目录不存在 → 自动创建
- `account.json` 字段缺失 → 默认空字符串
- `settings.json` 不存在 → 生成默认值
- 账号为空时提醒先配置
- 倍速输入非数字 → 提示重新输入，默认 2

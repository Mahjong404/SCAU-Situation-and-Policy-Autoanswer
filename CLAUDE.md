# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

超星学习通《形势与政策》自动答题工具。Playwright + Edge 浏览器自动化，支持字体混淆解码、题库匹配、视频播放。

## Commands

```bash
# 安装依赖（只需 Playwright，已预装 fonttools）
pip install playwright

# 运行
python main.py
```

无需 `playwright install` — 使用系统 Edge 浏览器 (`channel="msedge"`)。

## Architecture

三模块管道：`auto_sign_in` → `auto_course` → `auto_answer`

**auto_sign_in.py** — 打开 Edge，注入 `mouseout` 拦截脚本防止超星弹窗检测，从 `real_data/account.json` 读取凭据登录。

**auto_course.py** — 视频自动播放模块：
- `complete_course_videos()` 遍历课程目录树，找到未完成的叶子节点
- 检测任务完成状态（`"已完成"` 标签 / `aria-label`）
- 调用 `auto_video.play_player()` 播放每个视频 iframe
- 支持多 tab 切换、最多 100 轮遍历上限

**auto_video.py** — 单视频播放器操作：点击 `.vjs-big-play-button`，hover 控件，等待 `.vjs-ended`。

**auto_answer.py** — 核心模块：
- 进入三层嵌套 iframe，提取 base64 TTF 字体 → `chaoxing_solution_of_font_confusion/glyfSearch.py` 解码
- 遍历 `.TiMu` 题目块，`text_content()` 取题干文本
- `_normalize()` 去题号/题型标签/空白/统一括号
- `_match_question()` 先精确匹配，失败则 `SequenceMatcher` 模糊匹配（阈值 0.92）
- 选项匹配同样走模糊：`_best_match()` 精确 → `SequenceMatcher`≥0.85
- 多选题全部选项逐一点击；单/判题点击第一个匹配项
- 末尾点击 iframe 内 `#tempsave` 保存

## Key details

- **凭据**: `real_data/account.json`（gitignored），模板在 `data/account.json`
- **题库**: `data/questions.json`，格式 `{"type": "单选题|多选题|判断题", "question": "...", "options": [...], "answer": "A"|"AB"|"√"|"X"}`
- **字体解码**: `chaoxing_solution_of_font_confusion/` 需要 CWD 为 `codes/` 才能加载 `.pkl` 文件，`auto_answer.py` 在 import 时临时切换 CWD
- **模糊匹配日志**: 输出到 `fuzzy_matches.txt`（gitignored），供核验
- **已知问题**: 字体解码 "域" 有时错译为 "互"，通过选项级模糊匹配（0.85 阈值）兜底

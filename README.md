# SCAU《形势与政策》课程自动化

> **开发中** · 当前提供命令行脚本和按学期整理的题库。

面向超星学习通《形势与政策》课程，使用 Python 和 Playwright 处理视频和答题。另有独立脚本用于整理题库资料和复核 OCR 结果。

## 运行现有脚本

建议使用 Windows、Python 3.12+ 和已安装的 Microsoft Edge。在仓库根目录运行：

```powershell
python -m pip install playwright fonttools
python main.py
```

首次运行会创建 `real_data/account.json` 和 `real_data/settings.json`。在启动提示中输入 `y`，填写学习通账号、密码和课程链接。浏览器默认选 Edge，也可以选已安装的 Chrome，或在运行 `python -m playwright install chromium` 后选择 Chromium。视频默认以 2 倍速静音播放，启动时可调整。请将真实账号和课程链接留在 Git 忽略的 `real_data/` 中。

脚本先遍历待办视频，再尝试使用本地题库填写当前页面的单选、多选和判断题。遇到题干未匹配时，答题流程会退出。页面提供「暂时保存」按钮时，脚本会尝试点击，请在页面核对填写与暂存结果。

## 按学期使用题库

| 学期 | 可用于脚本的完整题目 | 数据 |
| --- | ---: | --- |
| 2025—2026 学年第二学期 | 60 | [完整题库](question%20bank/2025-2026-2/questions.json) |
| 2026—2027 学年第一学期 | 69 | [完整题库](question%20bank/2026-2027-1/questions.json) · [70 题答案汇总](question%20bank/2026-2027-1/answers.json) |

2026—2027 学年第一学期有 1 道题因题干遮挡待复核，答案收录于汇总。题库文件包含题型、题干、选项和答案，脚本固定读取 `data/questions.json`。请按实际课程学期选择完整题库。例如，切换到 2026—2027 学年第一学期：

```powershell
Copy-Item 'data/questions.json' 'data/questions.backup.json'
Copy-Item 'question bank/2026-2027-1/questions.json' 'data/questions.json' -Force
```

资料采集、OCR、人工复核和题库导出的说明见[题库维护文档](question%20bank/README.md)及[学期索引](question%20bank/index.json)。

## 开发计划

1. **选课与学期选择**。启动时选择课程和学期，直接加载对应题库，并预览待办任务和当前测验的匹配情况。
2. **运行状态与恢复**。按章节区分视频、测验和锁定状态，输出运行回执和故障原因，支持从中断处继续。
3. **题库维护**。把资料导入、OCR、去重、冲突复核和导出串成统一入口。
4. **评估与《美学原理》项目整合**。验证共用学习通运行流程的可行性，分别维护课程和学期题库，再评估图形界面和 Windows 分发。

## 鸣谢

感谢 **TellMeYourWish** 提供超星学习通混淆字体的映射与解码实现。 [chaoxing_solution_of_font_confusion](https://github.com/TellMeYourWish/chaoxing_solution_of_font_confusion)

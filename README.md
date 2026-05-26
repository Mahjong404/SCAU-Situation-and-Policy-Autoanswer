# SCAU 形势与政策 自动答题

超星学习通《形势与政策》课程自动答题脚本，基于 Playwright + Edge 浏览器。

## 环境要求

- Windows 系统（Edge 浏览器已预装）
- Python 3.12+
- Playwright

```bash
pip install playwright
```

## 设置方法

1. 在 `real_data/` 下创建 `account.json`，格式参考 `data/account.json`：

```json
{
  "phone": "your_phone_number",
  "password": "your_password",
  "course": "your_course_url"
}
```

2. 题库文件为 `data/questions.json`，格式参考已有条目。

## 使用

```bash
cd codes
python main.py
```

脚本将自动登录（如未登录）、进入答题页面、逐题匹配题库并点击正确答案，完成后自动点击"暂时保存"。

## 功能

- 自动登录超星学习通
- 字体混淆解码（chaoxing_solution_of_font_confusion）
- 题目模糊匹配（应对页面与题库文字细微差异）
- 单选题 / 多选题 / 判断题全部支持
- 模糊匹配题目输出至 `fuzzy_matches.txt` 供核验
- 答题完成自动点击"暂时保存"

## 鸣谢

- 字体解码：https://github.com/TellMeYourWish/chaoxing_solution_of_font_confusion
- 原始 Selenium 版本参考

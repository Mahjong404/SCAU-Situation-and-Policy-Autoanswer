# SCAU 形势与政策 自动答题

超星学习通《形势与政策》课程自动化工具，基于 Playwright + Edge 浏览器。
支持视频自动播放和题目自动作答。

## 环境要求

- Windows 系统（Edge 浏览器已预装）
- Python 3.12+

```bash
pip install playwright
```

无需 `playwright install`，使用系统 Edge 浏览器 (`channel="msedge"`)。

## 设置方法

1. 在 `real_data/` 下创建 `account.json`，格式参考 `data/account.json`：

```json
{
  "phone": "your_phone_number",
  "password": "your_password",
  "course": "your_course_url"
}
```

2. 题库文件 `data/questions.json`，格式：

```json
{
  "type": "单选题|多选题|判断题",
  "question": "题目文本",
  "options": ["选项A", "选项B", ...],
  "answer": "A" | "AB" | "√" | "X"
}
```

## 使用

```bash
python main.py
```

## 流程

三模块管道依次执行：

```
auto_sign_in → auto_course → auto_answer
```

### auto_sign_in — 自动登录

打开 Edge，注入脚本防止超星弹窗检测，从 `real_data/account.json` 读取凭据登录。

### auto_course — 视频自动播放

- 遍历课程目录树，定位未完成的叶子节点
- 按顺序播放每个视频 iframe，自动设置 2 倍速 + 静音
- 关闭"记笔记"提示弹窗，避免遮挡控制按钮
- 检测视频结束状态后进入下一个，支持多 tab 切换
- 最多 100 轮遍历上限，全部完成自动退出

### auto_answer — 自动答题

- 进入三层嵌套 iframe 定位题目区域
- 提取 base64 TTF 字体解码混淆文字
- 题目匹配：先精确匹配，失败则模糊匹配（阈值 0.92）
- 选项匹配：精确 → 模糊（阈值 0.85）
- 支持单选题、多选题、判断题，完成后自动保存

## 鸣谢

- 字体解码：[chaoxing_solution_of_font_confusion](https://github.com/TellMeYourWish/chaoxing_solution_of_font_confusion)

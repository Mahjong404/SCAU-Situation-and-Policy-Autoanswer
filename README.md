# SCAU 形势与政策 自动答题

超星学习通《形势与政策》课程自动化工具，基于 Playwright 浏览器自动化。
支持视频自动播放、题目自动作答，启动前可交互式修改设置。

## 环境要求

- Windows 系统（Edge 浏览器已预装）
- Python 3.12+

```bash
pip install playwright
```

无需 `playwright install`，默认使用系统 Edge 浏览器 (`channel="msedge"`)。

## 使用

```bash
python main.py
```

首次运行会自动生成 `real_data/account.json` 和 `real_data/settings.json`（模板参考 `data/` 下同名文件）。

启动时打印当前设置摘要，询问是否修改：

```
当前设置：
  账号: (空)
  密码: (空)
  课程URL: (空)
  浏览器: msedge
  倍速: 2.0x
  静音: 是

修改设置？(y/N):
```

回车跳过直接执行，输入 `y` 逐项修改：

| 项目 | 说明 |
|------|------|
| 账号/密码/URL | 超星学习通登录凭据和目标课程链接 |
| 浏览器 | Edge / Chrome / Chromium |
| 播放倍速 | 默认 2x，课程锁定倍速时自动回退 |
| 静音播放 | 默认静音 |

账号未填写完整时程序退出并提示先配置。

## 题库

`data/questions.json`，格式：

```json
{
  "type": "单选题|多选题|判断题",
  "question": "题目文本",
  "options": ["选项A", "选项B", ...],
  "answer": "A" | "AB" | "√" | "X"
}
```

## 流程

四模块管道依次执行：

```
setup → auto_sign_in → auto_course → auto_answer
```

### setup — 启动前设置

交互式确认/修改账号凭据、浏览器、倍速、静音等设置。详见上方「使用」部分。

### auto_sign_in — 自动登录

注入脚本防止超星弹窗检测，根据设置选用的浏览器和凭据登录。

### auto_course — 视频自动播放

- 遍历课程目录树，定位未完成的叶子节点
- 按顺序播放每个视频 iframe，自动设置倍速 + 静音
- 倍速设置三级回退：菜单点击 → 检测 playbackRate → 直接赋值
- 关闭"记笔记"提示弹窗，避免遮挡控制按钮
- 检测视频结束状态后进入下一个
- 最多 100 轮遍历上限，全部完成自动退出

### auto_answer — 自动答题

- 进入三层嵌套 iframe 定位题目区域
- 提取 base64 TTF 字体解码混淆文字
- 题目匹配：先精确匹配，失败则模糊匹配（阈值 0.92）
- 选项匹配：精确 → 模糊（阈值 0.85）
- 支持单选题、多选题、判断题，完成后自动保存

## 鸣谢

- 字体解码：[chaoxing_solution_of_font_confusion](https://github.com/TellMeYourWish/chaoxing_solution_of_font_confusion)

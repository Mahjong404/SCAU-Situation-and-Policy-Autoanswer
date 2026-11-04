# 规范题库

公开内容仅含题库、校验摘要及处理脚本；截图、笔记链接、原始OCR及来源记录保留本地。

2025-2026-2：60题完整。2026-2027-1：69题完整，另有1题题干遮挡待复核；answers.json包含70题答案。第43题答案ABCD，未猜补遮挡文字。

题目字段：type、question、options（带A.前缀）、answer。单选一个字母，多选按序且无重复，判断使用√/X。

## 本地使用

需要Python、Windows PowerShell 5.1和中文OCR语言包。在仓库根目录执行：

```powershell
python -m pip install -r scripts/bank_requirements.txt
Copy-Item scripts/xhs_links.example.txt scripts/xhs_links.txt
node "$env:USERPROFILE\.agents\skills\web-access\scripts\check-deps.mjs"
python scripts/xhs_collect.py --term 2026-2027-1 --input scripts/xhs_links.txt
python scripts/bank_build.py --term 2026-2027-1 --ocr
python -m unittest discover -s scripts -p 'test_bank_tools.py' -v
```

分享链接放在本地xhs_links.txt。采集器使用web-access代理和Edge的9222端口。重建需要自行提供图片并复核，规范题库可以直接读取。原图复核条目放在本地transcriptions目录后再重建；冲突和未解决内容隔离。

## 可选LLM

复制scripts/llm.example.json为scripts/llm.local.json，填写完整HTTPS endpoint（含/chat/completions）、model、api_key，或使用QUESTION_BANK_LLM_API_KEY环境变量。

```powershell
python scripts/bank_llm.py --config scripts/llm.local.json --input local-ocr.json --image local-image.png --output local-suggestions.json
```

输出经过格式校验后保存为建议，不自动覆盖题库，不能从资料恢复的内容继续待复核。参考[OpenAI官方接口文档](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)。本次未调用付费API或启动自动答题，现有答题代码保持不变。后续再增加复核界面、答题入口及Windows打包。

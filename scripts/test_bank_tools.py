"""Meaningful offline checks: pasted links, schema rejection, OCR parsing, conflicts."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from bank_build import build, parse_images, validate
from bank_llm import repair
from xhs_collect import extract_urls


class BankTests(unittest.TestCase):
    def setUp(self):
        self.question = {"type":"单选题","question":"这是一道用于校验的题目()。",
            "options":["A.甲","B.乙","C.丙","D.丁"],"answer":"B"}

    def test_share_url_preserves_access_query(self):
        text = r'57 【标题】 😆 https\://www\.xiaohongshu.com/discovery/item/0123456789abcdef01234567?xsec_token=ABC=&xsec_source=pc_share'
        url = extract_urls(text)[0]
        self.assertIn("/discovery/item/",url)
        self.assertTrue(url.endswith("xsec_token=ABC=&xsec_source=pc_share"))
        self.assertEqual(len(extract_urls(f"[{url}]({url})")),1)
        self.assertEqual(extract_urls("https://xhslink.com/a/abc"),["https://xhslink.com/a/abc"])

    def test_invalid_answer_and_missing_option_rejected(self):
        self.assertFalse(validate(self.question))
        for change in ({"answer":"AB"},{"answer":"E"},{"options":["A.甲"]},{"answer":["B"]}):
            self.assertTrue(validate(self.question | change))
        self.assertTrue(validate([]))
        self.assertFalse(validate(self.question | {"type":"判断题","options":[],"answer":"√"}))

    def test_ocr_parser_drops_ui_not_options(self):
        lines=["7·[单选题]","这是一道用于校验的题目(",")。","写笔记",
               "A·甲","B·乙","C·丙","D·丁","我的答案:B","得分:1·4分"]
        images=[{"note_id":"note","image":"images/note/001.webp","lines":[{"text":s} for s in lines]}]
        candidate=parse_images(images)[0]
        self.assertEqual(candidate["question"],self.question["question"])
        self.assertEqual(candidate["source_number"],7)
        self.assertEqual(candidate["options"],self.question["options"])

    def test_duplicate_conflict_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory)/"2026-2027-1"
            (folder/"transcriptions").mkdir(parents=True)
            first=self.question | {"source_image":"image1","source_number":1}
            second=copy.deepcopy(first) | {"answer":"C","source_image":"image2"}
            (folder/"transcriptions/source.json").write_text(json.dumps([first,second]),encoding="utf-8")
            build(folder,[])
            self.assertEqual(json.loads((folder/"questions.json").read_text()),[])
            self.assertEqual(json.loads((folder/"validation.json").read_text())["conflicts"],1)

    def test_no_key_never_calls_network(self):
        with self.assertRaises(ValueError):
            repair({"endpoint":"","model":"","api_key_env":"UNSET_BANK_TEST_KEY"},{})


if __name__ == "__main__":
    unittest.main()

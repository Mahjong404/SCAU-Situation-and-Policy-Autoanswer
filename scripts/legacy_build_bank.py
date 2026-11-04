"""Archive the existing text bank with independently extracted image answer evidence."""
import hashlib
import json
import re
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BANK = ROOT / "question bank" / "2025-2026-2"


def dump(name, value):
    (BANK / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def comparable(value):
    return "".join(c for c in unicodedata.normalize("NFKC", value) if c.isalnum())


def main():
    text_bank = ROOT / "codes/data/questions.json"
    if not text_bank.exists():
        text_bank = ROOT / "data/questions.json"
    questions = json.loads(text_bank.read_text(encoding="utf-8"))
    blocks = []
    images = []
    sources = [path for path in (BANK / "ocr").glob("*.json") if re.search(r"_(\d+)_", path.name)]
    for source in sorted(sources, key=lambda x: int(re.search(r"_(\d+)_", x.name)[1])):
        result = json.loads(source.read_text(encoding="utf-8"))
        lines = [re.sub(r"\s+", "", line["text"]) for line in result["lines"]]
        starts = [i for i, line in enumerate(lines) if re.search(r"单选题|多选题|判断题", line)]
        for start, end in zip(starts, starts[1:] + [len(lines)]):
            text = "\n".join(lines[start:end])
            answer_match = re.search(r"我的答案[：:·]?([A-D对错]+)", text)
            if not answer_match:
                raise ValueError(f"Missing image answer in {source.name}: {text}")
            answer = answer_match[1].replace("对", "√").replace("错", "X")
            blocks.append({"image": "images/" + result["image"], "ocr": "ocr/" + source.name,
                           "text": text, "answer": answer,
                           "type": re.search(r"单选题|多选题|判断题", text)[0]})
        image_path = BANK / "images" / result["image"]
        images.append({"path": "images/" + image_path.name, "sha256": hashlib.sha256(image_path.read_bytes()).hexdigest(),
                       "bytes": image_path.stat().st_size, "width": result["width"], "height": result["height"]})
    if len(blocks) != len(questions):
        raise ValueError(f"OCR {len(blocks)} blocks differs from existing {len(questions)} questions")
    records = []
    errors = []
    seen = {}
    duplicates = []
    for number, (question, evidence) in enumerate(zip(questions, blocks), 1):
        q = {key: question[key] for key in ("type", "question", "options", "answer")}
        # This character is visible in image 11 and was dropped in the pre-existing text.
        if number == 33:
            q["question"] = q["question"].replace("建立健全体推进", "建立健全一体推进")
        q["answer"] = "".join(sorted(set(q["answer"]))) if q["type"] != "判断题" else q["answer"]
        labels = []
        for option in q["options"]:
            match = re.match(r"^([A-D])[.、．](.+)$", option)
            if not match:
                errors.append({"question": number, "error": "invalid_option", "value": option})
            else:
                labels.append(match[1])
        if q["type"] == "判断题":
            valid_answer = q["answer"] in ("√", "X")
        else:
            valid_answer = bool(q["answer"]) and all(letter in labels for letter in q["answer"])
            valid_answer = valid_answer and (len(q["answer"]) == 1 if q["type"] == "单选题" else len(q["answer"]) >= 2)
        if not valid_answer:
            errors.append({"question": number, "error": "invalid_answer"})
        if q["type"] != evidence["type"] or q["answer"] != evidence["answer"]:
            errors.append({"question": number, "error": "ocr_answer_or_type_mismatch", "ocr_answer": evidence["answer"]})
        body = evidence["text"].split("我的答案", 1)[0]
        key = comparable(q["type"] + q["question"])
        if key in seen:
            duplicates.append({"question": number, "duplicates": seen[key]})
            if q != records[seen[key] - 1]["question"]:
                errors.append({"question": number, "error": "duplicate_conflict"})
            continue
        seen[key] = number
        score = SequenceMatcher(None, comparable(q["question"]), comparable(body)).ratio()
        records.append({"id": f"2025-2026-2-{number:03}", "source_question_number": number,
                        "question": q, "source": {"image": evidence["image"], "ocr": evidence["ocr"],
                        "text_origin": "codes/data/questions.json (pre-existing transcription)",
                        "answer_origin": "Windows.Media.Ocr extracted 我的答案; matches pre-existing answer"},
                        "verification": {"type_matches_ocr": q["type"] == evidence["type"],
                        "answer_matches_ocr": q["answer"] == evidence["answer"],
                        "ocr_block_text_similarity": round(score, 4),
                        "text_policy": "Retain existing transcription; OCR contains spaces, missing characters and interleaved UI text.",
                        "source_correction": "补回‘建立健全一体推进’中的‘一’，依据图片11与OCR。" if number == 33 else None}})
    dump("questions.json", [record["question"] for record in records])
    dump("records.json", records)
    dump("images.json", {"term": "2025-2026-2", "migrated_from": "2526_2", "source_note_title": "🌸华农26年第二学期形策答案（共60题）", "source_url": None, "images": images})
    dump("ocr/blocks.json", blocks)
    validation = {"term": "2025-2026-2", "image_count": len(images), "ocr_image_count": len(images),
                  "ocr_question_blocks": len(blocks), "question_count": len(records),
                  "type_counts": dict(Counter(r["question"]["type"] for r in records)),
                  "ocr_answer_matches": sum(r["verification"]["answer_matches_ocr"] for r in records),
                  "duplicates_removed": duplicates, "errors": errors, "format_valid": not errors,
                  "answer_semantics_verified": False,
                  "limitations": ["原始笔记URL未存于旧目录，保留原图文件名作为来源。", "题干和选项沿用现存转录，OCR核对题型与图片中我的答案。", "格式和图片答案一致性校验不构成对答案事实正确性的验证。"]}
    dump("validation.json", validation)
    print(json.dumps(validation, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

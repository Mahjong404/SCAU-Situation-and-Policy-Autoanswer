"""Offline OCR, normalization and conservative question-bank validation."""
import argparse
import hashlib
import json
import re
import subprocess
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def clean(text):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text))


def ocr(folder):
    tiles = folder / "ocr-input"
    tiles.mkdir(exist_ok=True)
    for path in (folder / "images").rglob("*.*"):
        with Image.open(path) as source:
            image = source.convert("RGB")
            for k, y in enumerate(range(0, image.height, 2100)):
                dest = tiles / f"{path.parent.name}_{path.stem}_{k:02}.png"
                if not dest.exists():
                    image.crop((0, max(0, y-80), image.width, min(image.height, y+2180))).save(dest)
    subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
        str(ROOT / "scripts/legacy_windows_ocr.ps1"), "-InputDirectory", str(tiles),
        "-OutputDirectory", str(folder / "ocr-tiles")], check=True)


def merge_ocr(folder):
    grouped = {}
    for path in sorted((folder / "ocr-tiles").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        note, image, tile = path.stem.split("_")
        offset = max(0, int(tile)*2100-80)
        for line in data["lines"]:
            words = line["words"]
            if not words:
                continue
            top = min(w["y"] for w in words) + offset
            bottom = max(w["y"]+w["height"] for w in words) + offset
            # Overlap protects text at crop boundaries. Keep each line in its central tile.
            center = (top+bottom)/2
            if not int(tile)*2100 <= center < (int(tile)+1)*2100:
                continue
            grouped.setdefault((note, image), []).append({"text":clean(line["text"]),
                "y":round(top, 2), "x":min(w["x"] for w in words),
                "tile":path.relative_to(folder).as_posix()})
    images = []
    for (note, image), lines in sorted(grouped.items()):
        lines.sort(key=lambda line:(line["y"], line["x"]))
        item = {"note_id":note, "image":f"images/{note}/{image}.webp", "lines":lines}
        dump(folder / "ocr" / f"{note}_{image}.json", item)
        (folder / "ocr" / f"{note}_{image}.txt").write_text("\n".join(l["text"] for l in lines), encoding="utf-8")
        images.append(item)
    return images


def parse_images(images):
    candidates = []
    for image in images:
        lines = [line["text"] for line in image["lines"]]
        starts = [i for i, line in enumerate(lines) if re.search(r"\[(单选题|多选题|判断题)\]", line)]
        blocks, anchors = [], []
        for index, (start, end) in enumerate(zip(starts, starts[1:] + [len(lines)])):
            block = lines[start:end]
            header = re.search(r"^(\d+)[·.、]?\[", block[0])
            number = int(header[1]) if header else None
            if len(block) > 1 and re.fullmatch(r"\d+[·.、]?", block[1]):
                number = int(re.match(r"\d+", block.pop(1))[0])
            if number:
                anchors.append(number-index)
            blocks.append(block)
        base = Counter(anchors).most_common(1)[0][0] if anchors else None
        for index, block in enumerate(blocks):
            kind = re.search(r"单选题|多选题|判断题", block[0])[0]
            question, options, answer = [], [], ""
            found_answer = False
            for line in block[1:]:
                match = re.search(r"我的答案[:：·]?([A-D对错√X×]+)", line)
                if match:
                    answer = match[1].replace("对", "√").replace("错", "X").replace("×", "X")
                    found_answer = True
                if found_answer or re.search(r"得分|写笔记|我的安|期末考试|讨论|KB/|^\d{1,2}:\d|^木[·.]|^·日", line):
                    continue
                if re.fullmatch(r"\d+[·.、]?", line):
                    continue
                option = re.match(r"^([A-D])[·.、](.*)", line)
                if option:
                    options.append(option[1] + "." + option[2])
                elif options:
                    options[-1] += line
                else:
                    question.append(line)
            text = "".join(question)
            if text.endswith("("):
                text += ")"
            candidates.append({"type":kind,"question":text,"options":options,"answer":answer,
                "source_image":image["image"],"source_number":base+index if base else None,
                "note_id":image["note_id"],"raw_lines":block})
    return candidates


def validate(q):
    if not isinstance(q, dict):
        return ["question_must_be_object"]
    errors = []
    if q.get("type") not in {"单选题", "多选题", "判断题"}:
        errors.append("invalid_type")
    if not isinstance(q.get("question"), str) or len(q["question"]) < 6:
        errors.append("missing_question")
    options = q.get("options", [])
    if not isinstance(options, list) or any(not isinstance(o, str) for o in options):
        return errors + ["options_must_be_string_array"]
    labels = []
    for option in options:
        match = re.fullmatch(r"([A-D])\.(.+)", option)
        if match:
            labels.append(match[1])
        else:
            errors.append("invalid_option")
    answer = q.get("answer", "")
    if not isinstance(answer, str):
        return errors + ["answer_must_be_string"]
    if q.get("type") == "判断题":
        if answer not in {"√", "X"}:
            errors.append("invalid_judgement")
    else:
        if labels != ["A", "B", "C", "D"]:
            errors.append("incomplete_options")
        if not answer or answer != "".join(sorted(set(answer))) or any(c not in labels for c in answer):
            errors.append("invalid_answer")
        if q.get("type") == "单选题" and len(answer) != 1:
            errors.append("single_answer_required")
        if q.get("type") == "多选题" and len(answer) < 2:
            errors.append("multiple_answers_required")
    return errors


def key(text):
    return "".join(c for c in clean(text) if c.isalnum())


def build(folder, images):
    candidates = parse_images(images)
    dump(folder / "ocr/candidates.json", candidates)
    # Human/assistant visual corrections remain separate and auditable; never overwrite raw OCR.
    transcribed = []
    for path in sorted((folder / "transcriptions").glob("*.json")):
        transcribed.extend(json.loads(path.read_text(encoding="utf-8-sig")))
    primary = sorted(transcribed, key=lambda q:q.get("source_number", 0)) if transcribed else candidates
    records, pending, duplicates, conflicts = [], [], [], []
    seen = {}
    for candidate in primary:
        q = {field:candidate.get(field, [] if field == "options" else "") for field in ("type", "question", "options", "answer")}
        errors = validate(q)
        if errors or candidate.get("review"):
            pending.append({"candidate":candidate,"errors":errors,"review":candidate.get("review")})
            continue
        identity = (q["type"], key(q["question"]))
        if identity in seen:
            previous = records[seen[identity]]
            same = {key(o[2:]) for o in previous["question"]["options"]} == {key(o[2:]) for o in q["options"]}
            def selected(item):
                return {key(o[2:]) for o in item["options"] if o[0] in item["answer"]} if item["options"] else item["answer"]
            if same and selected(q) == selected(previous["question"]):
                duplicates.append({"source":candidate.get("source_image"),"record":previous["id"]})
                previous["sources"].append(candidate)
            else:
                conflicts.append({"candidate":candidate,"record":previous["id"]})
            continue
        seen[identity] = len(records)
        number = candidate.get("source_number") or len(records)+1
        records.append({"id":f"{folder.name}-{number:03}","question":q,"sources":[candidate]})
    # Compare the second note conservatively. Number alone is never sufficient evidence.
    comparisons = []
    pending_records = [{"id":f"{folder.name}-{item['candidate']['source_number']:03}",
        "question":item["candidate"],"sources":[item["candidate"]]} for item in pending
        if item["candidate"].get("source_number")]
    comparison_pool = records + pending_records
    for candidate in candidates:
        ranked = sorted(((SequenceMatcher(None,key(candidate["question"]),key(r["question"]["question"])).ratio(),r) for r in comparison_pool), key=lambda pair:pair[0], reverse=True)
        if not ranked or ranked[0][0] < 0.75 or ranked[0][1]["question"]["type"] != candidate["type"]:
            comparisons.append({"source":candidate,"status":"unmatched_requires_review"})
            continue
        score, record = ranked[0]
        answer = candidate["answer"]
        # Check displayed option text/order before comparing letters; small OCR omissions allowed.
        expected = record["question"]
        option_scores = [SequenceMatcher(None,key(a),key(b)).ratio() for a,b in zip(candidate["options"],expected["options"])]
        options_match = expected["type"] == "判断题" or (len(option_scores)==4 and min(option_scores)>=0.70)
        status = "answer_agrees" if answer and answer == expected["answer"] and options_match else "requires_review"
        if answer and options_match and answer != expected["answer"]:
            status = "answer_conflict"
            conflicts.append({"source":candidate,"record":record["id"]})
        comparisons.append({"source_image":candidate["source_image"],"source_number":candidate["source_number"],
            "record":record["id"],"question_similarity":round(score,4),"option_similarities":option_scores,
            "ocr_answer":answer,"status":status})
        record.setdefault("ocr_evidence", []).append(comparisons[-1])
    conflicted_ids = {conflict["record"] for conflict in conflicts}
    ready = [record for record in records if record["id"] not in conflicted_ids]
    dump(folder / "records.json", records)
    dump(folder / "questions.json", [record["question"] for record in ready])
    dump(folder / "answers.json", [{"id":record["id"],
        "source_number":record["sources"][0].get("source_number"),"type":record["question"]["type"],
        "answer":record["question"]["answer"],"question_status":"needs_review" if record in pending_records or record["id"] in conflicted_ids else "ready",
        "source_image":record["sources"][0].get("source_image")}
        for record in sorted(comparison_pool,key=lambda r:r["id"])])
    groups = [{"id":record["id"],"occurrences":record.get("ocr_evidence", [])} for record in comparison_pool]
    dump(folder / "duplicates.json", {"groups":groups,
        "occurrences":sum(len(g["occurrences"]) for g in groups),"unique_questions":len(groups),
        "duplicate_occurrences":sum(max(0,len(g["occurrences"])-1) for g in groups)})
    dump(folder / "review.json", {"pending":pending,"conflicts":conflicts,
        "ocr_comparisons":comparisons})
    source_files = list((folder / "sources").glob("*.json"))
    summary = {"term":folder.name,"image_count":len(images),"source_count":len(source_files),
        "raw_ocr_candidates":len(candidates),"transcribed_candidates":len(transcribed),
        "question_count":len(ready),"type_counts":dict(Counter(r["question"]["type"] for r in ready)),
        "format_valid":all(not validate(r["question"]) for r in ready),"pending_count":len(pending),
        "conflicts":len(conflicts),"duplicates_removed":duplicates,
        "ocr_comparison_counts":dict(Counter(c["status"] for c in comparisons)),
        "answer_semantics_verified":False}
    summary.update(unique_questions_including_pending=len(comparison_pool),
        duplicate_occurrences=sum(max(0,len(g["occurrences"])-1) for g in groups))
    dump(folder / "validation.json", summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--term", required=True)
    parser.add_argument("--ocr", action="store_true")
    args = parser.parse_args()
    folder = ROOT / "question bank" / args.term
    if args.ocr:
        ocr(folder)
    images = merge_ocr(folder)
    build(folder, images)

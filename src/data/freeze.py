"""Kiểm tra Dataset v1 rồi ghi data/dataset_manifest.json (D06, mục 9.2 và 9.3 hướng dẫn TV1).

Các tiêu chí tự kiểm được ở mục 9.2 chạy ở đây; 2 tiêu chí cần người (đã tính kappa, nhóm đã duyệt
báo cáo) thì chỉ kiểm có file hay chưa và quyết định review_status:
    "draft"  : còn câu hỏi source=generated chưa duyệt hoặc chưa có label_agreement.md
    "frozen" : chạy với --final, mọi kiểm tra pass và không còn cảnh báo

Chạy từ gốc repo:  python -m src.data.freeze            (ghi manifest bản nháp)
                   python -m src.data.freeze --final    (chốt v1; lỗi hay cảnh báo nào cũng dừng)
"""
import csv
import hashlib
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone

import yaml

from src.data.split import ROOT, SPLITS

TYPES = {"direct", "paraphrase", "underspecified", "multi_intent", "confusable", "out_of_scope", "unsupported"}
NO_QRELS = {"out_of_scope", "unsupported"}


def read_csv(rel):
    with open(ROOT / rel, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def sha256(rel):
    # bỏ \r trước khi băm: Git trên Windows (autocrlf) checkout ra CRLF, máy nào băm cũng phải ra cùng 1 mã
    return hashlib.sha256((ROOT / rel).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def git(*args):
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def run_checks():
    """Trả về (errors, warnings, info). errors = vi phạm tiêu chí freeze."""
    err, warn = [], []
    chunks = [json.loads(l) for l in open(ROOT / "data/processed/chunks.jsonl", encoding="utf-8")]
    ids = [c["chunk_id"] for c in chunks]
    questions = read_csv("data/labels/questions.csv")
    qrels = read_csv("data/labels/qrels.csv")
    sources = read_csv("data/raw/source_list.csv")

    # 1. File gốc trong data/raw không bị sửa (so với commit hiện tại)
    changed = git("status", "--porcelain", "--", "data/raw")
    if changed is None:
        warn.append("không chạy được git, bỏ qua kiểm tra data/raw")
    else:
        modified = [l[3:] for l in changed.splitlines() if l[:2].strip() in {"M", "D", "MM", "AM"} and not l.startswith("??")]
        if modified:
            err.append(f"file trong data/raw bị sửa so với commit: {modified}")

    # 2. Văn bản có nguồn, ngày tải, tình trạng hiệu lực
    for s in sources:
        miss = [k for k in ("url", "accessed_at", "status") if not (s.get(k) or "").strip()]
        if miss:
            err.append(f"source_list: {s['doc_id']} thiếu {miss}")

    # 3. chunk_id duy nhất, không rỗng
    dup = [i for i, n in Counter(ids).items() if n > 1]
    if dup:
        err.append(f"chunk_id trùng: {dup[:5]}")
    if any(not c["chunk_text"].strip() for c in chunks):
        err.append("có chunk rỗng")

    # 4. questions.csv hợp lệ
    qids = [q["question_id"] for q in questions]
    if len(set(qids)) != len(qids):
        err.append(f"question_id trùng: {[q for q, n in Counter(qids).items() if n > 1]}")
    bad_type = {q["question_id"]: q["type"] for q in questions if q["type"] not in TYPES}
    if bad_type:
        err.append(f"type không hợp lệ: {bad_type}")
    missing_types = TYPES - {q["type"] for q in questions}
    if missing_types:
        err.append(f"chưa có loại câu hỏi: {sorted(missing_types)}")
    texts = Counter(q["question"].strip().lower() for q in questions)
    if any(n > 1 for n in texts.values()):
        warn.append(f"câu hỏi trùng nguyên văn: {[t for t, n in texts.items() if n > 1][:3]}")

    # 5. qrels: chunk tồn tại, relevance 1/2, câu hợp lệ có >= 1 dòng, out_of_scope/unsupported không có dòng
    idset, qtype = set(ids), {q["question_id"]: q["type"] for q in questions}
    for r in qrels:
        if r["question_id"] not in qtype:
            err.append(f"qrels trỏ tới câu không có: {r['question_id']}")
        if r["chunk_id"] not in idset:
            err.append(f"qrels trỏ tới chunk không có: {r['question_id']} → {r['chunk_id']}")
        if r["relevance"] not in {"1", "2"}:
            err.append(f"relevance phải là 1 hoặc 2: {r}")
    has_qrel = Counter(r["question_id"] for r in qrels)
    for q, t in qtype.items():
        if t in NO_QRELS and has_qrel[q]:
            err.append(f"{q} ({t}) không được có qrels")
        if t not in NO_QRELS and not has_qrel[q]:
            err.append(f"{q} ({t}) chưa có qrels")
    pairs = Counter((r["question_id"], r["chunk_id"]) for r in qrels)
    if any(n > 1 for n in pairs.values()):
        err.append("qrels có cặp (question_id, chunk_id) lặp")

    # 6. Split theo nhóm: không nhóm nào ở 2 tập, nhóm nào cũng được chia, tập nào cũng đủ 7 loại
    split_of = {}
    for s in SPLITS:
        p = ROOT / f"data/splits/{s}_qgroups.csv"
        if not p.exists():
            err.append(f"thiếu {p.relative_to(ROOT)} (chạy python -m src.data.split)")
            continue
        for row in read_csv(p.relative_to(ROOT)):
            g = row["question_group_id"]
            if g in split_of:
                err.append(f"nhóm {g} nằm ở cả {split_of[g]} và {s}")
            split_of[g] = s
    groups = {q["question_group_id"] for q in questions}
    if split_of and groups - set(split_of):
        err.append(f"nhóm chưa được chia: {sorted(groups - set(split_of))[:5]}")
    for s in SPLITS:
        got = {q["type"] for q in questions if split_of.get(q["question_group_id"]) == s}
        if split_of and TYPES - got:
            warn.append(f"tập {s} thiếu loại {sorted(TYPES - got)}")

    # 7. Tiêu chí cần người: duyệt câu generated, kappa, báo cáo chất lượng
    n_gen = sum(q["source"] == "generated" for q in questions)
    if n_gen:
        warn.append(f"{n_gen} câu source=generated: người trong nhóm phải duyệt (mục 7.1.5), test nên ưu tiên câu người viết")
    if not (ROOT / "results/data_quality/label_agreement.md").exists():
        warn.append("chưa có results/data_quality/label_agreement.md (Cohen kappa, TV2 chủ trì)")
    if not (ROOT / "results/data_quality/corpus_report.md").exists():
        err.append("chưa có results/data_quality/corpus_report.md (chạy python -m src.data.corpus_report)")

    info = dict(chunks=chunks, questions=questions, sources=sources, split_of=split_of)
    return err, warn, info


def main(final=False):
    err, warn, info = run_checks()
    for e in err:
        print("LỖI     ", e)
    for w in warn:
        print("CẢNH BÁO", w)
    if err or (final and warn):
        sys.exit("Chưa freeze được: sửa các mục trên rồi chạy lại.")

    chunks, questions, split_of = info["chunks"], info["questions"], info["split_of"]
    seg = yaml.safe_load(open(ROOT / "configs/preprocessing.yaml", encoding="utf-8"))["segmenter"]
    seed = yaml.safe_load(open(ROOT / "configs/split.yaml", encoding="utf-8"))["random_seed"]
    manifest = dict(
        dataset_version="v1",
        domain="ho_tich",
        n_documents=len(info["sources"]),
        n_documents_chunked=len({c["doc_id"] for c in chunks}),
        n_chunks=len(chunks),
        n_questions=len(questions),
        n_question_groups=len({q["question_group_id"] for q in questions}),
        n_questions_by_type=dict(sorted(Counter(q["type"] for q in questions).items())),
        n_questions_by_split={s: sum(split_of.get(q["question_group_id"]) == s for q in questions) for s in SPLITS},
        chunks_sha256=sha256("data/processed/chunks.jsonl"),
        questions_sha256=sha256("data/labels/questions.csv"),
        qrels_sha256=sha256("data/labels/qrels.csv"),
        segmenter=f"{seg['name']} {seg['version']}",
        random_seed=seed,
        source_commit=git("rev-parse", "HEAD"),
        created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        review_status="frozen" if final else "draft",
        warnings=warn,
    )
    out = ROOT / "data/dataset_manifest.json"
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(f"Ghi {out.relative_to(ROOT)} (review_status={manifest['review_status']})")


if __name__ == "__main__":
    main(final="--final" in sys.argv)

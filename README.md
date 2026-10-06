# Hệ thống gợi ý câu trả lời cho câu hỏi hành chính

Đề tài 10, môn Xử lý ngôn ngữ tự nhiên. Hệ thống nhận câu hỏi của người dùng, tìm đoạn văn bản hoặc câu hỏi tương tự trong kho tài liệu, xếp hạng và trả lời bằng trích dẫn nguyên văn kèm nguồn. Trọng tâm là retrieval và question matching, không phải chatbot tạo sinh.

**Phạm vi mặc định:** lĩnh vực hộ tịch (khai sinh, kết hôn, khai tử, thay đổi và cải chính hộ tịch, nhận cha mẹ con, giám hộ, trích lục). Nhóm chốt trong [docs/scope.md](docs/scope.md).

## Pipeline

```
tài liệu gốc → làm sạch → chia đoạn → lập chỉ mục → truy hồi → xếp hạng lại → trả lời có trích dẫn
                                         │             │            │
                                   TF-IDF / BM25   bi-encoder   cross-encoder
                                    (baseline)     (SBERT)      (PhoBERT pair)
```

## Phân công

| | Vai trò | Phụ trách chính |
|---|---|---|
| TV1 | Dữ liệu và baseline | Phạm vi, thu thập, làm sạch, chunking, freeze Dataset v1, TF-IDF/BM25, hard negatives |
| TV2 | Bộ test và đánh giá | Guideline gán nhãn, điều phối gán nhãn chéo, kappa, split, script đánh giá chung, phân tích lỗi |
| TV3 | Truy hồi dense | SBERT bi-encoder, hybrid, câu hỏi tương tự |
| TV4 | Rerank và trả lời | Cross-encoder / PhoBERT pair, template trả lời, ngưỡng từ chối |
| TV5 | App và báo cáo | Streamlit, SQLite lịch sử + thống kê, deploy, báo cáo và slide |

Cả nhóm: mỗi người viết khoảng 60 câu hỏi và gán nhãn câu của người khác. Chi tiết: [docs/lo-trinh-va-phan-cong.md](docs/lo-trinh-va-phan-cong.md).

## Tiến độ

Theo dõi ở tab **Issues** (mỗi giai đoạn một issue) và **Milestones**:

| Milestone | Nội dung |
|---|---|
| M1 Dataset v1 | S01, D01–D06: phạm vi, thu thập, làm sạch, chunking, câu hỏi và qrels, split, freeze |
| M2 Baseline | TF-IDF, BM25, bảng Recall@k, MRR, NDCG@k, hard negatives |
| M3 Mô hình cải tiến | Sentence-BERT, PhoBERT sentence-pair, bi-encoder + cross-encoder |
| M4 Ứng dụng | Giao diện hỏi đáp, nguồn trích dẫn, câu hỏi tương tự, đánh giá, lịch sử, thống kê |
| M5 Đánh giá và báo cáo | Chỉ số câu trả lời, 6 phân tích bắt buộc, báo cáo cuối |

## Cấu trúc thư mục

```
data/raw/          tài liệu gốc, bất biến
data/interim/      docs.jsonl đã làm sạch
data/processed/    chunks.jsonl (chunk_text, text_seg, display_text)
data/labels/       questions.csv, qrels.csv, annotation_guideline.md
data/splits/       question_group_id của train / validation / test
configs/           cấu hình tiền xử lý, chunking, baseline, split
src/data/          thu thập, trích xuất, làm sạch, chunking, split
src/retrieval/     BM25, TF-IDF, SBERT, cross-encoder, metrics
src/app/           giao diện hỏi đáp
tests/             pytest
results/           báo cáo chất lượng, bảng kết quả
artifacts/         index, model (không commit file lớn)
docs/              đề bài, phạm vi, hướng dẫn từng thành viên
```

## Chạy thử

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m pytest
```

## Tài liệu

- [Đề bài](docs/de-bai.md)
- [Lộ trình và phân công](docs/lo-trinh-va-phan-cong.md)
- [Phạm vi](docs/scope.md)
- [Hướng dẫn Thành viên 1: từ chốt phạm vi đến Dataset v1 và baseline](docs/huong-dan-thanh-vien-1.md) ([bản Word](docs/files/Huong_dan_Thanh_vien_1_De_tai_10_Dataset_v1.docx))

## Quy ước làm việc

- Nhánh `main` chỉ nhận code qua Pull Request; mỗi task một nhánh `feature/<ID>-<mo-ta>`, ví dụ `feature/D04-question-labels`.
- Commit theo dạng `feat(D04): ...`, `fix(M01): ...`, `docs: ...`.
- Không sửa dữ liệu trong `data/raw`; không commit file lớn hơn vài MB (dùng Drive chung, ghi đường dẫn trong manifest).
- Không dùng tập test để chọn tham số hoặc ngưỡng từ chối.

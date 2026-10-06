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

Chi tiết từng việc nằm trong [file phân công trên Google Docs](https://docs.google.com/document/d/1ZMDBBBsTeBdehL9hAiG091OWIV-9r98egQ3ygFb-t5o/edit).

| | Người | Vai trò | Phụ trách chính | Bàn giao cho |
|---|---|---|---|---|
| TV1 | Duy | Dữ liệu + baseline | Chốt danh sách thủ tục hộ tịch (1 cấp, có URL + ngày lấy); crawl, làm sạch, chia đoạn có tiền tố "tên thủ tục \| mục", tách từ; freeze dataset; TF-IDF và BM25; hard negative từ top-20 BM25 | Cả nhóm (kho dữ liệu), TV3 và TV4 (hard negative) |
| TV2 | Khang | Bộ test + đánh giá | Guideline gán nhãn (7 loại câu, relevance 2/1); chia người viết và người gán nhãn; Cohen's kappa; chia train/dev/test theo nhóm câu hỏi; 1 script đánh giá chung (Recall@k, MRR, NDCG, tỷ lệ từ chối); chỉ số câu trả lời (F1, đúng nguồn, faithfulness); trưởng phần phân tích lỗi | Cả nhóm (script đánh giá, split) |
| TV3 | | Mô hình truy hồi | SBERT tiếng Việt, hybrid với BM25; cross-encoder hoặc PhoBERT rerank top-20; fine-tune bằng hard negative nếu kịp; hàm `retrieve()` trả top-k đã rerank kèm điểm; câu hỏi tương tự | TV4 (`retrieve()`) |
| TV4 | | Trả lời + web | Template trả lời trích nguyên văn kèm nguồn; ngưỡng từ chối chọn trên dev; xử lý câu nhiều ý, câu dễ bịa; hàm `answer()`; Streamlit đủ 7 chức năng, SQLite lưu lịch sử và đánh giá; deploy. Làm khung web trên dữ liệu giả trước, có model thật thì ráp vào | TV5 (link demo) |
| TV5 | | Slide + báo cáo | Khung báo cáo và slide, thống nhất văn phong; kịch bản demo và video dự phòng; sơ đồ pipeline; log tiến độ nhóm | Cả nhóm |

Cả nhóm: mỗi người viết khoảng 60 câu hỏi và gán nhãn câu của người khác, không tự gán nhãn câu mình viết. Ai làm phần nào viết phần đó trong báo cáo. Lộ trình: [docs/lo-trinh-va-phan-cong.md](docs/lo-trinh-va-phan-cong.md).

## Tiến độ

Theo dõi ở tab **Issues** và **Milestones**. Mỗi milestone gắn với một người phụ trách chính, khớp bảng phân công ở trên.

| Milestone | Phụ trách | Nội dung | Phụ thuộc |
|---|---|---|---|
| M1 Kho dữ liệu | TV1 Duy | Chốt danh sách thủ tục hộ tịch (URL + ngày lấy); crawl, làm sạch, chia đoạn có tiền tố, tách từ | |
| M2 Bộ test | TV2 Khang | Guideline gán nhãn 7 loại câu; phân công viết và gán nhãn chéo (~60 câu/người); Cohen's kappa; chia train/dev/test theo nhóm câu hỏi | Câu hỏi viết được ngay; gán nhãn cần M1 |
| M3 Baseline + Dataset v1 | TV1 Duy | Freeze dataset; TF-IDF, BM25; hard negative từ top-20 BM25 | M1, M2, script đánh giá của TV2 |
| M4 Đánh giá chung | TV2 Khang | Script đánh giá dùng chung: Recall@k, MRR, NDCG, tỷ lệ từ chối; chỉ số câu trả lời: F1, đúng nguồn, faithfulness | Làm song song, cần xong trước khi chạy mô hình |
| M5 Mô hình truy hồi | TV3 | SBERT, hybrid với BM25; cross-encoder hoặc PhoBERT rerank top-20; fine-tune bằng hard negative; `retrieve()`; câu hỏi tương tự | M3 |
| M6 Trả lời + web | TV4 | Template trích nguyên văn kèm nguồn; ngưỡng từ chối trên dev; câu nhiều ý, câu dễ bịa; `answer()`; Streamlit + SQLite; deploy | Khung web làm trước trên dữ liệu giả; ráp thật cần M5 |
| M7 Phân tích + báo cáo | TV2 (phân tích lỗi), TV5 (slide, báo cáo) | 6 phân tích bắt buộc; báo cáo, slide, demo | M5, M6 |

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

## Pipeline dữ liệu (TV1)

```bash
python -m playwright install chromium
python -m src.data.crawl    # D01: source_list.csv → data/raw/html + raw_manifest.csv
python -m src.data.parse    # D02: → data/interim/docs.jsonl
python -m src.data.chunk    # D03: → data/processed/chunks.jsonl
python -m src.data.eda      # → results/data_quality/corpus_report.md + figures/
```

Chi tiết: [docs/huong-dan-cao-du-lieu.md](docs/huong-dan-cao-du-lieu.md).

## Tài liệu

- [Đề bài](docs/de-bai.md)
- [Lộ trình và phân công](docs/lo-trinh-va-phan-cong.md)
- [Hướng dẫn Git cho cả nhóm](docs/huong-dan-git.md): cài đặt, tạo nhánh, commit, mở Pull Request
- [Phạm vi](docs/scope.md)
- [Hướng dẫn D01–D03: crawl, làm sạch, chunk, báo cáo](docs/huong-dan-cao-du-lieu.md)
- [Hướng dẫn Thành viên 1: từ chốt phạm vi đến Dataset v1 và baseline](docs/huong-dan-thanh-vien-1.md) ([bản Word](docs/files/Huong_dan_Thanh_vien_1_De_tai_10_Dataset_v1.docx))

## Quy ước làm việc

- Nhánh `main` chỉ nhận code qua Pull Request; mỗi task một nhánh `feature/<ID>-<mo-ta>`, ví dụ `feature/D04-question-labels`.
- Commit theo dạng `feat(D04): ...`, `fix(M01): ...`, `docs: ...`.
- Không sửa dữ liệu trong `data/raw`; không commit file lớn hơn vài MB (dùng Drive chung, ghi đường dẫn trong manifest).
- Không dùng tập test để chọn tham số hoặc ngưỡng từ chối.

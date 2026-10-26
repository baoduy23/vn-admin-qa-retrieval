# Hệ thống gợi ý câu trả lời cho câu hỏi hành chính

Đề tài 10 môn Xử lý ngôn ngữ tự nhiên. Người dùng nhập câu hỏi, hệ thống tìm đoạn luật hoặc câu hỏi tương tự trong kho, xếp hạng rồi trả lời bằng cách trích nguyên văn kèm nguồn. Phần nhóm làm là truy hồi (retrieval) và so khớp câu hỏi (question matching), hệ thống không tự sinh câu trả lời như chatbot.

Nhóm chọn lĩnh vực hộ tịch: khai sinh, kết hôn, khai tử, thay đổi và cải chính hộ tịch, nhận cha mẹ con, giám hộ, trích lục. Kho dữ liệu gồm các quy định hộ tịch còn hiệu lực tại ngày 09/10/2026 và dùng được đến hết 28/02/2027. Phạm vi đã chốt nằm ở [docs/scope.md](docs/scope.md).

## Pipeline

```
tài liệu gốc → làm sạch → chia đoạn → lập chỉ mục → truy hồi → xếp hạng lại → trả lời có trích dẫn
                                         │             │            │
                                   TF-IDF / BM25   bi-encoder   cross-encoder
                                    (baseline)     (SBERT)      (PhoBERT pair)
```

## Phân công

| | Người | Vai trò | Phụ trách chính | Bàn giao cho |
|---|---|---|---|---|
| TV1 | Duy | Dữ liệu + baseline | Chốt và hợp nhất 10 văn bản luật (433 đoạn): tải văn bản, tách Chương/Điều/Khoản/Điểm, áp văn bản sửa đổi, làm sạch, chia đoạn có tiền tố "tên văn bản \| Điều", tách từ; freeze dataset; baseline TF-IDF và BM25; hard negative từ top-20 BM25 | Cả nhóm (kho dữ liệu), TV3 (hard negative) |
| TV2 | Khang | Nhãn + đánh giá + phân tích lỗi | Guideline gán nhãn (7 loại câu, relevance 2/1); đo Cohen's kappa, chốt 707 nhãn trong `qrels.csv` (quy tắc R1–R6); chia train/validation/test theo nhóm câu hỏi; script đánh giá chung cho truy hồi và tầng trả lời; phân tích lỗi (E1–E5); viết phần phương pháp và phân tích lỗi trong báo cáo | Cả nhóm (script đánh giá, split) |
| TV3 | Tín | Mô hình truy hồi | Bi-encoder (multilingual-e5-base), hybrid min-max với BM25, rerank bằng PhoRanker; khôi phục dấu bằng n-gram; hàm `retrieve()` trả top-k đã rerank kèm điểm; gợi ý câu hỏi tương tự | TV4 (`retrieve()`) |
| TV4 | Quân | Trả lời + web | Template trích nguyên văn điều luật kèm nguồn; chọn ngưỡng từ chối τ trên validation; tách câu nhiều ý; kiểm tra căn cứ con số; sửa lỗi gõ theo bigram; hàm `answer()`; web Streamlit + SQLite, deploy; slide | TV5 (link demo) |
| TV5 | Huy | Báo cáo + slide + web | Khung bài báo và slide; sơ đồ pipeline; kịch bản và video demo dự phòng; nhật ký tiến độ; biên soạn 80 câu hỏi (Q0221–Q0300): 40 câu tự viết, 40 câu soạn nháp bằng công cụ rồi rà soát, chỉnh sửa; biên soạn phần kết luận, tài liệu tham khảo và phụ lục; web Streamlit + SQLite, deploy (cùng TV4) | Cả nhóm |

Bộ câu hỏi có 300 câu: 83 câu do thành viên viết, 217 câu soạn nháp bằng công cụ hỗ trợ rồi nhóm rà lại (cột `source` trong `data/labels/questions.csv`). Nhãn ban đầu phần lớn cũng được soạn nháp rồi duyệt; TV1 vừa duyệt nhãn vừa tham gia gán độc lập để đo kappa. Ai làm phần nào thì viết phần đó trong báo cáo. Lộ trình: [docs/lo-trinh-va-phan-cong.md](docs/lo-trinh-va-phan-cong.md).

## Tiến độ

Tiến độ được theo dõi qua tab Issues và Milestones trên GitHub. Người phụ trách chính của mỗi milestone trùng với bảng phân công ở trên.

| Milestone | Phụ trách | Nội dung | Phụ thuộc |
|---|---|---|---|
| M1 Kho dữ liệu | TV1 Duy | Chốt danh sách văn bản luật (số hiệu, URL, ngày tải); tải văn bản, tách Chương/Điều/Khoản/Điểm, hợp nhất văn bản sửa đổi, làm sạch, chia đoạn có tiền tố, tách từ | |
| M2 Bộ test | TV2 Khang | Guideline gán nhãn 7 loại câu; phân công viết và gán nhãn chéo (~60 câu/người); Cohen's kappa; chia train/dev/test theo nhóm câu hỏi | Câu hỏi viết được ngay; gán nhãn cần M1 |
| M3 Baseline + Dataset v1 | TV1 Duy | Freeze dataset; TF-IDF, BM25; hard negative từ top-20 BM25 | M1, M2, script đánh giá của TV2 |
| M4 Đánh giá chung | TV2 Khang | Script đánh giá dùng chung: Recall@k, MRR, NDCG, tỷ lệ từ chối; chỉ số câu trả lời: F1, đúng nguồn, faithfulness | Làm song song, cần xong trước khi chạy mô hình |
| M5 Mô hình truy hồi | TV3 Tín | SBERT, hybrid với BM25; cross-encoder hoặc PhoBERT rerank top-20; fine-tune bằng hard negative; `retrieve()`; câu hỏi tương tự | M3 |
| M6 Trả lời + web | TV4 Quân, TV5 Huy (web, deploy) | Template trích nguyên văn kèm nguồn; ngưỡng từ chối trên dev; câu nhiều ý, câu dễ bịa; `answer()`; Streamlit + SQLite; deploy | Khung web làm trước trên dữ liệu giả; ráp thật cần M5 |
| M7 Phân tích + báo cáo | TV2 (phân tích lỗi) Khang, TV5 (slide, báo cáo) Huy | 6 phân tích bắt buộc; báo cáo, slide, demo | M5, M6 |

## Cấu trúc thư mục

```
data/raw/          văn bản gốc (.doc, .pdf, .html), bất biến; source_list.csv, amendments.yaml
data/interim/      bản .docx để code đọc
data/processed/    chunks.jsonl (433 chunk; text, text_seg, display_text), train_pairs.csv (hard negative)
data/labels/       questions.csv, qrels.csv, annotation_guideline.md
data/splits/       question_group_id của train / validation / test
data/dataset_manifest.json   số liệu + sha256 của Dataset v1 (freeze)
configs/           cấu hình tiền xử lý, chunking, baseline, split
src/data/          làm sạch, tách luật, chunking, split
src/labels/        gán nhãn chéo, Cohen's kappa
src/retrieval/     BM25, TF-IDF, SBERT, cross-encoder, metrics
src/answer/        answer(): trích nguyên văn kèm nguồn, ngưỡng từ chối, câu nhiều ý (Quân)
src/app/           web Streamlit + SQLite lịch sử, đánh giá (Quân)
notebooks/         thử nghiệm trước khi chuyển thành script (01_doc_luat.ipynb)
tests/             pytest
results/           báo cáo chất lượng, bảng kết quả
artifacts/         index, model (không commit file lớn)
docs/              đề bài, phạm vi, hướng dẫn từng thành viên
```

Thư mục nào cũng có README riêng, ghi rõ từng file làm gì và chạy bằng lệnh nào: [data](data/README.md), [src/data](src/data/README.md), [src/labels](src/labels/README.md), [src/retrieval](src/retrieval/README.md), [src/answer](src/answer/README.md), [src/app](src/app/README.md), [configs](configs/README.md), [results](results/README.md).

## Chạy thử

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m pytest
```

## Pipeline dữ liệu (TV1)

Kho gồm 10 văn bản luật về hộ tịch còn hiệu lực ngày 09/10/2026: Luật Hộ tịch 60/2014/QH13, các Nghị định, Thông tư hướng dẫn và văn bản sửa đổi. Văn bản được tải tay từ vbpl.vn. Với văn bản mà vbpl.vn hoặc vanban.chinhphu.vn chỉ có bản PDF scan, nhóm lấy toàn văn trên thuvienphapluat.vn. Nhóm không cào web. Danh sách văn bản ở [data/raw/source_list.csv](data/raw/source_list.csv), lý do chọn ở [docs/scope.md](docs/scope.md).

```
data/raw/        file gốc tải về (.doc, .pdf, .html trang TVPL), không sửa
                 amendments.yaml: phần sửa đổi, bổ sung, bãi bỏ của văn bản sửa đổi
data/interim/    <doc_id>.docx, bản gốc chưa áp sửa đổi
      │  tách Chương → Mục → Điều → Khoản → Điểm, áp amendments.yaml (bản hợp nhất)
data/processed/  chunks.jsonl: 1 Điều = 1 đoạn, Điều dài quá 200 từ thì tách theo Khoản
```

Để chạy lại từ dữ liệu gốc đến kết quả baseline, đứng ở thư mục gốc của repo và chạy lần lượt:

```bash
python -m src.data.parse_law          # interim/*.docx → processed/units.jsonl (kiểm số Điều từng văn bản)
python -m src.data.apply_amendments   # + raw/amendments.yaml → processed/units_current.jsonl, amendments_log.csv
python -m src.data.chunk              # → processed/chunks.jsonl (433 chunk)
python -m src.data.corpus_report      # → results/data_quality/corpus_report.md
python -m src.labels.sample_double   # phân người gán nhãn chéo + 20% gán đôi → labels/label_assignments.csv
python -m src.labels.kappa --a A.csv --b B.csv --out results/data_quality/label_agreement
python -m src.data.split              # labels/questions.csv → splits/*_qgroups.csv
python -m src.data.freeze             # kiểm tiêu chí freeze → data/dataset_manifest.json
python -m src.retrieval.evaluate      # TF-IDF, BM25 trên validation (thêm --test để chạy test 1 lần)
python -m src.retrieval.hard_negatives  # → processed/train_pairs.csv
python -m pytest
```

## Trả lời và web (Quân)

```bash
python -m src.app.images               # (tuỳ chọn) tải 3 ảnh giao diện mặc định về src/app/static/img/
python -m src.answer.evaluate_answer   # chọn ngưỡng từ chối τ trên validation → configs/answer_selected.yaml, results/answer/
streamlit run src/app/main.py          # web hỏi đáp; máy chưa cài torch: đặt ANSWER_PIPELINE=bm25 trước lệnh
python -m src.app.demo_seed            # (tùy chọn) nạp lịch sử mẫu để trang Thống kê có số liệu khi demo
```

`answer()` trả lời theo mẫu `Theo <tên văn bản>, Điều X Khoản Y: "<trích nguyên văn>"`. Hàm sẽ từ chối trả lời khi điểm top-1 thấp hơn τ, hoặc khi câu hỏi cần một con số (tiền, phạt, tuổi, thời hạn) mà văn bản tìm được không có số đó. Với câu hỏi nhiều ý, hệ thống tách ra và trả lời lần lượt từng ý. Giao diện web có đủ 7 chức năng theo yêu cầu của đề bài. Chi tiết và cách deploy nằm ở [src/answer](src/answer/README.md), [src/app](src/app/README.md), phần báo cáo của Quân ở [docs/bao-cao-quan.md](docs/bao-cao-quan.md).

## Tài liệu

- [Đề bài](docs/de-bai.md)
- [Lộ trình và phân công](docs/lo-trinh-va-phan-cong.md)
- [Hướng dẫn Git cho cả nhóm](docs/huong-dan-git.md) (cài đặt, tạo nhánh, commit, mở Pull Request)
- [Phạm vi](docs/scope.md)
- [Hướng dẫn Thành viên 1 (từ chốt phạm vi tới Dataset v1 và baseline)](docs/huong-dan-thanh-vien-1.md) ([bản Word](docs/files/Huong_dan_Thanh_vien_1_De_tai_10_Dataset_v1.docx))

## Quy ước làm việc

- Nhánh `main` chỉ nhận code qua Pull Request. Mỗi task một nhánh `feature/<ID>-<mo-ta>`, vd `feature/D04-question-labels`.
- Commit theo dạng `feat(D04): ...`, `fix(M01): ...`, `docs: ...`.
- Không sửa dữ liệu trong `data/raw`. File lớn hơn vài MB thì không commit mà để trên Drive chung, sau đó ghi đường dẫn vào `data/raw/source_list.csv`.
- Không dùng tập test để chọn tham số hoặc ngưỡng từ chối.


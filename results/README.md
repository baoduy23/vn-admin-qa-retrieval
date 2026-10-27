# results/

Thư mục chứa kết quả chạy, xem trực tiếp trên GitHub được. Các file lớn như index, model được để trong `artifacts/` và không commit lên repo.

| Thư mục | Nội dung | Ai ghi |
|---|---|---|
| `data_quality/` | `corpus_report.md` (số Điều, độ dài, trùng, hiệu lực, phân bố chunk), `dieu_table.csv`, `chunk_tokens.png`; sau này `label_agreement.md` (kappa, TV2) | TV1, TV2 |
| `retrieval/` | Bảng Recall@k, MRR, NDCG@k của từng mô hình trên validation (và test, chạy 1 lần cuối). Baseline: `baseline_report.md`, `baseline_results.csv`, `baseline_by_type.csv`, `grid_validation.csv`, `runs/` (top-10 từng câu, cho phân tích lỗi) | TV1, TV3, TV2 chạy script chung |
| `answer/` | `answer_report.md` (ngưỡng τ, tỉ lệ trả lời, đúng nguồn, F1, từ chối đúng/nhầm; tách / không tách câu nhiều ý; câu thiếu thông tin), `threshold_grid.csv`, `validation_answers.csv` (câu trả lời từng câu, dùng chấm tay faithfulness), `test_answers.csv` khi TV2 chạy `--test` | Quân, TV2 chạy test |

Mỗi file kết quả đều ghi kèm tên mô hình, tham số, phiên bản thư viện, seed và commit SHA của dữ liệu.

Lưu ý về hash qrels: `retrieval/baseline_report.md` và `retrieval/models/models_report.md` ghi `qrels_sha256 4a587a27e0ad`. Script chép số này từ `data/dataset_manifest.json`, mà lúc đó manifest vẫn là bản cũ 160 câu chưa được làm mới. Hai report được chạy ở commit 480d477, sau commit b35d8d9 chốt qrels 707 dòng, nên qrels thật sự dùng có sha256 bắt đầu bằng `b0002c7e0023`, khớp với manifest hiện tại. Không chạy lại script để sửa dòng này, vì làm vậy là chạy lại tập test.

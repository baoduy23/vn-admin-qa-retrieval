# results/

Kết quả chạy, đọc được ngay trên GitHub. File lớn (index, model) để ở `artifacts/`, không commit.

| Thư mục | Nội dung | Ai ghi |
|---|---|---|
| `data_quality/` | `corpus_report.md` (số Điều, độ dài, trùng, hiệu lực, phân bố chunk), `dieu_table.csv`, `chunk_tokens.png`; sau này `label_agreement.md` (kappa, TV2) | TV1, TV2 |
| `retrieval/` | Bảng Recall@k, MRR, NDCG@k của từng mô hình trên validation (và test, chạy 1 lần cuối). Baseline: `baseline_report.md`, `baseline_results.csv`, `baseline_by_type.csv`, `grid_validation.csv`, `runs/` (top-10 từng câu, cho phân tích lỗi) | TV1, TV3, TV2 chạy script chung |

Mỗi file kết quả ghi kèm: tên mô hình, tham số, phiên bản thư viện, seed, commit SHA của dữ liệu.

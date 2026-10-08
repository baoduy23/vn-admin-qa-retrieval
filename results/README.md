# results/

Kết quả chạy, đọc được ngay trên GitHub. File lớn (index, model) để ở `artifacts/`, không commit.

| Thư mục | Nội dung | Ai ghi |
|---|---|---|
| `data_quality/` | `corpus_report.md`, biểu đồ, danh sách thủ tục gần giống và đoạn trùng, các lỗi cần tra lại nguồn | `python -m src.data.eda` (TV1) |
| `retrieval/` | Bảng Recall@k, MRR, NDCG@k của từng mô hình trên validation (và test, chạy 1 lần cuối) | TV1, TV3, TV2 chạy script chung |

Mỗi file kết quả ghi kèm: tên mô hình, tham số, phiên bản thư viện, seed, commit SHA của dữ liệu.

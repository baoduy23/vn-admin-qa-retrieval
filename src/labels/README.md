# src/labels/ — gán nhãn chéo và độ đồng thuận (TV2)

| File | Làm gì |
|---|---|
| `sample_double.py` | Đọc người viết từ cột `annotator` (`TV2`, `TV1-Duy`...), phân người gán chính (TV kế tiếp, xoay vòng) và chọn 20% nhóm (phân tầng theo type) cho người thứ hai gán độc lập → `data/labels/label_assignments.csv` |
| `kappa.py` | Cohen's kappa giữa 2 người gán trên phần 20%: kappa liên quan/không, kappa trọng số 3 mức, kappa verdict mức câu; liệt kê cặp lệch để họp chốt → `results/data_quality/label_agreement.md` + `_diffs.csv` |
| `validate_labels.py` | `read_qrels()` đọc qrels từ CSV hoặc phiếu `.xlsx` (sheet `qrels`), dùng chung cho `kappa.py` |

Chạy từ gốc repo:

```
python -m src.labels.sample_double
python -m src.labels.kappa --a phieu_A.csv --b phieu_B.csv --out results/data_quality/label_agreement
```

Phiếu `.xlsx` cần `openpyxl` (có trong `requirements.txt`).

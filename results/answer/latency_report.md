# Thời gian phản hồi

Sinh bởi `python -m src.answer.latency --split validation --repeat 3`. 57 câu validation, mỗi câu đo 3 lần, sau 1 câu khởi động. Pipeline: **rerank**.

Máy: Windows 11, AMD64 Family 25 Model 80 Stepping 0, AuthenticAMD, 12 luồng, RAM 15.4 GB, Python 3.14.0, torch 2.14.1+cpu, 6 luồng torch.

Nạp hệ thống (dựng AnswerEngine, gồm nạp model): **111.5 s**. Web chỉ nạp 1 lần lúc mở, các lượt hỏi sau dùng lại.

| Bước | Câu đầu (ms) | Trung bình (ms) | Trung vị (ms) | p95 (ms) | Lớn nhất (ms) |
|---|---|---|---|---|---|
| BM25 (top-10) | 2 | 4 | 4 | 7 | 8 |
| Dense e5 (top-10) | 72 | 88 | 87 | 119 | 155 |
| Hybrid (top-10) | 78 | 92 | 90 | 124 | 204 |
| Hybrid + rerank (top-10) | 4709 | 5220 | 5180 | 6223 | 7191 |
| answer() như web | 10764 | 5606 | 5424 | 10127 | 15115 |

Mỗi bước đo riêng từ đầu (rerank đã gồm thời gian BM25 + dense + hybrid để lấy ứng viên). answer() còn gồm lọc câu, chọn dòng trích bằng PhoRanker và câu hỏi tương tự, nên chậm hơn rerank.

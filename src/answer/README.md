# src/answer/ — trả lời có trích dẫn (Quân, M6)

Nhận câu hỏi → gọi `retrieve()` của TV3 → trả lời bằng **trích nguyên văn** điều luật kèm nguồn, hoặc **từ chối** khi không đủ căn cứ. Không sinh chữ mới nên câu trả lời luôn faithful với văn bản; rủi ro còn lại là chọn sai đoạn.

```python
from src.answer import answer
r = answer("Đăng ký khai sinh cần giấy tờ gì?")
r["answer"]             # 'Theo Luật Hộ tịch 60/2014/QH13, Điều 16 Khoản 1: "1. Người đi đăng ký khai sinh nộp tờ khai ..."'
r["refused"], r["reason"]   # False, None   |  True, "low_score" / "no_evidence"
r["sources"]            # top-5: chunk_id, doc_title, citation, url, score, excerpt_html (đã tô sáng), used_in_answer
r["parts"]              # từng ý của câu (câu nhiều ý có 2-3 phần tử)
r["similar_questions"]  # câu hỏi tương tự (train + validation)
r["underspecified"]     # True: câu chưa nói rõ việc hộ tịch nào
r["notes"]              # lưu ý: thẩm quyền cấp huyện → cấp xã (NĐ 120/2025), Điều đã hợp nhất sửa đổi
```

## Các bước

```
câu hỏi ─► lĩnh vực khác (hộ chiếu, đất đai, thuế...) và không nhắc việc hộ tịch nào? ── có ──► từ chối (out_of_scope)
   │ không
   ▼
tách ý (intent.split_multi_intent) ─► mỗi ý: retrieve(ý, k)
                                                  │
                     điểm top-1 < τ ? ──── có ──► từ chối (low_score)
                                                  │ không
     câu đòi con số (tiền / phạt / tuổi / thời hạn) mà 3 đoạn đầu không có? ── có ──► từ chối (no_evidence)
                                                  │ không
          chọn dòng (khoản / điểm) khớp nhất trong đoạn top-1 (template.best_quote; IDF hoặc PhoRanker)
                                                  ▼
                Theo <tên văn bản>, Điều X Khoản Y: "<trích nguyên văn>"
```

| File | Nội dung |
|---|---|
| `answer.py` | `AnswerEngine`, `answer(q)`: ghép các bước trên, nguồn, câu tương tự, lưu ý pháp lý |
| `template.py` | Mẫu câu trả lời; `best_quote` chọn dòng có tổng IDF âm tiết trùng câu hỏi cao nhất (ưu tiên dòng có con số đúng loại câu hỏi đòi); `citation` đọc số Khoản/Điểm từ đầu dòng; `highlight_html` tô chữ trùng |
| `intent.py` | Luật nhận dạng: tách câu nhiều ý, loại con số câu hỏi đòi + kiểm tra căn cứ, câu thiếu thông tin, chủ đề (việc hộ tịch) cho thống kê, câu ngoài phạm vi (`out_of_scope_topic`) |
| `line_scorer.py` | Chấm từng khoản / điểm bằng PhoRanker để chọn đoạn trích (`quote.scorer: rerank` trong `configs/answer.yaml`; mặc định `idf`) |
| `compare_quote.py` | So 2 cách chọn khoản (IDF / PhoRanker) trên train + validation, xuất `results/answer/quote_compare.csv` để chấm tay (cần torch) |
| `text.py` | Âm tiết bỏ dấu, hư từ, IDF |
| `retriever.py` | Nạp `retrieve()` của TV3 theo `configs/answer.yaml`; lỗi thì lùi về BM25 |
| `evaluate_answer.py` | Chọn τ trên validation, đánh giá câu trả lời, so tách / không tách câu nhiều ý |

So khớp chữ làm trên dạng **có dấu** khi câu hỏi có dấu (bỏ dấu thì "đầu" trùng "đâu", "máy" trùng "mấy", "phát" trùng "phạt"), câu gõ không dấu mới so trên dạng bỏ dấu.

## Chọn ngưỡng và đánh giá

```bash
python -m src.answer.evaluate_answer                 # validation → configs/answer_selected.yaml, results/answer/
python -m src.answer.evaluate_answer --live selected # phần câu nhiều ý chạy bằng pipeline TV3 (cần torch)
python -m src.answer.evaluate_answer --test          # TV2 chạy MỘT lần cuối, τ đã chốt
```

- τ chọn bằng file kết quả chạy validation TV3 đã lưu (`results/retrieval/models/runs/*_validation.csv`), không cần nạp model. Cách chọn giống TV1/TV3: từ chối đúng nhiều nhất mà từ chối nhầm ≤ 10%.
- Kiểm tra căn cứ con số được bật cho pipeline nào mà trên validation nó tăng từ chối đúng và không vượt trần từ chối nhầm (rerank, hybrid, dense: bật; BM25: tắt).
- Kết quả: [results/answer/answer_report.md](../../results/answer/answer_report.md).

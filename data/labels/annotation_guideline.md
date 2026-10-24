# Guideline gán nhãn qrels

`qrels.csv`: `question_id, chunk_id, relevance`. Chunk không liên quan thì không ghi dòng.

## Mức điểm

- **2**: chunk tự trả lời được câu hỏi, không cần đọc thêm chunk khác.
- **1**: có liên quan nhưng phải đọc kèm chunk khác; hoặc câu hỏi mơ hồ, chunk trả lời được một nghĩa.
- **0** (không ghi): chunk không giúp trả lời câu hỏi.
- Câu `out_of_scope` (không phải hộ tịch) và `unsupported` (đúng chủ đề nhưng kho không có quy định) không có qrels.

## Quy tắc bổ sung sau buổi chốt nhãn (24/10/2026)

Thêm vào vì 80/112 cặp lệch trong lần đo kappa là "A có, B không" (58 cặp A = 1), tức là nhóm hiểu mức 1 khác nhau. Mỗi quy tắc đo bằng việc **câu trả lời đúng có cần ý trong chunk không**, không đo bằng việc chunk cùng chủ đề.

| Mã | Quy tắc |
|---|---|
| R1 | **1** khi chunk chứa ít nhất một ý mà câu trả lời đúng phải nêu: một ý của câu nhiều ý, một điều kiện hoặc ngoại lệ, hoặc phần dẫn của chunk bị tách đôi (P1/P2). |
| R2 | **0** khi chunk chỉ cùng thủ tục hoặc chủ đề mà không góp ý nào: thẩm quyền cho câu hỏi về giấy tờ, "Chính phủ quy định chi tiết", phạm vi chung, thủ tục chung khi đáp án nằm ở ngoại lệ. |
| R3 | **0** cho chunk của trường hợp mà câu hỏi không nêu: thủ tục có yếu tố nước ngoài (Chương III Luật), khu vực biên giới, đã khai sinh rồi mới bổ sung... Áp dụng cả khi câu chữ giống, vì trích chunk đó là trích sai thủ tục. |
| R4 | Câu `confusable`: chunk của thủ tục dễ bị nhầm = **0**. |
| R5 | Câu `multi_intent`: chunk trả lời trọn một ý = **2** (giữ quy ước đã có). |
| R6 | Câu `underspecified`: tối đa **1**, mỗi nghĩa một chunk; câu quá rộng thì chỉ giữ phần chung. |

Bảng chốt từng cặp kèm lý do: `results/data_quality/label_adjudication.csv`. Kappa trước buổi chốt: `results/data_quality/label_agreement.md` (không tính lại sau buổi chốt).

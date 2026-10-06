# Đề tài 10. Hệ thống gợi ý câu trả lời cho câu hỏi hành chính hoặc học vụ

## 1. Mô tả

Xây dựng hệ thống tiếp nhận câu hỏi của người dùng và tìm câu hỏi tương tự hoặc đoạn văn phù hợp trong kho tài liệu.

Ví dụ: "Em nghỉ học một học kỳ thì có mất kết quả không?" Hệ thống cần tìm được quy định liên quan đến bảo lưu hoặc tạm dừng học tập.

Đề tài tập trung vào NLP retrieval và question matching, không yêu cầu xây dựng một chatbot tạo sinh quy mô lớn.

## 2. Yêu cầu cụ thể

Pipeline tối thiểu:

1. Tiền xử lý tài liệu.
2. Chia tài liệu thành các đoạn.
3. Lập chỉ mục.
4. Tìm kiếm câu hỏi hoặc đoạn văn liên quan.
5. Xếp hạng kết quả.
6. Sinh câu trả lời bằng template hoặc trích dẫn nguyên văn.

Baseline bắt buộc: TF-IDF hoặc BM25.

Mô hình cải tiến:

- Sentence-BERT.
- PhoBERT cho sentence-pair classification.
- Bi-encoder + cross-encoder.
- Có thể sử dụng một mô hình sinh nhỏ, nhưng câu trả lời phải kèm nguồn tham chiếu.

## 3. Sản phẩm ứng dụng

- Giao diện hỏi đáp.
- Hiển thị câu trả lời đề xuất.
- Hiển thị nguồn tài liệu và đoạn trích.
- Hiển thị các câu hỏi tương tự.
- Cho phép người dùng đánh giá câu trả lời.
- Trả về thông báo phù hợp khi không tìm thấy bằng chứng.
- Có lịch sử truy vấn và thống kê chủ đề được hỏi nhiều.

## 4. Chỉ số đánh giá

Đối với retrieval: Recall@k, MRR, NDCG@k.

Đối với câu trả lời:

- Exact match hoặc token-level F1 nếu có đáp án chuẩn.
- Answer relevance.
- Faithfulness đối với tài liệu nguồn.
- Tỷ lệ trả lời đúng nguồn.
- Tỷ lệ từ chối hợp lý khi không đủ thông tin.

## 5. Phân tích bắt buộc

- Câu hỏi diễn đạt khác tài liệu.
- Câu hỏi thiếu thông tin.
- Câu hỏi gồm nhiều ý.
- Nhiều tài liệu có nội dung gần giống.
- Câu hỏi nằm ngoài phạm vi hệ thống.
- Nguy cơ sinh câu trả lời không có căn cứ.

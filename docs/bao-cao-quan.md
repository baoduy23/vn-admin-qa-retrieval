# Bản nháp phần báo cáo của Quân: sinh câu trả lời và ứng dụng web

Bản nháp để TV5 ghép vào báo cáo chung. Số liệu lấy từ `results/answer/answer_report.md` (validation). Số liệu test sẽ điền sau khi TV2 chạy `python -m src.answer.evaluate_answer --test` một lần.

## 1. Sinh câu trả lời bằng trích dẫn nguyên văn

Đề tài không dùng mô hình sinh. Câu trả lời ghép từ một khung cố định và một đoạn trích nguyên văn của điều luật được xếp hạng cao nhất:

> Theo `<tên văn bản>`, Điều X Khoản Y: "`<trích nguyên văn>`"

Một đoạn (chunk) có thể là cả một Điều gồm nhiều khoản, nên trước khi trích, hệ thống chọn dòng (khoản hoặc điểm) khớp câu hỏi nhất. Điểm của một dòng là tổng IDF các âm tiết nội dung của câu hỏi có mặt trong dòng (đã bỏ hư từ như "thì", "có", "gì"), chia nhẹ theo độ dài dòng. Nếu dòng được chọn là một điểm "a)" thì lấy thêm dòng dẫn phía trên ("1. Hồ sơ gồm:") để câu đọc được. Số Khoản/Điểm trong phần dẫn nguồn đọc trực tiếp từ đầu dòng được trích.

Trên validation, trích một dòng cho token F1 so với đáp án mẫu là 0.336, so với 0.305 khi trích cả đoạn (pipeline rerank). F1 thấp là bình thường vì đáp án mẫu là câu tóm tắt ngắn còn câu trả lời là văn bản luật nguyên văn; chỉ số này chỉ dùng để so hai cách trích.

Về faithfulness: vì không có chữ nào ngoài khung mẫu và văn bản gốc, câu trả lời không thể chứa thông tin không có trong nguồn. Lỗi còn lại là trích sai đoạn, đo bằng tỉ lệ đúng nguồn: trong các câu hợp lệ được trả lời, 46% trích đúng đoạn có trong nhãn (42% nếu chỉ tính đoạn trả lời trực tiếp, relevance 2).

## 2. Ngưỡng từ chối τ

Hệ thống từ chối khi điểm của đoạn top-1 thấp hơn τ. τ chọn trên validation bằng file kết quả chạy đã lưu của TV3, cùng cách với TV1 và TV3: lấy τ từ chối đúng nhiều câu `out_of_scope` + `unsupported` nhất, với điều kiện từ chối nhầm câu hợp lệ không quá 10%.

Chỉ dùng ngưỡng thì khó chặn câu `unsupported`: các câu này nói đúng chủ đề hộ tịch (ví dụ "Lệ phí cấp bản sao trích lục hộ tịch là bao nhiêu tiền một bản?") nên điểm truy hồi vẫn cao, dù kho không có biểu phí. Vì vậy thêm một bước kiểm tra căn cứ: nhận dạng loại con số câu hỏi đòi (số tiền, mức phạt, độ tuổi, thời hạn) bằng mẫu từ khóa, rồi kiểm tra 3 đoạn đầu có chứa con số đúng loại đó không (ví dụ "60 ngày", "… đồng", "miễn lệ phí"). Không có thì từ chối với lý do "văn bản không nêu số tiền mà câu hỏi đòi".

| Pipeline (validation) | τ | Trả lời | Đúng nguồn | Từ chối đúng | Từ chối nhầm |
|---|---|---|---|---|---|
| rerank, chỉ ngưỡng | 0.709 | 0.96 | 0.46 | 0.40 | 0.04 |
| rerank, ngưỡng + kiểm tra căn cứ | 0.709 | 0.96 | 0.46 | 0.60 | 0.04 |
| BM25, chỉ ngưỡng | 6.940 | 1.00 | 0.15 | 0.20 | 0.00 |

Kiểm tra căn cứ tăng từ chối đúng từ 0.40 lên 0.60 mà không tăng từ chối nhầm, nên được bật cho rerank, hybrid và dense. Với BM25, bật nó làm từ chối nhầm vượt 10% nên tắt. Validation chỉ có 5 câu cần từ chối nên các tỉ lệ này thay đổi theo bước 0.2; cần đọc cùng số liệu test.

Ví dụ lỗi (validation): "Làm hộ chiếu mất bao lâu?" (ngoài phạm vi) vẫn được trả lời vì điểm vượt τ và kho có rất nhiều đoạn nêu thời hạn; "Người đã chuyển giới thì đổi giới tính trên giấy khai sinh như thế nào" (kho không có quy định) được trả lời bằng đoạn ghi Sổ về việc xác định lại giới tính, vì câu không đòi con số nên kiểm tra căn cứ không áp dụng.

## 3. Câu nhiều ý

Câu như "Kết hôn cần giấy gì và nộp ở đâu?" được tách theo liên từ và dấu phẩy ("và", "còn", ","), chỉ khi mỗi vế đều có từ để hỏi (gì, đâu, bao lâu, mấy, không…), để không cắt nhầm "cha và mẹ". Vế sau thiếu chủ đề thì được ghép phần chủ đề ở đầu vế trước: "nộp ở đâu" → "Kết hôn nộp ở đâu". Mỗi ý truy hồi riêng; câu trả lời đánh số từng ý; danh sách nguồn xen kẽ kết quả các ý. Từ để hỏi được so khớp trên chữ có dấu, vì bỏ dấu thì "đầu" trùng "đâu", "máy" trùng "mấy".

Trên 9 câu `multi_intent` có nhãn của train + validation (truy hồi BM25, vì phần này phải chạy lại truy hồi cho từng ý):

| | R@5 | R@10 | NDCG@5 |
|---|---|---|---|
| Không tách | 0.570 | 0.733 | 0.556 |
| Tách ý | 0.644 | 0.678 | 0.559 |

Tách ý tăng R@5 (5 nguồn hiện trên web) nhưng giảm R@10 vì mỗi ý chỉ góp khoảng 5 đoạn. 78% câu nhiều ý được tách; không câu một ý nào bị tách nhầm. Số câu còn ít nên kết luận chưa chắc; chạy lại bằng pipeline rerank: `python -m src.answer.evaluate_answer --live selected`.

## 4. Câu thiếu thông tin

Câu không nhắc việc hộ tịch nào (khai sinh, kết hôn, khai tử…) và có ≤ 5 âm tiết nội dung, như "Đăng ký mất bao lâu?", được coi là thiếu thông tin. Hệ thống vẫn trả lời nhưng hiện gợi ý chọn việc cụ thể để hỏi lại. Trên train + validation luật này có precision 0.60, recall 0.27: bắt được câu rất ngắn ("Nộp hồ sơ ở xã nào?", "Giấy này còn hạn không?") nhưng bỏ sót câu có nhắc tên việc mà vẫn thiếu trường hợp cụ thể, như "Đăng ký giám hộ cần giấy tờ gì?" (giám hộ đương nhiên hay giám hộ cử) hoặc "Ghi chú hộ tịch cần giấy tờ gì?" (ghi chú việc gì). Hai lần đoán sai là câu ngoài phạm vi ngắn ("Làm hộ chiếu mất bao lâu?"); với câu này gợi ý chọn việc hộ tịch cũng có ích vì nhắc người dùng rằng hệ thống chỉ trả lời về hộ tịch.

## 5. Ứng dụng web

Streamlit, tông cam đất. Bố cục ghép hai mẫu: phần đầu trang và thanh menu theo Cổng Dịch vụ công quốc gia; banner, khu tìm kiếm (câu chào, ô bo tròn, ảnh hoa sen bên cạnh, nền hoa văn trống đồng), danh sách "chủ đề hữu ích" và chân trang nhiều cột theo Kho tri thức UEH (hotro.ueh.edu.vn). Trang chỉ dùng 3 ảnh: hoa sen, dải chim Lạc ở chân trang và hoa văn mặt trống đồng làm nền mờ; nhóm thay được bằng cách chép ảnh vào `src/app/static/img/`. Có ghi rõ đây là sản phẩm học tập, không phải cổng của cơ quan nhà nước.

| Yêu cầu đề bài | Cách làm |
|---|---|
| Giao diện hỏi đáp | Ô hỏi, 3 nút hỏi nhanh, 8 chủ đề hộ tịch kèm câu hỏi mẫu (train + validation) |
| Câu trả lời đề xuất | Thẻ câu trả lời theo mẫu trích dẫn, câu nhiều ý trả lời từng ý |
| Nguồn và đoạn trích | Top-5 đoạn kèm Điều/Khoản, link văn bản gốc, thanh điểm; tô chữ trùng câu hỏi và tô nền dòng được trích |
| Câu hỏi tương tự | `similar_questions` của TV3, bấm để hỏi lại |
| Đánh giá | Nút Hữu ích / Chưa đúng kèm góp ý, lưu SQLite |
| Không có căn cứ | Thẻ "Chưa đủ căn cứ" nêu lý do, gợi ý liên hệ UBND cấp xã |
| Lịch sử, thống kê | SQLite `queries`, `feedback`; tab Lịch sử (lọc, hỏi lại, tải CSV), tab Thống kê (tỉ lệ trả lời/từ chối, % hữu ích, chủ đề hỏi nhiều theo đoạn luật được trích, Điều được trích nhiều nhất) |

Ngoài ra web tự thêm lưu ý khi đoạn trích còn ghi thẩm quyền "cấp huyện", dẫn nguyên văn Nghị định 120/2025/NĐ-CP (chuyển nhiệm vụ về cấp xã), và khi Điều được trích đã hợp nhất nội dung sửa đổi.

Mô hình và chỉ mục nạp một lần (`st.cache_resource`). Máy không có torch hoặc không tải được model thì tự lùi về BM25 và báo trên giao diện.

## 6. Hạn chế và hướng cải thiện

- Đúng nguồn mới 46%: phụ thuộc chất lượng truy hồi; câu `confusable` (nhiều Điều gần giống nhau, ví dụ khai sinh trong nước và có yếu tố nước ngoài) hay chọn nhầm.
- Kiểm tra căn cứ chỉ áp dụng cho câu đòi con số; câu `unsupported` dạng "thủ tục như thế nào" vẫn lọt. Có thể thêm bộ phân loại câu trong / ngoài phạm vi học từ tập train.
- Luật tách ý và nhận câu thiếu thông tin là luật thủ công, recall thấp với câu dài.
- Lịch sử trên Streamlit Community Cloud mất khi app khởi động lại (ổ đĩa tạm); muốn lưu lâu dài cần cơ sở dữ liệu ngoài.

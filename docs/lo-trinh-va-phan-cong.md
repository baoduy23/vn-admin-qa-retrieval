# Lộ trình và phân công: Đề tài 10, gợi ý câu trả lời cho câu hỏi hành chính

Bản này thay cho file lộ trình cũ (B0 đến B7). Nó gộp lộ trình cũ với file "Hướng dẫn Thành viên 1" (bản 06/10/2026) và chia việc cho 5 người. Nếu hai file lệch nhau thì lấy file này làm chuẩn.

---

## 1. Những gì đã thay đổi so với lộ trình cũ

| Chủ đề | Lộ trình cũ | Bây giờ chốt | Lý do |
|---|---|---|---|
| Phạm vi | Hộ tịch + cư trú, khoảng 50 thủ tục | **Hộ tịch trước.** Chỉ thêm cư trú khi Dataset v1 đã freeze mà vẫn còn dư thời gian | Câu hỏi có nhãn mới là phần tốn công. Thêm lĩnh vực thì phải viết thêm câu hỏi |
| Cấp thực hiện | Chỉ 1 cấp (ví dụ cấp xã) | Giữ nguyên | Tránh có 2 bản gần như giống hệt nhau của cùng một thủ tục |
| Định dạng nhãn | `gold_chunk_ids` dạng list, đúng hoặc sai | **`qrels.csv` có relevance 2 hoặc 1** | NDCG@k chỉ có nghĩa khi có độ liên quan nhiều mức |
| Định dạng kho | `docs.jsonl`, `chunks.jsonl` | Giữ `docs.jsonl` và `chunks.jsonl`, câu hỏi để trong `questions.csv` cộng `qrels.csv` | jsonl chứa được các mục lồng nhau, còn câu hỏi thì sửa bằng bảng tính cho nhanh |
| Loại câu hỏi | 7 loại (có "dễ bịa") | **7 loại**, file hướng dẫn được bổ sung loại `unsupported` | Phân tích bắt buộc số 6 (trả lời không có căn cứ) cần loại này |
| Số câu | 200, chia dev 50 / test 150 | **Khoảng 300 câu, chia train 120 / dev 60 / test 120** theo nhóm câu hỏi | Mỗi người viết 60 câu. Train dùng để fine-tune PhoBERT hoặc cross-encoder |
| Đồng thuận nhãn | Cohen's kappa trên 20% | **Cohen's kappa trên 20%** | Chuẩn hơn tỷ lệ trùng khớp đơn thuần |
| Chia tập | Theo câu | **Theo `question_group_id`** | Tránh rò rỉ khi các cách hỏi khác nhau của cùng một ý rơi vào cả train lẫn test |
| Ai gán nhãn | Cả nhóm | Cả nhóm viết câu hỏi, **người gán nhãn phải khác người viết câu hỏi**. TV2 điều phối | Một người viết rồi tự gán nhãn cho chính câu mình viết thì nhãn sẽ thiên vị |

Ngoài các mục trên, những phần còn lại của lộ trình cũ vẫn giữ nguyên: thêm tiền tố `<tên thủ tục> | <tên mục>` vào mỗi đoạn, mẫu câu trả lời trích nguyên văn, ngưỡng từ chối τ chọn trên dev, app Streamlit dùng SQLite, dàn ý báo cáo.

---

## 2. Bảng phân công

| | Vai trò | Phụ trách chính | Bàn giao cho |
|---|---|---|---|
| **TV1** | Dữ liệu và baseline | B0 chốt phạm vi, B1 thu thập, B2 làm sạch và chia đoạn, freeze Dataset v1, TF-IDF và BM25, đào hard negative | Cả nhóm (kho), TV3 và TV4 (hard negative) |
| **TV2** | Bộ test và đánh giá | Hướng dẫn gán nhãn, điều phối viết câu hỏi và gán nhãn chéo, tính kappa, chia tập, viết **một script đánh giá chung**, chỉ số câu trả lời, trưởng nhóm phân tích lỗi (B6) | Cả nhóm (script đánh giá, split) |
| **TV3** | Truy hồi dense | Bi-encoder SBERT tiếng Việt, hybrid BM25 + SBERT, fine-tune bi-encoder bằng hard negative nếu kịp, tính "câu hỏi tương tự" cho app | TV4 (top-k ứng viên), TV5 (hàm tìm kiếm) |
| **TV4** | Xếp hạng lại và trả lời | Cross-encoder hoặc PhoBERT phân loại cặp, mẫu câu trả lời, ngưỡng từ chối τ, kiểm tra câu `unsupported` | TV5 (hàm `answer(question)`) |
| **TV5** | App và báo cáo | App Streamlit đủ 7 chức năng đề yêu cầu, SQLite lưu lịch sử và đánh giá, thống kê chủ đề, deploy, trưởng nhóm báo cáo và slide | Cả nhóm (link demo, khung báo cáo) |

**Việc chung của cả 5 người:** mỗi người viết 60 câu hỏi và gán nhãn câu của người khác. Mỗi người viết phần báo cáo cho phần mình phụ trách.

**Gợi ý xếp người:** người nào định theo hướng Data Engineering nên nhận TV1 (pipeline, kiểm tra chất lượng, freeze dữ liệu). Người mạnh về deep learning nhận TV3 và TV4. Người cẩn thận, viết lách tốt nhận TV2. Người thích làm giao diện nhận TV5.

---

## 3. Thứ tự làm và việc song song

```
Giai đoạn 1  Dữ liệu       TV1: B0 → B1 → B2 ─────────────────────► freeze Dataset v1
                           TV2: hướng dẫn gán nhãn + script đánh giá (chạy trên dữ liệu giả)
                           TV3, TV4: dựng code model trên 20 đoạn mẫu
                           TV5: khung app chạy với hàm giả
                           Cả nhóm: viết câu hỏi (chỉ cần danh sách thủ tục, chưa cần chunk)

Giai đoạn 2  Gán nhãn      Cả nhóm gán nhãn chéo → TV2 tính kappa, chia tập train/dev/test

Giai đoạn 3  Mô hình       TV1 baseline → TV3 dense + hybrid → TV4 rerank + τ
                           TV5 nối app với hàm thật

Giai đoạn 4  Phân tích     TV2 chạy test một lần cho mọi mô hình → cả nhóm viết B6
             và báo cáo    TV5 ghép báo cáo và slide, quay video demo dự phòng
```

**Hai điểm nghẽn:** (1) chunk_id phải ổn định thì mới gán nhãn được, nên TV1 cần xong B2 trước giai đoạn 2. (2) Script đánh giá của TV2 phải có trước khi chạy bất kỳ mô hình nào, để mọi mô hình đều đo bằng cùng một code.

---

## 4. Việc cụ thể từng người

### TV1. Dữ liệu và baseline

Làm theo file **Hướng dẫn Thành viên 1** (S01 đến D06, M01, M02). Riêng D04 và D05 thì TV1 chỉ làm phần của mình, TV2 làm điều phối.

- [ ] `docs/scope.md`, `data/raw/source_list.csv` (thủ tục hộ tịch của 1 cấp thực hiện, có URL và ngày lấy)
- [ ] `data/raw/` + `raw_manifest.csv` (sha256)
- [ ] `data/interim/docs.jsonl` gồm các mục: trình tự, cách thức, hồ sơ, thời hạn, lệ phí, cơ quan, đối tượng, điều kiện, căn cứ
- [ ] `data/processed/chunks.jsonl` (`chunk_id = <doc_id>__<muc>__<i>`, `text` có tiền tố, `text_seg` đã tách từ, `display_text` nguyên văn)
- [ ] Báo cáo kho: số thủ tục, số đoạn, độ dài min/median/max, danh sách các cặp thủ tục gần trùng
- [ ] TF-IDF và BM25 ở hai mức token (âm tiết và từ), chạy bằng script đánh giá của TV2
- [ ] `train_pairs.csv`: mỗi câu train có 1 đoạn đúng và 3 đến 5 hard negative lấy từ top-20 BM25
- [ ] `dataset_manifest.json`, chốt Dataset v1

### TV2. Bộ test và đánh giá

- [ ] `data/labels/annotation_guideline.md`: định nghĩa 7 loại câu, khi nào chấm relevance 2 hay 1, cách xử lý câu nhiều ý và câu thiếu thông tin
- [ ] Phân công: mỗi người viết 60 câu (khoảng 20 nhóm gốc, mỗi nhóm 3 cách hỏi), phủ đều các thủ tục và đủ 7 loại
- [ ] Phân công gán nhãn chéo: người gán nhãn khác người viết. Lấy 20% số câu cho 2 người gán độc lập, tính Cohen's kappa, họp chốt các câu lệch nhau
- [ ] `data/splits/`: chia theo nhóm, stratify theo loại câu, seed 42, train 120 / dev 60 / test 120
- [ ] `src/retrieval/evaluate.py`: nhận file kết quả chạy (`qid → danh sách chunk_id và điểm`), xuất Recall@1/3/5/10, MRR, NDCG@5/10, tách theo từng loại câu, cộng tỷ lệ từ chối đúng và từ chối nhầm
- [ ] Chỉ số câu trả lời: token F1 so với `answer_text`, tỷ lệ đúng nguồn, chấm tay faithfulness và answer relevance trên khoảng 50 câu (2 người chấm)
- [ ] Trưởng nhóm B6: mỗi loại câu có 1 số liệu, 2 đến 3 ví dụ thật và 1 đề xuất cải thiện

### TV3. Truy hồi dense

- [ ] Bi-encoder đã train sẵn (thử 2 model tiếng Việt, ví dụ `bkai-foundation-models/vietnamese-bi-encoder`, `keepitreal/vietnamese-sbert`). Kiểm tra model nhận văn bản đã tách từ hay chưa
- [ ] Lưu embedding và index (FAISS hoặc numpy) vào `artifacts/`
- [ ] Hybrid: chuẩn hóa điểm (min-max hoặc RRF) rồi cộng có trọng số với BM25, chọn trọng số trên dev
- [ ] Nếu kịp: fine-tune bi-encoder bằng `train_pairs.csv` (MultipleNegativesRankingLoss), so sánh với bản chưa fine-tune
- [ ] Hàm `similar_questions(q, k)` tìm trong các câu hỏi đã gán nhãn, **không lấy câu thuộc tập test**
- [ ] Hàm `retrieve(q, k=20)` trả về ứng viên cho TV4 và TV5

### TV4. Xếp hạng lại và trả lời

- [ ] Cross-encoder rerank top-20 của TV3 (thử model đa ngôn ngữ train sẵn trước)
- [ ] PhoBERT phân loại cặp (câu hỏi, đoạn) → liên quan hay không, fine-tune bằng `train_pairs.csv`. Đầu vào phải tách từ, tối đa 256 token
- [ ] Mẫu câu trả lời: `Theo thủ tục <X>, mục <Y>: "<trích nguyên văn>"` kèm URL nguồn
- [ ] Ngưỡng từ chối τ chọn trên dev. Báo cáo tỷ lệ từ chối đúng trên câu `out_of_scope` và `unsupported`, tỷ lệ từ chối nhầm trên câu trả lời được
- [ ] Câu nhiều ý: thử tách câu hỏi theo liên từ ("và", "còn") rồi trả lời từng ý, so sánh với không tách
- [ ] Hàm `answer(q)` trả về `{answer, sources[], similar_questions[], refused, scores}`

### TV5. App và báo cáo

- [ ] App Streamlit có đủ: ô hỏi, câu trả lời đề xuất, nguồn kèm đoạn trích tô sáng, câu hỏi tương tự, nút đánh giá, thông báo khi không có căn cứ, lịch sử truy vấn, thống kê chủ đề hỏi nhiều
- [ ] Làm trước với hàm `answer()` giả trả dữ liệu mẫu, khi TV4 xong thì thay bằng hàm thật
- [ ] SQLite: bảng `queries(id, time, question, refused, top_doc_id)` và bảng `feedback(query_id, rating)`. Thống kê chủ đề = đếm theo `top_doc_id`
- [ ] `@st.cache_resource` cho model và index. Deploy lên Streamlit Community Cloud, quay video demo dự phòng
- [ ] Khung báo cáo (7 mục như lộ trình cũ) và slide 12 đến 15 trang. Mỗi người điền phần của mình, TV5 thống nhất văn phong
- [ ] Chuẩn bị sẵn 7 câu demo, mỗi loại câu 1 câu

---

## 5. Quy ước chung

- Mỗi task một issue trên GitHub, một nhánh `feature/<ID>-<mo-ta>`, merge qua Pull Request và cần ít nhất 1 người khác review.
- Không ai đọc tập test trước khi các mô hình đã chốt tham số. TV2 giữ file test và chạy đánh giá cuối.
- Mọi mô hình ghi lại tên model, phiên bản thư viện và seed vào `results/`.
- Tuần nào cũng cập nhật trạng thái issue để nhìn tab Issues là biết tiến độ.

## 6. Checklist yêu cầu của đề

- [ ] Pipeline: tiền xử lý → chia đoạn → lập chỉ mục → truy hồi → xếp hạng → trả lời theo mẫu hoặc trích nguyên văn (TV1, TV3, TV4)
- [ ] Baseline TF-IDF hoặc BM25 (TV1)
- [ ] Ít nhất một mô hình cải tiến: SBERT, PhoBERT hoặc bi-encoder + cross-encoder (TV3, TV4)
- [ ] App: câu trả lời, nguồn kèm đoạn trích, câu hỏi tương tự, đánh giá, thông báo khi không có căn cứ, lịch sử và thống kê (TV5)
- [ ] Chỉ số truy hồi: Recall@k, MRR, NDCG@k (TV2)
- [ ] Chỉ số câu trả lời: EM hoặc F1, answer relevance, faithfulness, đúng nguồn, từ chối hợp lý (TV2, TV4)
- [ ] Phân tích đủ 6 trường hợp (TV2 điều phối, cả nhóm)

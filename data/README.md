# data/

Dữ liệu đi một chiều `raw → interim → processed`. Mỗi thư mục sau đều sinh lại được từ thư mục trước bằng code trong `src/data/`, vì vậy không sửa tay các file trong `interim/` và `processed/`.

| Thư mục / file | Nội dung | Ai tạo | Commit? |
|---|---|---|---|
| `raw/` | Văn bản gốc, bất biến: `.doc`/`.pdf` tải từ vbpl.vn hoặc vanban.chinhphu.vn, `.html` trang thuvienphapluat.vn lưu bằng Ctrl+S (khi bản PDF chỉ là scan) | TV1, tải tay | Có (file nhỏ) |
| `raw/source_list.csv` | Danh sách văn bản đã tải. Cột: `doc_id, title, source_type, url, issuing_level`, `amended_by` (văn bản sửa câu chữ, nạp vào `amendments.yaml`), `affected_by` (văn bản đổi hiệu lực mà không sửa câu chữ, ví dụ NĐ 120/2025), `effective_date` (ngày có hiệu lực), `status` (tình trạng hiệu lực tại ngày tải), `accessed_at, in_scope`. Ý nghĩa từng cột: mục 3.4 [hướng dẫn TV1](../docs/huong-dan-thanh-vien-1.md) | TV1, điền tay | Có |
| `raw/amendments.yaml` | Phần sửa đổi, bổ sung, bãi bỏ lấy từ văn bản sửa đổi, mỗi dòng một thao tác (xem mục bên dưới) | TV1, viết tay | Có |
| `interim/` | `<doc_id>.docx`: toàn văn bản gốc, chưa áp sửa đổi, là đầu vào duy nhất của code | TV1, dán Word | Có |
| `processed/units.jsonl`, `units_current.jsonl`, `amendments_log.csv` | Đơn vị Điều/Khoản/Điểm trước và sau khi áp `amendments.yaml`, log từng op | `parse_law.py`, `apply_amendments.py` | Không (sinh lại được) |
| `processed/chunks.jsonl` | 1 dòng = 1 đoạn để lập chỉ mục (1 Điều, hoặc 1 Khoản nếu Điều dài), đã áp `amendments.yaml`; schema ở mục bên dưới | `src/data/chunk.py` | Có |
| `processed/train_pairs.csv` | Cặp (câu hỏi, chunk) có nhãn 1/0, hard negative từ top-20 BM25 trên train, cho TV3 | `src/retrieval/hard_negatives.py` | Có |
| `labels/questions.csv` | Câu hỏi: `question_id, question_group_id, question, type, answer_text, source, annotator` | Cả nhóm viết, TV2 quản | Có |
| `labels/qrels.csv` | Nhãn liên quan: `question_id, chunk_id, relevance` (2 = trả lời trực tiếp, 1 = liên quan một phần) | Gán nhãn chéo, TV2 quản | Có |
| `splits/` | `question_group_id` của train / validation / test | `src/data/split.py`, TV2 quản | Có |
| `dataset_manifest.json` | Số văn bản, chunk, câu hỏi; sha256 của chunks/questions/qrels; seed, commit; `review_status` (draft/frozen) | `src/data/freeze.py` | Có |

## Văn bản trong `raw/`

| doc_id | Văn bản | File | Ghi chú |
|---|---|---|---|
| 60.2014.QH13 | Luật Hộ tịch 2014 | `60.2014.QH13.doc`, `VanBanGoc_60.2014.QH13.PDF` | 7 Chương, 77 Điều |
| 123.2015.ND-CP | Nghị định 123/2015/NĐ-CP hướng dẫn Luật Hộ tịch | `123.2015.ND-CP.html`, `123.2015.ND-CP.pdf` (bản scan) | 45 Điều; bị sửa bởi 87/2020, 104/2022, 07/2025, 18/2026 |
| 04.2020.TT-BTP | Thông tư 04/2020/TT-BTP hướng dẫn Luật Hộ tịch và NĐ 123 | `04.2020.TT-BTP.html`, `04.2020.TT-BTP.pdf` (bản scan) | 39 Điều; bị sửa bởi 09/2022/TT-BTP, 04/2024/TT-BTP |
| 07.2025.ND-CP | Nghị định 07/2025/NĐ-CP sửa đổi các Nghị định về hộ tịch, quốc tịch, chứng thực | `07.2025.ND-CP.html` | 5 Điều; chỉ Điều 2 (sửa NĐ 123) và Điều 3 (sửa NĐ 87/2020 về CSDL hộ tịch điện tử) liên quan hộ tịch. Hiệu lực từ ngày ký 09/01/2025 |
| 04.2024.TT-BTP | Thông tư 04/2024/TT-BTP sửa đổi TT 02/2020 (quốc tịch) và TT 04/2020 (hộ tịch) | `04.2024.TT-BTP.html` | 4 Điều; chỉ Điều 2 (sửa TT 04/2020) liên quan hộ tịch. Hiệu lực từ 06/06/2024 |
| 87.2020.ND-CP | Nghị định 87/2020/NĐ-CP về CSDL hộ tịch điện tử, đăng ký hộ tịch trực tuyến | `87.2020.ND-CP.html` | 25 Điều; văn bản gốc. Điều 25 khoản 2 bãi bỏ khoản 1, 2 Điều 12 NĐ 123; bị sửa bởi 07/2025 (Điều 3) |
| 104.2022.ND-CP | Nghị định 104/2022/NĐ-CP sửa đổi quy định về nộp, xuất trình sổ hộ khẩu, sổ tạm trú | `104.2022.ND-CP.html` | Văn bản sửa đổi; phần hộ tịch chỉ có Điều 13 khoản 2 (bãi bỏ một cụm từ ở khoản 1 Điều 2 NĐ 123) |
| 120.2025.ND-CP | Nghị định 120/2025/NĐ-CP quy định về phân định thẩm quyền của chính quyền địa phương 02 cấp trong lĩnh vực quản lý nhà nước của Bộ Tư pháp | `120.2025.ND-CP.html` | Thẩm quyền theo chính quyền 2 cấp, không sửa câu chữ văn bản khác (cột `affected_by`). Phụ lục mục I đổi thời hạn giải quyết (ví dụ kết hôn có yếu tố nước ngoài 05 ngày làm việc) nên chunk riêng Điều 4–8, 23, khoản 1 Điều 24 và mục I Phụ lục |
| 09.2022.TT-BTP | Thông tư 09/2022/TT-BTP bãi bỏ một số nội dung tại các Thông tư về trợ giúp pháp lý, hộ tịch | `interim/09.2022.TT-BTP.docx` (tải từ vbpl) | Chỉ Điều 2 (bỏ "sổ hộ khẩu, sổ tạm trú" ở khoản 1 Điều 8 và điểm b khoản 3 Điều 9 TT 04/2020) liên quan hộ tịch. Hiệu lực 01/01/2023 |
| 18.2026.ND-CP | Nghị định 18/2026/NĐ-CP sửa đổi một số nghị định để cắt giảm, đơn giản hóa thủ tục hành chính thuộc Bộ Tư pháp | `interim/18.2026.ND-CP.docx` (tải từ vbpl) | Chỉ Điều 13 (sửa khoản 1 Điều 2, khoản 2 Điều 22, 24, 27, Điều 26 NĐ 123) liên quan hộ tịch. Hiệu lực 15/01/2026 |

File `.html` là trang thuvienphapluat.vn lưu bằng Ctrl+S ("Trang web, chỉ HTML"), chỉ dùng để lưu bản gốc, code không đọc file html. Thay vào đó, phần toàn văn tiếng Việt được copy, dán vào Word bằng Keep Text Only rồi lưu thành `interim/<doc_id>.docx`, nhờ vậy cả 10 văn bản dùng chung một bộ đọc .docx. File `.pdf` của vanban.chinhphu.vn là bản scan, không lấy chữ ra được, chỉ giữ để đối chiếu.

## Văn bản sửa đổi: `raw/amendments.yaml`

Văn bản sửa đổi thường viết theo kiểu "sửa Điều X thành: ...", nếu chunk nguyên như vậy thì đoạn tách ra sẽ khó hiểu. Vì vậy nhóm chọn cách hợp nhất: code tách văn bản gốc trong `interim/`, áp từng dòng của `amendments.yaml` để ra bản đang có hiệu lực, rồi chỉ chunk bản này.

- Áp theo thứ tự ngày hiệu lực (07/2025 trước 18/2026). Một chỗ bị sửa nhiều lần thì lấy lần sửa sau cùng.
- Mỗi phần tử gồm `id`, `op`, `target` (chỗ bị sửa), `source` (Điều, Khoản trong văn bản sửa đổi chứa đoạn trích “...”; code tự lấy câu chữ mới từ đây) và `effective_date`. Giải thích đầy đủ ở đầu file yaml.
- 5 kiểu thao tác: `replace` (thay Điều/Khoản/Điểm), `insert` (thêm Khoản hoặc Điều như 28a), `repeal`, `remove_phrase`, `rename`.
- NĐ 120/2025 không sửa câu chữ nên không có op, chỉ ghi ở cột `affected_by` của `source_list.csv` và chunk mang theo cột này.
- Bỏ cụm từ theo 104/2022 và 09/2022 là `remove_phrase`. Câu chữ trong văn bản gốc có thể khác chữ hoa, dấu câu so với văn bản sửa đổi (ví dụ "Sổ hộ khẩu; Sổ tạm trú ;" trong TT 04/2020), phải kiểm tra tay.
- Bãi bỏ thì không đánh số lại Khoản. Unit vẫn nằm trong `units_current.jsonl` với `status=repealed`, tới bước chunk mới bỏ ra.

## Schema `processed/chunks.jsonl`

Mỗi dòng 1 chunk, do `python -m src.data.chunk` sinh ra:

| Trường | Ý nghĩa |
|---|---|
| `chunk_id` | Ổn định, qrels trỏ vào đây: `<doc_id>__D<dieu>`, thêm `__K<khoan>` khi tách theo Khoản, `__P<n>` khi Khoản dài phải chia phần; Phụ lục NĐ 120: `120.2025.ND-CP__PL1__K1__P1` |
| `chunk_text` | Tiền tố "văn bản \| Điều \| Khoản" + nội dung, đưa vào mô hình (mức âm tiết) |
| `text_seg` | `chunk_text` đã tách từ bằng underthesea, cho mô hình mức từ |
| `display_text` | Nguyên văn không tiền tố, để trích dẫn trên web |
| `doc_id`, `doc_title`, `dieu`, `dieu_title`, `khoan`, `phan`, `chuong`, `chuong_ten`, `muc`, `muc_ten` | Vị trí trong văn bản; `dieu` là chuỗi vì có Điều 28a |
| `n_tokens` | Số từ của `text_seg`, tối đa 200 |
| `amended_by`, `amendment_ops`, `affected_by`, `effective_from` | Văn bản và op đã sửa đoạn này, văn bản ảnh hưởng hiệu lực, ngày hiệu lực của lần sửa gần nhất |
| `url`, `accessed_at` | Nguồn và ngày tải, lấy từ `source_list.csv` |

## Quy tắc

- Không sửa `raw/`. Tải bản mới thì lưu thành file mới và ghi vào `source_list.csv`.
- Đổi cách chia đoạn sau khi đã gán nhãn là phải làm lại qrels. Hỏi TV1 và TV2 trước.
- Không ai mở tập test để chọn tham số hay ngưỡng từ chối.

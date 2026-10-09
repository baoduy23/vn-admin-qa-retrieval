# data/

Dữ liệu đi một chiều: `raw → interim → processed`. Thư mục sau luôn sinh lại được từ thư mục trước bằng code trong `src/data/`, nên **không sửa tay** file trong `interim/` và `processed/`.

| Thư mục / file | Nội dung | Ai tạo | Commit? |
|---|---|---|---|
| `raw/` | Văn bản gốc, **bất biến**: `.doc`/`.pdf` tải từ vbpl.vn hoặc vanban.chinhphu.vn, `.html` trang thuvienphapluat.vn lưu bằng Ctrl+S (khi bản PDF chỉ là scan) | TV1, tải tay | Có (file nhỏ) |
| `raw/source_list.csv` | Danh sách văn bản đã tải. Cột: `doc_id, title, source_type, url, issuing_level`, `amended_by` (văn bản sửa câu chữ, nạp vào `amendments.yaml`), `affected_by` (văn bản đổi hiệu lực mà không sửa câu chữ, ví dụ NĐ 120/2025), `effective_date` (ngày có hiệu lực), `status` (tình trạng hiệu lực tại ngày tải), `accessed_at, in_scope`. Ý nghĩa từng cột: mục 3.4 [hướng dẫn TV1](../docs/huong-dan-thanh-vien-1.md) | TV1, điền tay | Có |
| `raw/amendments.yaml` | Phần sửa đổi, bổ sung, bãi bỏ lấy từ văn bản sửa đổi, mỗi dòng một thao tác (xem mục bên dưới) | TV1, viết tay | Có |
| `interim/` | `<doc_id>.docx`: toàn văn **bản gốc, chưa áp sửa đổi**, là đầu vào duy nhất của code | TV1, dán Word | Có |
| `processed/chunks.jsonl` | 1 dòng = 1 đoạn để lập chỉ mục (1 Điều, hoặc 1 Khoản nếu Điều dài), **đã áp `amendments.yaml`** | Script tách luật (đang làm trong notebook) | Có |
| `labels/questions.csv` | Câu hỏi: `question_id, question_group_id, question, type, answer_text, source, annotator` | Cả nhóm viết, TV2 quản | Có |
| `labels/qrels.csv` | Nhãn liên quan: `question_id, chunk_id, relevance` (2 = trả lời trực tiếp, 1 = liên quan một phần) | Gán nhãn chéo, TV2 quản | Có |
| `splits/` | `question_group_id` của train / validation / test | TV2 | Có |

## Văn bản trong `raw/`

| doc_id | Văn bản | File | Ghi chú |
|---|---|---|---|
| 60.2014.QH13 | Luật Hộ tịch 2014 | `60.2014.QH13.doc`, `VanBanGoc_60.2014.QH13.PDF` | 7 Chương, 77 Điều |
| 123.2015.ND-CP | Nghị định 123/2015/NĐ-CP hướng dẫn Luật Hộ tịch | `123.2015.ND-CP.html`, `123.2015.ND-CP.pdf` (bản scan) | 45 Điều; bị sửa bởi 87/2020, 104/2022, 07/2025, 18/2026 |
| 04.2020.TT-BTP | Thông tư 04/2020/TT-BTP hướng dẫn Luật Hộ tịch và NĐ 123 | `04.2020.TT-BTP.html`, `04.2020.TT-BTP.pdf` (bản scan) | 39 Điều; bị sửa bởi 09/2022/TT-BTP, 04/2024/TT-BTP |
| 07.2025.ND-CP | Nghị định 07/2025/NĐ-CP sửa đổi các Nghị định về hộ tịch, quốc tịch, chứng thực | `07.2025.ND-CP.html` | 5 Điều; chỉ **Điều 2** (sửa NĐ 123) và Điều 3 (sửa NĐ 87/2020 về CSDL hộ tịch điện tử) liên quan hộ tịch. Hiệu lực từ ngày ký 09/01/2025 |
| 04.2024.TT-BTP | Thông tư 04/2024/TT-BTP sửa đổi TT 02/2020 (quốc tịch) và TT 04/2020 (hộ tịch) | `04.2024.TT-BTP.html` | 4 Điều; chỉ **Điều 2** (sửa TT 04/2020) liên quan hộ tịch. Hiệu lực từ 06/06/2024 |
| 87.2020.ND-CP | Nghị định 87/2020/NĐ-CP về CSDL hộ tịch điện tử, đăng ký hộ tịch trực tuyến | `87.2020.ND-CP.html` | 25 Điều; văn bản gốc. Điều 25 khoản 2 bãi bỏ khoản 1, 2 Điều 12 NĐ 123; bị sửa bởi 07/2025 (Điều 3) |
| 104.2022.ND-CP | Nghị định 104/2022/NĐ-CP sửa đổi quy định về nộp, xuất trình sổ hộ khẩu, sổ tạm trú | `104.2022.ND-CP.html` | Văn bản sửa đổi; phần hộ tịch chỉ có Điều 13 khoản 2 (bãi bỏ một cụm từ ở khoản 1 Điều 2 NĐ 123) |
| 120.2025.ND-CP | Nghị định 120/2025/NĐ-CP quy định về phân định thẩm quyền của chính quyền địa phương 02 cấp trong lĩnh vực quản lý nhà nước của Bộ Tư pháp | `120.2025.ND-CP.html` | Thẩm quyền theo chính quyền 2 cấp, không sửa câu chữ văn bản khác (cột `affected_by`). **Phụ lục mục I đổi thời hạn giải quyết** (ví dụ kết hôn có yếu tố nước ngoài 05 ngày làm việc) nên phải chunk riêng, không chỉ ghi `note` |
| 09.2022.TT-BTP | Thông tư 09/2022/TT-BTP bãi bỏ một số nội dung tại các Thông tư về trợ giúp pháp lý, hộ tịch | `interim/09.2022.TT-BTP.docx` (tải từ vbpl) | Chỉ **Điều 2** (bỏ "sổ hộ khẩu, sổ tạm trú" ở khoản 1 Điều 8 và điểm b khoản 3 Điều 9 TT 04/2020) liên quan hộ tịch. Hiệu lực 01/01/2023 |
| 18.2026.ND-CP | Nghị định 18/2026/NĐ-CP sửa đổi một số nghị định để cắt giảm, đơn giản hóa thủ tục hành chính thuộc Bộ Tư pháp | `interim/18.2026.ND-CP.docx` (tải từ vbpl) | Chỉ **Điều 13** (sửa khoản 1 Điều 2, khoản 2 Điều 22, 24, 27, Điều 26 NĐ 123) liên quan hộ tịch. Hiệu lực 15/01/2026 |

File `.html` là trang thuvienphapluat.vn lưu bằng Ctrl+S ("Trang web, chỉ HTML"), chỉ để lưu bản gốc. Code không đọc html: copy phần toàn văn tiếng Việt, dán vào Word bằng Keep Text Only, lưu thành `interim/<doc_id>.docx`. Cả 10 văn bản dùng chung một bộ đọc .docx. File `.pdf` của vanban.chinhphu.vn là bản scan, không trích được chữ, chỉ giữ để đối chiếu.

## Văn bản sửa đổi: `raw/amendments.yaml`

Văn bản sửa đổi viết kiểu "sửa Điều X thành: ...", để nguyên mà chunk thì đoạn rất khó hiểu. Nhóm chốt **hợp nhất**: code tách văn bản gốc trong `interim/`, rồi áp từng dòng của `amendments.yaml` để ra bản đang có hiệu lực, chỉ bản này được chunk.

- Áp theo thứ tự ngày hiệu lực (07/2025 trước 18/2026); cùng một chỗ bị sửa nhiều lần thì bản sau cùng thắng.
- Mỗi dòng gồm văn bản sửa đổi, văn bản bị sửa, vị trí (Điều, Khoản, Điểm), kiểu thao tác và câu chữ mới.
- 10 kiểu thao tác: `replace_dieu`, `replace_khoan`, `replace_diem`, `insert_khoan`, `insert_dieu`, `rename_dieu`, `repeal`, `remove_phrase`, `replace_phrase`, `note`.
- `note` dùng cho thay đổi không sửa câu chữ (thẩm quyền theo 120/2025): gắn ghi chú vào Điều liên quan, không đổi nội dung.
- Bỏ cụm từ theo 104/2022 và 09/2022 là `remove_phrase`. Câu chữ trong văn bản gốc có thể khác chữ hoa, dấu câu so với văn bản sửa đổi (ví dụ "Sổ hộ khẩu; Sổ tạm trú ;" trong TT 04/2020), phải kiểm tra tay.
- Chép câu chữ thì bỏ dấu “ ” ở đầu và cuối đoạn trích. Bãi bỏ thì không đánh số lại Khoản.
- Định dạng chi tiết từng trường chốt khi viết file.

## Schema `processed/chunks.jsonl`

Chốt khi chuyển notebook tách luật thành script. Tối thiểu cần: `chunk_id` (ổn định, qrels trỏ vào đây), `text` (đưa vào mô hình), `display_text` (trích dẫn trên web), nguồn (`doc_id`, `dieu`, `khoan`, `diem`) và `amended_by` (các văn bản đã sửa đoạn này). `dieu` lưu dạng **chuỗi** vì có Điều chèn thêm như `28a`.

## Quy tắc

- Không sửa `raw/`. Tải bản mới thì lưu thành file mới và ghi vào `source_list.csv`.
- Đổi cách chia đoạn sau khi đã gán nhãn là phải làm lại qrels. Hỏi TV1 và TV2 trước.
- Không ai mở tập test để chọn tham số hay ngưỡng từ chối.

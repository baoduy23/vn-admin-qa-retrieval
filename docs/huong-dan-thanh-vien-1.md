# Hướng dẫn công việc Thành viên 1

_Từ chốt phạm vi tài liệu đến Dataset v1 và baseline BM25_

**Dự án:** Đề tài 10. Hệ thống gợi ý câu trả lời cho câu hỏi hành chính
hoặc học vụ

**Vai trò:** Thành viên 1 phụ trách thu thập tài liệu, tiền xử lý, chia
đoạn, freeze Dataset v1 và baseline TF IDF, BM25. Bộ câu hỏi do cả nhóm
viết, Thành viên 2 điều phối (xem file Lộ trình và phân công)

**Phạm vi đã chốt:** lĩnh vực hộ tịch. Kho gồm 10 văn bản: Luật Hộ tịch
60/2014/QH13, Nghị định 123/2015/NĐ-CP, Thông tư 04/2020/TT-BTP và các
văn bản sửa đổi, hướng dẫn liên quan (danh sách trong
data/raw/source_list.csv, lý do trong docs/scope.md). Kho phản ánh
quy định có hiệu lực tại 09/10/2026, dùng được đến 28/02/2027. Tải tay từ vbpl.vn; văn bản chỉ có PDF scan thì lấy toàn
văn trên thuvienphapluat.vn. Không cào web.

**Repository:** repo này

**Đầu ra bắt buộc:** Dataset v1 gồm văn bản gốc, chunks, questions,
qrels, split theo nhóm câu hỏi, báo cáo chất lượng và kết quả baseline

> **Kết luận quan trọng.** Làm trọn một lĩnh vực, rồi dồn công vào bộ
> câu hỏi có gán đoạn đúng. Mọi chỉ số Recall@k, MRR, NDCG@k và việc
> huấn luyện cross-encoder đều phụ thuộc vào bộ câu hỏi này, không phụ
> thuộc vào số lượng văn bản.
>
> **Phạm vi tài liệu.** Tài liệu mô tả tuần tự các bước S01 đến D06 cho
> dữ liệu, M01 đến M02 cho baseline và chuẩn bị dữ liệu cho mô hình cải
> tiến, sau đó là quy trình Pull Request và bàn giao cho các thành viên
> làm Sentence-BERT, PhoBERT, cross-encoder và giao diện.

## 1 Tổng quan trách nhiệm của Thành viên 1

| **Giai đoạn** | **Công việc**                                         | **Đầu ra chính**                                   |
|---------------|-------------------------------------------------------|----------------------------------------------------|
| S01           | Chốt phạm vi và danh sách văn bản                     | docs/scope.md, data/raw/source_list.csv            |
| D01           | Tải văn bản gốc (vbpl.vn, thuvienphapluat.vn)         | data/raw/ (.doc, .pdf, .html), .docx trong interim/ |
| D02           | Tách cấu trúc Chương, Điều, Khoản; làm sạch; EDA      | bảng Điều/Khoản, báo cáo chất lượng                |
| D03           | Chia đoạn (chunking)                                  | chunks.jsonl có chunk_id ổn định                   |
| D04           | Viết câu hỏi phần mình, gán nhãn chéo (TV2 điều phối) | questions.csv, qrels.csv                           |
| D05           | Kiểm tra chất lượng nhãn (TV2 chủ trì)                | Cohen kappa, danh sách sửa nhãn                    |
| D06           | Chia tập theo nhóm câu hỏi và Freeze Dataset v1       | splits, dataset_manifest.json                      |
| M01           | Baseline TF IDF và BM25                               | Index, bảng Recall@k, MRR, NDCG@k                  |
| M02           | Đào hard negative và bàn giao                         | train_pairs.csv cho bi-encoder, cross-encoder      |

## 2 Cấu trúc thư mục và nguyên tắc lưu

```
data/
  raw/source_list.csv          danh sách văn bản: số hiệu, tên, url, ngày tải
  raw/<so_hieu>.doc/.pdf/.html file gốc (vbpl.vn, vanban.chinhphu.vn, TVPL)
  interim/<so_hieu>.docx       bản .docx để code đọc
  processed/chunks.jsonl
  labels/questions.csv
  labels/qrels.csv
  labels/annotation_guideline.md
  splits/train_qgroups.csv
  splits/validation_qgroups.csv
  splits/test_qgroups.csv
configs/
  preprocessing.yaml
  chunking.yaml
  retrieval_baseline.yaml
notebooks/                     thử nghiệm (ví dụ 01_doc_luat.ipynb)
src/data/                      text_utils (làm sạch, normalize_tone), script tách luật
src/retrieval/                 tfidf, bm25, evaluate
tests/
results/data_quality/
results/retrieval/
artifacts/                     index, vectorizer
```

- data/raw: bản gốc tải về, bất biến. Không sửa bằng tay, không ghi đè.
  URL và ngày tải ghi trong source_list.csv.

- data/interim: bản .docx chuyển từ file gốc, đọc được bằng code.

- data/processed: các đoạn dùng để lập chỉ mục. Mọi mô hình truy hồi
  dùng chung file này.

- data/labels: câu hỏi và nhãn đoạn đúng. Đây là tài sản quan trọng nhất
  của nhóm.

- data/splits: chỉ lưu question_group_id của từng tập, không sao chép dữ
  liệu.

- Code thử trong notebooks/ trước, chạy ổn thì chuyển thành script trong
  src/data/ để cả nhóm chạy lại được bằng một lệnh.

## 3 S01 Chốt phạm vi và nguồn tài liệu

### 3.1 Vì sao chỉ làm một lĩnh vực

- Mỗi văn bản thêm vào kéo theo hàng chục câu hỏi phải viết và gán nhãn.
  Kho tăng thì công gán nhãn tăng theo, trong khi thời gian dự án không
  đổi.

- Lấy rải rác nhiều lĩnh vực (hộ tịch, đất đai, cư trú) thì lĩnh vực nào
  cũng mỏng, hỏi sâu là hệ thống trả lời sai, và phần phân tích lỗi
  không có gì để nói.

- Đất đai, cư trú, thuế dùng làm câu hỏi ngoài phạm vi (out_of_scope).

### 3.2 Quyết định của nhóm

| **Mục**           | **Đã chốt**                                                                 |
|-------------------|-----------------------------------------------------------------------------|
| Lĩnh vực          | Hộ tịch                                                                     |
| Nguồn             | vbpl.vn; thuvienphapluat.vn khi văn bản chỉ có PDF scan                       |
| Cách lấy          | Tải tay file .doc và PDF bản gốc, không cào web                             |
| Văn bản trong kho | 10 văn bản: Luật 60/2014, NĐ 123/2015, TT 04/2020, NĐ 87/2020 và 6 văn bản sửa đổi, ảnh hưởng hiệu lực (xem source_list.csv) |
| Văn bản sửa đổi   | Không chunk riêng; áp vào văn bản gốc qua data/raw/amendments.yaml (mục 5.4). Riêng NĐ 120/2025 (không sửa câu chữ) thì chunk Điều 4–8 và mục I Phụ lục |
| Cấu trúc tài liệu | Chương, (Mục), Điều, Khoản, Điểm                                             |
| Viết câu hỏi      | Đóng vai người dân hỏi về đăng ký khai sinh, kết hôn, khai tử, cải chính... |

### 3.3 Mở rộng kho (nếu cần)

- Chi tiết hồ sơ, giấy tờ, cách làm từng trường hợp thường nằm ở nghị
  định và thông tư hướng dẫn, nên kho đã có Nghị định 123/2015 và Thông
  tư 04/2020. Chỉ thêm văn bản khác khi bộ câu hỏi cần mà kho hiện tại
  không có đáp án.

- Trước khi thêm, xem tab hiệu lực trên vbpl.vn: chỉ lấy văn bản còn
  hiệu lực tại ngày tải, ghi văn bản sửa đổi nếu có.

- Không lấy bài tổng hợp trên blog hay diễn đàn làm tài liệu gốc.

### 3.4 File source_list.csv

| **Cột**       | **Ý nghĩa**                                                         |
|---------------|---------------------------------------------------------------------|
| doc_id        | Số hiệu viết không dấu, ví dụ 60.2014.QH13, 123.2015.ND-CP; không đổi về sau |
| title         | Tên văn bản, ví dụ Luật Hộ tịch                                     |
| source_type   | legal_text                                                          |
| url           | Đường dẫn trang văn bản đã lấy chữ (vbpl.vn hoặc thuvienphapluat.vn) |
| issuing_level | Cơ quan ban hành: Quốc hội, Chính phủ, Bộ Tư pháp                   |
| amended_by    | Văn bản sửa câu chữ văn bản này (nếu có), ghi doc_id, nhiều văn bản cách nhau dấu ;, ví dụ 87.2020.ND-CP;07.2025.ND-CP. Là nguồn để viết amendments.yaml |
| affected_by   | Văn bản đổi hiệu lực, thẩm quyền, thời hạn mà không sửa câu chữ (nếu có), ví dụ 120.2025.ND-CP |
| effective_date | Ngày văn bản có hiệu lực, định dạng YYYY-MM-DD                     |
| status        | Tình trạng hiệu lực tại ngày tải, ghi theo tab hiệu lực của trang nguồn: Còn hiệu lực, Hết hiệu lực một phần, Hết hiệu lực |
| accessed_at   | Ngày tải, định dạng YYYY-MM-DD                                      |
| in_scope      | yes hoặc no; văn bản ngoài phạm vi vẫn ghi lại để làm câu hỏi từ chối |

## 4 D01 Tải văn bản gốc

1.  Mở trang văn bản trên vbpl.vn, kiểm tra tình trạng hiệu lực.

2.  Tải file gốc (.doc và PDF nếu có) về data/raw, đặt tên theo số hiệu.
    Không đổi tên hay sửa nội dung file gốc.

    Nếu chỉ có PDF scan (ví dụ file .signed.pdf của vanban.chinhphu.vn:
    chuyển sang text chỉ ra dòng "Ký bởi..." của chữ ký số), thì vẫn giữ
    file scan trong data/raw để đối chiếu, rồi mở văn bản trên
    thuvienphapluat.vn: Ctrl+S lưu trang thành data/raw/<so_hieu>.html,
    và copy phần toàn văn (dán vào Word chọn Keep Text Only) để làm bản
    .docx. Không cào TVPL bằng code.

3.  Chuyển .doc sang .docx (Word: Save As, hoặc LibreOffice) và lưu vào
    data/interim/<doc_id>.docx. Văn bản lấy từ TVPL thì copy phần toàn
    văn, dán vào Word bằng Keep Text Only rồi lưu cùng chỗ. Code chỉ đọc
    bản .docx, không đọc html.

4.  Ghi một dòng vào source_list.csv: url, ngày tải. Tải bản mới thì lưu
    thành file mới, không ghi đè.

5.  Mở bản .docx kiểm tra: đủ số Điều (ví dụ NĐ 123: 45, TT 04/2020:
    39), không mất bảng, không lẫn chú thích, header trang, ô "Từ khóa",
    danh sách văn bản liên quan hay quảng cáo của trang nguồn.

**Input:** trang văn bản trên vbpl.vn hoặc thuvienphapluat.vn. **Output:** data/raw/,
data/interim/, data/raw/source_list.csv.

## 5 D02 Tách cấu trúc, làm sạch và EDA

### 5.1 Tách theo cấu trúc văn bản luật

Văn bản luật có cấu trúc cố định. Tách thành từng đơn vị có địa chỉ rõ
ràng thay vì gộp thành một khối văn bản; việc này giúp chunking và hiển
thị nguồn (Điều mấy, khoản mấy) chính xác hơn.

| **Trường**  | **Ví dụ**                                        |
|-------------|--------------------------------------------------|
| doc_id      | 60.2014.QH13                                     |
| chuong      | Chương II. Đăng ký hộ tịch tại Ủy ban nhân dân cấp xã |
| muc         | Mục 1. Đăng ký khai sinh (để trống nếu không có) |
| dieu        | "16", "28a" (lưu dạng chuỗi)                     |
| tieu_de     | Thủ tục đăng ký khai sinh                        |
| khoan       | 1, 2, 3... (để trống nếu Điều không chia khoản)  |
| diem        | a, b, c, đ... (để trống nếu Khoản không chia điểm) |
| noi_dung    | Nguyên văn nội dung Điều hoặc Khoản              |

Nhận diện bằng mẫu đầu dòng: "Chương" (không phân biệt hoa thường),
"Mục <số>.", "Điều <số>." với số có thể kèm chữ (regex `(\d+[a-z]?)`
để bắt Điều 28a), "<số>." cho khoản, "<chữ cái>)" cho điểm.

Kiểm tra tối thiểu: NĐ 123 ra 45 Điều, Luật 60 ra 77 Điều, Điều 12
NĐ 123 có 4 khoản, Điều 4 khoản 1 NĐ 123 có điểm c.

### 5.2 Làm sạch văn bản

- Chuẩn hóa Unicode về NFC và thống nhất kiểu bỏ dấu (hoà → hòa, huỷ →
  hủy) bằng `normalize_tone` trong src/data/text_utils.py. Câu hỏi người
  dùng cũng phải qua đúng hàm này.

- Loại header, footer, số trang, phần chữ ký và nơi nhận ở cuối văn bản.
  Rule loại phải cụ thể và được log số lần tác động.

- Giữ nguyên số liệu, ngày, số hiệu văn bản, tên cơ quan. Đây là thông
  tin người dùng hỏi nhiều nhất.

- Không lowercase và không bỏ dấu ở bước này. Các biến đổi đó thuộc cấu
  hình của từng mô hình truy hồi.

### 5.3 EDA và kiểm tra chất lượng

| **Kiểm tra**   | **Đạt khi**                                               | **Nếu không đạt**                         |
|----------------|-----------------------------------------------------------|-------------------------------------------|
| Số Điều        | Khớp số Điều của văn bản gốc, đánh số liên tục            | Sửa regex nhận diện Điều                  |
| Phân bổ        | Có số Điều theo từng Chương                               | Kiểm tra lỗi nhận diện Chương             |
| Độ dài         | Có min, median, max số từ mỗi Điều; biết Điều nào quá dài | Đánh dấu Điều cần tách theo Khoản         |
| Rỗng           | Không có Điều nào nội dung rỗng                           | Tra lại file gốc                          |
| Trùng nội dung | Không có hai đoạn giống hệt nhau                          | Giữ một bản, log lý do                    |
| Hiệu lực       | Điều bị bãi bỏ hoặc sửa đổi được đánh dấu                 | Ghi chú trong source_list, cập nhật bản mới |

**Output:** bảng Điều/Khoản (trong notebook hoặc file trung gian),
results/data_quality/corpus_report.md.

### 5.4 Áp văn bản sửa đổi (amendments.yaml)

Văn bản sửa đổi (07/2025/NĐ-CP, 04/2024/TT-BTP...) viết kiểu "sửa Điều X
thành: ...", chunk nguyên văn thì đoạn rất khó hiểu và dễ trả về Điều
cũ đã bị sửa. Vì vậy kho dùng bản hợp nhất:

1.  Đọc phần sửa đổi trong văn bản sửa đổi, mỗi thay đổi ghi thành một
    dòng trong data/raw/amendments.yaml: văn bản sửa đổi, văn bản bị
    sửa, vị trí (Điều, Khoản, Điểm), kiểu thao tác, câu chữ mới.

2.  10 kiểu thao tác: replace_dieu, replace_khoan, replace_diem,
    insert_khoan, insert_dieu, rename_dieu, repeal, remove_phrase,
    replace_phrase, note. Bỏ cụm từ "sổ hộ khẩu, sổ tạm trú" (104/2022,
    09/2022) là remove_phrase; câu chữ trong văn bản gốc có thể khác chữ
    hoa, dấu câu nên phải kiểm tra tay. Thẩm quyền theo chính quyền 2
    cấp (NĐ 120/2025) không sửa câu chữ, ghi bằng note gắn vào Điều liên
    quan; thời hạn mới trong mục I Phụ lục NĐ 120 thì chunk riêng, không
    chỉ ghi note.

3.  Chép câu chữ thì bỏ dấu “ ” ở đầu và cuối đoạn trích. Bãi bỏ thì
    không đánh số lại Khoản.

4.  Áp theo thứ tự ngày hiệu lực của văn bản sửa đổi: 87/2020 →
    104/2022 → 09/2022 → 04/2024 → 07/2025 → 18/2026. Cùng một Khoản bị
    sửa nhiều lần (ví dụ khoản 1 Điều 2 NĐ 123 bị 07/2025 rồi 18/2026
    thay) thì bản sau cùng thắng.

5.  Code áp amendments.yaml sau bước tách cấu trúc, trước bước chunk.
    Đoạn bị sửa ghi lại amended_by để hiển thị nguồn.

## 6 D03 Chia đoạn (chunking)

Đề yêu cầu hiển thị nguồn và đoạn trích, nên đoạn phải đủ ngắn để trích
nguyên văn nhưng đủ dài để tự đứng được.

1.  Mỗi Điều là một đoạn.

2.  Điều dài hơn 200 từ (sau tách từ) thì tách theo Khoản, mỗi Khoản một
    đoạn. Ngưỡng 200 chừa chỗ cho câu hỏi khi ghép cặp vào PhoBERT hoặc
    cross-encoder (giới hạn 256 subword).

3.  Gắn tiền tố ngữ cảnh vào văn bản đoạn, ví dụ "Luật Hộ tịch 2014 |
    Điều 16. Thủ tục đăng ký khai sinh | Khoản 1: ...". Không có tiền tố
    thì một Khoản đứng riêng không biết thuộc Điều nào.

4.  Tạo chunk_id ổn định ghép từ số hiệu, Điều, Khoản, ví dụ
    60.2014.QH13\_\_D16\_\_K1 hoặc 123.2015.ND-CP\_\_D28a. Không dùng
    số dòng làm ID. Format cuối cùng chốt theo notebook 01_doc_luat.

5.  Lưu chunk_text (có tiền tố, dùng cho mô hình) và display_text
    (nguyên văn, dùng để hiển thị trích dẫn).

| **Trường trong chunks.jsonl** | **Ý nghĩa**                                            |
|-------------------------------|--------------------------------------------------------|
| chunk_id                      | Khóa chính, ổn định qua các phiên bản                  |
| doc_id, dieu, khoan           | Thuộc văn bản nào, Điều nào (chuỗi), Khoản nào         |
| amended_by                    | Các văn bản đã sửa đoạn này (rỗng nếu chưa bị sửa)     |
| chunk_text                    | Có tiền tố ngữ cảnh, đã làm sạch                       |
| display_text                  | Nguyên văn để trích dẫn                                |
| url, accessed_at              | Nguồn tham chiếu hiển thị trên giao diện               |
| text_seg                      | chunk_text đã tách từ, dùng cho BM25 mức từ và PhoBERT |
| n_tokens                      | Số token sau tách từ                                   |

### 6.1 Biến thể tách từ

- Trường chunk_text giữ văn bản chưa tách từ, dùng cho Sentence-BERT đa
  ngôn ngữ và BM25 mức âm tiết.

- Trường text_seg tách từ bằng một công cụ duy nhất đã chốt
  (underthesea, pyvi hoặc VnCoreNLP), ghi tên và phiên bản vào
  preprocessing.yaml. PhoBERT yêu cầu đầu vào đã tách từ.

- Không loại stopword mặc định. Nếu muốn thử thì làm như một biến thể
  ablation của BM25, vì từ như "không", "chưa" có thể đổi nghĩa câu hỏi.

### 6.2 Kiểm tra tự động

| **Assertion** | **Kỳ vọng**                                      |
|---------------|--------------------------------------------------|
| chunk_id      | Duy nhất; mọi chunk có cả chunk_text và text_seg |
| Bao phủ       | Mọi Điều có ít nhất một chunk                    |
| Rỗng          | 0 chunk rỗng                                     |
| Độ dài        | Không chunk nào vượt ngưỡng token đã cấu hình    |
| Tái lập       | Chạy hai lần cho cùng hash file đầu ra           |

## 7 D04 Xây bộ câu hỏi và gán nhãn

> **Đây là phần quan trọng nhất.** Mục tiêu khoảng 300 câu hỏi (5 người,
> mỗi người khoảng 60 câu), mỗi câu gán một hoặc vài chunk đúng. Thà ít
> văn bản mà nhiều câu hỏi chất lượng, còn hơn nhiều văn bản mà câu hỏi
> sơ sài.

### 7.1 Quy trình viết câu hỏi

1.  Với mỗi Điều quan trọng (đăng ký khai sinh, kết hôn, khai tử, cải
    chính...), viết một câu hỏi gốc cho mỗi ý người dân hay hỏi (giấy
    tờ, thời hạn, nộp ở đâu, ai được làm). Mỗi câu gốc là một
    question_group.

2.  Với mỗi câu gốc, viết thêm 2 đến 3 cách hỏi khác: văn nói, không
    dấu, viết tắt, dùng từ đời thường thay thuật ngữ. Ví dụ "giấy khai
    sinh cho con mới đẻ cần gì" thay cho "thành phần hồ sơ đăng ký khai
    sinh".

3.  Thêm câu hỏi theo từng loại phân tích bắt buộc ở bảng 7.2.

4.  Viết câu hỏi trước khi nhìn kỹ đoạn văn, tránh chép nguyên cụm từ
    trong tài liệu. Câu hỏi giống tài liệu quá thì BM25 thắng dễ và kết
    quả không phản ánh thực tế.

5.  Nếu dùng mô hình ngôn ngữ để sinh thêm cách hỏi thì đánh dấu source
    = generated và người trong nhóm phải duyệt từng câu. Tập test nên ưu
    tiên câu do người viết.

### 7.2 Phân loại câu hỏi theo yêu cầu phân tích của đề

| **type**       | **Mô tả**                                       | **Ví dụ**                                       | **Tỷ lệ gợi ý** |
|----------------|-------------------------------------------------|-------------------------------------------------|-----------------|
| direct         | Hỏi gần sát tài liệu                            | Đăng ký khai sinh cần những giấy tờ gì          | 20%             |
| paraphrase     | Diễn đạt khác tài liệu                          | Con mới sinh thì làm giấy tờ gì ở phường        | 25%             |
| underspecified | Thiếu thông tin                                 | Đăng ký mất bao lâu                             | 10%             |
| multi_intent   | Nhiều ý trong một câu                           | Kết hôn cần giấy gì và nộp ở đâu                | 10%             |
| confusable     | Dễ nhầm giữa tài liệu gần giống                 | Vợ người nước ngoài thì đăng ký kết hôn thế nào | 15%             |
| out_of_scope   | Ngoài phạm vi, phải từ chối                     | Thủ tục tách thửa đất như thế nào               | 10%             |
| unsupported    | Trong phạm vi nhưng kho không có đáp án, dễ bịa | Đăng ký khai sinh trễ bị phạt bao nhiêu         | 10%             |

### 7.3 Định dạng file

| **questions.csv** | **Ý nghĩa**                                                        |
|-------------------|--------------------------------------------------------------------|
| question_id       | Mã câu hỏi, ví dụ Q0001                                            |
| question_group_id | Nhóm câu gốc; các cách hỏi khác của cùng một ý có cùng group       |
| question          | Nội dung câu hỏi                                                   |
| type              | Một trong bảy loại ở bảng 7.2                                      |
| answer_text       | Câu trả lời chuẩn ngắn, dùng tính exact match hoặc token F1 nếu có |
| source            | human hoặc generated                                               |
| annotator         | Người viết                                                         |

| **qrels.csv** | **Ý nghĩa**                                                      |
|---------------|------------------------------------------------------------------|
| question_id   | Khóa ngoại tới questions.csv                                     |
| chunk_id      | Đoạn liên quan                                                   |
| relevance     | 2 là trả lời trực tiếp, 1 là liên quan một phần; dùng cho NDCG@k |

Câu hỏi out_of_scope và unsupported không có dòng nào trong qrels. Hệ
thống được tính đúng khi từ chối trả lời.

### 7.4 Hướng dẫn gán nhãn

- Viết annotation_guideline.md trước khi gán nhãn: khi nào gán 2, khi
  nào gán 1, xử lý câu nhiều ý thế nào (gán đủ chunk cho mọi ý).

- Với câu underspecified, gán các chunk của mọi Điều có thể đúng và
  ghi chú cần hỏi lại người dùng.

- Không gán nhãn bằng cách xem kết quả BM25 trả về rồi chọn. Làm vậy sẽ
  thiên vị baseline.

## 8 D05 Kiểm tra chất lượng nhãn

1.  Người gán nhãn phải khác người viết câu hỏi. Lấy ngẫu nhiên khoảng
    20% số câu cho hai người gán độc lập.

2.  Tính Cohen kappa trên quyết định liên quan hay không của từng cặp
    (câu hỏi, chunk). Kappa dưới khoảng 0,6 thì sửa guideline và gán
    lại; các câu lệch nhau thì họp chốt. Đưa con số kappa vào báo cáo.

3.  Loại câu hỏi trùng hoặc gần trùng trong cùng nhóm; câu trùng giữa
    hai nhóm khác nhau thì gộp nhóm.

4.  Thống kê số câu theo type, theo Chương, theo Điều. Điều quan trọng
    nào ít câu hỏi thì bổ sung.

**Output:** results/data_quality/label_agreement.md,
results/data_quality/question_stats.csv.

## 9 D06 Chia tập và Freeze Dataset v1

### 9.1 Chia theo nhóm câu hỏi

> **Lỗi rò rỉ phải tránh.** Các cách hỏi khác của cùng một ý phải nằm
> chung một tập. Nếu câu gốc ở train mà câu diễn đạt lại ở test thì
> cross-encoder học thuộc và chỉ số test cao giả.

1.  Chia theo question_group_id với tỷ lệ gợi ý 40/20/40 cho train,
    validation, test (khoảng 120/60/120 câu). Train dùng để fine-tune
    PhoBERT hoặc cross-encoder; nếu nhóm không fine-tune thì gộp train
    vào test.

2.  Stratify theo type để tập nào cũng có đủ bảy loại, đặc biệt là
    out_of_scope và unsupported.

3.  Dùng seed cố định, ví dụ 42, ghi vào configs/split.yaml.

4.  Khóa test: không dùng test để chọn k, ngưỡng từ chối hay siêu tham
    số.

Lưu ý: kho tài liệu (chunks) dùng chung cho cả ba tập. Chỉ câu hỏi được
chia.

### 9.2 Tiêu chí được phép freeze

- File gốc trong data/raw còn nguyên, không bị sửa.

- Mọi tài liệu có nguồn, ngày tải và căn cứ còn hiệu lực.

- chunk_id ổn định, tests chunking pass.

- Mỗi question_id hợp lệ có ít nhất một dòng qrels, trừ out_of_scope và
  unsupported.

- Mọi chunk_id trong qrels tồn tại trong chunks.jsonl.

- Đã tính Cohen kappa và sửa guideline nếu cần.

- Split theo nhóm, không có question_group_id xuất hiện ở hai tập.

- Nhóm đã duyệt báo cáo chất lượng.

### 9.3 Manifest gợi ý

> dataset_version: v1
>
> domain: ho_tich
>
> n_documents: \<n\>
>
> n_chunks: \<n\>
>
> n_questions: \<n\>
>
> n_question_groups: \<n\>
>
> chunks_sha256: \<hash\>
>
> qrels_sha256: \<hash\>
>
> segmenter: \<ten-thu-vien\>==\<phien-ban\>
>
> random_seed: 42
>
> source_commit: \<git-sha\>
>
> created_at: \<YYYY-MM-DD\>
>
> review_status: approved

## 10 M01 Baseline TF IDF và BM25

### 10.1 Cách chạy

- Lập chỉ mục trên toàn bộ chunks. Không cần fit trên train vì baseline
  không học từ câu hỏi; chỉ chọn tham số trên validation.

- Thử hai mức token: âm tiết (chunk_text) và từ đã tách (text_seg). Câu
  hỏi phải tách từ bằng đúng công cụ đã dùng cho chunk.

- TF IDF: thử n gram 1 đến 2, sublinear_tf, cosine similarity.

- BM25: thử k1 trong khoảng 1,2 đến 2,0 và b khoảng 0,75 trên
  validation, chốt rồi mới chạy test một lần.

### 10.2 Công thức chỉ số

Với Q là tập câu hỏi có nhãn, rel(q) là tập chunk đúng của q, rank_q là
vị trí chunk đúng đầu tiên:

> Recall@k = (1/\|Q\|) \* Σ_q \|top_k(q) ∩ rel(q)\| / \|rel(q)\|
>
> MRR = (1/\|Q\|) \* Σ_q 1 / rank_q (= 0 nếu không có chunk đúng)
>
> DCG@k = Σ\_{i=1..k} (2^{rel_i} - 1) / log2(i + 1)
>
> NDCG@k = DCG@k / IDCG@k

- Báo cáo k = 1, 3, 5, 10. Tách bảng theo type để có sẵn số liệu cho
  phần phân tích bắt buộc.

- Với out_of_scope và unsupported: chọn ngưỡng điểm trên validation;
  dưới ngưỡng thì từ chối. Báo tỷ lệ từ chối đúng và tỷ lệ từ chối nhầm
  câu hợp lệ.

### 10.3 Bảng kết quả mẫu cần nộp

| **Mô hình** | **Token** | **R@1** | **R@5** | **MRR** | **NDCG@10** | **Từ chối đúng** |
|-------------|-----------|---------|---------|---------|-------------|------------------|
| TF IDF      | âm tiết   |         |         |         |             |                  |
| TF IDF      | từ        |         |         |         |             |                  |
| BM25        | âm tiết   |         |         |         |             |                  |
| BM25        | từ        |         |         |         |             |                  |

## 11 M02 Chuẩn bị dữ liệu cho mô hình cải tiến

1.  Với mỗi câu hỏi trong train, lấy top 20 của BM25. Chunk không nằm
    trong qrels là hard negative.

2.  Tạo train_pairs.csv gồm question_id, chunk_id, label (1 hoặc 0). Tỷ
    lệ gợi ý 1 positive với 3 đến 5 hard negative.

3.  Ưu tiên hard negative thuộc Điều gần giống, ví dụ đăng ký khai sinh
    tại cấp xã và đăng ký khai sinh có yếu tố nước ngoài. Đây là thứ
    giúp cross-encoder phân biệt hai trường hợp này.

4.  Chỉ đào hard negative trên train. Không đụng tới validation và test.

5.  Bàn giao cho thành viên phụ trách Sentence-BERT và PhoBERT: đường
    dẫn file, cách đọc, kết quả baseline để làm mốc so sánh.

## 12 Quy trình commit và Pull Request

> git switch main
>
> git pull --ff-only origin main
>
> git switch -c feature/D04-question-labels
>
> git status
>
> git diff
>
> git add \<cac-file-lien-quan\>
>
> git commit -m "feat(D04): add labelled questions and qrels"
>
> git push -u origin feature/D04-question-labels

- Mỗi giai đoạn một nhánh riêng; không commit trực tiếp lên main.

- Base branch là main. Hướng dẫn Git từng bước cho cả nhóm:
  [huong-dan-git.md](huong-dan-git.md). Mô tả PR gồm Task ID, thay đổi, lệnh chạy, kết
  quả và điểm reviewer cần xem.

- File .doc/.PDF gốc nếu lớn (vài MB trở lên) thì không commit thẳng;
  lưu trên Drive chung và ghi đường dẫn trong source_list.csv.

## 13 Checklist bàn giao cho nhóm

- docs/scope.md ghi rõ lĩnh vực đã chọn và lý do.

- source_list.csv đủ 10 văn bản: số hiệu, URL, ngày hiệu lực, tình trạng hiệu lực, ngày tải.

- amendments.yaml đủ các thay đổi của văn bản sửa đổi; chunks.jsonl là bản hợp nhất.

- Văn bản đã tách Chương/Điều/Khoản đủ trường; báo cáo EDA kho văn bản.

- chunks.jsonl có chunk_text, text_seg, display_text; tests pass.

- questions.csv, qrels.csv, annotation_guideline.md; đủ bảy loại câu
  hỏi.

- Báo cáo Cohen kappa.

- Split theo question_group_id, test được khóa.

- dataset_manifest.json và commit SHA.

- Bảng kết quả TF IDF, BM25 trên validation và test, tách theo type.

- train_pairs.csv có hard negative cho mô hình cải tiến.

- README ghi lệnh chạy lại từ raw đến kết quả baseline.

## 14 Các lỗi thường gặp và cách tránh

| **Lỗi**                               | **Hậu quả**                          | **Cách tránh**                                |
|---------------------------------------|--------------------------------------|-----------------------------------------------|
| Mở rộng phạm vi quá nhiều lĩnh vực    | Thiếu câu hỏi, chỉ số không tin cậy  | Một lĩnh vực, làm trọn                        |
| Câu hỏi chép nguyên văn tài liệu      | BM25 thắng dễ, kết quả ảo            | Viết câu hỏi trước, đọc tài liệu sau          |
| Split theo từng câu thay vì theo nhóm | Rò rỉ paraphrase giữa train và test  | Split theo question_group_id                  |
| Gán nhãn dựa trên kết quả BM25        | Thiên vị baseline                    | Gán nhãn độc lập với mô hình                  |
| Chunk không có tiền tố ngữ cảnh       | Truy hồi đúng đoạn nhưng sai Điều    | Thêm tên văn bản và tên Điều vào chunk_text   |
| chunk_id theo số dòng                 | Đổi chunking là mất toàn bộ nhãn     | ID ghép từ doc_id, Điều, Khoản                |
| Dùng văn bản hết hiệu lực             | Trả lời sai thực tế                  | Ghi ngày tải, kiểm tra hiệu lực               |
| Không có câu ngoài phạm vi            | Không đo được tỷ lệ từ chối hợp lý   | Khoảng 10% out_of_scope và 10% unsupported    |
| Chọn ngưỡng trên test                 | Kết quả test không còn khách quan    | Chọn trên validation                          |

## 15 Lệnh kiểm tra nhanh cuối mỗi giai đoạn

> git status
>
> python -m pytest
>
> python -m src.data.validate
>
> python -m src.retrieval.evaluate --split validation
>
> git diff --check
>
> git diff --stat

**Ghi chú.** Tên module là gợi ý, đổi theo mã thực tế của nhóm. README
phải ghi đúng lệnh chạy được sau khi mã được tạo.

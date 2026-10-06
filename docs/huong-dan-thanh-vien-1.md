# Hướng dẫn công việc Thành viên 1

_Từ chốt phạm vi tài liệu đến Dataset v1 và baseline BM25_

**Dự án:** Đề tài 10. Hệ thống gợi ý câu trả lời cho câu hỏi hành chính
hoặc học vụ

**Vai trò:** Thành viên 1 phụ trách thu thập tài liệu, tiền xử lý, chia
đoạn, freeze Dataset v1 và baseline TF IDF, BM25. Bộ câu hỏi do cả nhóm
viết, Thành viên 2 điều phối (xem file Lộ trình và phân công)

**Phạm vi mặc định:** lĩnh vực hộ tịch (có thể đổi sang học vụ UEH, xem
mục 3)

**Repository:** repo này

**Đầu ra bắt buộc:** Dataset v1 gồm documents, chunks, questions, qrels,
split theo nhóm câu hỏi, báo cáo chất lượng và kết quả baseline

> **Kết luận quan trọng.** Không mở rộng sang toàn bộ thủ tục dân sự.
> Làm trọn một lĩnh vực, rồi dồn công vào bộ câu hỏi có gán đoạn đúng.
> Mọi chỉ số Recall@k, MRR, NDCG@k và việc huấn luyện cross-encoder đều
> phụ thuộc vào bộ câu hỏi này, không phụ thuộc vào số lượng thủ tục.
>
> **Phạm vi tài liệu.** Tài liệu mô tả tuần tự các bước S01 đến D06 cho
> dữ liệu, M01 đến M02 cho baseline và chuẩn bị dữ liệu cho mô hình cải
> tiến, sau đó là quy trình Pull Request và bàn giao cho các thành viên
> làm Sentence-BERT, PhoBERT, cross-encoder và giao diện.

## 1 Tổng quan trách nhiệm của Thành viên 1

| **Giai đoạn** | **Công việc**                                         | **Đầu ra chính**                              |
|---------------|-------------------------------------------------------|-----------------------------------------------|
| S01           | Chốt phạm vi và danh sách nguồn                       | docs/scope.md, data/raw/source_list.csv       |
| D01           | Thu thập tài liệu gốc                                 | data/raw/html hoặc pdf, raw_manifest.csv      |
| D02           | Trích xuất, làm sạch và EDA kho tài liệu              | docs.jsonl, báo cáo chất lượng                |
| D03           | Chia đoạn (chunking)                                  | chunks.jsonl có chunk_id ổn định              |
| D04           | Viết câu hỏi phần mình, gán nhãn chéo (TV2 điều phối) | questions.csv, qrels.csv                      |
| D05           | Kiểm tra chất lượng nhãn (TV2 chủ trì)                | Cohen kappa, danh sách sửa nhãn               |
| D06           | Chia tập theo nhóm câu hỏi và Freeze Dataset v1       | splits, dataset_manifest.json                 |
| M01           | Baseline TF IDF và BM25                               | Index, bảng Recall@k, MRR, NDCG@k             |
| M02           | Đào hard negative và bàn giao                         | train_pairs.csv cho bi-encoder, cross-encoder |

## 2 Cấu trúc thư mục và nguyên tắc lưu

> data/
>
> raw/source_list.csv
>
> raw/html/\<doc_id\>.html \# hoặc raw/pdf/\<doc_id\>.pdf
>
> raw/raw_manifest.csv
>
> interim/docs.jsonl
>
> processed/chunks.jsonl
>
> labels/questions.csv
>
> labels/qrels.csv
>
> labels/annotation_guideline.md
>
> splits/train_qgroups.csv
>
> splits/validation_qgroups.csv
>
> splits/test_qgroups.csv
>
> configs/
>
> preprocessing.yaml
>
> chunking.yaml
>
> retrieval_baseline.yaml
>
> src/data/ \# crawl, extract, clean, chunk, build_splits
>
> src/retrieval/ \# tfidf, bm25, evaluate
>
> tests/
>
> results/data_quality/
>
> results/retrieval/
>
> artifacts/ \# index, vectorizer

- data/raw: bản gốc tải về, bất biến. Không sửa bằng tay, không ghi đè,
  luôn kèm URL và ngày tải.

- data/interim: văn bản đã trích xuất và làm sạch, mỗi dòng là một tài
  liệu (một thủ tục hoặc một điều khoản quy chế).

- data/processed: các đoạn dùng để lập chỉ mục. Mọi mô hình truy hồi
  dùng chung file này.

- data/labels: câu hỏi và nhãn đoạn đúng. Đây là tài sản quan trọng nhất
  của nhóm.

- data/splits: chỉ lưu question_group_id của từng tập, không sao chép dữ
  liệu.

## 3 S01 Chốt phạm vi và nguồn tài liệu

### 3.1 Vì sao không lấy toàn bộ thủ tục dân sự

- Mỗi thủ tục thêm vào kéo theo hàng chục câu hỏi phải viết và gán nhãn.
  Số thủ tục tăng thì công gán nhãn tăng theo, trong khi thời gian dự án
  không đổi.

- Lấy rải rác nhiều lĩnh vực (hộ tịch, đất đai, cư trú) thì lĩnh vực nào
  cũng mỏng, hỏi sâu là hệ thống trả lời sai, và phần phân tích lỗi
  không có gì để nói.

- Đất đai có luật riêng, quy trình dài và nhiều trường hợp đặc thù,
  không hợp với dự án ngắn. Đưa vào mục hướng phát triển.

### 3.2 Hai lựa chọn phạm vi

| **Tiêu chí**       | **Hộ tịch (mặc định)**                                                 | **Học vụ UEH**                                                |
|--------------------|------------------------------------------------------------------------|---------------------------------------------------------------|
| Nguồn              | Cổng Dịch vụ công quốc gia, văn bản pháp luật về hộ tịch               | Quy chế đào tạo, quy định học vụ, sổ tay sinh viên của trường |
| Cấu trúc tài liệu  | Rất đều: trình tự, cách thức, hồ sơ, thời hạn, cơ quan, lệ phí, căn cứ | Theo chương, điều, khoản                                      |
| Viết câu hỏi       | Phải đóng vai người dân                                                | Nhóm là sinh viên, tự viết câu hỏi thật                       |
| Tài liệu gần giống | Có sẵn, ví dụ khai sinh thường và khai sinh có yếu tố nước ngoài       | Có, ví dụ bảo lưu, tạm dừng học, thôi học                     |
| Rủi ro             | Văn bản thay đổi sau sắp xếp chính quyền hai cấp từ 01/7/2025          | Quy chế có thể có nhiều phiên bản theo khóa                   |

> **Quyết định.** Nhóm chọn một trong hai và ghi vào docs/scope.md. Phần
> còn lại của tài liệu dùng hộ tịch làm ví dụ; nếu chọn học vụ thì thay
> "thủ tục" bằng "điều khoản quy chế", quy trình giữ nguyên.

### 3.3 Danh sách thủ tục hộ tịch gợi ý

- Đăng ký khai sinh; khai sinh có yếu tố nước ngoài; đăng ký lại khai
  sinh.

- Đăng ký kết hôn; kết hôn có yếu tố nước ngoài; cấp giấy xác nhận tình
  trạng hôn nhân.

- Đăng ký khai tử; đăng ký lại khai tử.

- Thay đổi, cải chính, bổ sung thông tin hộ tịch; xác định lại dân tộc.

- Nhận cha, mẹ, con; đăng ký giám hộ và chấm dứt giám hộ.

- Cấp bản sao trích lục hộ tịch; ghi vào sổ hộ tịch việc hộ tịch đã giải
  quyết ở nước ngoài.

Lấy đủ các thủ tục thuộc lĩnh vực Hộ tịch trên Cổng Dịch vụ công quốc
gia (lọc theo lĩnh vực), không chỉ danh sách trên. Báo cáo được ghi là
bao phủ toàn bộ lĩnh vực hộ tịch.

### 3.4 File source_list.csv

| **Cột**       | **Ý nghĩa**                                                            |
|---------------|------------------------------------------------------------------------|
| doc_id        | Mã ổn định do nhóm đặt, ví dụ HT_KHAISINH_01; không đổi về sau         |
| title         | Tên thủ tục hoặc tên điều khoản                                        |
| source_type   | dvc_portal, legal_text, school_regulation                              |
| url           | Đường dẫn gốc                                                          |
| issuing_level | Cấp thực hiện, ví dụ cấp xã, cấp tỉnh                                  |
| legal_basis   | Văn bản căn cứ, ví dụ Luật Hộ tịch 2014 và nghị định hướng dẫn         |
| accessed_at   | Ngày tải, định dạng YYYY-MM-DD                                         |
| in_scope      | yes hoặc no; tài liệu ngoài phạm vi vẫn ghi lại để làm câu hỏi từ chối |

> **Lưu ý hiệu lực.** Chỉ dùng phiên bản đang có hiệu lực tại ngày tải.
> Không lấy bài tổng hợp trên blog hay diễn đàn làm tài liệu gốc vì có
> thể đã lỗi thời sau khi bỏ cấp huyện. Kiểm tra hiệu lực văn bản trước
> khi đưa vào kho.

## 4 D01 Thu thập tài liệu gốc

1.  Với mỗi dòng in_scope = yes trong source_list.csv, tải trang hoặc
    file gốc về data/raw, đặt tên theo doc_id.

2.  Ghi raw_manifest.csv gồm doc_id, url, file_path, sha256, bytes,
    http_status, accessed_at.

3.  Đặt độ trễ giữa các lần tải, tôn trọng robots.txt và điều khoản sử
    dụng của trang. Nếu trang không cho tải tự động thì lưu thủ công và
    ghi rõ trong manifest.

4.  Mở thủ công ít nhất 5 file ngẫu nhiên để chắc chắn tải đúng nội
    dung, không phải trang lỗi hay trang đăng nhập.

**Input:** data/raw/source_list.csv. **Output:** data/raw/html hoặc pdf,
data/raw/raw_manifest.csv.

**Không được:** sửa file gốc, tải lại đè lên file cũ mà không ghi sha256
mới.

## 5 D02 Trích xuất, làm sạch và EDA kho tài liệu

### 5.1 Trích xuất theo trường

Thủ tục hành chính có cấu trúc cố định. Trích từng trường thành cột
riêng thay vì gộp thành một khối văn bản; việc này giúp chunking và hiển
thị nguồn chính xác hơn.

| **Trường**       | **Ví dụ nội dung**                         | **Câu hỏi thường gặp** |
|------------------|--------------------------------------------|------------------------|
| trinh_tu         | Các bước nộp, tiếp nhận, giải quyết        | Làm như thế nào        |
| cach_thuc        | Trực tiếp, trực tuyến, bưu chính           | Nộp online được không  |
| thanh_phan_ho_so | Tờ khai, giấy tờ tùy thân, giấy chứng sinh | Cần mang giấy gì       |
| thoi_han         | Số ngày làm việc                           | Bao lâu thì có kết quả |
| doi_tuong        | Người yêu cầu đăng ký                      | Ai được nộp thay       |
| co_quan          | Cơ quan thực hiện                          | Nộp ở đâu              |
| le_phi           | Mức phí, trường hợp miễn                   | Tốn bao nhiêu tiền     |
| can_cu_phap_ly   | Luật, nghị định, thông tư                  | Quy định ở văn bản nào |

### 5.2 Làm sạch văn bản

- Chuẩn hóa Unicode về NFC; loại HTML tag, ký tự điều khiển, khoảng
  trắng thừa.

- Loại phần điều hướng, menu, chân trang của cổng thông tin. Rule loại
  phải cụ thể và được log số lần tác động.

- Giữ nguyên số liệu, ngày, số hiệu văn bản (ví dụ 123/2015/NĐ-CP), tên
  cơ quan. Đây là thông tin người dùng hỏi nhiều nhất.

- Không lowercase và không bỏ dấu ở bước này. Các biến đổi đó thuộc cấu
  hình của từng mô hình truy hồi.

### 5.3 EDA và kiểm tra chất lượng

| **Kiểm tra**       | **Đạt khi**                                                | **Nếu không đạt**                                 |
|--------------------|------------------------------------------------------------|---------------------------------------------------|
| doc_id             | Duy nhất, không rỗng                                       | Dừng, sửa source_list                             |
| Trường bắt buộc    | Mỗi thủ tục có đủ ít nhất hồ sơ, thời hạn, cơ quan         | Ghi vào issue_samples, tra lại nguồn              |
| Độ dài từng trường | Có min, median, max; không có trường cực ngắn bất thường   | Kiểm tra lỗi trích xuất                           |
| Trùng nội dung     | Không có hai doc_id cùng nội dung y hệt                    | Giữ một bản, log lý do                            |
| Gần giống          | Có danh sách cặp thủ tục giống nhau trên 0,8 cosine TF IDF | Giữ cả hai; dùng cho phân tích tài liệu gần giống |
| Hiệu lực           | Mọi căn cứ pháp lý đều còn hiệu lực                        | Thay bằng văn bản mới hoặc loại                   |

**Output:** data/interim/docs.jsonl,
results/data_quality/corpus_report.md,
results/data_quality/near_duplicate_docs.csv.

## 6 D03 Chia đoạn (chunking)

Đề yêu cầu hiển thị nguồn và đoạn trích, nên đoạn phải đủ ngắn để trích
nguyên văn nhưng đủ dài để tự đứng được.

1.  Chia theo cấu trúc trước: mỗi trường của một thủ tục là một đoạn.
    Với quy chế học vụ, mỗi khoản là một đoạn.

2.  Nếu một đoạn dài hơn ngưỡng (ví dụ 256 token sau tách từ, vì PhoBERT
    giới hạn 256 token) thì cắt tiếp theo câu, chồng lấn 1 câu.

3.  Gắn tiền tố ngữ cảnh vào văn bản đoạn, ví dụ "Đăng ký khai sinh.
    Thành phần hồ sơ: ...". Không có tiền tố thì đoạn "Thời hạn: 1 ngày
    làm việc" không biết thuộc thủ tục nào.

4.  Tạo chunk_id ổn định theo dạng
    \<doc_id\>\_\_\<truong\>\_\_\<so_thu_tu\>. Không dùng số dòng làm
    ID.

5.  Lưu chunk_text (dùng cho mô hình) và display_text (nguyên văn, dùng
    để hiển thị trích dẫn).

| **Trường trong chunks.jsonl** | **Ý nghĩa**                                            |
|-------------------------------|--------------------------------------------------------|
| chunk_id                      | Khóa chính, ổn định qua các phiên bản                  |
| doc_id, field                 | Thuộc tài liệu nào, trường nào                         |
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
| Bao phủ       | Mọi doc_id có ít nhất một chunk                  |
| Rỗng          | 0 chunk rỗng                                     |
| Độ dài        | Không chunk nào vượt ngưỡng token đã cấu hình    |
| Tái lập       | Chạy hai lần cho cùng hash file đầu ra           |

## 7 D04 Xây bộ câu hỏi và gán nhãn

> **Đây là phần quan trọng nhất.** Mục tiêu khoảng 300 câu hỏi (5 người,
> mỗi người khoảng 60 câu), mỗi câu gán một hoặc vài chunk đúng. Thà ít
> thủ tục mà nhiều câu hỏi chất lượng, còn hơn nhiều thủ tục mà câu hỏi
> sơ sài.

### 7.1 Quy trình viết câu hỏi

1.  Với mỗi thủ tục, viết một câu hỏi gốc cho mỗi trường quan trọng (hồ
    sơ, thời hạn, cơ quan, lệ phí, cách thức). Mỗi câu gốc là một
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

- Với câu underspecified, gán các chunk của mọi thủ tục có thể đúng và
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

4.  Thống kê số câu theo type, theo thủ tục, theo trường. Thủ tục nào ít
    câu hỏi thì bổ sung.

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

- Raw còn nguyên, sha256 khớp raw_manifest.

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

3.  Ưu tiên hard negative thuộc thủ tục gần giống (cùng nhóm trong
    near_duplicate_docs.csv). Đây là thứ giúp cross-encoder phân biệt
    khai sinh thường và khai sinh có yếu tố nước ngoài.

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

- File HTML hoặc PDF gốc nếu lớn thì không commit thẳng; dùng Git LFS
  hoặc lưu trên Drive chung và ghi đường dẫn trong raw_manifest.

## 13 Checklist bàn giao cho nhóm

- docs/scope.md ghi rõ lĩnh vực đã chọn và lý do.

- source_list.csv và raw_manifest.csv đầy đủ URL, ngày tải, sha256.

- docs.jsonl có đủ các trường; báo cáo chất lượng kho tài liệu.

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
| Chunk không có tiền tố ngữ cảnh       | Truy hồi đúng đoạn nhưng sai thủ tục | Thêm tên thủ tục và tên trường vào chunk_text |
| chunk_id theo số dòng                 | Đổi chunking là mất toàn bộ nhãn     | ID ghép từ doc_id, trường, số thứ tự          |
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

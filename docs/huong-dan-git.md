# Hướng dẫn Git cho cả nhóm

Quy tắc chính: **không ai push thẳng lên `main`**. Mỗi việc làm trên một nhánh riêng, đẩy lên GitHub, mở Pull Request (PR), có 1 người khác xem rồi mới merge.

## 1. Cài đặt (làm 1 lần)

1. Cài Git: https://git-scm.com/downloads (Windows để mặc định hết, bấm Next).
2. Khai báo tên và email (email trùng với tài khoản GitHub):
   ```bash
   git config --global user.name "Ten Cua Ban"
   git config --global user.email "email-github@example.com"
   ```
3. Đăng nhập GitHub. GitHub **không nhận mật khẩu** khi push, nên chọn 1 trong 2 cách:
   - Cách dễ nhất: cài GitHub CLI (https://cli.github.com) rồi chạy `gh auth login`, chọn GitHub.com → HTTPS → Login with a web browser.
   - Hoặc: lần đầu push, Windows sẽ hiện cửa sổ đăng nhập GitHub (Git Credential Manager), cứ đăng nhập trên trình duyệt.
4. Bấm **Accept** lời mời vào repo (email hoặc https://github.com/baoduy23/vn-admin-qa-retrieval/invitations).
5. Tải repo về máy và cài thư viện:
   ```bash
   git clone https://github.com/baoduy23/vn-admin-qa-retrieval.git
   cd vn-admin-qa-retrieval
   python -m venv .venv
   .venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
   pip install -r requirements.txt
   ```

## 2. Mỗi lần bắt đầu một việc mới

Mỗi task trên GitHub Issues có một mã (S01, D01, M01...). Đặt tên nhánh theo mã đó.

```bash
git switch main
git pull                                   # lấy code mới nhất của cả nhóm
git switch -c feature/D04-question-labels  # tạo nhánh mới cho việc của mình
```

## 3. Lưu và đẩy code lên (làm nhiều lần trong ngày cũng được)

```bash
git status                     # xem file nào đã đổi
git add data/labels/questions.csv src/data/clean.py   # chọn file cần lưu
git commit -m "feat(D04): them 60 cau hoi ho tich"
git push -u origin feature/D04-question-labels       # lần đầu
git push                                             # các lần sau
```

Mẫu message commit: `feat(MÃ): ...` khi thêm mới, `fix(MÃ): ...` khi sửa lỗi, `docs: ...` khi sửa tài liệu.

Trước khi commit, chạy `python -m pytest` để chắc không làm hỏng gì.

## 4. Mở Pull Request

1. Push xong, vào trang repo trên GitHub sẽ thấy nút vàng **Compare & pull request**, bấm vào.
2. Base là `main`, compare là nhánh của mình.
3. Điền mẫu có sẵn (Task ID, thay đổi gì, cách chạy, kết quả). Ghi `Closes #12` (số issue) để merge xong issue tự đóng.
4. Bên phải chọn **Reviewers**: 1 bạn trong nhóm.
5. Đợi dấu tick xanh (tests chạy tự động) và reviewer bấm Approve, rồi bấm **Merge pull request**.

Reviewer góp ý thì cứ sửa trên chính nhánh đó, `commit` rồi `push` lại, PR tự cập nhật.

## 5. Sau khi PR đã merge

```bash
git switch main
git pull
git branch -d feature/D04-question-labels   # xoá nhánh cũ trên máy
```

Rồi quay lại bước 2 cho việc tiếp theo.

## 6. Lỗi hay gặp

| Lỗi | Cách xử lý |
|---|---|
| `Authentication failed` / `Password authentication is not supported` | Chưa đăng nhập đúng cách, làm lại mục 1.3 (`gh auth login`). |
| `Permission denied` / `403` | Chưa Accept lời mời vào repo. |
| `rejected ... (fetch first)` khi push | Trên GitHub có code mới hơn. Chạy `git pull` rồi push lại. |
| `CONFLICT` sau khi pull | Mở file bị conflict, giữ phần đúng, xoá các dòng `<<<<<<<`, `=======`, `>>>>>>>`, rồi `git add <file>` và `git commit`. Không chắc thì hỏi nhóm trước. |
| Lỡ commit lên `main` trên máy | Chưa push thì: `git switch -c feature/<ten>` (mang commit sang nhánh mới), rồi `git switch main` và `git reset --hard origin/main`. |
| File quá lớn (> vài MB, PDF, model) | Không commit. Để trên Drive chung, ghi đường dẫn vào manifest. |

## 7. Nhớ nhanh

```
git switch main → git pull → git switch -c feature/<MÃ>-<mo-ta>
→ sửa code → git add → git commit → git push → mở PR → review → merge
```

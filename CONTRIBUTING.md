# Contributing Guidelines

Vui vui thoai
---

## 🚀 Quy Trình Làm Việc Với Git (Git Workflow)

 Sử dụng mô hình Git Flow đơn giản. **TUYỆT ĐỐI KHÔNG COMMIT TRỰC TIẾP LÊN NHÁNH `main` HOẶC `develop`**.

### 1. Phân Nhánh (Branching)

- **`main`**: Nhánh ổn định nhất, chỉ chứa code đã hoàn thiện và sẵn sàng để "phát hành" (nộp bài). Nhánh này được bảo vệ.
- **`develop`**: Nhánh phát triển chính. Tất cả các tính năng sau khi hoàn thành sẽ được hợp nhất (merge) vào đây.
- **`feature/<feature-name>`**: Khi bắt đầu một tính năng mới.
  - Tên nhánh phải viết bằng tiếng Anh không dấu, dùng dấu gạch ngang `-` để phân tách các từ.
  - Ví dụ: `feature/client-command-ls`, `feature/clamav-agent-socket`
- **`fix/<bug-name>`**: Khi sửa một lỗi nào đó.
  - Ví dụ: `fix/handle-connection-timeout`
- **`docs/<doc-name>`**: Khi chỉnh sửa tài liệu.
  - Ví dụ: `docs/update-readme`

### 2. Quy Tắc Viết Commit Message

Sử dụng quy chuẩn **Conventional Commits**. Điều này giúp log của chúng ta sạch sẽ và dễ đọc.

**Cấu trúc:** `<type>: <description>`

- **`feat`**: Cho một tính năng mới (feature).
  - `feat: Implement 'ls' and 'pwd' commands for FTP client`
- **`fix`**: Khi sửa một lỗi (bug fix).
  - `fix: Correctly handle file not found error in ClamAV agent`
- **`docs`**: Khi thay đổi tài liệu (README, contributing guidelines, etc.).
  - `docs: Add contributing guidelines for the team`
- **`style`**: Thay đổi về định dạng code (dấu chấm phẩy, thụt đầu dòng...).
  - `style: Format client code using Black`
- **`refactor`**: Tái cấu trúc code mà không thay đổi chức năng.
  - `refactor: Optimize file transfer buffer`
- **`test`**: Thêm hoặc sửa các bài test.
  - `test: Add unit test for command parser`

### 3. Tạo Pull Request (PR)

1.  Hoàn thành công việc trên nhánh `feature/*` hoặc `fix/*`.
2.  Push nhánh đó lên GitHub.
3.  Trên GitHub, tạo một **Pull Request** từ nhánh của vào nhánh `develop`.
4.  Trong phần mô tả của PR, ghi rõ đã làm những gì.
5.  Tag (mention) ít nhất **một thành viên khác** vào để review code.
6.  **Không tự merge PR của chính mình.** Chỉ sau khi PR được thành viên khác chấp thuận (Approve), người tạo PR mới tiến hành merge.

---

## 💻 Tiêu Chuẩn về Code (Coding Standards)

### Ngôn Ngữ

- **Ngôn ngữ chính**: Python
- **Phiên bản**: 3.12

### Code Style

- **Code Formatter**: Sử dụng **Black** để tự động định dạng code.
- **Linter**: Sử dụng **Flake8** để kiểm tra lỗi và các vấn đề về style.
- **Quy tắc**: Viết comment và tên biến/hàm bằng tiếng Anh để giữ tính chuyên nghiệp.

---

## 🛠️ Thiết Lập Môi Trường (Environment Setup)

Dự án sử dụng file `requirements.txt` để quản lý các thư viện.

- Để cài đặt tất cả các thư viện cần thiết, chạy lệnh:
  ```bash
  pip install -r requirements.txt

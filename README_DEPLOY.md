# Deploy Flask Quiz App lên Render

## 1. Kiểm tra trước khi deploy

Đảm bảo project có:

- `app.py`
- `quiz.db`
- `requirements.txt`
- `Procfile`
- `render.yaml`
- `runtime.txt`
- `templates/`
- `static/`

Chạy thử local:

```bash
python app.py
```

Chạy thử bằng Gunicorn:

```bash
gunicorn app:app
```

## 2. Đẩy project lên GitHub

```bash
cd /Users/pro201715inch/Documents/on_thi_anh_son
git init
git add .
git commit -m "Build Flask quiz app"
git branch -M main
git remote add origin <YOUR_GITHUB_REPO_URL>
git push -u origin main
```

Lưu ý:

- `quiz.db` phải được commit lên GitHub.
- `.gitignore` không được bỏ qua `quiz.db`.
- Không commit giá trị `SECRET_KEY` thật vào source code.

## 3. Deploy trên Render

Vào Render.com và chọn:

```text
New -> Web Service
```

Sau đó:

- Connect GitHub repository.
- Chọn repository chứa project.
- Runtime: `Python`.
- Build Command: `pip install -r requirements.txt`.
- Start Command: `gunicorn app:app`.
- Plan: `Free`.

Project cũng có sẵn `render.yaml` để tạo service bằng Render Blueprint.

## 4. Environment Variables

Tạo biến môi trường:

```text
SECRET_KEY=<một chuỗi random bất kỳ>
```

Ví dụ minh họa:

```text
SECRET_KEY=quiz-app-secret-key-2026
```

Trong production nên dùng một chuỗi dài, ngẫu nhiên và không chia sẻ công khai.

## 5. Sau khi deploy

Render sẽ cung cấp URL dạng:

```text
https://your-app-name.onrender.com
```

Mở URL đó và test:

- Trang chủ
- Làm 20 câu ngẫu nhiên
- Nộp bài
- Xem kết quả
- Xem review
- Xem warnings

## 6. Lưu ý về SQLite trên Render

App hiện chỉ đọc `quiz.db`, nên SQLite phù hợp.

Không nên lưu lịch sử bài làm lâu dài vào SQLite trên Render free. Kết quả hiện
được lưu tạm trong RAM và có thể mất khi service restart hoặc request đi vào
worker khác.

Nếu sau này cần đăng nhập, lưu lịch sử điểm, admin upload đề hoặc nhiều người
dùng, nên chuyển sang PostgreSQL.

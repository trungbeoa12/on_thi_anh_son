# Web ôn thi trắc nghiệm

## 1. Mục tiêu

Web app Flask đọc dữ liệu câu hỏi từ `quiz.db` và hiển thị bài trắc nghiệm.
Ứng dụng không parse lại file Word.

## 2. Chạy local

```bash
cd /Users/pro201715inch/Documents/on_thi_anh_son
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Mở trình duyệt:

```text
http://127.0.0.1:5000
```

## 3. Các chức năng

- Làm toàn bộ câu hỏi
- Làm 20 câu ngẫu nhiên
- Làm 50 câu ngẫu nhiên
- Nộp bài và chấm điểm
- Xem kết quả
- Xem lại đáp án đúng và đáp án đã chọn
- Xem danh sách warning parse

## 4. Lưu ý

- Web app không parse lại Word, chỉ đọc `quiz.db`.
- File `quiz.db` phải nằm cùng thư mục với `app.py`.
- Nội dung HTML đã parse được render bằng Jinja2 filter `|safe` để giữ bold,
  màu đỏ và highlight.
- Kết quả bài làm được giữ tạm trong RAM của server và không lưu lịch sử lâu dài.
- Khi server khởi động lại, kết quả tạm sẽ mất.

## 5. Chạy bằng Gunicorn

```bash
cd /Users/pro201715inch/Documents/on_thi_anh_son
source .venv/bin/activate
gunicorn app:app
```

Mở:

```text
http://127.0.0.1:8000
```

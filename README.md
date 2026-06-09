# DOCX Quiz Parser

Chương trình đọc bộ câu hỏi trắc nghiệm từ `data.docx`, giữ định dạng Word theo
từng run dưới dạng HTML an toàn, nhận diện đáp án đúng bằng độ đậm và lưu vào
SQLite.

## Cài đặt

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
```

## Chạy

```bash
./.venv/bin/python main.py data.docx \
  --db quiz.db \
  --json parsed_questions.json \
  --report parse_report.txt
```

Chương trình tạo:

- `quiz.db`: các bảng `questions`, `options`, `parse_warnings`
- `parsed_questions.json`: dữ liệu chi tiết để kiểm tra
- `parse_report.txt`: số liệu tổng hợp và danh sách câu có warning

CLI cũng in 5 câu đầu tiên, từng option, `is_correct` và `bold_ratio`.

## Quy tắc parse

- Câu hỏi bắt đầu bằng `số.` hoặc `số)`.
- Option bắt đầu bằng `A.` đến `D.` hoặc `A)` đến `D)`.
- Paragraph không có prefix được nối vào câu hỏi/option gần nhất bằng `<br>`.
- Text luôn được escape trước khi bọc `<strong>`, `<em>`, `<u>`, `<span>` và
  `<mark>`.
- Option đúng khi label in đậm hoặc `bold_ratio >= 0.5`.
- Nếu không option nào đạt ngưỡng, parser chọn option có số ký tự bold lớn nhất
  và ghi warning để kiểm tra thủ công.

Mỗi lần chạy, dữ liệu cũ trong ba bảng output được xóa trước khi lưu kết quả mới.

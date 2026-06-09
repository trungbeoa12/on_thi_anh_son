"""CLI parse bộ câu hỏi DOCX sang SQLite, JSON và báo cáo text."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from db import init_db, save_questions
from parser import parse_docx


def build_report(questions: list[dict]) -> str:
    """Tạo nội dung báo cáo tổng hợp."""
    warning_numbers = [q["question_number"] for q in questions if q.get("warnings")]
    total_options = sum(len(q["options"]) for q in questions)
    missing_options = sum(len(q["options"]) < 4 for q in questions)
    no_correct = sum(not any(o["is_correct"] for o in q["options"]) for q in questions)
    multiple_correct = sum(sum(o["is_correct"] for o in q["options"]) > 1 for q in questions)
    return "\n".join(
        [
            f"Tổng số câu hỏi parse được: {len(questions)}",
            f"Tổng số option parse được: {total_options}",
            f"Số câu thiếu option: {missing_options}",
            f"Số câu không nhận diện được đáp án đúng: {no_correct}",
            f"Số câu có nhiều hơn 1 đáp án đúng: {multiple_correct}",
            "Danh sách question_number có warning: "
            + (", ".join(map(str, warning_numbers)) if warning_numbers else "Không có"),
        ]
    ) + "\n"


def print_preview(questions: list[dict], limit: int = 5) -> None:
    """In các câu đầu tiên để kiểm tra nhanh kết quả parse."""
    print("\n=== 5 CÂU ĐẦU TIÊN ===")
    for question in questions[:limit]:
        print(f"\nCâu {question['question_number']}: {question['question_plain']}")
        for option in question["options"]:
            print(
                f"  {option['label']}. {option['option_plain']} "
                f"| is_correct={option['is_correct']} | bold_ratio={option['bold_ratio']:.4f}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse câu hỏi trắc nghiệm DOCX sang SQLite.")
    parser.add_argument("input", help="Đường dẫn file DOCX đầu vào")
    parser.add_argument("--db", default="quiz.db", help="Đường dẫn SQLite output")
    parser.add_argument("--json", default="parsed_questions.json", help="Đường dẫn JSON output")
    parser.add_argument("--report", default="parse_report.txt", help="Đường dẫn report output")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.is_file():
        parser.error(f"Không tìm thấy file: {input_path}")
    if input_path.suffix.lower() != ".docx":
        parser.error("Input phải là file .docx")

    questions = parse_docx(str(input_path))
    init_db(args.db)
    save_questions(args.db, questions)

    Path(args.json).write_text(
        json.dumps(questions, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report = build_report(questions)
    Path(args.report).write_text(report, encoding="utf-8")

    print(report, end="")
    print_preview(questions)


if __name__ == "__main__":
    main()


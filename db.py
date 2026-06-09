"""Khởi tạo và lưu kết quả parse vào SQLite."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_number INTEGER,
    question_html TEXT,
    question_plain TEXT,
    source_file TEXT,
    warning TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS options (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER,
    label TEXT,
    option_html TEXT,
    option_plain TEXT,
    is_correct INTEGER,
    bold_char_count INTEGER,
    total_char_count INTEGER,
    bold_ratio REAL,
    FOREIGN KEY(question_id) REFERENCES questions(id)
);

CREATE TABLE IF NOT EXISTS parse_warnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_number INTEGER,
    warning_type TEXT,
    message TEXT,
    raw_text TEXT
);
"""


def init_db(db_path: str) -> None:
    """Tạo schema; xóa dữ liệu parse cũ để mỗi lần chạy có kết quả xác định."""
    with sqlite3.connect(db_path) as connection:
        connection.executescript(SCHEMA)
        connection.execute("DELETE FROM options")
        connection.execute("DELETE FROM questions")
        connection.execute("DELETE FROM parse_warnings")


def save_questions(db_path: str, questions: list[dict]) -> None:
    """Lưu toàn bộ câu hỏi, option và warning trong một transaction."""
    created_at = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(db_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        for question in questions:
            cursor = connection.execute(
                """
                INSERT INTO questions (
                    question_number, question_html, question_plain,
                    source_file, warning, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    question["question_number"],
                    question["question_html"],
                    question["question_plain"],
                    question["source_file"],
                    question.get("warning", ""),
                    created_at,
                ),
            )
            question_id = cursor.lastrowid

            for option in question["options"]:
                connection.execute(
                    """
                    INSERT INTO options (
                        question_id, label, option_html, option_plain, is_correct,
                        bold_char_count, total_char_count, bold_ratio
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        question_id,
                        option["label"],
                        option["option_html"],
                        option["option_plain"],
                        int(option["is_correct"]),
                        option["bold_char_count"],
                        option["total_char_count"],
                        option["bold_ratio"],
                    ),
                )

            for warning in question.get("warnings", []):
                connection.execute(
                    """
                    INSERT INTO parse_warnings (
                        question_number, warning_type, message, raw_text
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (
                        question["question_number"],
                        warning["warning_type"],
                        warning["message"],
                        warning.get("raw_text", question["question_plain"]),
                    ),
                )


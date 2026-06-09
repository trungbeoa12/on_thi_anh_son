"""Web ôn thi trắc nghiệm Flask, chỉ đọc dữ liệu từ quiz.db."""

from __future__ import annotations

import os
import sqlite3
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from flask import Flask, g, redirect, render_template, request, session, url_for


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "quiz.db")
DB_MISSING_MESSAGE = (
    "Không tìm thấy quiz.db. Hãy chắc chắn file quiz.db nằm cùng thư mục "
    "với app.py và đã được commit lên repository."
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

# Demo không lưu lịch sử lâu dài. Session chỉ giữ result_id nhỏ gọn.
RESULT_STORE: dict[str, dict[str, Any]] = {}
MAX_STORED_RESULTS = 100


def clean_quiz_html(html_text: str) -> str:
    """
    Bỏ định dạng có thể làm lộ đáp án trong chế độ làm bài thật.

    Các tag định dạng được unwrap để giữ nguyên text bên trong. Các style còn
    sót lại cũng bị xóa, trong khi cấu trúc nội dung như <br> vẫn được giữ.
    """
    if not html_text:
        return ""

    soup = BeautifulSoup(html_text, "html.parser")
    for tag_name in ("strong", "b", "mark", "span", "em", "i", "u"):
        for tag in soup.find_all(tag_name):
            tag.unwrap()

    for tag in soup.find_all(True):
        tag.attrs.pop("style", None)
    return str(soup)


def apply_display_mode(questions: list[dict], display: str) -> list[dict]:
    """Gắn display_html cho câu hỏi và option theo chế độ hiển thị."""
    for question in questions:
        question["display_html"] = (
            clean_quiz_html(question["question_html"])
            if display == "exam"
            else question["question_html"]
        )
        for option in question["options"]:
            option["display_html"] = (
                clean_quiz_html(option["option_html"])
                if display == "exam"
                else option["option_html"]
            )
    return questions


def get_db() -> sqlite3.Connection:
    """Mở một kết nối SQLite cho request hiện tại."""
    if not Path(DB_PATH).is_file():
        raise FileNotFoundError(DB_MISSING_MESSAGE)
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_error: BaseException | None = None) -> None:
    """Đóng kết nối sau khi Flask xử lý xong request."""
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


@app.errorhandler(FileNotFoundError)
def handle_missing_db(error: FileNotFoundError) -> tuple[str, int]:
    return render_template("base.html", database_error=str(error)), 500


def get_question_count() -> int:
    return get_db().execute("SELECT COUNT(*) FROM questions").fetchone()[0]


def get_option_count() -> int:
    return get_db().execute("SELECT COUNT(*) FROM options").fetchone()[0]


def get_warning_count() -> int:
    """Đếm số câu riêng biệt có warning."""
    return get_db().execute(
        "SELECT COUNT(DISTINCT question_number) FROM parse_warnings"
    ).fetchone()[0]


def get_options_by_question_ids(question_ids: list[int]) -> dict[int, list[dict]]:
    """Lấy options theo danh sách question_id và gom nhóm theo câu."""
    if not question_ids:
        return {}
    placeholders = ",".join("?" for _ in question_ids)
    rows = get_db().execute(
        f"""
        SELECT id, question_id, label, option_html, option_plain, is_correct, bold_ratio
        FROM options
        WHERE question_id IN ({placeholders})
        ORDER BY question_id, label
        """,
        question_ids,
    ).fetchall()
    grouped: dict[int, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["question_id"]].append(dict(row))
    return dict(grouped)


def get_questions(mode: str = "all", limit: int | None = None) -> list[dict]:
    """Lấy toàn bộ hoặc lấy ngẫu nhiên một số câu hỏi."""
    connection = get_db()
    if mode == "random":
        safe_limit = max(1, min(limit or 20, get_question_count()))
        rows = connection.execute(
            """
            SELECT id, question_number, question_html, question_plain
            FROM questions
            ORDER BY RANDOM()
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()
    else:
        rows = connection.execute(
            """
            SELECT id, question_number, question_html, question_plain
            FROM questions
            ORDER BY question_number
            """
        ).fetchall()

    questions = [dict(row) for row in rows]
    options_by_question = get_options_by_question_ids([q["id"] for q in questions])
    for question in questions:
        question["options"] = options_by_question.get(question["id"], [])
        question["count_correct"] = sum(
            option["is_correct"] for option in question["options"]
        )
    return questions


def get_question_with_options(question_id: int) -> dict | None:
    """Lấy một câu hỏi và toàn bộ options của câu đó."""
    row = get_db().execute(
        """
        SELECT id, question_number, question_html, question_plain
        FROM questions
        WHERE id = ?
        """,
        (question_id,),
    ).fetchone()
    if row is None:
        return None
    question = dict(row)
    question["options"] = get_options_by_question_ids([question_id]).get(question_id, [])
    question["count_correct"] = sum(o["is_correct"] for o in question["options"])
    return question


def get_warnings() -> list[dict]:
    """Lấy warning và question_id tương ứng nếu tìm thấy."""
    rows = get_db().execute(
        """
        SELECT w.id, w.question_number, w.warning_type, w.message, w.raw_text,
               q.id AS question_id
        FROM parse_warnings AS w
        LEFT JOIN questions AS q ON q.question_number = w.question_number
        ORDER BY w.question_number, w.id
        """
    ).fetchall()
    return [dict(row) for row in rows]


def _parse_question_ids(raw_ids: str) -> list[int]:
    """Chỉ nhận danh sách ID số nguyên dương, giữ nguyên thứ tự và bỏ trùng."""
    result: list[int] = []
    seen: set[int] = set()
    for value in raw_ids.split(","):
        value = value.strip()
        if value.isdigit() and int(value) > 0 and int(value) not in seen:
            result.append(int(value))
            seen.add(int(value))
    return result


def grade_submission(question_ids: list[int], form_data: Any) -> dict:
    """Chấm bài bằng phép so sánh chính xác tập option đã chọn và tập đáp án đúng."""
    if not question_ids:
        return {
            "total": 0,
            "correct": 0,
            "wrong": 0,
            "unanswered": 0,
            "score_percent": 0.0,
            "items": [],
        }

    placeholders = ",".join("?" for _ in question_ids)
    rows = get_db().execute(
        f"""
        SELECT id, question_number, question_html
        FROM questions
        WHERE id IN ({placeholders})
        """,
        question_ids,
    ).fetchall()
    question_by_id = {row["id"]: dict(row) for row in rows}
    options_by_question = get_options_by_question_ids(question_ids)

    items: list[dict] = []
    for question_id in question_ids:
        question = question_by_id.get(question_id)
        if question is None:
            continue

        options = options_by_question.get(question_id, [])
        valid_option_ids = {option["id"] for option in options}
        selected_ids = {
            int(value)
            for value in form_data.getlist(f"q_{question_id}")
            if value.isdigit() and int(value) in valid_option_ids
        }
        correct_ids = {option["id"] for option in options if option["is_correct"]}
        is_answered = bool(selected_ids)
        is_correct = is_answered and selected_ids == correct_ids

        item_options = []
        for option in options:
            option_copy = dict(option)
            option_copy["user_selected"] = option["id"] in selected_ids
            item_options.append(option_copy)

        items.append(
            {
                **question,
                "question_id": question_id,
                "options": item_options,
                "is_answered": is_answered,
                "is_correct": is_correct,
            }
        )

    total = len(items)
    correct = sum(item["is_correct"] for item in items)
    unanswered = sum(not item["is_answered"] for item in items)
    wrong = total - correct - unanswered
    return {
        "total": total,
        "correct": correct,
        "wrong": wrong,
        "unanswered": unanswered,
        "score_percent": round(correct * 100 / total, 1) if total else 0.0,
        "items": items,
    }


def _store_result(result: dict) -> str:
    """Lưu kết quả tạm server-side và giới hạn số bài đang giữ trong RAM."""
    if len(RESULT_STORE) >= MAX_STORED_RESULTS:
        RESULT_STORE.pop(next(iter(RESULT_STORE)))
    result_id = uuid.uuid4().hex
    RESULT_STORE[result_id] = result
    return result_id


def _current_result() -> dict | None:
    return RESULT_STORE.get(session.get("result_id", ""))


def _local_retry_url(value: str | None) -> str:
    """Chỉ chấp nhận đường dẫn nội bộ để link Làm lại không trỏ ra ngoài."""
    if value and value.startswith("/") and not value.startswith("//"):
        return value
    return url_for("index")


@app.route("/")
def index() -> str:
    return render_template(
        "index.html",
        question_count=get_question_count(),
        option_count=get_option_count(),
        warning_count=get_warning_count(),
    )


@app.route("/quiz")
def quiz() -> str:
    mode = request.args.get("mode", "all")
    if mode not in {"all", "random"}:
        mode = "all"
    display = request.args.get("display", "exam")
    if display not in {"exam", "hint"}:
        display = "exam"
    limit = request.args.get("limit", default=20, type=int)
    questions = apply_display_mode(get_questions(mode, limit), display)
    return render_template(
        "quiz.html",
        questions=questions,
        question_ids=",".join(str(q["id"]) for q in questions),
        mode=mode,
        limit=limit,
        display=display,
    )


@app.post("/submit")
def submit():
    question_ids = _parse_question_ids(request.form.get("question_ids", ""))
    result = grade_submission(question_ids, request.form)
    result["retry_url"] = _local_retry_url(request.form.get("retry_url"))
    session["result_id"] = _store_result(result)
    return redirect(url_for("result"))


@app.route("/result")
def result():
    current = _current_result()
    if current is None:
        return redirect(url_for("index"))
    return render_template("result.html", result=current)


@app.route("/review")
def review():
    current = _current_result()
    if current is None:
        return redirect(url_for("index"))
    return render_template("review.html", result=current)


@app.route("/warnings")
def warnings() -> str:
    return render_template("warnings.html", warnings=get_warnings())


@app.route("/question/<int:question_id>")
def question_detail(question_id: int):
    question = get_question_with_options(question_id)
    if question is None:
        return redirect(url_for("warnings"))
    display = request.args.get("display", "exam")
    if display not in {"exam", "hint"}:
        display = "exam"
    questions = apply_display_mode([question], display)
    return render_template(
        "quiz.html",
        questions=questions,
        question_ids=str(question_id),
        display=display,
    )


if __name__ == "__main__":
    app.run(debug=True)

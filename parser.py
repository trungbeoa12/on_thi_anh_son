"""Parser bộ câu hỏi trắc nghiệm từ DOCX, giữ định dạng run dưới dạng HTML."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from docx import Document

from utils import (
    effective_bool,
    effective_color,
    effective_highlight,
    wrap_html,
)


QUESTION_RE = re.compile(r"^\s*(\d+)[\.\)]\s+")
# Fallback cho lỗi định dạng thực tế như "*294. ..."; vẫn ghi warning để rà soát.
NONSTANDARD_QUESTION_RE = re.compile(r"^\s*\*\s*(\d+)[\.\)]\s+")
OPTION_RE = re.compile(r"^\s*([A-D])[\.\)]\s+", re.IGNORECASE)


def run_to_html(run: Any) -> str:
    """Chuyển một Word run sang HTML an toàn, có giữ định dạng."""
    return wrap_html(
        run.text,
        bold=effective_bool(run, "b"),
        italic=effective_bool(run, "i"),
        underline=effective_bool(run, "u"),
        color=effective_color(run),
        highlight=effective_highlight(run),
    )


def paragraph_to_html(paragraph: Any) -> str:
    """Chuyển toàn bộ paragraph sang HTML dựa trên từng run."""
    return "".join(run_to_html(run) for run in paragraph.runs)


def paragraph_to_plain_text(paragraph: Any) -> str:
    """Lấy plain text của paragraph, không dùng để tạo HTML."""
    return "".join(run.text for run in paragraph.runs)


def _paragraph_fragment(paragraph: Any, prefix_length: int = 0) -> dict:
    """Bỏ prefix câu/option rồi trả về HTML, text và thống kê bold."""
    remaining_prefix = prefix_length
    html_parts: list[str] = []
    plain_parts: list[str] = []
    bold_count = 0
    total_count = 0
    label_bold = False

    for run in paragraph.runs:
        text = run.text
        is_bold = effective_bool(run, "b")
        if remaining_prefix:
            removed = text[:remaining_prefix]
            if removed.strip() and is_bold:
                label_bold = True
            text = text[remaining_prefix:]
            remaining_prefix -= len(removed)
        if not text:
            continue

        plain_parts.append(text)
        total_count += len(text)
        if is_bold:
            bold_count += len(text)
        html_parts.append(
            wrap_html(
                text,
                bold=is_bold,
                italic=effective_bool(run, "i"),
                underline=effective_bool(run, "u"),
                color=effective_color(run),
                highlight=effective_highlight(run),
            )
        )

    return {
        "html": "".join(html_parts).strip(),
        "plain": "".join(plain_parts).strip(),
        "bold_char_count": bold_count,
        "total_char_count": total_count,
        "label_bold": label_bold,
    }


def _append_fragment(target: dict, fragment: dict) -> None:
    """Ghép paragraph nối tiếp vào câu hỏi hoặc option hiện tại."""
    if fragment["plain"]:
        if target["plain"]:
            target["plain"] += "\n" + fragment["plain"]
            target["html"] += "<br>" + fragment["html"]
        else:
            target["plain"] = fragment["plain"]
            target["html"] = fragment["html"]
    target["bold_char_count"] = target.get("bold_char_count", 0) + fragment["bold_char_count"]
    target["total_char_count"] = target.get("total_char_count", 0) + fragment["total_char_count"]


def _detect_correct_with_warnings(options: list[dict]) -> tuple[list[dict], list[dict]]:
    warnings: list[dict] = []
    for option in options:
        total = option.get("total_char_count", 0)
        option["bold_ratio"] = option.get("bold_char_count", 0) / total if total else 0.0
        option["is_correct"] = bool(option.get("label_bold") or option["bold_ratio"] >= 0.5)

    selected = [option for option in options if option["is_correct"]]
    if not selected and options:
        max_bold = max(option["bold_char_count"] for option in options)
        if max_bold > 0:
            candidates = [option for option in options if option["bold_char_count"] == max_bold]
            for option in candidates:
                option["is_correct"] = True
            warnings.append(
                {
                    "warning_type": "fallback_bold_count",
                    "message": (
                        "Không có option đạt bold_ratio >= 0.5; "
                        f"chọn option có bold_char_count lớn nhất: {', '.join(o['label'] for o in candidates)}."
                    ),
                }
            )
        else:
            warnings.append(
                {
                    "warning_type": "no_correct_answer",
                    "message": "Không nhận diện được đáp án đúng vì các option không có chữ in đậm.",
                }
            )

    selected = [option for option in options if option["is_correct"]]
    if len(selected) > 1:
        warnings.append(
            {
                "warning_type": "multiple_correct_answers",
                "message": f"Nhận diện nhiều đáp án đúng: {', '.join(o['label'] for o in selected)}.",
            }
        )
    return options, warnings


def detect_correct_option(options: list[dict]) -> list[dict]:
    """Đánh dấu đáp án đúng dựa trên label bold, bold_ratio và fallback bold count."""
    detected, _ = _detect_correct_with_warnings(options)
    return detected


def parse_docx(path: str) -> list[dict]:
    """Parse DOCX thành danh sách câu hỏi có HTML, plain text, option và warning."""
    document = Document(path)
    questions: list[dict] = []
    current_question: dict | None = None
    current_option: dict | None = None

    def flush_question() -> None:
        nonlocal current_question, current_option
        if current_question is None:
            return

        options, detection_warnings = _detect_correct_with_warnings(current_question["options"])
        current_question["options"] = options
        current_question["warnings"].extend(detection_warnings)
        if len(options) < 4:
            current_question["warnings"].append(
                {
                    "warning_type": "missing_options",
                    "message": f"Câu hỏi chỉ có {len(options)} option, ít hơn 4.",
                }
            )
        current_question["warning"] = " | ".join(w["message"] for w in current_question["warnings"])
        for warning in current_question["warnings"]:
            warning["raw_text"] = current_question["question_plain"]
        questions.append(current_question)
        current_question = None
        current_option = None

    for paragraph in document.paragraphs:
        plain = paragraph_to_plain_text(paragraph)
        if not plain.strip():
            continue

        question_match = QUESTION_RE.match(plain)
        nonstandard_question_match = None
        if question_match is None:
            nonstandard_question_match = NONSTANDARD_QUESTION_RE.match(plain)
            question_match = nonstandard_question_match
        option_match = OPTION_RE.match(plain)

        if question_match:
            flush_question()
            fragment = _paragraph_fragment(paragraph, question_match.end())
            initial_warnings = []
            if nonstandard_question_match is not None:
                initial_warnings.append(
                    {
                        "warning_type": "nonstandard_question_prefix",
                        "message": "Số câu có ký tự '*' đứng trước; parser đã dùng fallback để nhận diện.",
                    }
                )
            current_question = {
                "question_number": int(question_match.group(1)),
                "question_html": fragment["html"],
                "question_plain": fragment["plain"],
                "source_file": Path(path).name,
                "options": [],
                "warnings": initial_warnings,
                "warning": "",
            }
            current_option = None
            continue

        if option_match and current_question is not None:
            fragment = _paragraph_fragment(paragraph, option_match.end())
            current_option = {
                "label": option_match.group(1).upper(),
                "content": fragment["html"],
                "option_html": fragment["html"],
                "option_plain": fragment["plain"],
                "plain": fragment["plain"],
                "bold_char_count": fragment["bold_char_count"],
                "total_char_count": fragment["total_char_count"],
                "bold_ratio": 0.0,
                "label_bold": fragment["label_bold"],
                "is_correct": False,
            }
            current_question["options"].append(current_option)
            continue

        if current_question is None:
            continue

        fragment = _paragraph_fragment(paragraph)
        if current_option is not None:
            option_target = {
                "html": current_option["option_html"],
                "plain": current_option["option_plain"],
                "bold_char_count": current_option["bold_char_count"],
                "total_char_count": current_option["total_char_count"],
            }
            _append_fragment(option_target, fragment)
            current_option["content"] = option_target["html"]
            current_option["option_html"] = option_target["html"]
            current_option["plain"] = option_target["plain"]
            current_option["option_plain"] = option_target["plain"]
            current_option["bold_char_count"] = option_target["bold_char_count"]
            current_option["total_char_count"] = option_target["total_char_count"]
        else:
            question_target = {
                "html": current_question["question_html"],
                "plain": current_question["question_plain"],
                "bold_char_count": 0,
                "total_char_count": 0,
            }
            _append_fragment(question_target, fragment)
            current_question["question_html"] = question_target["html"]
            current_question["question_plain"] = question_target["plain"]

    flush_question()
    return questions

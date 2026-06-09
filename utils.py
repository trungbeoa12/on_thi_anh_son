"""Các hàm tiện ích dùng chung khi chuyển định dạng Word sang HTML."""

from __future__ import annotations

import html
from typing import Any

from docx.enum.text import WD_COLOR_INDEX
from docx.oxml.ns import qn


HIGHLIGHT_COLORS = {
    WD_COLOR_INDEX.BLACK: "#000000",
    WD_COLOR_INDEX.BLUE: "#0000FF",
    WD_COLOR_INDEX.BRIGHT_GREEN: "#00FF00",
    WD_COLOR_INDEX.DARK_BLUE: "#000080",
    WD_COLOR_INDEX.DARK_RED: "#800000",
    WD_COLOR_INDEX.DARK_YELLOW: "#808000",
    WD_COLOR_INDEX.GRAY_25: "#C0C0C0",
    WD_COLOR_INDEX.GRAY_50: "#808080",
    WD_COLOR_INDEX.GREEN: "#008000",
    WD_COLOR_INDEX.PINK: "#FF00FF",
    WD_COLOR_INDEX.RED: "#FF0000",
    WD_COLOR_INDEX.TEAL: "#008080",
    WD_COLOR_INDEX.TURQUOISE: "#00FFFF",
    WD_COLOR_INDEX.VIOLET: "#800080",
    WD_COLOR_INDEX.WHITE: "#FFFFFF",
    WD_COLOR_INDEX.YELLOW: "#FFFF00",
}


def xml_on_off(element: Any, property_name: str) -> bool | None:
    """Đọc thuộc tính on/off của Word XML; trả về None nếu không khai báo."""
    if element is None:
        return None
    prop = element.find(qn(f"w:{property_name}"))
    if prop is None:
        return None
    value = prop.get(qn("w:val"))
    return value not in {"0", "false", "off", "none"}


def effective_bool(run: Any, property_name: str) -> bool:
    """Tìm định dạng thực tế từ run, style của run, paragraph và style paragraph."""
    attr_name = {"b": "bold", "i": "italic", "u": "underline"}[property_name]
    direct_value = getattr(run, attr_name)
    if direct_value is not None:
        return bool(direct_value)

    for rpr in (
        getattr(run._element, "rPr", None),
        getattr(getattr(run.style, "element", None), "rPr", None),
        getattr(getattr(run._parent._p, "pPr", None), "rPr", None),
        getattr(getattr(run._parent.style, "element", None), "rPr", None),
    ):
        value = xml_on_off(rpr, property_name)
        if value is not None:
            return value

    # Một số tài liệu Word dùng bCs/iCs cho chữ tiếng Việt.
    complex_property = {"b": "bCs", "i": "iCs", "u": "u"}[property_name]
    for rpr in (
        getattr(run._element, "rPr", None),
        getattr(getattr(run._parent._p, "pPr", None), "rPr", None),
    ):
        value = xml_on_off(rpr, complex_property)
        if value is not None:
            return value
    return False


def effective_color(run: Any) -> str | None:
    """Lấy màu RGB hiệu lực của run nếu Word cung cấp được."""
    color = run.font.color.rgb
    if color is not None:
        return f"#{color}"

    paragraph_rpr = getattr(getattr(run._parent._p, "pPr", None), "rPr", None)
    if paragraph_rpr is not None:
        color_node = paragraph_rpr.find(qn("w:color"))
        if color_node is not None:
            value = color_node.get(qn("w:val"))
            if value and value.lower() != "auto":
                return f"#{value.upper()}"
    return None


def effective_highlight(run: Any) -> str | None:
    """Lấy màu highlight; None nghĩa là không có highlight."""
    highlight = run.font.highlight_color
    if highlight is None:
        return None
    return HIGHLIGHT_COLORS.get(highlight, "#FFFF00")


def wrap_html(
    text: str,
    *,
    bold: bool = False,
    italic: bool = False,
    underline: bool = False,
    color: str | None = None,
    highlight: str | None = None,
) -> str:
    """Escape text trước, sau đó bọc các tag HTML theo thứ tự ổn định."""
    result = html.escape(text, quote=True)
    if color:
        result = f'<span style="color:{color}">{result}</span>'
    if highlight:
        if highlight.upper() == "#FFFF00":
            result = f"<mark>{result}</mark>"
        else:
            result = f'<mark style="background-color:{highlight}">{result}</mark>'
    if underline:
        result = f"<u>{result}</u>"
    if italic:
        result = f"<em>{result}</em>"
    if bold:
        result = f"<strong>{result}</strong>"
    return result


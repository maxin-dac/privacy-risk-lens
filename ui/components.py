from __future__ import annotations
import re
import html
import streamlit as st


_WARN_SVG = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M12 3l9 16H3z"/><path d="M12 10v4"/><path d="M12 17l.01 0"/></svg>'
)

_OK_SVG = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M5 12l4 4 10-10"/></svg>'
)

_INFO_SVG = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>'
)

_ERR_SVG = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<circle cx="12" cy="12" r="10"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/></svg>'
)

_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")


def esc(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def md_bold_to_html(value) -> str:
    if value is None:
        return ""
    s = str(value)
    s = s.replace("<strong>", "**").replace("</strong>", "**")
    s = s.replace("<b>", "**").replace("</b>", "**")
    s = esc(s)
    return _BOLD_RE.sub(r"<b>\1</b>", s)


def page_header(title: str, sub: str = "") -> None:
    st.markdown(
        f'<div class="pg-h"><h1>{esc(title)}</h1><p>{esc(sub)}</p></div>',
        unsafe_allow_html=True,
    )


def section(title: str) -> None:
    st.markdown(f'<div class="sec-h">{esc(title)}</div>', unsafe_allow_html=True)


def card(inner_html: str) -> None:
    st.markdown(f'<div class="card">{inner_html}</div>', unsafe_allow_html=True)


def kv_grid(pairs) -> None:
    cells = "".join(f'<div class="kvcell"><div class="k">{esc(k)}</div><div class="v">{esc(v)}</div></div>' for k, v in pairs)
    st.markdown(f'<div class="kvgrid">{cells}</div>', unsafe_allow_html=True)


def warn_box(text: str) -> None:
    st.markdown(
        f'<div class="warnbox">{_WARN_SVG}<span>{esc(text)}</span></div>',
        unsafe_allow_html=True,
    )


def ok_box(text: str) -> None:
    st.markdown(
        f'<div class="okbox">{_OK_SVG}<span>{esc(text)}</span></div>',
        unsafe_allow_html=True,
    )


def info_box(text: str) -> None:
    st.markdown(
        f'<div class="infobox">{_INFO_SVG}<span>{esc(text)}</span></div>',
        unsafe_allow_html=True,
    )


def err_box(text: str) -> None:
    st.markdown(
        f'<div class="errbox">{_ERR_SVG}<span>{esc(text)}</span></div>',
        unsafe_allow_html=True,
    )

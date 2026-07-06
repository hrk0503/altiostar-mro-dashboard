"""Static guard: no decorative HTML element may LOOK clickable without being
a real Streamlit widget.

This is the test that would have caught the dead top-bar "Quick Export"
chip: it was a `<span class="topnav-chip">` styled identically to a real
button (border, padding, font) with a `:hover` glow (border-color + color +
box-shadow change — the same three properties `.stButton > button:hover`
uses) but with ZERO click handler behind it. Every prior code review read
the source and moved on because the span "looked fine" in isolation; only
driving the rendered UI (or, cheaply, statically flagging the affordance
mismatch below) surfaces the problem.

Three checks, all against the raw source of src/dashboard/app.py:

1. No element uses the literal ``topnav-chip`` class (the exact name of the
   original dead control) — hard regression guard.
2. No custom (non-Streamlit-widget) CSS class applied to a bare <span>/<div>
   mimics a button's interactive affordance (cursor:pointer, or a :hover
   rule that changes >=2 of {box-shadow, border-color, color}) unless it is
   explicitly justified in ALLOWLIST below.
3. No raw ``<button`` HTML tag exists anywhere (all buttons must be real
   ``st.button`` / ``st.download_button`` widgets, not markdown strings).

ALLOWLIST — intentional, consciously-reviewed non-interactive labels.
A future dev adding a new decorative chip/label with hover or pointer-cursor
styling MUST add it here with a one-line justification, or convert it to a
real widget instead (the correct fix, as done for the Anomaly/Health/Export
chips in this same change).
"""
from __future__ import annotations

import re
from pathlib import Path

APP_PATH = Path(__file__).resolve().parents[1] / "src" / "dashboard" / "app.py"

# class_name -> justification. Empty on purpose: every current label in the
# dashboard (badges, the "Live Monitor" .status-label) has no hover/pointer
# affordance at all, so nothing needs an exemption today.
ALLOWLIST: dict[str, str] = {}

REAL_WIDGET_HOOK_MARKERS = (
    "data-testid", "stButton", "stRadio", "stCheckbox", "stSelectbox",
    "stMultiSelect", "stTextInput", "stTabs", "stDownloadButton", "stSlider",
    "stTextArea", "stDateInput", "stNumberInput", "stFileUploader",
    "stColorPicker", "stSidebar", "stHeader",
)


def _extract_style_blocks(src: str) -> list[str]:
    return re.findall(r"<style>(.*?)</style>", src, flags=re.S)


def _extract_css_rules(css_text: str) -> list[tuple[str, str]]:
    """Balanced-brace CSS rule extractor (handles one level of nesting, e.g.
    @keyframes, without needing a full CSS parser)."""
    rules: list[tuple[str, str]] = []
    depth = 0
    selector_start = 0
    body_start = 0
    selector = ""
    for i, ch in enumerate(css_text):
        if ch == "{":
            if depth == 0:
                selector = css_text[selector_start:i].strip()
                body_start = i + 1
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                rules.append((selector, css_text[body_start:i]))
                selector_start = i + 1
    return rules


def _has_hover_button_affordance(body: str) -> bool:
    has_box_shadow = "box-shadow" in body
    has_border_color = "border-color" in body
    has_plain_color = bool(re.search(r"(?<!-)\bcolor\s*:", body))
    return sum([has_box_shadow, has_border_color, has_plain_color]) >= 2


def _is_real_widget_hook(selector: str) -> bool:
    return any(marker in selector for marker in REAL_WIDGET_HOOK_MARKERS)


def _classes_used_on_bare_elements(src: str) -> set[str]:
    """Class names actually applied to a plain <span> or <div> somewhere in
    the file's markdown/HTML strings (as opposed to only defined in CSS but
    never used, or applied to a real Streamlit-rendered element)."""
    used = set()
    for m in re.finditer(r"<(?:span|div)\b[^>]*class=\"([^\"]+)\"", src):
        used.update(m.group(1).split())
    return used


def test_no_topnav_chip_class_regression():
    """Hard regression guard for the exact bug: the dead Quick Export /
    Anomaly Scan / Health Check / Live Monitor spans all used this class."""
    src = APP_PATH.read_text(encoding="utf-8")
    assert "topnav-chip" not in src, (
        "topnav-chip was the decorative, unwired class behind the dead "
        "Quick Export chip. It must not reappear — either wire the control "
        "as a real st.button, or use a class with no hover/pointer "
        "affordance for pure status labels (e.g. .status-label)."
    )


def test_no_raw_button_tags():
    src = APP_PATH.read_text(encoding="utf-8")
    assert not re.search(r"<button\b", src, re.I), (
        "found a raw <button> HTML tag — all buttons must be real "
        "st.button / st.download_button widgets, not markdown strings."
    )


def test_no_decorative_elements_mimic_button_affordance():
    src = APP_PATH.read_text(encoding="utf-8")
    bare_classes = _classes_used_on_bare_elements(src)

    violations = []
    for style_text in _extract_style_blocks(src):
        normalized = style_text.replace("{{", "{").replace("}}", "}")
        for selector, body in _extract_css_rules(normalized):
            if not selector or _is_real_widget_hook(selector):
                continue
            class_names = re.findall(r"\.([\w-]+)", selector)
            if not class_names:
                continue
            is_hover = ":hover" in selector
            cursor_pointer = bool(re.search(r"cursor:\s*pointer", body))
            risky = cursor_pointer or (is_hover and _has_hover_button_affordance(body))
            if not risky:
                continue
            for cls in class_names:
                if cls in ALLOWLIST:
                    continue
                if cls in bare_classes:
                    violations.append((cls, selector))

    assert not violations, (
        "decorative element(s) with button-like hover/cursor affordance but "
        "no real widget behind them (the dead-Quick-Export-chip pattern): "
        f"{violations}. Either wire a real st.button/st.download_button, or "
        "add the class to ALLOWLIST in tests/test_no_dead_controls.py with "
        "a justification (e.g. it's a genuine non-interactive status label)."
    )

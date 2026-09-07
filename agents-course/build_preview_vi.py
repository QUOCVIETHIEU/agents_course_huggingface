#!/usr/bin/env python3
"""Build Agents Course local learning app (Udemy-style course player)."""

from __future__ import annotations

import html as html_lib
import json
import os
import re
import shutil
from pathlib import Path

try:
    import markdown
    import yaml
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Missing dependency: "
        f"{exc.name}. Run:\n"
        "  python3 -m venv .venv-preview && "
        ".venv-preview/bin/pip install -r requirements.txt\n"
        "Then: .venv-preview/bin/python build_preview_vi.py"
    ) from exc

ROOT = Path(__file__).resolve().parent
UNITS = ROOT / "units"
OUT = ROOT / "preview-vi"
HF_LOGO = "/huggingface.svg"
HF_COURSE_URL = "https://hf.co/learn/agents-course"
HF_REPO_URL = "https://github.com/huggingface/agents-course"
HF_COURSE_SHORT = "hf.co/learn/agents-course"
HF_REPO_SHORT = "github.com/huggingface/agents-course"

LANGS = {
    "en": {
        "label": "EN",
        "html_lang": "en",
        "course_title": "Hugging Face Agents Course",
        "curriculum": "Course content",
        "on_this_page": "On this page",
        "progress": "Your progress",
        "complete": "Complete lesson",
        "completed": "Completed",
        "mark_undone": "Mark incomplete",
        "next": "Next lesson",
        "prev": "Previous",
        "reset": "Reset progress",
        "reset_confirm": "Clear all learning progress on this device?",
        "lessons": "lessons",
        "section_of": "Section",
        "continue_learning": "Continue learning",
        "open_curriculum": "Curriculum",
        "attribution": "Cloned from Hugging Face:",
        "repo_label": "Repo",
        "course_label": "Course",
        "save_online": "Save online",
        "sign_in_google": "Sign in with Google",
        "sign_out": "Sign out",
        "signed_in_as": "Signed in",
        "auth_title": "Save progress to your account",
        "auth_body": "Progress stays on this device by default. Sign in only if you want the same progress on other devices. You can keep learning without an account.",
        "auth_cancel": "Keep local only",
        "reset_confirm_cloud": "Clear all learning progress on this device and in your account?",
        "source_menu": "Source",
        "source_title": "Course source",
        "source_body": "This learning app is built from a clone of the Hugging Face Agents Course repository. Content remains attributed to Hugging Face.",
        "source_close": "Close",
        "complete_hint": "Scroll to the end to mark complete",
    },
    "vi": {
        "label": "VN",
        "html_lang": "vi",
        "course_title": "Hugging Face Agents Course",
        "curriculum": "Nội dung khóa học",
        "on_this_page": "Trên trang này",
        "progress": "Tiến độ của bạn",
        "complete": "Hoàn thành bài học",
        "completed": "Đã hoàn thành",
        "mark_undone": "Đánh dấu chưa xong",
        "next": "Bài tiếp theo",
        "prev": "Bài trước",
        "reset": "Xóa tiến độ",
        "reset_confirm": "Xóa toàn bộ tiến độ học trên thiết bị này?",
        "lessons": "bài học",
        "section_of": "Chương",
        "continue_learning": "Tiếp tục học",
        "open_curriculum": "Mục lục",
        "attribution": "Clone Repo từ Hugging Face:",
        "repo_label": "Repo",
        "course_label": "Course",
        "save_online": "Lưu online",
        "sign_in_google": "Đăng nhập bằng Google",
        "sign_out": "Đăng xuất",
        "signed_in_as": "Đã đăng nhập",
        "auth_title": "Lưu tiến độ theo tài khoản",
        "auth_body": "Mặc định tiến độ chỉ lưu trên thiết bị này. Đăng nhập khi bạn muốn đồng bộ sang máy khác. Bạn vẫn học bình thường mà không cần tài khoản.",
        "auth_cancel": "Giữ lưu local",
        "reset_confirm_cloud": "Xóa toàn bộ tiến độ trên thiết bị này và trên tài khoản?",
        "source_menu": "Nguồn",
        "source_title": "Nguồn khóa học",
        "source_body": "App học này được dựng từ bản clone repo Hugging Face Agents Course. Nội dung vẫn thuộc về Hugging Face.",
        "source_close": "Đóng",
        "complete_hint": "Cuộn hết bài để đánh dấu hoàn thành",
    },
}


def preprocess_mdx(text: str) -> str:
    text = re.sub(
        r">\s*\[!TIP\]\s*\n((?:>.*\n?)*)",
        lambda m: "> **Tip**\n" + m.group(1),
        text,
    )
    text = re.sub(r">\s*\[!WARNING\]\s*\n", "> **Warning**\n", text)
    text = re.sub(r">\s*\[!NOTE\]\s*\n", "> **Note**\n", text)
    text = re.sub(r"\s*\[\[[^\]]+\]\]", "", text)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    return text


def render_md(text: str) -> str:
    return markdown.markdown(
        preprocess_mdx(text),
        extensions=["fenced_code", "tables", "toc", "sane_lists", "attr_list"],
    )


def inject_heading_ids(md_html: str) -> tuple[str, list[tuple[str, str, int]]]:
    items: list[tuple[str, str, int]] = []

    def repl(m: re.Match) -> str:
        level = int(m.group(1))
        inner = m.group(2)
        raw = re.sub(r"<[^>]+>", "", inner).strip()
        slug = re.sub(r"[^\w\-]+", "-", raw.lower(), flags=re.U).strip("-") or f"h{level}"
        base, n = slug, 2
        existing = {s for s, _, _ in items}
        while slug in existing:
            slug = f"{base}-{n}"
            n += 1
        if level in (2, 3):
            items.append((slug, raw, level))
        return f'<h{level} id="{html_lib.escape(slug)}">{inner}</h{level}>'

    return re.sub(r"<h([1-6])>(.*?)</h\1>", repl, md_html, flags=re.S), items


def load_toc(lang: str) -> list[dict]:
    return yaml.safe_load((UNITS / lang / "_toctree.yml").read_text(encoding="utf-8"))


CSS = r"""
:root {
  --bg: #f7f9fa;
  --panel: #ffffff;
  --ink: #1c1d1f;
  --muted: #6a6f73;
  --line: #d1d7dc;
  --accent: #b8860b;
  --accent-dark: #8b6914;
  --accent-soft: #f7f1e1;
  --ok: #19a863;
  --ok-bg: #e8faf0;
  --curr: #2d2f31;
  --curr-hover: #3e4143;
  --lesson-active: #f7f1e1;
  --font: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
  --mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  --top: 56px;
  --curr-w: 360px;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  font-family: var(--font);
  color: var(--ink);
  background: var(--bg);
  min-height: 100vh;
}
a { color: inherit; }
button, select { font: inherit; }

/* ===== Top bar (Udemy-like) ===== */
.topbar {
  position: sticky;
  top: 0;
  z-index: 50;
  height: var(--top);
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0 1rem 0 1.1rem;
  background: var(--ink);
  color: #fff;
}
.topbar .brand {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  text-decoration: none;
  color: #fff;
  font-weight: 700;
  font-size: 0.92rem;
  white-space: nowrap;
}
.topbar .brand .logo {
  width: 22px;
  height: 22px;
  display: block;
  object-fit: contain;
}
.topbar .course-name {
  flex: 1;
  min-width: 0;
  font-size: 0.88rem;
  font-weight: 500;
  opacity: 0.92;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  border-left: 1px solid rgba(255,255,255,.18);
  padding-left: 1rem;
}
.topbar .right {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin-left: auto;
}
/* Shared compact control chrome — same height / radius / type */
.tb-ctl,
.prog-chip,
.lang-select,
.info-btn,
.account-btn,
.curr-toggle {
  box-sizing: border-box;
  height: 30px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  margin: 0;
  padding: 0 0.7rem;
  border: 0.5px solid rgba(255,255,255,.22);
  border-radius: 8px;
  background: rgba(255,255,255,.08);
  color: rgba(255,255,255,.92);
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: -0.01em;
  line-height: 1;
  white-space: nowrap;
  cursor: pointer;
  transition: background .15s ease, border-color .15s ease, color .15s ease;
}
.tb-ctl:hover,
.prog-chip:hover,
.info-btn:hover,
.account-btn:hover,
.curr-toggle:hover {
  background: rgba(255,255,255,.14);
  border-color: rgba(255,255,255,.32);
  color: #fff;
}
.lang-select:hover {
  background-color: rgba(255,255,255,.14);
  border-color: rgba(255,255,255,.32);
  color: #fff;
}
.prog-chip {
  padding: 0 0.65rem 0 0.4rem;
  gap: 0.4rem;
  cursor: default;
}
.prog-chip:hover { background: rgba(255,255,255,.08); border-color: rgba(255,255,255,.22); }
.ring {
  --p: 0;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: conic-gradient(#ffd21e calc(var(--p) * 1%), rgba(255,255,255,.22) 0);
  display: grid;
  place-items: center;
  flex: none;
}
.ring::after {
  content: "";
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--ink);
}
.prog-chip .pct {
  font-size: 0.72rem;
  font-weight: 650;
  min-width: 1.7rem;
  letter-spacing: -0.02em;
}
.lang-select {
  appearance: none;
  -webkit-appearance: none;
  background-color: rgba(255,255,255,.08);
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%23ffffff' stroke-width='2.2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 0.45rem center;
  background-size: 9px;
  padding-right: 1.35rem;
  padding-left: 0.6rem;
}
.lang-select option { color: #111; }
.curr-toggle {
  display: none;
}
.info-btn {
  background: rgba(255,255,255,.08);
}
.account-wrap {
  position: relative;
  display: none;
}
.account-wrap.enabled { display: block; }
.account-btn {
  max-width: 9.5rem;
}
.account-btn img {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  object-fit: cover;
  flex: none;
}
.account-btn .label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.account-menu {
  display: none;
  position: absolute;
  right: 0;
  top: calc(100% + 0.4rem);
  min-width: 12rem;
  background: #fff;
  color: var(--ink);
  border: 0.5px solid rgba(0,0,0,.12);
  border-radius: 12px;
  box-shadow: 0 12px 40px rgba(0,0,0,.16);
  padding: 0.4rem;
  z-index: 60;
}
.account-wrap.open .account-menu { display: block; }
.account-menu .who {
  padding: 0.45rem 0.55rem 0.55rem;
  border-bottom: 0.5px solid rgba(0,0,0,.08);
  margin-bottom: 0.3rem;
}
.account-menu .who strong {
  display: block;
  font-size: 0.8rem;
  margin-bottom: 0.15rem;
}
.account-menu .who span {
  font-size: 0.72rem;
  color: var(--muted);
}
.account-menu button {
  width: 100%;
  text-align: left;
  border: 0;
  background: transparent;
  padding: 0.45rem 0.55rem;
  border-radius: 8px;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  color: var(--ink);
}
.account-menu button:hover { background: rgba(120,120,128,.12); }
.auth-dialog {
  border: 0;
  padding: 0;
  border-radius: 12px;
  max-width: min(420px, calc(100vw - 2rem));
  box-shadow: 0 18px 50px rgba(28,29,31,.28);
}
.auth-dialog::backdrop { background: rgba(28,29,31,.45); }
.auth-card {
  padding: 1.25rem 1.3rem 1.15rem;
  background: #fff;
  color: var(--ink);
}
.auth-card h2 {
  margin: 0 0 0.55rem;
  font-size: 1.1rem;
  letter-spacing: -0.02em;
}
.auth-card p {
  margin: 0 0 1.1rem;
  font-size: 0.9rem;
  line-height: 1.55;
  color: #3e4143;
}
.auth-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  justify-content: flex-end;
}
.auth-actions .btn { font-size: 0.84rem; }
.btn-google {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
}
.btn-google svg { width: 16px; height: 16px; }
.source-links {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  margin: 0 0 1rem;
}
.source-links a {
  color: var(--accent-dark);
  font-weight: 650;
  text-decoration: underline;
  text-underline-offset: 2px;
  font-size: 0.9rem;
  word-break: break-all;
}

/* ===== Layout ===== */
.player {
  display: grid;
  grid-template-columns: 1fr var(--curr-w);
  min-height: calc(100vh - var(--top));
}
.stage {
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.stage-inner {
  flex: 1;
  width: min(820px, 100%);
  margin: 0 auto;
  padding: 1.75rem 1.5rem 1.5rem;
}
.lesson-kicker {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--muted);
  font-size: 0.8rem;
  font-weight: 600;
  margin-bottom: 0.55rem;
}
.lesson-kicker .dot {
  width: 5px; height: 5px; border-radius: 50%; background: var(--accent);
}
.lesson-title {
  margin: 0 0 1.25rem;
  font-size: clamp(1.45rem, 2.2vw, 1.85rem);
  line-height: 1.25;
  font-weight: 750;
  letter-spacing: -0.02em;
}

/* Content prose */
.prose {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 1.5rem 1.6rem 1.75rem;
  box-shadow: 0 1px 2px rgba(28,29,31,.04);
}
.prose > *:first-child { margin-top: 0; }
.prose h1 { display: none; } /* title shown above */
.prose h2 {
  font-size: 1.2rem;
  margin: 1.75rem 0 0.65rem;
  scroll-margin-top: 5rem;
}
.prose h3 {
  font-size: 1.05rem;
  margin: 1.35rem 0 0.5rem;
  scroll-margin-top: 5rem;
}
.prose p, .prose li {
  font-size: 1rem;
  line-height: 1.7;
  color: #2d2f31;
}
.prose p { margin: 0.8rem 0; }
.prose ul, .prose ol { padding-left: 1.25rem; margin: 0.7rem 0; }
.prose a { color: var(--accent-dark); }
.prose strong { color: var(--ink); }
.prose img {
  display: block;
  max-width: 100%;
  height: auto;
  margin: 1.1rem 0;
  border-radius: 6px;
}
.prose blockquote {
  margin: 1rem 0;
  padding: 0.75rem 0.9rem;
  background: #f7f9fa;
  border-left: 3px solid var(--accent);
  color: #3e4143;
}
.prose pre {
  background: #1c1d1f;
  color: #f7f9fa;
  border-radius: 6px;
  padding: 0.95rem 1rem;
  overflow-x: auto;
  margin: 1rem 0;
}
.prose code {
  font-family: var(--mono);
  font-size: 0.88em;
  background: #f1f2f3;
  padding: 0.1em 0.32em;
  border-radius: 3px;
}
.prose pre code { background: none; padding: 0; color: inherit; }
.prose table {
  width: 100%;
  border-collapse: collapse;
  margin: 1rem 0;
  font-size: 0.92rem;
}
.prose th, .prose td {
  border: 1px solid var(--line);
  padding: 0.5rem 0.65rem;
  text-align: left;
}
.prose th { background: #f7f9fa; }

.lesson-end-sentinel {
  height: 1px;
  width: 100%;
  margin: 1.5rem 0 0;
  padding-bottom: 0.25rem;
  pointer-events: none;
}

/* Apple-like compact footer — frosted, quiet, precise */
.lesson-footer {
  position: sticky;
  bottom: 0;
  z-index: 30;
  padding: 0;
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: saturate(180%) blur(20px);
  -webkit-backdrop-filter: saturate(180%) blur(20px);
  border-top: 0.5px solid rgba(0, 0, 0, 0.12);
  box-shadow: none;
  transform: translateY(110%);
  opacity: 0;
  pointer-events: none;
  transition: transform 0.35s cubic-bezier(0.22, 1, 0.36, 1), opacity 0.25s ease;
}
.lesson-footer.is-visible {
  transform: translateY(0);
  opacity: 1;
  pointer-events: auto;
}
.lesson-footer-inner {
  width: min(820px, 100%);
  margin: 0 auto;
  min-height: 52px;
  padding: 0.55rem 1.25rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}
.lesson-footer .nav-left,
.lesson-footer .nav-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
}
.lesson-footer .nav-right { margin-left: auto; }
.lesson-footer .btn {
  border: 0;
  border-radius: 980px;
  padding: 0.45rem 0.95rem;
  font-size: 0.8125rem;
  font-weight: 510;
  letter-spacing: -0.01em;
  gap: 0.35rem;
  box-shadow: none;
  transition: background 0.18s ease, color 0.18s ease, opacity 0.18s ease, transform 0.12s ease;
}
.lesson-footer .btn:active {
  transform: scale(0.98);
}
.lesson-footer .btn-ghost {
  background: rgba(120, 120, 128, 0.12);
  color: #1c1d1f;
}
.lesson-footer .btn-ghost:hover {
  background: rgba(120, 120, 128, 0.18);
  color: #1c1d1f;
  border-color: transparent;
}
.lesson-footer .btn-primary {
  background: #1c1d1f;
  color: #fff;
}
.lesson-footer .btn-primary:hover {
  background: #000;
  color: #fff;
  border-color: transparent;
}
.lesson-footer .btn-ok {
  background: rgba(52, 199, 89, 0.14);
  color: #1b7f3a;
}
.lesson-footer .btn-ok:hover {
  background: rgba(52, 199, 89, 0.22);
}
.lesson-footer .btn .check {
  width: 0.9rem;
  height: 0.9rem;
  font-size: 0.58rem;
  border-width: 1.5px;
  border-color: currentColor;
}
.lesson-footer .btn .arrow {
  width: 0.85em;
  height: 0.85em;
  opacity: 0.7;
}
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  border-radius: 999px;
  border: 1px solid transparent;
  padding: 0.55rem 0.95rem;
  font-size: 0.84rem;
  font-weight: 700;
  cursor: pointer;
  text-decoration: none;
  white-space: nowrap;
  transition: background .15s, border-color .15s, color .15s, transform .1s;
}
.btn:active { transform: translateY(1px); }
.btn-ghost {
  background: #fff;
  border-color: var(--line);
  color: var(--ink);
}
.btn-ghost:hover {
  border-color: var(--ink);
  background: #f7f9fa;
}
.btn-primary {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}
.btn-primary:hover { background: var(--accent-dark); border-color: var(--accent-dark); }
.btn-ok {
  background: var(--ok-bg);
  color: #0e6b3f;
  border-color: #9fe0bf;
}
.btn-ok:hover { background: #d8f5e6; }
.btn .check {
  width: 1rem; height: 1rem;
  border: 1.5px solid currentColor;
  border-radius: 50%;
  display: inline-grid;
  place-items: center;
  font-size: 0.65rem;
}
.btn .arrow {
  width: 1em;
  height: 1em;
  display: inline-block;
  flex: none;
}
.btn .arrow svg {
  width: 100%;
  height: 100%;
  display: block;
}

/* ===== Curriculum panel (clean / Apple-like) ===== */
.curriculum {
  border-left: 0.5px solid rgba(0,0,0,.12);
  background: #fbfbfd;
  height: calc(100vh - var(--top));
  position: sticky;
  top: var(--top);
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.curr-head {
  padding: 1.15rem 1.15rem 0.95rem;
  background: rgba(255,255,255,.72);
  backdrop-filter: saturate(180%) blur(16px);
  -webkit-backdrop-filter: saturate(180%) blur(16px);
  border-bottom: 0.5px solid rgba(0,0,0,.08);
}
.curr-head h2 {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 650;
  letter-spacing: -0.02em;
  color: var(--ink);
}
.curr-head .meta {
  margin-top: 0.3rem;
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--muted);
  letter-spacing: -0.01em;
}
.curr-head .meta strong {
  color: var(--ink);
  font-weight: 600;
}
.curr-track {
  margin-top: 0.75rem;
  height: 3px;
  background: rgba(120,120,128,.16);
  border-radius: 999px;
  overflow: hidden;
}
.curr-fill {
  height: 100%;
  width: 0%;
  background: var(--ink);
  border-radius: 999px;
  transition: width .3s cubic-bezier(.22,1,.36,1);
}
.curr-actions {
  margin-top: 0.55rem;
  display: flex;
  justify-content: flex-end;
}
.curr-actions button {
  border: 0;
  background: none;
  color: var(--muted);
  font-size: 0.72rem;
  font-weight: 500;
  letter-spacing: -0.01em;
  cursor: pointer;
  padding: 0;
  text-decoration: none;
}
.curr-actions button:hover { color: var(--ink); }
.curr-body {
  overflow-y: auto;
  flex: 1;
  padding: 0.35rem 0 1rem;
  scrollbar-width: thin;
  scrollbar-color: rgba(0,0,0,.15) transparent;
}
.section {
  border: 0;
  margin: 0 0.55rem;
}
.section + .section {
  border-top: 0.5px solid rgba(0,0,0,.08);
}
.section-btn {
  width: 100%;
  display: flex;
  align-items: flex-start;
  gap: 0.55rem;
  text-align: left;
  background: transparent;
  border: 0;
  border-radius: 10px;
  padding: 0.7rem 0.65rem;
  cursor: pointer;
  color: var(--ink);
  transition: background .15s ease;
}
.section-btn:hover { background: rgba(120,120,128,.1); }
.section.open > .section-btn {
  background: transparent;
}
.section-btn .chev {
  margin-top: 0.15rem;
  width: 0.75rem;
  height: 0.75rem;
  flex: none;
  color: rgba(60,60,67,.45);
  transition: transform .22s cubic-bezier(.22,1,.36,1);
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.section-btn .chev svg {
  width: 100%;
  height: 100%;
  display: block;
}
.section.open .section-btn .chev { transform: rotate(90deg); }
.section-btn .s-title {
  flex: 1;
  font-size: 0.84rem;
  font-weight: 600;
  line-height: 1.3;
  letter-spacing: -0.015em;
}
.section-btn .s-meta {
  display: block;
  margin-top: 0.15rem;
  font-size: 0.7rem;
  font-weight: 500;
  color: rgba(60,60,67,.55);
  letter-spacing: -0.01em;
}
.section-lessons {
  display: none;
  padding: 0 0 0.45rem 0.15rem;
}
.section.open .section-lessons { display: block; }
.lesson-link {
  display: flex;
  align-items: flex-start;
  gap: 0.55rem;
  margin: 0.1rem 0.25rem;
  padding: 0.55rem 0.65rem;
  text-decoration: none;
  color: #3a3a3c;
  border: 0;
  border-radius: 8px;
  font-size: 0.8rem;
  font-weight: 450;
  line-height: 1.35;
  letter-spacing: -0.01em;
  transition: background .15s ease, color .15s ease;
}
.lesson-link:hover {
  background: rgba(120,120,128,.1);
  color: var(--ink);
}
.lesson-link.active {
  background: rgba(184,134,11,.12);
  box-shadow: none;
  color: var(--ink);
  font-weight: 600;
}
.lesson-link .status {
  flex: none;
  width: 16px;
  height: 16px;
  margin-top: 1px;
  border-radius: 50%;
  border: 1.5px solid rgba(60,60,67,.28);
  background: transparent;
}
.lesson-link.done .status {
  border-color: transparent;
  background: #34c759 url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Cpath fill='none' stroke='%23fff' stroke-width='2.2' d='M3.5 8.5l3 3 6-6'/%3E%3C/svg%3E") center/10px no-repeat;
}
.lesson-link .l-title { flex: 1; min-width: 0; }

/* Overlay curriculum on mobile */
.curr-backdrop {
  display: none;
  position: fixed;
  inset: var(--top) 0 0 0;
  background: rgba(0,0,0,.28);
  z-index: 40;
}
@media (max-width: 980px) {
  .player { grid-template-columns: 1fr; }
  .curriculum {
    position: fixed;
    top: var(--top);
    right: 0;
    width: min(100%, 380px);
    height: calc(100vh - var(--top));
    z-index: 45;
    transform: translateX(105%);
    transition: transform .28s cubic-bezier(.22,1,.36,1);
    box-shadow: -8px 0 40px rgba(0,0,0,.12);
    background: #fff;
  }
  body.curr-open .curriculum { transform: translateX(0); }
  body.curr-open .curr-backdrop { display: block; }
  .curr-toggle { display: inline-flex; }
}
"""


APP_JS = r"""
const STORAGE_KEY = 'agents-course-progress-v1';
const PROGRESS_DOC = 'course';

let auth = null;
let db = null;
let currentUser = null;
let cloudSaveTimer = null;
let authReady = false;

function emptyProgress() {
  return { completed: {}, lastVisited: null };
}

function loadProgress() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return emptyProgress();
    const data = JSON.parse(raw);
    return {
      completed: data.completed || {},
      lastVisited: data.lastVisited || null,
    };
  } catch (e) {
    return emptyProgress();
  }
}

function firebaseEnabled() {
  const cfg = window.__FIREBASE_CONFIG__;
  return !!(cfg && cfg.apiKey && window.firebase);
}

function progressRef(uid) {
  return db.collection('users').doc(uid).collection('progress').doc(PROGRESS_DOC);
}

function queueCloudSave(data) {
  if (!authReady || !currentUser || !db) return;
  clearTimeout(cloudSaveTimer);
  cloudSaveTimer = setTimeout(() => {
    progressRef(currentUser.uid).set({
      completed: data.completed || {},
      lastVisited: data.lastVisited || null,
      updatedAt: firebase.firestore.FieldValue.serverTimestamp(),
    }, { merge: true }).catch((err) => console.warn('Cloud save failed', err));
  }, 450);
}

function saveProgress(data) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  queueCloudSave(data);
}

function mergeProgress(a, b) {
  const completed = { ...(b.completed || {}) };
  Object.entries(a.completed || {}).forEach(([key, ts]) => {
    const other = completed[key];
    if (!other || (typeof ts === 'number' && ts > other)) completed[key] = ts;
  });
  return {
    completed,
    lastVisited: a.lastVisited || b.lastVisited || null,
  };
}

async function pullAndMergeCloud() {
  if (!currentUser || !db) return;
  try {
    const snap = await progressRef(currentUser.uid).get();
    const remote = snap.exists
      ? {
          completed: snap.data().completed || {},
          lastVisited: snap.data().lastVisited || null,
        }
      : emptyProgress();
    const merged = mergeProgress(loadProgress(), remote);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(merged));
    await progressRef(currentUser.uid).set({
      completed: merged.completed,
      lastVisited: merged.lastVisited,
      updatedAt: firebase.firestore.FieldValue.serverTimestamp(),
    }, { merge: true });
    refreshUI();
  } catch (err) {
    console.warn('Cloud sync failed', err);
  }
}

function isDone(local) {
  return !!loadProgress().completed[local];
}

function setDone(local, done) {
  const data = loadProgress();
  if (done) data.completed[local] = Date.now();
  else delete data.completed[local];
  data.lastVisited = local;
  saveProgress(data);
  refreshUI();
}

function toggleDone(local) {
  setDone(local, !isDone(local));
}

function resetProgress() {
  const cloud = !!currentUser;
  const msg = cloud
    ? (document.body.dataset.resetConfirmCloud || document.body.dataset.resetConfirm)
    : (document.body.dataset.resetConfirm || 'Reset progress?');
  if (!confirm(msg)) return;
  saveProgress(emptyProgress());
  refreshUI();
}

function switchLang(el) {
  const next = el.value;
  const local = el.getAttribute('data-local') || 'unit0/introduction';
  window.location.href = '/' + next + '/' + local + '.html';
}

function toggleCurriculum(force) {
  const open = typeof force === 'boolean' ? force : !document.body.classList.contains('curr-open');
  document.body.classList.toggle('curr-open', open);
}

function toggleSection(btn) {
  const section = btn.closest('.section');
  if (!section) return;
  section.classList.toggle('open');
}

function refreshUI() {
  const data = loadProgress();
  const completed = data.completed || {};
  const links = [...document.querySelectorAll('.lesson-link[data-lesson]')];
  const all = [...new Set(links.map((a) => a.dataset.lesson))];
  const doneCount = all.filter((k) => completed[k]).length;
  const total = Number(document.body.dataset.total || all.length) || all.length;
  const pct = total ? Math.round((doneCount / total) * 100) : 0;

  links.forEach((a) => {
    a.classList.toggle('done', !!completed[a.dataset.lesson]);
  });

  document.querySelectorAll('.section').forEach((sec) => {
    const lessons = [...sec.querySelectorAll('.lesson-link[data-lesson]')];
    const done = lessons.filter((a) => completed[a.dataset.lesson]).length;
    const meta = sec.querySelector('[data-section-meta]');
    if (meta) {
      const n = lessons.length;
      meta.textContent = done + '/' + n + ' · ' + n + ' ' + (document.body.dataset.lessonsLabel || 'lessons');
    }
  });

  const fill = document.getElementById('curr-fill');
  const pctEls = document.querySelectorAll('[data-progress-pct]');
  const doneEls = document.querySelectorAll('[data-progress-done]');
  if (fill) fill.style.width = pct + '%';
  pctEls.forEach((el) => { el.textContent = pct + '%'; });
  doneEls.forEach((el) => { el.textContent = String(doneCount); });
  document.querySelectorAll('.ring').forEach((el) => { el.style.setProperty('--p', String(pct)); });

  const local = document.body.dataset.lesson;
  const btn = document.getElementById('mark-btn');
  const label = document.getElementById('mark-label');
  const icon = document.getElementById('mark-icon');
  if (btn && local) {
    const done = !!completed[local];
    btn.classList.toggle('btn-ok', done);
    btn.classList.toggle('btn-primary', !done);
    if (label) label.textContent = done
      ? (document.body.dataset.markUndone || 'Incomplete')
      : (document.body.dataset.complete || 'Complete');
    if (icon) icon.textContent = done ? '✓' : '';
  }
}

function openSourceDialog() {
  const dialog = document.getElementById('source-dialog');
  if (dialog && typeof dialog.showModal === 'function') dialog.showModal();
}

function setLessonFooterVisible(show) {
  const footer = document.getElementById('lesson-footer');
  if (!footer) return;
  footer.classList.toggle('is-visible', !!show);
  footer.setAttribute('aria-hidden', show ? 'false' : 'true');
}

function updateLessonFooterFromScroll() {
  const sentinel = document.getElementById('lesson-end-sentinel');
  if (!sentinel) {
    setLessonFooterVisible(true);
    return;
  }
  const rect = sentinel.getBoundingClientRect();
  // Show once the end of the lesson reaches (or passes) the viewport
  const reached = rect.top < window.innerHeight - 12;
  setLessonFooterVisible(reached);
}

function watchLessonEnd() {
  const sentinel = document.getElementById('lesson-end-sentinel');
  const footer = document.getElementById('lesson-footer');
  if (!footer) return;
  if (!sentinel) {
    setLessonFooterVisible(true);
    return;
  }

  const io = new IntersectionObserver(() => {
    updateLessonFooterFromScroll();
  }, { root: null, threshold: [0, 0.01, 1], rootMargin: '0px 0px 40px 0px' });
  io.observe(sentinel);

  window.addEventListener('scroll', updateLessonFooterFromScroll, { passive: true });
  window.addEventListener('resize', updateLessonFooterFromScroll);
  // Run after layout (fonts/images may shift height)
  requestAnimationFrame(updateLessonFooterFromScroll);
  setTimeout(updateLessonFooterFromScroll, 100);
  setTimeout(updateLessonFooterFromScroll, 500);
}

function closeAccountMenu() {
  const wrap = document.getElementById('account-wrap');
  if (wrap) wrap.classList.remove('open');
}

function renderAccountUI(user) {
  const wrap = document.getElementById('account-wrap');
  const btn = document.getElementById('account-btn');
  const menu = document.getElementById('account-menu');
  if (!wrap || !btn || !menu) return;

  wrap.classList.add('enabled');
  if (!user) {
    btn.innerHTML = '<span class="label"></span>';
    btn.querySelector('.label').textContent = document.body.dataset.saveOnline || 'Save online';
    btn.removeAttribute('title');
    menu.innerHTML = '';
    wrap.classList.remove('open');
    return;
  }

  const name = user.displayName || user.email || document.body.dataset.signedInAs || 'Account';
  const photo = user.photoURL
    ? '<img src="' + user.photoURL + '" alt="" referrerpolicy="no-referrer">'
    : '';
  btn.innerHTML = photo + '<span class="label"></span>';
  btn.querySelector('.label').textContent = name;
  btn.title = user.email || name;
  menu.innerHTML =
    '<div class="who"><strong></strong><span></span></div>' +
    '<button type="button" id="sign-out-btn"></button>';
  menu.querySelector('.who strong').textContent = document.body.dataset.signedInAs || 'Signed in';
  menu.querySelector('.who span').textContent = user.email || name;
  menu.querySelector('#sign-out-btn').textContent = document.body.dataset.signOut || 'Sign out';
}

async function signInWithGoogle() {
  if (!auth) return;
  const provider = new firebase.auth.GoogleAuthProvider();
  provider.setCustomParameters({ prompt: 'select_account' });
  try {
    await auth.signInWithPopup(provider);
  } catch (err) {
    if (err && (err.code === 'auth/popup-blocked' || err.code === 'auth/popup-closed-by-user')) {
      if (err.code === 'auth/popup-blocked') await auth.signInWithRedirect(provider);
      return;
    }
    console.warn(err);
    alert(err.message || 'Sign-in failed');
  }
}

async function signOut() {
  closeAccountMenu();
  if (!auth) return;
  await auth.signOut();
}

function openAuthDialog() {
  const dialog = document.getElementById('auth-dialog');
  if (dialog && typeof dialog.showModal === 'function') dialog.showModal();
  else signInWithGoogle();
}

function wireAuthUI() {
  const wrap = document.getElementById('account-wrap');
  const btn = document.getElementById('account-btn');
  const googleBtn = document.getElementById('auth-google-btn');
  if (!wrap || !btn) return;

  btn.addEventListener('click', () => {
    if (currentUser) {
      wrap.classList.toggle('open');
      return;
    }
    openAuthDialog();
  });

  document.addEventListener('click', (e) => {
    if (!wrap.contains(e.target)) closeAccountMenu();
  });

  wrap.addEventListener('click', (e) => {
    if (e.target && e.target.id === 'sign-out-btn') signOut();
  });

  if (googleBtn) {
    googleBtn.addEventListener('click', async () => {
      const dialog = document.getElementById('auth-dialog');
      if (dialog && dialog.open) dialog.close();
      await signInWithGoogle();
    });
  }
}

function initFirebase() {
  if (!firebaseEnabled()) {
    renderAccountUI(null);
    const wrap = document.getElementById('account-wrap');
    if (wrap) wrap.classList.remove('enabled');
    return;
  }

  try {
    if (!firebase.apps.length) firebase.initializeApp(window.__FIREBASE_CONFIG__);
    auth = firebase.auth();
    db = firebase.firestore();
  } catch (err) {
    console.warn('Firebase init failed', err);
    return;
  }

  wireAuthUI();
  auth.getRedirectResult().catch(() => {});
  auth.onAuthStateChanged(async (user) => {
    currentUser = user;
    authReady = true;
    renderAccountUI(user);
    if (user) await pullAndMergeCloud();
    refreshUI();
  });
}

document.addEventListener('DOMContentLoaded', () => {
  const local = document.body.dataset.lesson;
  if (local) {
    const data = loadProgress();
    data.lastVisited = local;
    // local-only until auth is ready; cloud queue no-ops without user
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    const active = document.querySelector('.lesson-link.active');
    const section = active && active.closest('.section');
    if (section) section.classList.add('open');
  }
  refreshUI();
  const btn = document.getElementById('mark-btn');
  if (btn && local) btn.addEventListener('click', () => toggleDone(local));
  const sourceBtn = document.getElementById('source-btn');
  if (sourceBtn) sourceBtn.addEventListener('click', openSourceDialog);
  watchLessonEnd();
  initFirebase();
});
"""


def lang_dropdown(lang: str, local: str) -> str:
    opts = []
    for code, meta in LANGS.items():
        sel = " selected" if code == lang else ""
        opts.append(f'<option value="{code}"{sel}>{meta["label"]}</option>')
    return (
        f'<select class="lang-select" data-local="{html_lib.escape(local)}" '
        f'aria-label="Language" onchange="switchLang(this)">{"".join(opts)}</select>'
    )


def build_curriculum(
    toc: list[dict],
    active_local: str,
    lang: str,
    total_lessons: int,
) -> str:
    meta = LANGS[lang]
    parts = [
        '<aside class="curriculum" id="curriculum">',
        '  <div class="curr-head">',
        f'    <h2>{html_lib.escape(meta["curriculum"])}</h2>',
        f'    <div class="meta"><strong data-progress-pct>0%</strong> · '
        f'<span data-progress-done>0</span>/{total_lessons} {html_lib.escape(meta["lessons"])}</div>',
        '    <div class="curr-track"><div class="curr-fill" id="curr-fill"></div></div>',
        '    <div class="curr-actions">',
        f'      <button type="button" onclick="resetProgress()">{html_lib.escape(meta["reset"])}</button>',
        "    </div>",
        "  </div>",
        '  <div class="curr-body" id="course-nav">',
    ]

    for idx, chapter in enumerate(toc, start=1):
        sections = chapter.get("sections", [])
        n = len(sections)
        # open if contains active
        is_open = any(s["local"] == active_local for s in sections)
        open_cls = " open" if is_open else ""
        parts.append(f'<div class="section{open_cls}">')
        parts.append(
            '<button type="button" class="section-btn" onclick="toggleSection(this)">'
            '<span class="chev" aria-hidden="true">'
            '<svg viewBox="0 0 24 24" fill="none">'
            '<path d="M9.5 6.5L15 12l-5.5 5.5" stroke="currentColor" stroke-width="2.2" '
            'stroke-linecap="round" stroke-linejoin="round"/>'
            "</svg></span>"
            "<span>"
            f'<span class="s-title">{html_lib.escape(chapter["title"])}</span>'
            f'<span class="s-meta" data-section-meta>0/{n} · {n} {html_lib.escape(meta["lessons"])}</span>'
            "</span></button>"
        )
        parts.append('<div class="section-lessons">')
        for sec in sections:
            local = sec["local"]
            href = f"/{lang}/{local}.html"
            cls = "lesson-link active" if local == active_local else "lesson-link"
            parts.append(
                f'<a class="{cls}" href="{href}" data-lesson="{html_lib.escape(local)}">'
                f'<span class="status" aria-hidden="true"></span>'
                f'<span class="l-title">{html_lib.escape(sec["title"])}</span></a>'
            )
        parts.append("</div></div>")

    parts.append("  </div>")  # curr-body
    parts.append("</aside>")
    return "\n".join(parts)


def find_section_title(toc: list[dict], local: str) -> str:
    for chapter in toc:
        for sec in chapter.get("sections", []):
            if sec["local"] == local:
                return chapter["title"]
    return ""


def shell(
    *,
    title: str,
    body: str,
    curriculum: str,
    prev_href: str | None,
    prev_title: str | None,
    next_href: str | None,
    next_title: str | None,
    lang: str,
    local: str,
    section_title: str,
    total_lessons: int,
) -> str:
    meta = LANGS[lang]
    fb_on = bool(firebase_web_config().get("apiKey"))
    firebase_scripts = (
        '<script src="https://www.gstatic.com/firebasejs/11.0.2/firebase-app-compat.js"></script>\n'
        '<script src="https://www.gstatic.com/firebasejs/11.0.2/firebase-auth-compat.js"></script>\n'
        '<script src="https://www.gstatic.com/firebasejs/11.0.2/firebase-firestore-compat.js"></script>\n'
        if fb_on
        else ""
    )
    arrow_left = (
        '<span class="arrow" aria-hidden="true">'
        '<svg viewBox="0 0 24 24" fill="none">'
        '<path d="M14.5 6.5L9 12l5.5 5.5" stroke="currentColor" stroke-width="2.2" '
        'stroke-linecap="round" stroke-linejoin="round"/>'
        "</svg></span>"
    )
    arrow_right = (
        '<span class="arrow" aria-hidden="true">'
        '<svg viewBox="0 0 24 24" fill="none">'
        '<path d="M9.5 6.5L15 12l-5.5 5.5" stroke="currentColor" stroke-width="2.2" '
        'stroke-linecap="round" stroke-linejoin="round"/>'
        "</svg></span>"
    )
    prev_btn = (
        f'<a class="btn btn-ghost" href="{prev_href}">{arrow_left}{html_lib.escape(meta["prev"])}</a>'
        if prev_href
        else ""
    )
    next_btn = (
        f'<a class="btn btn-ghost" href="{next_href}">{html_lib.escape(meta["next"])}{arrow_right}</a>'
        if next_href
        else ""
    )

    html = f"""<!DOCTYPE html>
<html lang="{meta["html_lang"]}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html_lib.escape(title)} · {html_lib.escape(meta["course_title"])}</title>
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon-32.png" type="image/png" sizes="32x32">
<link rel="icon" href="/favicon-16.png" type="image/png" sizes="16x16">
<link rel="shortcut icon" href="/favicon.ico">
<link rel="apple-touch-icon" href="/apple-touch-icon.png" sizes="180x180">
<meta name="theme-color" content="#1c1d1f">
<style>{CSS}</style>
</head>
<body
  data-lesson="{html_lib.escape(local)}"
  data-lang="{html_lib.escape(lang)}"
  data-total="{total_lessons}"
  data-complete="{html_lib.escape(meta["complete"])}"
  data-mark-undone="{html_lib.escape(meta["mark_undone"])}"
  data-reset-confirm="{html_lib.escape(meta["reset_confirm"])}"
  data-reset-confirm-cloud="{html_lib.escape(meta["reset_confirm_cloud"])}"
  data-lessons-label="{html_lib.escape(meta["lessons"])}"
  data-save-online="{html_lib.escape(meta["save_online"])}"
  data-sign-in-google="{html_lib.escape(meta["sign_in_google"])}"
  data-sign-out="{html_lib.escape(meta["sign_out"])}"
  data-signed-in-as="{html_lib.escape(meta["signed_in_as"])}"
>
<header class="topbar">
  <a class="brand" href="/{lang}/unit0/introduction.html">
    <img class="logo" src="{HF_LOGO}" alt="Hugging Face">
    <span>Agents Course</span>
  </a>
  <div class="course-name">{html_lib.escape(meta["course_title"])}</div>
  <div class="right">
    <div class="prog-chip" title="{html_lib.escape(meta["progress"])}">
      <span class="ring" aria-hidden="true"></span>
      <span class="pct" data-progress-pct>0%</span>
    </div>
    <div class="account-wrap" id="account-wrap">
      <button type="button" class="account-btn" id="account-btn" aria-haspopup="true">
        <span class="label">{html_lib.escape(meta["save_online"])}</span>
      </button>
      <div class="account-menu" id="account-menu" role="menu"></div>
    </div>
    {lang_dropdown(lang, local)}
    <button type="button" class="info-btn" id="source-btn">{html_lib.escape(meta["source_menu"])}</button>
    <button type="button" class="curr-toggle" onclick="toggleCurriculum()">{html_lib.escape(meta["open_curriculum"])}</button>
  </div>
</header>

<div class="curr-backdrop" onclick="toggleCurriculum(false)"></div>

<div class="player">
  <main class="stage">
    <div class="stage-inner">
      <div class="lesson-kicker">
        <span class="dot"></span>
        <span>{html_lib.escape(section_title or meta["section_of"])}</span>
      </div>
      <h1 class="lesson-title">{html_lib.escape(title)}</h1>
      <article class="prose">
{body}
      </article>
      <div id="lesson-end-sentinel" class="lesson-end-sentinel" aria-hidden="true"></div>
    </div>
    <footer class="lesson-footer" id="lesson-footer" aria-label="Lesson navigation">
      <div class="lesson-footer-inner">
        <div class="nav-left">{prev_btn}</div>
        <div class="nav-right">
          <button type="button" class="btn btn-primary" id="mark-btn">
            <span class="check" id="mark-icon"></span>
            <span id="mark-label">{html_lib.escape(meta["complete"])}</span>
          </button>
          {next_btn}
        </div>
      </div>
    </footer>
  </main>
{curriculum}
</div>

<dialog id="source-dialog" class="auth-dialog">
  <form method="dialog" class="auth-card">
    <h2>{html_lib.escape(meta["source_title"])}</h2>
    <p>{html_lib.escape(meta["source_body"])}</p>
    <p class="source-links">
      <span>{html_lib.escape(meta["attribution"])}</span>
      <a href="{HF_REPO_URL}" target="_blank" rel="noopener noreferrer">{HF_REPO_SHORT}</a>
      <a href="{HF_COURSE_URL}" target="_blank" rel="noopener noreferrer">{HF_COURSE_SHORT}</a>
    </p>
    <div class="auth-actions">
      <button value="cancel" class="btn btn-ghost">{html_lib.escape(meta["source_close"])}</button>
    </div>
  </form>
</dialog>

<dialog id="auth-dialog" class="auth-dialog">
  <form method="dialog" class="auth-card">
    <h2>{html_lib.escape(meta["auth_title"])}</h2>
    <p>{html_lib.escape(meta["auth_body"])}</p>
    <div class="auth-actions">
      <button value="cancel" class="btn btn-ghost">{html_lib.escape(meta["auth_cancel"])}</button>
      <button type="button" class="btn btn-primary btn-google" id="auth-google-btn">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path fill="#fff" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
          <path fill="#fff" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
          <path fill="#fff" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
          <path fill="#fff" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
        </svg>
        {html_lib.escape(meta["sign_in_google"])}
      </button>
    </div>
  </form>
</dialog>

<script src="/firebase-config.js"></script>
<script src="/app.js"></script>
</body>
</html>
"""
    return html.replace(
        '<script src="/firebase-config.js"></script>',
        firebase_scripts + '<script src="/firebase-config.js"></script>',
        1,
    )


def build_lang(lang: str) -> tuple[int, list[str]]:
    toc = load_toc(lang)
    pages: list[tuple[str, str]] = []
    for chapter in toc:
        for sec in chapter.get("sections", []):
            pages.append((sec["local"], sec["title"]))

    total = len(pages)
    missing: list[str] = []
    built = 0

    for i, (local, title) in enumerate(pages):
        src = UNITS / lang / f"{local}.mdx"
        if not src.exists():
            missing.append(f"{lang}/{local}")
            continue

        body = render_md(src.read_text(encoding="utf-8"))
        body, _ = inject_heading_ids(body)

        prev_href = prev_title = next_href = next_title = None
        if i > 0:
            pl, pt = pages[i - 1]
            prev_href, prev_title = f"/{lang}/{pl}.html", pt
        if i < len(pages) - 1:
            nl, nt = pages[i + 1]
            next_href, next_title = f"/{lang}/{nl}.html", nt

        html = shell(
            title=title,
            body=body,
            curriculum=build_curriculum(toc, local, lang, total),
            prev_href=prev_href,
            prev_title=prev_title,
            next_href=next_href,
            next_title=next_title,
            lang=lang,
            local=local,
            section_title=find_section_title(toc, local),
            total_lessons=total,
        )
        dest = OUT / lang / f"{local}.html"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(html, encoding="utf-8")
        built += 1

    return built, missing


def load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def firebase_web_config() -> dict[str, str]:
    return {
        "apiKey": os.environ.get("FIREBASE_API_KEY", ""),
        "authDomain": os.environ.get("FIREBASE_AUTH_DOMAIN", ""),
        "projectId": os.environ.get("FIREBASE_PROJECT_ID", ""),
        "storageBucket": os.environ.get("FIREBASE_STORAGE_BUCKET", ""),
        "messagingSenderId": os.environ.get("FIREBASE_MESSAGING_SENDER_ID", ""),
        "appId": os.environ.get("FIREBASE_APP_ID", ""),
    }


def write_app_icons() -> None:
    src = ROOT / "assets" / "app-icon-cap.svg"
    if src.exists():
        shutil.copyfile(src, OUT / "icon.svg")
        shutil.copyfile(src, OUT / "favicon.svg")
        shutil.copyfile(src, ROOT / "assets" / "app-icon.svg")
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("  Icons: SVG only (install pillow for PNG/ICO favicons)")
        return

    def draw_icon(size: int) -> Image.Image:
        """Rasterize graduation-cap mark to match app-icon-cap.svg (64 viewBox)."""
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        s = size / 64.0

        def xy(*pts: float) -> list[tuple[float, float]]:
            out = []
            it = iter(pts)
            for x in it:
                y = next(it)
                out.append((x * s, y * s))
            return out

        def oval(cx: float, cy: float, r: float, fill: tuple[int, int, int, int]) -> None:
            draw.ellipse(
                ((cx - r) * s, (cy - r) * s, (cx + r) * s, (cy + r) * s),
                fill=fill,
            )

        radius = max(2, int(14 * s))
        draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=(28, 29, 31, 255))
        # base / gown
        draw.polygon(xy(20, 30, 20, 42, 32, 49, 44, 42, 44, 30, 32, 36), fill=(212, 160, 23, 255))
        # mortarboard
        draw.polygon(xy(10, 28, 32, 18, 54, 28, 32, 38), fill=(184, 134, 11, 255))
        # tassel
        tw = max(1, int(2.2 * s))
        draw.line(xy(50, 28, 50, 40), fill=(139, 105, 20, 255), width=tw)
        oval(50, 42, 2.4, (247, 241, 225, 255))
        # neural spark
        oval(32, 10, 2.8, (184, 134, 11, 255))
        oval(26.2, 15.2, 2.2, (247, 241, 225, 255))
        oval(38.2, 15.2, 2.2, (247, 241, 225, 255))
        lw = max(1, int(1.5 * s))
        draw.line(xy(26, 15, 30.5, 11.5), fill=(247, 241, 225, 255), width=lw)
        draw.line(xy(38, 15, 33.5, 11.5), fill=(247, 241, 225, 255), width=lw)
        return img

    icon180 = draw_icon(180)
    icon180.save(OUT / "apple-touch-icon.png", "PNG")
    icon32 = draw_icon(32)
    icon16 = draw_icon(16)
    icon32.save(OUT / "favicon-32.png", "PNG")
    icon16.save(OUT / "favicon-16.png", "PNG")
    icon32.save(OUT / "favicon.ico", format="ICO", sizes=[(16, 16), (32, 32)])
    print("  Icons: cap SVG + PNG + ICO")


def write_runtime_assets() -> None:
    cfg = firebase_web_config()
    (OUT / "firebase-config.js").write_text(
        "window.__FIREBASE_CONFIG__ = " + json.dumps(cfg, ensure_ascii=True) + ";\n",
        encoding="utf-8",
    )
    (OUT / "app.js").write_text(APP_JS, encoding="utf-8")
    logo_src = ROOT / "assets" / "huggingface.svg"
    if logo_src.exists():
        shutil.copyfile(logo_src, OUT / "huggingface.svg")
    write_app_icons()
    if cfg.get("apiKey"):
        print("  Firebase: configured (Save online enabled)")
    else:
        print("  Firebase: not configured (local progress only)")


def build() -> None:
    load_dotenv()
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    write_runtime_assets()

    total = 0
    missing_all: list[str] = []
    for lang in ("en", "vi"):
        n, missing = build_lang(lang)
        total += n
        missing_all.extend(missing)
        print(f"  {lang}: {n} pages")

    (OUT / "index.html").write_text(
        """<!DOCTYPE html>
<html lang="vi"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agents Course</title>
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon-32.png" type="image/png" sizes="32x32">
<link rel="icon" href="/favicon-16.png" type="image/png" sizes="16x16">
<link rel="shortcut icon" href="/favicon.ico">
<link rel="apple-touch-icon" href="/apple-touch-icon.png" sizes="180x180">
<meta name="theme-color" content="#1c1d1f">
<meta http-equiv="refresh" content="0; url=/vi/unit0/introduction.html">
</head><body>
<p><a href="/vi/unit0/introduction.html">VN</a> · <a href="/en/unit0/introduction.html">EN</a></p>
</body></html>
""",
        encoding="utf-8",
    )
    print(f"Built {total} pages → {OUT}")
    if missing_all:
        print("Missing:", ", ".join(missing_all))


if __name__ == "__main__":
    build()

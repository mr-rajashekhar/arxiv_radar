"""
Delivery: markdown digest writer + Gmail SMTP sender (with HTML email).

SMTP credentials stored in Windows Credential Manager via keyring:
    keyring.set_password("arxiv_radar", "gmail", "<16-char Google App Password>")
"""

from __future__ import annotations

import html
import logging
import smtplib
from email.message import EmailMessage
from pathlib import Path
from datetime import datetime

import keyring

from arxiv_client import Paper

log = logging.getLogger(__name__)

KEYRING_SERVICE = "arxiv_radar"
KEYRING_KEY = "gmail"


# (paper, score, reason, summary_dict)
SelectedRow = tuple[Paper, int, str, dict]


# ---------- Markdown (archive + plain-text fallback) ----------

_FIELD_ORDER = [
    ("problem",      "Problem"),
    ("contribution", "Contribution"),
    ("results",      "Results"),
    ("setup",        "Setup"),
    ("baselines",    "Baselines"),
    ("why_for_you",  "Why for you"),
    ("caveat",       "Caveat"),
]


def _md_paper(paper: Paper, score: int, reason: str, s: dict, rank: int) -> str:
    authors = ", ".join(paper.authors[:4]) + (" et al." if len(paper.authors) > 4 else "")
    lines = [
        f"### {rank}. [{paper.title}]({paper.url})",
        f"*Score: {score}/10 — {reason}*  ",
        f"**Authors:** {authors} · **Category:** `{paper.primary_category}`  ",
        f"**Links:** [abs]({paper.url}) · [pdf]({paper.pdf_url})",
        "",
    ]
    for key, label in _FIELD_ORDER:
        lines.append(f"- **{label}:** {s.get(key, '').strip()}")
    lines.append("\n---\n")
    return "\n".join(lines)


def write_digest(
    path: Path,
    selected: list[SelectedRow],
    skipped_titles: list[tuple[str, int]],
) -> Path:
    date_str = datetime.now().strftime("%Y-%m-%d")
    path.parent.mkdir(parents=True, exist_ok=True)

    n_total = len(selected) + len(skipped_titles)
    parts: list[str] = [
        f"# Arxiv Radar — {date_str}\n\n",
        f"**{len(selected)} relevant** / {n_total} scanned.\n\n---\n\n",
    ]

    if not selected:
        parts.append("_No papers cleared the relevance threshold today._\n\n")
    else:
        parts.append("## Top papers\n\n")
        for i, (paper, score, reason, s) in enumerate(selected, 1):
            parts.append(_md_paper(paper, score, reason, s, i))
            parts.append("\n")

    if skipped_titles:
        parts.append("## Also scanned (below threshold)\n\n")
        for title, score in skipped_titles[:30]:
            parts.append(f"- ({score}) {title}\n")
        if len(skipped_titles) > 30:
            parts.append(f"- _...and {len(skipped_titles) - 30} more_\n")

    path.write_text("".join(parts), encoding="utf-8")
    log.info("Wrote digest: %s", path)
    return path


# ---------- HTML email rendering (inline CSS for Gmail) ----------

def _score_color(score: int) -> str:
    if score >= 9:
        return "#0a7f3f"  # deep green
    if score >= 8:
        return "#3a8a3a"
    return "#7a6a00"       # olive for 7


def _html_paper(paper: Paper, score: int, reason: str, s: dict, rank: int) -> str:
    title = html.escape(paper.title)
    reason_h = html.escape(reason or "")
    authors = ", ".join(paper.authors[:4]) + (" et al." if len(paper.authors) > 4 else "")
    authors_h = html.escape(authors)
    cat_h = html.escape(paper.primary_category)
    color = _score_color(score)

    field_rows = []
    for key, label in _FIELD_ORDER:
        val = html.escape(str(s.get(key, "")).strip())
        field_rows.append(
            f'<tr>'
            f'<td class="ar-label" style="padding:4px 10px 4px 0;vertical-align:top;color:#555;'
            f'font-size:12px;font-weight:600;white-space:nowrap;width:110px;">{label}</td>'
            f'<td class="ar-val" style="padding:4px 0;vertical-align:top;color:#222;font-size:14px;line-height:1.5;">{val}</td>'
            f'</tr>'
        )
    fields_html = "".join(field_rows)

    return f"""
<div class="ar-card" style="margin:0 0 18px 0;border:1px solid #e5e5e5;border-left:4px solid {color};
            border-radius:6px;background:#ffffff;padding:16px 18px;">
  <div style="font-size:16px;font-weight:700;color:#111;line-height:1.35;margin-bottom:8px;">
    <span style="color:#888;font-weight:500;">#{rank}</span>
    &nbsp;<a href="{paper.url}" style="color:#111;text-decoration:none;">{title}</a>
  </div>
  <div style="font-size:12px;color:#666;margin-bottom:10px;line-height:1.5;">
    <span style="display:inline-block;background:{color};color:#fff;padding:2px 7px;
                 border-radius:3px;font-weight:700;font-size:11px;margin-right:6px;">
      {score}/10
    </span>
    <span style="color:#444;">{reason_h}</span>
  </div>
  <div class="ar-meta" style="font-size:12px;color:#666;margin-bottom:12px;line-height:1.5;">
    {authors_h} · <code style="background:#f4f4f4;padding:1px 5px;border-radius:3px;font-size:11px;">{cat_h}</code>
    · <a href="{paper.url}" style="color:#1756a9;text-decoration:none;">abs</a>
    · <a href="{paper.pdf_url}" style="color:#1756a9;text-decoration:none;">pdf</a>
  </div>
  <table class="ar-fields" role="presentation" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;width:100%;">{fields_html}</table>
</div>
"""


def render_html(
    selected: list[SelectedRow],
    skipped_titles: list[tuple[str, int]],
    date_str: str,
) -> str:
    n_total = len(selected) + len(skipped_titles)

    if selected:
        papers_html = "".join(
            _html_paper(p, sc, r, s, i)
            for i, (p, sc, r, s) in enumerate(selected, 1)
        )
    else:
        papers_html = (
            '<div style="padding:20px;background:#fafafa;border-radius:6px;color:#666;'
            'text-align:center;font-style:italic;">'
            'No papers cleared the relevance threshold today.</div>'
        )

    skipped_html = ""
    if skipped_titles:
        items = "".join(
            f'<li style="color:#666;font-size:12px;margin-bottom:3px;">'
            f'<span style="color:#999;">({sc})</span> {html.escape(t)}</li>'
            for t, sc in skipped_titles[:20]
        )
        more = ""
        if len(skipped_titles) > 20:
            more = (f'<li style="color:#999;font-size:12px;font-style:italic;">'
                    f'…and {len(skipped_titles) - 20} more</li>')
        skipped_html = f"""
<details style="margin-top:24px;padding:12px 16px;background:#fafafa;border-radius:6px;">
  <summary style="cursor:pointer;font-size:13px;color:#555;font-weight:600;">
    Also scanned ({len(skipped_titles)} below threshold)
  </summary>
  <ul style="margin:10px 0 0 0;padding-left:20px;">{items}{more}</ul>
</details>
"""

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light only">
<meta name="supported-color-schemes" content="light only">
<title>Arxiv Radar — {date_str}</title>
<style>
  /* Mobile: stack the label/value rows and shrink padding */
  @media only screen and (max-width: 600px) {{
    .ar-container {{ padding: 16px 10px !important; }}
    .ar-card      {{ padding: 14px 14px !important; border-radius: 4px !important; }}
    .ar-title     {{ font-size: 24px !important; }}
    .ar-subtitle  {{ font-size: 12px !important; }}
    .ar-fields, .ar-fields tbody, .ar-fields tr, .ar-fields td {{
      display: block !important;
      width: 100% !important;
    }}
    .ar-label {{
      padding: 10px 0 2px 0 !important;
      width: auto !important;
      font-size: 11px !important;
      letter-spacing: 0.5px;
      text-transform: uppercase;
      color: #888 !important;
    }}
    .ar-val   {{ padding: 0 0 4px 0 !important; font-size: 14px !important; }}
    .ar-meta  {{ font-size: 11px !important; }}
  }}
  /* Dark-mode clients: keep cards readable */
  @media (prefers-color-scheme: dark) {{
    body, .ar-bg {{ background: #1a1a1a !important; }}
  }}
  a {{ color: #1756a9; }}
</style>
</head>
<body class="ar-bg" style="margin:0;padding:0;background:#f5f5f7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;-webkit-text-size-adjust:100%;">
<div class="ar-container" style="max-width:720px;margin:0 auto;padding:24px 16px;">
  <div style="margin-bottom:20px;">
    <div class="ar-title" style="font-size:22px;font-weight:700;color:#111;letter-spacing:-0.3px;line-height:1.2;">
      📡 Arxiv Radar
    </div>
    <div class="ar-subtitle" style="font-size:13px;color:#777;margin-top:4px;line-height:1.4;">
      {date_str} · <strong style="color:#0a7f3f;">{len(selected)} relevant</strong>
      out of {n_total} scanned
    </div>
  </div>
  {papers_html}
  {skipped_html}
  <div style="margin-top:30px;padding-top:14px;border-top:1px solid #e5e5e5;
              font-size:11px;color:#999;text-align:center;line-height:1.5;">
    Generated by arxiv_radar · GPT-5 via TRAPI · Scored against your profile.md
  </div>
</div>
</body></html>
"""


# ---------- Email ----------

def send_email(
    digest_path: Path,
    selected: list[SelectedRow],
    skipped_titles: list[tuple[str, int]],
    sender: str,
    recipient: str | list[str],
    subject: str,
    smtp_host: str = "smtp.gmail.com",
    smtp_port: int = 587,
) -> None:
    app_password = keyring.get_password(KEYRING_SERVICE, KEYRING_KEY)
    if not app_password:
        raise RuntimeError(
            f"No Gmail app password in keyring. Run once:\n"
            f'  python -c "import keyring; keyring.set_password(\'{KEYRING_SERVICE}\', \'{KEYRING_KEY}\', \'<APP-PASSWORD>\')"'
        )

    if isinstance(recipient, str):
        recipients = [r.strip() for r in recipient.split(",") if r.strip()]
    else:
        recipients = [r.strip() for r in recipient if r and r.strip()]
    if not recipients:
        raise ValueError("At least one recipient required")

    plain_body = digest_path.read_text(encoding="utf-8")
    date_str = datetime.now().strftime("%Y-%m-%d")
    html_body = render_html(selected, skipped_titles, date_str)

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.set_content(plain_body)
    msg.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(smtp_host, smtp_port, timeout=60) as s:
        s.starttls()
        s.login(sender, app_password)
        s.send_message(msg, from_addr=sender, to_addrs=recipients)
    log.info("Email sent to %s", ", ".join(recipients))

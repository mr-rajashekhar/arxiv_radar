"""
One-off: re-send an existing digest markdown file via the same Gmail SMTP
credentials radar.py uses. Run after rotating the Gmail app password if a
prior run wrote the digest to disk but failed at the email step.

Usage:
    python resend_digest.py                 # sends today's digest
    python resend_digest.py 2026-06-09      # sends a specific date
"""
from __future__ import annotations

import smtplib
import sys
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

import keyring
import yaml

ROOT = Path(__file__).resolve().parent

date_str = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")
cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))

digest_path = ROOT / cfg["paths"]["digests_dir"] / f"{date_str}.md"
if not digest_path.exists():
    raise SystemExit(f"No digest at {digest_path}")

sender = cfg["email"]["sender"]
recipient = cfg["email"]["recipient"]
if isinstance(recipient, str):
    recipients = [r.strip() for r in recipient.split(",") if r.strip()]
else:
    recipients = [r.strip() for r in recipient if r and r.strip()]

subject = f"{cfg['email']['subject_prefix']} {date_str} (resend)"
body = digest_path.read_text(encoding="utf-8")

app_password = keyring.get_password("arxiv_radar", "gmail")
if not app_password:
    raise SystemExit("No app password in keyring.")

msg = EmailMessage()
msg["From"] = sender
msg["To"] = ", ".join(recipients)
msg["Subject"] = subject
msg.set_content(body)

with smtplib.SMTP(cfg["email"]["smtp_host"], cfg["email"]["smtp_port"], timeout=60) as s:
    s.starttls()
    s.login(sender, app_password)
    s.send_message(msg, from_addr=sender, to_addrs=recipients)

print(f"Sent {digest_path.name} to {', '.join(recipients)}")

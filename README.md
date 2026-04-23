# Arxiv Research Radar

A small agent that emails you a personalized daily digest of newly-published
arxiv papers relevant to **your** research, every morning.

## Pipeline

```
fetch (arxiv API, last ~36h, cs.DC/cs.AR/cs.OS/cs.LG/cs.SY/cs.PF)
  -> dedup           (SQLite)
  -> triage          (LLM, titles only — drops obvious irrelevants)
  -> score           (LLM, abstract + profile — relevance 0-10)
  -> filter          (score >= 7, cap N per day)
  -> summarize       (LLM + ar5iv HTML Intro/Conclusion — 7 structured fields)
  -> write digests/YYYY-MM-DD.md
  -> email           (Gmail SMTP, responsive HTML + plain-text fallback)
```

## Features

- **Two-pass scoring**: cheap title-only triage drops ~80% of noise before the
  expensive abstract-based pass.
- **ar5iv enrichment**: pulls Introduction + Conclusion from the paper's HTML
  render so summaries have concrete mechanism names (not just abstract fluff).
- **7-field summary**: Problem, Contribution, Results, Setup, Baselines,
  Why-for-you, Caveat.
- **Responsive HTML email**: looks clean on phone, iPad, and laptop.
- **Idempotent + retry-friendly**: runs from 7 AM with 5-min retries for 3h;
  self-disables after the first success; a companion task re-enables it at
  6:59 AM the next day.

## One-time setup

```powershell
cd arxiv_radar

# 1. Install deps
pip install -r requirements.txt

# 2. Authenticate to TRAPI (Microsoft internal)
az login

# 3. Smoke-test the LLM endpoint
python llm_client.py      # expected: "Paris"

# 4. Seed your research profile (reads papers you point bootstrap_profile.py at)
cp profile.example.md profile.md   # or: python bootstrap_profile.py
# Then hand-edit profile.md to reflect your interests precisely.

# 5. Store Gmail App Password (NOT your Google password; needs 2FA on).
#    Generate one at: https://myaccount.google.com/apppasswords
python -c "import keyring; keyring.set_password('arxiv_radar','gmail','xxxxxxxxxxxxxxxx')"

# 6. Edit config.yaml — set email.sender and email.recipient.
cp config.example.yaml config.yaml

# 7. Dry-run
python radar.py

# 8. Register the daily schedule (7 AM start, retry every 5 min for 3h)
powershell -ExecutionPolicy Bypass -File .\register_task.ps1
```

## Files

| File | Purpose |
|------|---------|
| `radar.py` | Orchestrator (entrypoint) |
| `llm_client.py` | TRAPI Azure OpenAI wrapper with retry/backoff |
| `arxiv_client.py` | Arxiv API fetcher |
| `ar5iv_client.py` | Pulls Intro + Conclusion from ar5iv HTML |
| `scorer.py` | Two-pass batched LLM relevance scorer |
| `summarizer.py` | Per-paper 7-field structured summarizer |
| `memory.py` | SQLite dedup |
| `deliver.py` | Markdown digest writer + responsive HTML email sender |
| `bootstrap_profile.py` | One-time profile seeder from your own papers |
| `test_email.py` | Standalone SMTP tester (skips fetch/LLM) |
| `config.yaml` | Categories, thresholds, ar5iv toggle, email settings |
| `profile.md` | Your research profile (git-ignored; personal) |
| `profile.example.md` | Template for new users |
| `run_radar.bat` | Task Scheduler wrapper |
| `register_task.ps1` | Registers the two daily tasks |

## Configuration

All runtime behavior lives in `config.yaml`:

- `arxiv.categories`, `arxiv.lookback_hours`
- `scoring.triage.enabled / batch_size / threshold`
- `scoring.batch_size / threshold / max_summaries / use_ar5iv`
- `email.enabled / sender / recipient`

## Tuning

- **Too many papers?** Raise `scoring.threshold` to 8 or lower `max_summaries`.
- **Missing relevant papers?** Edit `profile.md`; be specific in INTERESTED_IN;
  use concrete terminology the LLM can match against.
- **Digest feels generic?** Make `profile.md` reference your specific
  papers/projects by name — the `why_for_you` field improves dramatically.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `DefaultAzureCredential failed` | `az login` again |
| `No Gmail app password in keyring` | Run the `keyring.set_password` command above |
| `535 Authentication failed` on SMTP | Use an **App Password**, not your Google password |
| Task didn't run | `Get-ScheduledTaskInfo -TaskName ArxivRadar`; confirm machine TZ |
| Empty digest every day | Edit `profile.md`; lower `scoring.threshold`; widen categories |
| Task stays disabled | `schtasks /Change /TN ArxivRadar /ENABLE` or wait for 6:59 AM reset |

## Privacy

- `profile.md`, `digests/`, `logs/`, `seen.db`, and `state/` are all in
  `.gitignore`. Your research interests, read history, and generated content
  never leave your machine (other than what you explicitly email).
- TRAPI calls go to Microsoft's internal endpoint only.

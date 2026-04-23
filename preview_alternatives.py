"""
Render 3 alternative HTML email styles for arxiv_radar, using the same dummy data.
Writes preview_a.html, preview_b.html, preview_c.html.
"""
from __future__ import annotations
import html
import webbrowser
from pathlib import Path

FIELDS = [
    ("problem",      "Problem"),
    ("contribution", "Contribution"),
    ("results",      "Results"),
    ("setup",        "Setup"),
    ("baselines",    "Baselines"),
    ("why_for_you",  "Why for you"),
    ("caveat",       "Caveat"),
]

# --- dummy data ---
PAPERS = [
    dict(rank=1, score=9,
         title="DistServe: Disaggregating Prefill and Decoding for Goodput-Optimized LLM Serving",
         authors="Yinmin Zhong, Shengyu Liu, Junda Chen et al.",
         cat="cs.DC",
         url="https://arxiv.org/abs/2604.18529",
         pdf="https://arxiv.org/pdf/2604.18529",
         reason="Directly relevant to disaggregated serving and scheduling.",
         fields=dict(
           problem="Co-locating prefill and decoding causes interference that hurts TTFT/TPOT SLOs.",
           contribution="Disaggregates prefill and decode onto separate GPU pools and co-optimizes placement + parallelism for goodput.",
           results="Up to 4.48x goodput at the same SLO vs vLLM on Llama-2-13B.",
           setup="Llama-2-13B, OPT-66B on 8xA100, ShareGPT + LongBench traces.",
           baselines="vLLM, DeepSpeed-MII, TensorRT-LLM.",
           why_for_you="Directly informs XWind/Heron cross-site routing: same disagg primitive could span sites.",
           caveat="Assumes reliable NVLink between pools; inter-site latency not modeled.")),
    dict(rank=2, score=8,
         title="GreenServe: Carbon-Aware LLM Inference Across Heterogeneous GPU Fleets",
         authors="A. Researcher, B. Author",
         cat="cs.DC",
         url="https://arxiv.org/abs/2604.17695",
         pdf="https://arxiv.org/pdf/2604.17695",
         reason="Carbon-aware scheduling overlaps with Greenferencing.",
         fields=dict(
           problem="Inference fleets ignore regional carbon intensity.",
           contribution="Scheduler that shifts decode requests to low-carbon sites using a lightweight forecaster.",
           results="18-27% carbon reduction with 3% p99 latency overhead.",
           setup="Simulated 4-region fleet, Azure carbon traces.",
           baselines="Round-robin, least-loaded.",
           why_for_you="Direct overlap with AI Greenferencing; compare their forecaster to ours.",
           caveat="Simulation only; no real deployment.")),
    dict(rank=3, score=7,
         title="vAttention: Dynamic Memory Management for Serving LLMs without PagedAttention",
         authors="R. Prabhu, A. Nayak et al.",
         cat="cs.AR",
         url="https://arxiv.org/abs/2604.17861",
         pdf="https://arxiv.org/pdf/2604.17861",
         reason="KV-cache memory system, relevant to serving stack.",
         fields=dict(
           problem="PagedAttention pollutes the attention kernel with virtual-memory bookkeeping.",
           contribution="Uses CUDA VMM APIs to get paging benefits without kernel changes.",
           results="1.23-1.97x higher throughput; retains unmodified FlashAttention kernels.",
           setup="Llama-3-8B / 70B on H100.",
           baselines="vLLM (PagedAttention), TensorRT-LLM.",
           why_for_you="Cleaner KV mgmt primitive to consider when prototyping cross-site migration.",
           caveat="CUDA-specific; ROCm / TPU path unclear.")),
]
SKIPPED = [("Tangential paper on classical DB indexing", 3),
           ("Yet another RL benchmark", 2),
           ("Compiler paper about SIMD", 4)]

def esc(s): return html.escape(str(s))

# ====================================================================
# Style A: Newsletter (Stripe/Linear-style) — minimalist, serif headers
# ====================================================================
def render_a():
    def card(p):
        fs = "".join(
            f'<p style="margin:0 0 8px 0;font-size:14px;line-height:1.55;color:#1a1a1a;">'
            f'<strong style="color:#6b46c1;font-weight:600;">{lbl}.</strong> '
            f'{esc(p["fields"][k])}</p>'
            for k, lbl in FIELDS
        )
        return f"""
<article style="margin:0 0 36px 0;padding-bottom:28px;border-bottom:1px solid #ececec;">
  <div style="font-size:11px;color:#888;letter-spacing:1.2px;text-transform:uppercase;margin-bottom:6px;">
    Paper #{p['rank']} &nbsp;·&nbsp; Score {p['score']}/10 &nbsp;·&nbsp; {esc(p['cat'])}
  </div>
  <h2 style="margin:0 0 6px 0;font-family:Georgia,serif;font-size:20px;font-weight:normal;color:#111;line-height:1.3;">
    <a href="{p['url']}" style="color:#111;text-decoration:none;">{esc(p['title'])}</a>
  </h2>
  <div style="font-size:12px;color:#777;margin-bottom:4px;">{esc(p['authors'])}</div>
  <div style="font-size:13px;color:#6b46c1;font-style:italic;margin-bottom:14px;">
    "{esc(p['reason'])}"
  </div>
  {fs}
  <div style="margin-top:12px;font-size:12px;">
    <a href="{p['url']}" style="color:#6b46c1;text-decoration:none;font-weight:600;">Read abstract →</a>
    &nbsp;&nbsp;<a href="{p['pdf']}" style="color:#888;text-decoration:none;">PDF</a>
  </div>
</article>"""
    papers = "".join(card(p) for p in PAPERS)
    skipped = "<ul style='padding-left:18px;color:#888;font-size:12px;'>" + "".join(
        f"<li>({s}) {esc(t)}</li>" for t, s in SKIPPED) + "</ul>"
    return f"""<!doctype html><html><body style="margin:0;background:#fafaf8;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<div style="max-width:640px;margin:0 auto;padding:40px 24px;background:#ffffff;">
  <div style="text-align:center;margin-bottom:40px;padding-bottom:24px;border-bottom:2px solid #111;">
    <div style="font-family:Georgia,serif;font-size:32px;font-weight:normal;color:#111;letter-spacing:-0.5px;">
      Arxiv Radar
    </div>
    <div style="font-size:12px;color:#888;margin-top:4px;letter-spacing:1px;">
      DAILY DIGEST · 2026-04-21 · 3 OF 152
    </div>
  </div>
  {papers}
  <details style="margin-top:30px;color:#888;font-size:12px;">
    <summary style="cursor:pointer;">Also scanned ({len(SKIPPED)} below threshold)</summary>
    {skipped}
  </details>
</div></body></html>"""

# ====================================================================
# Style B: Dashboard (GitHub/Notion-style) — dense, monospace accents
# ====================================================================
def render_b():
    def score_badge(s):
        bg = "#238636" if s >= 9 else "#1f6feb" if s >= 8 else "#9e6a03"
        return f'<span style="display:inline-block;background:{bg};color:#fff;padding:3px 8px;border-radius:10px;font-size:11px;font-weight:600;font-family:ui-monospace,monospace;">{s}/10</span>'

    def card(p):
        rows = "".join(
            f'<div style="display:flex;padding:6px 0;border-top:1px solid #30363d;">'
            f'<div style="width:110px;flex-shrink:0;color:#7d8590;font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:11px;padding-top:2px;">{lbl.lower().replace(" ","_")}</div>'
            f'<div style="color:#e6edf3;font-size:13px;line-height:1.5;">{esc(p["fields"][k])}</div>'
            f'</div>'
            for k, lbl in FIELDS
        )
        return f"""
<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;margin-bottom:16px;overflow:hidden;">
  <div style="padding:14px 18px;background:#0d1117;border-bottom:1px solid #30363d;">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
      {score_badge(p['score'])}
      <span style="color:#7d8590;font-size:11px;font-family:ui-monospace,monospace;">#{p['rank']} · {esc(p['cat'])}</span>
    </div>
    <a href="{p['url']}" style="color:#58a6ff;text-decoration:none;font-size:15px;font-weight:600;line-height:1.35;">{esc(p['title'])}</a>
    <div style="color:#7d8590;font-size:11px;margin-top:4px;">{esc(p['authors'])}</div>
    <div style="color:#8b949e;font-size:12px;margin-top:8px;font-style:italic;">› {esc(p['reason'])}</div>
  </div>
  <div style="padding:4px 18px 14px 18px;">
    {rows}
  </div>
  <div style="padding:10px 18px;background:#0d1117;border-top:1px solid #30363d;font-size:12px;font-family:ui-monospace,monospace;">
    <a href="{p['url']}" style="color:#58a6ff;text-decoration:none;">[abs]</a>&nbsp;
    <a href="{p['pdf']}" style="color:#58a6ff;text-decoration:none;">[pdf]</a>
  </div>
</div>"""
    papers = "".join(card(p) for p in PAPERS)
    skipped = "".join(
        f'<div style="padding:4px 0;color:#7d8590;font-size:12px;font-family:ui-monospace,monospace;">'
        f'<span style="color:#8b949e;">({s})</span> {esc(t)}</div>'
        for t, s in SKIPPED)
    return f"""<!doctype html><html><body style="margin:0;background:#0d1117;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:#e6edf3;">
<div style="max-width:760px;margin:0 auto;padding:24px 16px;">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;padding-bottom:14px;border-bottom:1px solid #30363d;">
    <div>
      <div style="font-size:18px;font-weight:700;color:#e6edf3;font-family:ui-monospace,SFMono-Regular,Consolas,monospace;">
        arxiv_radar<span style="color:#7d8590;">/digest</span>
      </div>
      <div style="font-size:12px;color:#7d8590;margin-top:2px;font-family:ui-monospace,monospace;">
        2026-04-21 · scanned=152 · kept=3 · threshold=7
      </div>
    </div>
    <div style="color:#238636;font-size:11px;font-family:ui-monospace,monospace;">● RUN OK</div>
  </div>
  {papers}
  <details style="margin-top:20px;background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px 18px;">
    <summary style="cursor:pointer;color:#8b949e;font-size:12px;font-family:ui-monospace,monospace;">below_threshold ({len(SKIPPED)})</summary>
    <div style="margin-top:10px;">{skipped}</div>
  </details>
</div></body></html>"""

# ====================================================================
# Style C: Magazine (The Browser / Atlantic-style) — editorial, warm
# ====================================================================
def render_c():
    def card(p):
        # put results + contribution as the big "pull"; rest as sidebar-ish
        primary = f"""
<div style="font-size:18px;line-height:1.55;color:#2a2420;margin-bottom:14px;font-family:Charter,Georgia,serif;">
  <strong style="color:#8b4513;">{esc(p['fields']['contribution'])}</strong>
</div>
<div style="font-size:15px;line-height:1.6;color:#3a342e;margin-bottom:16px;font-family:Charter,Georgia,serif;">
  <em>The problem:</em> {esc(p['fields']['problem'])}
  &nbsp;<em>The number:</em> {esc(p['fields']['results'])}
</div>
<div style="background:#f5f0e8;border-left:3px solid #8b4513;padding:12px 16px;margin-bottom:14px;font-size:14px;color:#3a342e;font-style:italic;font-family:Charter,Georgia,serif;">
  Why this matters to you: {esc(p['fields']['why_for_you'])}
</div>"""
        meta_rows = [
            ("Setup", p['fields']['setup']),
            ("Compared against", p['fields']['baselines']),
            ("Caveat", p['fields']['caveat']),
        ]
        meta = "".join(
            f'<div style="font-size:12px;color:#6b5d50;margin-bottom:6px;">'
            f'<strong style="color:#8b4513;">{lbl}.</strong> {esc(v)}</div>'
            for lbl, v in meta_rows
        )
        return f"""
<article style="margin:0 0 44px 0;padding-bottom:32px;border-bottom:1px dashed #c4b8a8;">
  <div style="font-size:11px;color:#8b4513;letter-spacing:2px;margin-bottom:8px;font-weight:600;">
    No. {p['rank']}  ·  RELEVANCE {p['score']}/10  ·  {esc(p['cat']).upper()}
  </div>
  <h2 style="margin:0 0 10px 0;font-family:Charter,Georgia,serif;font-size:26px;font-weight:700;color:#1a1410;line-height:1.2;">
    <a href="{p['url']}" style="color:#1a1410;text-decoration:none;border-bottom:2px solid #8b4513;">{esc(p['title'])}</a>
  </h2>
  <div style="font-size:12px;color:#8a7d70;font-style:italic;margin-bottom:20px;font-family:Charter,Georgia,serif;">
    By {esc(p['authors'])}
  </div>
  {primary}
  {meta}
  <div style="margin-top:14px;font-size:11px;letter-spacing:1.5px;">
    <a href="{p['url']}" style="color:#8b4513;text-decoration:none;font-weight:600;">READ THE ABSTRACT →</a>
    &nbsp;·&nbsp;<a href="{p['pdf']}" style="color:#8a7d70;text-decoration:none;">PDF</a>
  </div>
</article>"""
    papers = "".join(card(p) for p in PAPERS)
    skipped = "".join(f"<li style='margin-bottom:4px;'>({s}) {esc(t)}</li>" for t, s in SKIPPED)
    return f"""<!doctype html><html><body style="margin:0;background:#faf6ef;font-family:Charter,Georgia,serif;">
<div style="max-width:620px;margin:0 auto;padding:48px 28px;background:#fffdf8;box-shadow:0 0 40px rgba(0,0,0,0.04);">
  <div style="text-align:center;margin-bottom:44px;">
    <div style="font-size:11px;letter-spacing:4px;color:#8b4513;margin-bottom:10px;font-weight:700;font-family:-apple-system,sans-serif;">
      ✦&nbsp;&nbsp;ARXIV RADAR&nbsp;&nbsp;✦
    </div>
    <div style="font-size:44px;font-family:Charter,Georgia,serif;color:#1a1410;font-weight:700;letter-spacing:-1px;line-height:1;">
      Today's Dispatch
    </div>
    <div style="font-size:13px;color:#8a7d70;margin-top:10px;font-style:italic;">
      April 21, 2026 &nbsp;·&nbsp; 3 papers worth your time, out of 152 scanned
    </div>
  </div>
  {papers}
  <details style="margin-top:20px;font-size:12px;color:#8a7d70;font-family:-apple-system,sans-serif;">
    <summary style="cursor:pointer;letter-spacing:1px;text-transform:uppercase;font-weight:600;color:#8b4513;">
      Also on the radar ({len(SKIPPED)} below threshold)
    </summary>
    <ul style="padding-left:20px;margin-top:10px;">{skipped}</ul>
  </details>
  <div style="text-align:center;margin-top:40px;padding-top:20px;border-top:1px solid #e8dfd0;font-size:11px;color:#a89888;letter-spacing:2px;font-family:-apple-system,sans-serif;">
    ✦&nbsp;&nbsp;&nbsp;F I N I S&nbsp;&nbsp;&nbsp;✦
  </div>
</div></body></html>"""

root = Path(__file__).parent
for name, fn in [("a", render_a), ("b", render_b), ("c", render_c)]:
    path = root / f"preview_{name}.html"
    path.write_text(fn(), encoding="utf-8")
    print("wrote", path)
    webbrowser.open(path.as_uri())

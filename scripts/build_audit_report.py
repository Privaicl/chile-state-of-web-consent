"""Build a static HTML audit report for human review of LLM agent predictions.

Usage:
    uv run python scripts/build_audit_report.py
    uv run python scripts/build_audit_report.py --validations results/validations --out results/audit_report.html
"""
from __future__ import annotations

import argparse
import base64
import html
import json
from pathlib import Path

CATEGORIES = ["accept", "reject", "settings", "save", "pay"]

CATEGORY_LABELS = {
    "accept": "Accept",
    "reject": "Reject",
    "settings": "Settings",
    "save": "Save prefs",
    "pay": "Pay/subscribe",
}


def _img_tag(path: Path, width: int = 600, alt: str = "") -> str:
    """Return an <img> tag with a base64-encoded data URI so the report is self-contained."""
    if not path.exists():
        return "<em style='color:#999'>image not found</em>"
    try:
        raw = path.read_bytes()
        b64 = base64.b64encode(raw).decode("ascii")
        return (
            f'<img src="data:image/png;base64,{b64}" '
            f'width="{width}" style="max-width:100%;border:1px solid #ccc;border-radius:4px" '
            f'alt="{html.escape(alt)}">'
        )
    except Exception as exc:
        return f"<em style='color:red'>image error: {html.escape(str(exc))}</em>"


def _radio(name: str, value: str, label: str, checked: bool = False) -> str:
    c = " checked" if checked else ""
    return (
        f'<label style="margin-right:12px;cursor:pointer">'
        f'<input type="radio" name="{html.escape(name)}" '
        f'value="{html.escape(value)}"{c}> {label}</label>'
    )


def _build_button_row(rank: int, cat: str, pred: dict | None, val_dir: Path) -> str:
    cat_label = CATEGORY_LABELS.get(cat, cat)
    img_cell: str
    pred_cell: str

    if pred is None:
        img_cell = "<em style='color:#999'>— null prediction</em>"
        pred_cell = "<em style='color:#999'>null</em>"
    else:
        img_path = val_dir / f"{cat}.png"
        img_cell = _img_tag(img_path, width=300, alt=f"{cat} button")
        role = html.escape(str(pred.get("role") or ""))
        name = html.escape(str(pred.get("name") or ""))
        ref = html.escape(str(pred.get("ref") or ""))
        snippet = html.escape((pred.get("outer_html_snippet") or "")[:200])
        pred_cell = (
            f"<strong>ref:</strong> {ref}<br>"
            f"<strong>role:</strong> {role}<br>"
            f"<strong>name:</strong> {name}<br>"
            f'<details><summary style="cursor:pointer;color:#555">HTML snippet</summary>'
            f'<pre style="font-size:11px;max-width:400px;white-space:pre-wrap;overflow:auto">'
            f"{snippet}</pre></details>"
        )

    radio_name = f"btn_{rank}_{cat}"
    radio_html = (
        _radio(radio_name, "ok", "correct")
        + _radio(radio_name, "wrong", "wrong")
        + _radio(radio_name, "na", "not applicable")
    )

    return (
        f"<tr>"
        f'<td style="padding:8px;font-weight:bold;white-space:nowrap">{html.escape(cat_label)}</td>'
        f'<td style="padding:8px">{img_cell}</td>'
        f'<td style="padding:8px;vertical-align:top;font-size:13px">{pred_cell}</td>'
        f'<td style="padding:8px;white-space:nowrap">{radio_html}</td>'
        f"</tr>"
    )


def _build_site_section(rank: int, pred_doc: dict, val_dir: Path) -> str:
    company = html.escape(pred_doc.get("company") or "")
    url = html.escape(pred_doc.get("url") or "")
    scraped_url = html.escape(pred_doc.get("scraped_url") or url)
    cmp_name = html.escape(pred_doc.get("cmp_name") or "—")
    cmp_source = html.escape(pred_doc.get("cmp_source") or "—")
    conf = pred_doc.get("banner_validator_confidence")
    conf_str = f"{conf:.2f}" if conf is not None else "—"

    heading = (
        f"<h2 style='margin-top:0;color:#1a1a2e'>"
        f"#{rank} {company}"
        f"</h2>"
        f"<p style='margin:4px 0;font-size:13px;color:#555'>"
        f'CMP: <strong>{cmp_name}</strong> ({cmp_source}) &nbsp;|&nbsp; '
        f"banner_validator confidence: <strong>{conf_str}</strong> &nbsp;|&nbsp; "
        f'<a href="{url}" target="_blank" rel="noopener">{url}</a>'
        f"</p>"
    )

    banner_img = _img_tag(val_dir / "banner.png", width=600, alt="banner screenshot")

    # Banner validator section
    aria_txt_path = val_dir / "banner.aria.txt"
    if aria_txt_path.exists():
        aria_content = html.escape(aria_txt_path.read_text(encoding="utf-8", errors="replace"))
    else:
        aria_content = "(banner.aria.txt not found)"

    banner_radio_name = f"banner_{rank}"
    banner_radios = (
        _radio(banner_radio_name, "yes", "banner")
        + _radio(banner_radio_name, "no", "not a banner")
        + _radio(banner_radio_name, "unsure", "unsure")
    )
    banner_section = (
        f"<div style='margin:12px 0;padding:12px;background:#f8f8ff;border-left:4px solid #6c63ff;border-radius:4px'>"
        f"<strong>banner_validator</strong> &nbsp; {banner_radios}<br><br>"
        f'<details><summary style="cursor:pointer;color:#555;font-size:13px">ARIA snapshot (banner.aria.txt)</summary>'
        f'<pre style="font-size:11px;max-width:700px;max-height:300px;overflow:auto;'
        f'white-space:pre-wrap;background:#fafafa;padding:8px;border:1px solid #ddd">'
        f"{aria_content}</pre></details>"
        f"</div>"
    )

    # Button table
    predictions = pred_doc.get("predictions") or {}
    rows = "".join(
        _build_button_row(rank, cat, predictions.get(cat), val_dir)
        for cat in CATEGORIES
    )
    table = (
        f"<table style='border-collapse:collapse;width:100%;margin:12px 0'>"
        f"<thead><tr style='background:#eee'>"
        f"<th style='padding:8px;text-align:left'>Category</th>"
        f"<th style='padding:8px;text-align:left'>Screenshot</th>"
        f"<th style='padding:8px;text-align:left'>Prediction</th>"
        f"<th style='padding:8px;text-align:left'>Label</th>"
        f"</tr></thead><tbody>{rows}</tbody></table>"
    )

    return (
        f"<section id='site-{rank}' "
        f"style='margin:32px 0;padding:20px;background:#fff;border-radius:8px;"
        f"box-shadow:0 2px 8px rgba(0,0,0,.1)'>"
        f"{heading}"
        f"<div style='margin:12px 0'>{banner_img}</div>"
        f"{banner_section}"
        f"{table}"
        f"</section>"
    )


def build_report(validations_dir: Path, out_path: Path) -> int:
    """Build the HTML report. Returns the number of sites rendered."""
    rank_dirs = sorted(
        (d for d in validations_dir.iterdir() if d.is_dir() and d.name.isdigit()),
        key=lambda d: int(d.name),
    )

    sections: list[str] = []
    toc_items: list[str] = []

    for d in rank_dirs:
        pred_path = d / "predictions.json"
        if not pred_path.exists():
            continue
        try:
            pred_doc = json.loads(pred_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        rank = int(d.name)
        company = html.escape(pred_doc.get("company") or "")
        toc_items.append(
            f'<li><a href="#site-{rank}">#{rank} {company}</a></li>'
        )
        sections.append(_build_site_section(rank, pred_doc, d))

    toc_html = (
        f"<nav style='padding:16px;background:#f0f0f0;border-radius:6px;margin-bottom:24px'>"
        f"<strong>Sites ({len(sections)})</strong>"
        f"<ul style='margin:8px 0 0 0;padding-left:20px'>{''.join(toc_items)}</ul>"
        f"</nav>"
    ) if toc_items else "<p>No validation directories found.</p>"

    save_script = """
<script>
function collectLabels() {
  const data = {};
  document.querySelectorAll('input[type=radio]:checked').forEach(function(el) {
    const name = el.name;
    const val = el.value;
    // name is "banner_<rank>" or "btn_<rank>_<cat>"
    const bannerMatch = name.match(/^banner_(\\d+)$/);
    const btnMatch = name.match(/^btn_(\\d+)_(.+)$/);
    if (bannerMatch) {
      const rank = bannerMatch[1];
      if (!data[rank]) data[rank] = {};
      data[rank]['banner'] = val;
    } else if (btnMatch) {
      const rank = btnMatch[1];
      const cat = btnMatch[2];
      if (!data[rank]) data[rank] = {};
      data[rank][cat] = val;
    }
  });
  return data;
}

document.getElementById('save-btn').addEventListener('click', function() {
  const labels = collectLabels();
  fetch('http://localhost:8123/save', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(labels)
  })
  .then(function(r) { return r.json(); })
  .then(function(d) {
    document.getElementById('save-status').textContent =
      'Saved ' + Object.keys(d.saved || {}).length + ' sites at ' + new Date().toLocaleTimeString();
  })
  .catch(function(e) {
    document.getElementById('save-status').textContent = 'Error: ' + e.message;
  });
});
</script>
"""

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Cookie Consent Banner Audit Report</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 900px; margin: 0 auto; padding: 24px; background: #f5f5f5; }}
  h1 {{ color: #1a1a2e; }}
  a {{ color: #6c63ff; }}
  section:target {{ outline: 3px solid #6c63ff; }}
</style>
</head>
<body>
<h1>Cookie Consent Banner Audit Report</h1>
<p style="color:#555">Validate <strong>banner_validator</strong> and <strong>button_classifier</strong> agent predictions.
Choose a label for each item, then click <em>Save labels</em> at the bottom.</p>
{toc_html}
{''.join(sections)}
<div style="position:sticky;bottom:0;background:#fff;padding:16px;box-shadow:0 -2px 8px rgba(0,0,0,.15);border-top:2px solid #6c63ff;margin-top:32px;border-radius:8px 8px 0 0">
  <button id="save-btn" style="padding:10px 24px;font-size:15px;background:#6c63ff;color:#fff;border:none;border-radius:4px;cursor:pointer">
    Save labels
  </button>
  &nbsp;
  <span id="save-status" style="color:#555;font-size:13px"></span>
  <p style="font-size:12px;color:#999;margin:6px 0 0 0">
    POSTs to <code>localhost:8123/save</code> — run <code>uv run python scripts/label_server.py</code> first.
  </p>
</div>
{save_script}
</body>
</html>
"""

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_doc, encoding="utf-8")
    return len(sections)


def main() -> None:
    p = argparse.ArgumentParser(description="Build audit HTML report from validation artifacts")
    p.add_argument(
        "--validations",
        default="results/validations",
        help="Path to results/validations directory (default: results/validations)",
    )
    p.add_argument(
        "--out",
        default="results/audit_report.html",
        help="Output HTML path (default: results/audit_report.html)",
    )
    args = p.parse_args()

    val_dir = Path(args.validations)
    out_path = Path(args.out)

    if not val_dir.exists():
        print(f"Validations directory not found: {val_dir}")
        raise SystemExit(1)

    n = build_report(val_dir, out_path)
    print(f"Wrote {out_path} ({n} sites)")


if __name__ == "__main__":
    main()

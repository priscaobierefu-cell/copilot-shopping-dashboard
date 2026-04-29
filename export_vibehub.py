"""
Generate a VibeHub-ready ZIP containing a static HTML report.
If multiple waves exist in the database, includes a wave selector.

Usage:
    python export_vibehub.py
    → creates vibehub_export.zip with index.html inside
"""

import json
import os
from storage import init_db, get_all_waves, get_wave_scores
from report_template import generate_html_report
import zipfile
from io import BytesIO


def export_vibehub(output_path="vibehub_export.zip"):
    init_db()
    waves = get_all_waves()

    if not waves:
        print("No waves in database. Upload data via the dashboard first.")
        return

    if len(waves) == 1:
        # Single wave — just export the report
        w = waves[0]
        scores = get_wave_scores(w['id'])
        html = generate_html_report(scores, w['wave_label'], w['wave_date'])
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("index.html", html)
        print(f"Exported single wave '{w['wave_label']}' → {output_path}")
    else:
        # Multiple waves — generate each report and a selector page
        wave_files = []
        for w in waves:
            scores = get_wave_scores(w['id'])
            html = generate_html_report(scores, w['wave_label'], w['wave_date'])
            filename = f"wave_{w['id']}.html"
            wave_files.append({
                'id': w['id'],
                'label': w['wave_label'],
                'date': w['wave_date'],
                'filename': filename,
                'overall': w['overall_score'],
                'n': w['n_responses'],
                'html': html,
            })

        # Build index page with wave selector
        index_html = _build_index(wave_files)

        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("index.html", index_html)
            for wf in wave_files:
                zf.writestr(wf['filename'], wf['html'])

        print(f"Exported {len(wave_files)} waves → {output_path}")
        for wf in wave_files:
            print(f"  {wf['label']} ({wf['date']}) → {wf['filename']}")


def _build_index(wave_files):
    """Build a wave selector landing page."""
    cards = ''
    for wf in reversed(wave_files):  # newest first
        cards += f'''
        <a href="{wf['filename']}" class="wave-card">
          <div class="wave-label">{wf['label']}</div>
          <div class="wave-score">{wf['overall']}</div>
          <div class="wave-sub">Overall Score</div>
          <div class="wave-meta">{wf['date']} &middot; {wf['n']} responses</div>
        </a>'''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Copilot Shopping — User Metrics Dashboard</title>
<style>
:root {{
  --bg: #FEF9ED;
  --bg-card: #EFE2D1;
  --text: #3B230E;
  --text-muted: #7A6A56;
  --accent: #2E4D4D;
  --border: #D4C4AE;
  --shadow: 0 2px 12px rgba(59,35,14,0.08);
  --shadow-hover: 0 8px 32px rgba(59,35,14,0.16);
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
  font-family: 'Segoe UI', system-ui, sans-serif;
  background: var(--bg); color: var(--text);
  min-height: 100vh; display: flex; flex-direction: column;
  align-items: center; padding: 3rem 2rem;
}}
.hero {{
  text-align: center; margin-bottom: 3rem; max-width: 600px;
}}
.hero-label {{
  font-size: 0.72rem; font-weight: 600; letter-spacing: 0.15em;
  text-transform: uppercase; color: var(--text-muted); margin-bottom: 0.75rem;
}}
.hero h1 {{
  font-family: Georgia, serif; font-size: 2.2rem; font-weight: 400;
  margin-bottom: 0.5rem;
}}
.hero p {{
  color: var(--text-muted); font-size: 0.95rem; line-height: 1.6;
}}
.waves-grid {{
  display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 1.5rem; max-width: 900px; width: 100%;
}}
.wave-card {{
  background: var(--bg-card); border-radius: 16px; padding: 2rem;
  text-align: center; text-decoration: none; color: var(--text);
  box-shadow: var(--shadow); transition: transform 0.3s, box-shadow 0.3s;
  border: 1px solid transparent;
}}
.wave-card:hover {{
  transform: translateY(-4px); box-shadow: var(--shadow-hover);
  border-color: var(--accent);
}}
.wave-label {{
  font-size: 0.72rem; font-weight: 600; letter-spacing: 0.12em;
  text-transform: uppercase; color: var(--text-muted); margin-bottom: 1rem;
}}
.wave-score {{
  font-family: Georgia, serif; font-size: 3rem; font-weight: 400;
  color: var(--accent); line-height: 1;
}}
.wave-sub {{
  font-size: 0.78rem; color: var(--text-muted); margin-top: 0.3rem;
}}
.wave-meta {{
  font-size: 0.75rem; color: var(--text-muted); margin-top: 1rem;
  padding-top: 0.75rem; border-top: 1px solid var(--border);
}}
.footer {{
  margin-top: 3rem; font-size: 0.78rem; color: var(--text-muted);
  text-align: center;
}}
</style>
</head>
<body>
<div class="hero">
  <div class="hero-label">Copilot Shopping</div>
  <h1>User Metrics Dashboard</h1>
  <p>Select a wave below to view the full scorecard report with metrics, journey stages, satisfaction, and user voices.</p>
</div>
<div class="waves-grid">
  {cards}
</div>
<div class="footer">
  Copilot Shopping User Metrics Research &middot; {len(wave_files)} wave(s) available
</div>
</body>
</html>'''


if __name__ == '__main__':
    export_vibehub()

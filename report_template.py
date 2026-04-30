"""
Generates a standalone HTML scorecard report from wave scores,
matching the v3 template design.
"""
import json
import html

DOMAIN_ORDER = ['Quality', 'Trust & Confidence', 'Privacy & Security']
STAGE_ORDER = ['Inspiration', 'Research', 'Ready to Purchase', 'Post-Purchase']

SATISFACTION_LABELS = {
    1: 'Very Dissatisfied',
    2: 'Dissatisfied',
    3: 'Neutral',
    4: 'Satisfied',
    5: 'Very Satisfied',
}


def generate_html_report(scores: dict, wave_label: str, wave_date: str, all_waves: list = None) -> str:
    """Generate a standalone HTML scorecard report.
    
    Args:
        scores: current wave scores dict
        wave_label: e.g. 'Wave 1 Baseline'
        wave_date: e.g. '2026-04-29'
        all_waves: optional list of dicts with keys: wave_label, wave_date, overall_score, sat_score, domains, metrics
                   If provided and len >= 2, a Trends section is shown.
    """

    # Build JS DATA object
    js_metrics = []
    for m in scores.get('metrics', []):
        js_metrics.append({
            'name': m['name'],
            'domain': m['domain'],
            'score': m['score_100'],
            'mean': m['mean_1_5'],
            'sd': m['sd'],
            'n': m['n'],
        })

    js_data = {
        'metrics': js_metrics,
        'distributions': scores.get('distributions', {}),
        'stageData': scores.get('stage_data', {}),
        'metricQuotes': scores.get('metric_quotes', {}),
        'qualitativeThemes': scores.get('qualitative_themes', {}),
        'quotesPos': scores.get('quotes_pos', []),
        'quotesNeg': scores.get('quotes_neg', []),
        'stageN': scores.get('stage_n', {}),
        'surveyQuestions': {
            'Accuracy': 'How accurate was the shopping information provided by Copilot?',
            'Relevance': 'How relevant was Copilot\u2019s responses to what you wanted or needed?',
            'Personalization': 'How personalized was Copilot\u2019s response to your needs and preferences?',
            'Trustworthiness': 'Overall, how trustworthy and reliable are the sources of information in the Copilot responses?',
            'Data Protection': 'How protected do you think your data is while viewing the shopping information provided by Copilot?',
            'Comfort Sharing Info': 'How comfortable are you (or would you feel) sharing personal information with Copilot during shopping?',
            'Privacy-Respecting': 'How well did Copilot respect your privacy in its shopping response?',
            'Clarity': 'How clear was what you should do next when looking at the responses provided by Copilot?',
            'Intuitiveness': 'How easy was it to understand and use the shopping information Copilot gave you?',
            'Ease of Finding Info': 'How easy was it to find the product/service information you were interested in from Copilot\u2019s response?',
            'Helpfulness': 'How helpful was the Copilot\u2019s shopping information in giving you clear steps that saved you time and effort?',
            'Visual Appeal': 'Overall, how visually appealing was the Copilot\u2019s shopping information?',
            'Proactiveness': 'How well did the Copilot responses anticipate your next steps, offering ideas or guidance before you had to ask, reducing the need for follow-ups?',
        },
    }

    n_metrics = len(scores.get('metrics', []))
    has_themes = bool(scores.get('qualitative_themes', {}))

    n = scores.get('n', 0)
    overall = scores.get('overall', 0)
    domains = scores.get('domains', {})
    sat_score = scores.get('sat_score', 0)
    sat_mean = scores.get('sat_mean', 0)
    sat_n = scores.get('sat_n', 0)
    sat_dist = scores.get('sat_dist', {})
    stage_sat = scores.get('stage_sat', {})
    stage_n = scores.get('stage_n', {})

    # Build domain cards HTML
    domain_cards = ''
    domain_bg_colors = {'Quality': '#2E4D4D', 'Trust & Confidence': '#5B7E5B', 'Privacy & Security': '#C07D10'}
    for d in DOMAIN_ORDER:
        dd = domains.get(d, {})
        bg = domain_bg_colors.get(d, '#2E4D4D')
        domain_cards += f'''
        <div class="stat-card" style="background:{bg};color:#FEF9ED">
          <div class="stat-card-label" style="color:rgba(254,249,237,0.6)">{html.escape(d)}</div>
          <div class="stat-card-number" style="color:#FEF9ED">{dd.get('score_100', '—')}</div>
          <div class="stat-card-sub" style="color:rgba(254,249,237,0.6)">{dd.get('n_metrics', 0)} metrics &middot; mean {dd.get('mean_1_5', '—')}</div>
        </div>'''

    # Build satisfaction stage cards
    sat_stage_cards = ''
    for stage in STAGE_ORDER:
        sat = stage_sat.get(stage, {})
        sn = sat.get('n', stage_n.get(stage, 0))
        grey = ' grey' if sn < 30 else ''
        score_val = sat.get('score', '—')
        sat_stage_cards += f'''
      <div class="sat-card{grey}">
        <div class="sat-card-stage">{html.escape(stage)} <span class="metric-q-tip sat-q-tip" data-question="How well did Copilot help you accomplish this goal that you previously selected?">i</span></div>
        <div class="sat-card-score">{score_val}</div>
        <div class="sat-card-n">n = {sn}</div>
      </div>'''

    # Build heatmap stage headers
    heatmap_headers = ''
    for stage in STAGE_ORDER:
        sn = stage_n.get(stage, 0)
        grey_class = ' class="grey-header"' if sn < 30 else ''
        heatmap_headers += f'''
            <th{grey_class}>{html.escape(stage)}<br><span style="font-weight:400;font-size:0.65rem;opacity:0.7">n = {sn}</span></th>'''

    # Find the metric with lowest score for takeaway
    metrics_sorted = sorted(scores.get('metrics', []), key=lambda x: -x['score_100'])
    top3 = metrics_sorted[:3] if len(metrics_sorted) >= 3 else metrics_sorted
    bot3 = metrics_sorted[-3:] if len(metrics_sorted) >= 3 else metrics_sorted

    strongest = max(domains.items(), key=lambda x: x[1].get('score_100', 0)) if domains else ('—', {'score_100': 0})
    weakest = min(domains.items(), key=lambda x: x[1].get('score_100', 0)) if domains else ('—', {'score_100': 0})

    # Top metrics within the strongest domain
    strongest_domain_metrics = sorted(
        [m for m in scores.get('metrics', []) if m['domain'] == strongest[0]],
        key=lambda x: -x['score_100']
    )
    sd_top1 = strongest_domain_metrics[0] if len(strongest_domain_metrics) > 0 else top3[0]
    sd_top2 = strongest_domain_metrics[1] if len(strongest_domain_metrics) > 1 else top3[1]

    # Takeaway cards
    takeaway_cards = f'''
        <div class="takeaway-card">
          <div class="takeaway-num">1</div>
          <div class="takeaway-text">Overall perception is <strong>strong at {overall}/100</strong>, indicating Copilot Shopping meets core user needs well.</div>
        </div>
        <div class="takeaway-card">
          <div class="takeaway-num">2</div>
          <div class="takeaway-text"><strong>{html.escape(strongest[0])} leads</strong> at {strongest[1].get('score_100', 0)}/100, driven by high {html.escape(sd_top1['name'])} ({sd_top1['score_100']}) and {html.escape(sd_top2['name'])} ({sd_top2['score_100']}) scores.</div>
        </div>
        <div class="takeaway-card">
          <div class="takeaway-num">3</div>
          <div class="takeaway-text"><strong>{html.escape(weakest[0])} lags</strong> at {weakest[1].get('score_100', 0)}/100 &mdash; the primary area for improvement, especially {html.escape(bot3[-1]['name'])} ({bot3[-1]['score_100']}).</div>
        </div>
        <div class="takeaway-card">
          <div class="takeaway-num">4</div>
          <div class="takeaway-text">Top metrics: <strong>{html.escape(top3[0]['name'])}</strong> ({top3[0]['score_100']}), <strong>{html.escape(top3[1]['name'])}</strong> ({top3[1]['score_100']}), <strong>{html.escape(top3[2]['name'] if len(top3) > 2 else '—')}</strong> ({top3[2]['score_100'] if len(top3) > 2 else '—'}).</div>
        </div>'''

    # Insufficient sample footnotes (n < 30)
    _insufficient_stages = {stage for stage in STAGE_ORDER if stage_n.get(stage, 0) < 30}
    post_footnote = ''
    for stage in STAGE_ORDER:
        sn = stage_n.get(stage, 0)
        if 0 < sn < 30:
            post_footnote += f'<p class="table-footnote">* {html.escape(stage)} has only {sn} respondent(s) (n &lt; 30). Scores are directional only.</p>'

    # Pre-compute sat_dist JSON to avoid f-string brace parsing issues
    sat_dist_json = json.dumps({str(k): v for k, v in sat_dist.items()})

    # ── Build Trends Section ──────────────────────────────────────────
    trends_html = ''
    if all_waves and len(all_waves) >= 2:
        trends_html = _build_trends_section(all_waves, wave_label)
    elif all_waves and len(all_waves) == 1:
        trends_html = '''
<hr class="chapter-divider">
<section id="trends">
  <div class="container">
    <div class="fade-in">
      <p class="section-label">Historical</p>
      <h2 class="section-title">Trends</h2>
      <p class="section-desc">Wave-over-wave trends will appear here once a second wave is collected. This is the baseline measurement.</p>
    </div>
  </div>
</section>'''

    # Build Contacts & Related Docs section
    contributors_raw = scores.get('contributors', '')
    related_docs_raw = scores.get('related_docs', '')

    # Contributors: always include Jian Yang, append extras if provided
    contributor_list = 'Jian Yang'
    if contributors_raw and contributors_raw.strip():
        contributor_list += ', ' + html.escape(contributors_raw.strip())

    # Related documents: parse lines, format as links or text
    doc_lines = [line.strip() for line in related_docs_raw.split('\n') if line.strip()] if related_docs_raw else []
    if doc_lines:
        docs_html = ''
        for line in doc_lines:
            if '|' in line:
                parts = line.split('|', 1)
                title = html.escape(parts[0].strip())
                url = parts[1].strip()
                docs_html += f'<a href="{url}" class="resource-link" target="_blank">{title}</a>\n'
            else:
                docs_html += f'<span class="resource-link">{html.escape(line)}</span>\n'
    else:
        docs_html = '<p style="color:var(--text-muted);font-size:0.85rem">No documents added for this wave.</p>'

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Copilot Shopping — User Metrics Scorecard</title>
<style>
:root {{
  --bg: #FEF9ED;
  --bg-card: #EFE2D1;
  --bg-card-alt: #F5EBDB;
  --text: #3B230E;
  --text-muted: #7A6A56;
  --accent: #2E4D4D;
  --accent-light: #3D6B6B;
  --accent-lighter: rgba(46,77,77,0.12);
  --green: #3A7D44;
  --amber: #C07D10;
  --red: #B84233;
  --domain-quality: #2E4D4D;
  --domain-trust: #5B7E5B;
  --domain-privacy: #C07D10;
  --bar-track: #E8DBC8;
  --border: #D4C4AE;
  --hero-bg: #3B230E;
  --hero-text: #FEF9ED;
  --shadow: 0 2px 12px rgba(59,35,14,0.08);
  --shadow-hover: 0 4px 20px rgba(59,35,14,0.14);
  --radius: 12px;
  --transition: 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}}

* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html {{ scroll-behavior: smooth; }}

body {{
  font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}}

.scroll-progress {{
  position: fixed; top: 0; left: 0; height: 3px; z-index: 1001;
  background: linear-gradient(90deg, var(--accent), var(--green));
  width: 0%; transition: width 0.1s linear;
}}

.sticky-nav {{
  position: fixed; top: 0; left: 0; right: 0; z-index: 1000;
  background: rgba(59,35,14,0.95); backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(254,249,237,0.1);
  transform: translateY(-100%); transition: transform 0.3s ease;
}}
.sticky-nav.visible {{ transform: translateY(0); }}
.sticky-nav-inner {{
  max-width: 1080px; margin: 0 auto; padding: 0 2rem;
  display: flex; align-items: center; height: 48px; gap: 0.25rem;
  overflow-x: auto;
}}
.sticky-nav a {{
  color: rgba(254,249,237,0.6); text-decoration: none;
  font-size: 0.78rem; font-weight: 500; padding: 0.35rem 0.7rem;
  border-radius: 6px; transition: all 0.2s; white-space: nowrap;
  letter-spacing: 0.02em;
}}
.sticky-nav a.active {{ color: #FEF9ED; background: rgba(254,249,237,0.12); }}
.sticky-nav a:hover {{ color: #FEF9ED; }}

.hero {{
  background: var(--hero-bg); color: var(--hero-text);
  padding: 5rem 2rem 4rem; text-align: center; position: relative;
  overflow: hidden;
}}
.hero::before {{
  content: ''; position: absolute; top: -50%; left: -50%;
  width: 200%; height: 200%;
  background: radial-gradient(ellipse at 30% 50%, rgba(46,77,77,0.15) 0%, transparent 60%),
              radial-gradient(ellipse at 70% 80%, rgba(192,125,16,0.08) 0%, transparent 50%);
}}
.hero-content {{ position: relative; z-index: 1; max-width: 720px; margin: 0 auto; }}
.hero-label {{
  font-size: 0.75rem; font-weight: 600; letter-spacing: 0.15em;
  text-transform: uppercase; color: rgba(254,249,237,0.5);
  margin-bottom: 1rem;
}}
.hero h1 {{
  font-family: Georgia, 'Times New Roman', serif;
  font-size: clamp(2rem, 5vw, 3.2rem); font-weight: 400;
  line-height: 1.2; margin-bottom: 1rem;
}}
.hero-sub {{
  font-size: 1rem; color: rgba(254,249,237,0.65);
  max-width: 500px; margin: 0 auto 2rem;
}}
.hero-score {{
  display: inline-flex; align-items: baseline; gap: 0.3rem;
  background: rgba(254,249,237,0.08); border: 1px solid rgba(254,249,237,0.12);
  border-radius: 16px; padding: 1.2rem 2.5rem;
}}
.hero-score-num {{
  font-family: Georgia, serif; font-size: 3.5rem; font-weight: 400;
  line-height: 1;
}}
.hero-score-label {{
  font-size: 0.85rem; color: rgba(254,249,237,0.5);
}}

.container {{ max-width: 820px; margin: 0 auto; padding: 0 2rem; }}
.container-wide {{ max-width: 1080px; margin: 0 auto; padding: 0 2rem; }}
section {{ padding: 4rem 0; }}

.chapter-divider {{
  height: 3px; border: none; margin: 0;
  background: linear-gradient(90deg, var(--accent) 0%, var(--bg-card) 100%);
}}

.section-label {{
  font-size: 0.7rem; font-weight: 600; letter-spacing: 0.15em;
  text-transform: uppercase; color: var(--text-muted); margin-bottom: 0.5rem;
}}
.section-title {{
  font-family: Georgia, serif; font-size: clamp(1.6rem, 3vw, 2.2rem);
  font-weight: 400; line-height: 1.25; margin-bottom: 0.75rem;
}}
.section-desc {{
  color: var(--text-muted); font-size: 0.95rem; max-width: 600px;
  margin-bottom: 2.5rem; line-height: 1.7;
}}

.kpi-hierarchy {{ margin-bottom: 2rem; }}
.kpi-overall {{ display: flex; justify-content: center; margin-bottom: 0.75rem; }}
.kpi-overall .stat-card {{ max-width: 340px; width: 100%; }}
.kpi-connector {{ display: flex; justify-content: center; margin-bottom: 0.75rem; position: relative; height: 32px; }}
.kpi-connector svg {{ display: block; }}
.kpi-domains {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; }}

.stat-row {{
  display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem; margin-bottom: 2rem;
}}
.stat-card {{
  background: var(--bg-card); border-radius: var(--radius);
  padding: 1.5rem; text-align: center; box-shadow: var(--shadow);
  transition: transform var(--transition), box-shadow var(--transition);
}}
.stat-card:hover {{ transform: translateY(-2px); box-shadow: var(--shadow-hover); }}
.stat-card-label {{
  font-size: 0.72rem; font-weight: 600; letter-spacing: 0.1em;
  text-transform: uppercase; color: var(--text-muted); margin-bottom: 0.5rem;
}}
.stat-card-number {{
  font-family: Georgia, serif; font-size: 2.4rem; font-weight: 400;
  color: var(--text); line-height: 1;
}}
.stat-card-sub {{ font-size: 0.8rem; color: var(--text-muted); margin-top: 0.3rem; }}
.stat-card.accent {{ background: var(--accent); color: var(--hero-text); }}
.stat-card.accent .stat-card-label {{ color: rgba(254,249,237,0.5); }}
.stat-card.accent .stat-card-number {{ color: var(--hero-text); }}
.stat-card.accent .stat-card-sub {{ color: rgba(254,249,237,0.6); }}

.bar-section {{ margin-bottom: 1.5rem; }}
.bar-section-title {{
  font-size: 0.72rem; font-weight: 600; letter-spacing: 0.12em;
  text-transform: uppercase; color: var(--text-muted);
  margin-bottom: 0.75rem; padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--border);
}}
.bar-row {{
  display: grid; grid-template-columns: 180px 1fr 55px 20px;
  align-items: center; gap: 1rem; padding: 0.55rem 0;
  cursor: pointer; border-radius: 6px; transition: background 0.2s, box-shadow 0.2s;
  padding-left: 0.5rem; padding-right: 0.5rem;
  position: relative; overflow: visible;
}}
.bar-row:hover {{ background: var(--accent-lighter); box-shadow: inset 0 0 0 1px var(--border); }}
.bar-row.expanded {{ background: var(--accent-lighter); }}
.bar-label {{ font-size: 0.88rem; font-weight: 500; white-space: nowrap; text-overflow: ellipsis; display: flex; align-items: center; gap: 0.3rem; position: relative; overflow: visible; }}
.metric-q-tip {{
  display: inline-flex; cursor: help;
  font-size: 0.78rem; color: var(--text-muted);
  flex-shrink: 0; margin-left: 2px;
  transition: color 0.2s;
}}
.metric-q-tip:hover {{ color: var(--accent); }}
.sat-q-tip {{
  display: inline-flex; align-items: center; justify-content: center;
  width: 14px; height: 14px; border-radius: 50%;
  border: 1.5px solid currentColor; font-size: 0.6rem;
  font-weight: 700; font-style: normal; font-family: 'Segoe UI', system-ui, sans-serif;
  line-height: 1; vertical-align: middle; text-transform: lowercase;
}}
#metricTooltip {{
  position: fixed; z-index: 9999; pointer-events: none;
  max-width: 300px; padding: 0.75rem 1rem;
  background: var(--hero-bg); color: var(--hero-text); border-radius: 8px;
  font-size: 0.82rem; line-height: 1.55; font-weight: 400;
  font-style: italic; box-shadow: 0 6px 24px rgba(0,0,0,0.35);
  opacity: 0; transition: opacity 0.15s;
  font-family: 'Segoe UI', system-ui, sans-serif;
}}
.bar-chevron {{ font-size: 0.7rem; color: var(--text-muted); transition: transform 0.3s ease; display: flex; align-items: center; justify-content: center; }}
.bar-row.expanded .bar-chevron {{ transform: rotate(90deg); color: var(--accent); }}
.bar-track {{ height: 28px; background: var(--bar-track); border-radius: 6px; overflow: hidden; position: relative; }}
.bar-fill {{ height: 100%; border-radius: 6px; width: 0%; transition: width 1.2s cubic-bezier(0.25, 0.46, 0.45, 0.94); position: relative; }}
.bar-fill.quality {{ background: var(--domain-quality); }}
.bar-fill.trust {{ background: var(--domain-trust); }}
.bar-fill.privacy {{ background: var(--domain-privacy); }}
.bar-value {{ font-size: 0.88rem; font-weight: 600; text-align: right; font-variant-numeric: tabular-nums; }}

.bar-drawer {{ max-height: 0; overflow: hidden; transition: max-height 0.5s ease; margin-left: 0.5rem; margin-right: 0.5rem; }}
.bar-drawer.open {{ max-height: 2000px; }}
.bar-drawer-inner {{
  padding: 0.75rem 0 0.75rem 0;
  display: flex; gap: 1.5rem; align-items: flex-end;
  height: 80px;
  margin-left: 180px; margin-right: 75px;
  padding-left: 1rem;
}}
.dist-bar-wrap {{ display: flex; flex-direction: column; align-items: center; justify-content: flex-end; height: 100%; }}
.dist-count {{ font-size: 0.78rem; color: var(--text-muted); font-weight: 500; font-variant-numeric: tabular-nums; margin-bottom: 0.2rem; }}
.dist-bar {{ width: 36px; border-radius: 4px 4px 0 0; background: var(--accent); opacity: 0.55; min-height: 3px; }}
.dist-label {{ font-size: 0.72rem; color: var(--accent); margin-top: 0.25rem; font-weight: 600; font-variant-numeric: tabular-nums; }}

.drawer-quotes {{ margin: 0.5rem 0 0.25rem; padding: 0.75rem 1rem; background: var(--bg-card-alt); border-radius: 8px; border-left: 3px solid var(--accent); }}
.drawer-quotes-title {{ font-size: 0.68rem; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; color: var(--text-muted); margin-bottom: 0.5rem; }}
.drawer-quote-item {{ font-size: 0.82rem; font-style: italic; color: var(--text); line-height: 1.55; padding: 0.35rem 0; border-bottom: 1px solid var(--border); }}
.drawer-quote-item:last-child {{ border-bottom: none; }}

/* Qualitative themes in drawer */
.drawer-themes {{ margin: 0.5rem 0 0.25rem; padding: 0.75rem 1rem; background: var(--bg-card-alt); border-radius: 8px; border-left: 3px solid var(--amber); }}
.drawer-themes-title {{ font-size: 0.68rem; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; color: var(--text-muted); margin-bottom: 0.6rem; }}
.theme-item {{ margin-bottom: 0.6rem; padding-bottom: 0.5rem; border-bottom: 1px solid var(--border); }}
.theme-item:last-child {{ border-bottom: none; margin-bottom: 0; padding-bottom: 0; }}
.theme-label-row {{ display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem; }}
.theme-dot {{ width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }}
.theme-name {{ font-weight: 600; font-size: 0.85rem; color: var(--text); }}
.theme-pct {{ font-weight: 700; font-size: 0.78rem; color: var(--accent); margin-left: auto; }}
.theme-count {{ font-size: 0.72rem; color: var(--text-muted); }}
.theme-quote {{ font-size: 0.8rem; color: var(--text-muted); font-style: italic; padding: 0.2rem 0 0.15rem 1.2rem; line-height: 1.5; border-left: 2px solid var(--border); margin-top: 0.15rem; }}

.heatmap-wrap {{ overflow-x: auto; margin-top: 1.5rem; }}
.heatmap-table {{ width: 100%; border-collapse: separate; border-spacing: 3px; font-size: 0.82rem; table-layout: fixed; }}
.heatmap-table th {{ padding: 0.6rem 0.75rem; text-align: center; font-weight: 600; font-size: 0.7rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--text-muted); background: transparent; width: 17.5%; }}
.heatmap-table th:first-child {{ text-align: left; width: 30%; }}
.heatmap-table td {{ padding: 0.55rem 0.75rem; text-align: center; border-radius: 6px; font-weight: 500; font-variant-numeric: tabular-nums; transition: transform 0.2s; }}
.heatmap-table td:first-child {{ text-align: left; font-weight: 500; background: transparent !important; color: var(--text); }}
.heatmap-table td:hover {{ transform: scale(1.05); }}
.heatmap-table tr {{ transition: opacity 0.2s; }}
.heatmap-grey {{ background: rgba(122,106,86,0.08) !important; color: var(--text-muted) !important; font-weight: 400 !important; }}
.heatmap-table th.grey-header {{ color: #A89A88; }}

.quotes-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1rem; margin-top: 1.5rem; }}
.quote-card {{ background: var(--bg-card); border-radius: var(--radius); padding: 1.5rem; box-shadow: var(--shadow); border-left: 3px solid var(--accent); transition: transform var(--transition), box-shadow var(--transition); }}
.quote-card:hover {{ transform: translateY(-2px); box-shadow: var(--shadow-hover); }}
.quote-card.negative {{ border-left-color: var(--red); }}
.quote-card.privacy {{ border-left-color: var(--amber); }}
.quote-text {{ font-size: 0.92rem; line-height: 1.7; font-style: italic; color: var(--text); }}
.quote-tag {{ display: inline-block; font-size: 0.65rem; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; padding: 0.2rem 0.5rem; border-radius: 4px; margin-top: 0.75rem; }}
.quote-tag.pos {{ background: rgba(58,125,68,0.12); color: var(--green); }}
.quote-tag.neg {{ background: rgba(184,66,51,0.12); color: var(--red); }}
.quote-tag.priv {{ background: rgba(192,125,16,0.12); color: var(--amber); }}

.sat-cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 1rem; margin-top: 1.5rem; }}
.sat-card {{ background: var(--bg-card); border-radius: var(--radius); padding: 1.25rem 1rem; text-align: center; box-shadow: var(--shadow); }}
.sat-card.grey {{ opacity: 0.55; }}
.sat-card-stage {{ font-size: 0.72rem; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; color: var(--text-muted); margin-bottom: 0.4rem; display: flex; align-items: center; justify-content: center; gap: 0.3rem; flex-wrap: nowrap; white-space: nowrap; }}
.sat-card-score {{ font-family: Georgia, serif; font-size: 2rem; font-weight: 400; color: var(--text); }}
.sat-card-n {{ font-size: 0.75rem; color: var(--text-muted); margin-top: 0.2rem; }}

.takeaway-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem; margin-top: 1.5rem; }}
.takeaway-card {{ background: var(--bg-card); border-radius: var(--radius); padding: 1.25rem; box-shadow: var(--shadow); }}
.takeaway-num {{ font-family: Georgia, serif; font-size: 1.5rem; font-weight: 400; color: var(--accent); margin-bottom: 0.3rem; }}
.takeaway-text {{ font-size: 0.88rem; line-height: 1.6; }}

.legend {{ display: flex; gap: 1.2rem; flex-wrap: wrap; margin-bottom: 1.5rem; }}
.legend-chip {{ display: flex; align-items: center; gap: 0.4rem; font-size: 0.75rem; color: var(--text-muted); }}
.legend-dot {{ width: 10px; height: 10px; border-radius: 3px; }}

.table-footnote {{ font-size: 0.75rem; color: var(--text-muted); margin-top: 0.75rem; font-style: italic; }}

/* Info tooltip (weighting rationale) */
.info-tooltip {{
  position: relative; display: inline-flex; cursor: help;
  align-items: center; justify-content: center;
  width: 16px; height: 16px; border-radius: 50%;
  border: 1.5px solid var(--text-muted); color: var(--text-muted);
  font-size: 0.6rem; font-weight: 700; font-style: normal;
  font-family: 'Segoe UI', system-ui, sans-serif;
  line-height: 1; vertical-align: middle; margin-left: 0.3rem;
  text-transform: lowercase;
}}
.info-tooltip-text {{
  display: none; position: absolute; bottom: calc(100% + 10px); left: 50%;
  transform: translateX(-50%); width: 340px; padding: 1rem 1.2rem;
  background: var(--hero-bg); color: var(--hero-text); border-radius: 10px;
  font-size: 0.82rem; line-height: 1.6; z-index: 10; font-weight: 400;
  box-shadow: 0 6px 24px rgba(0,0,0,0.25);
  text-transform: none;
}}
.info-tooltip-text::after {{
  content: ''; position: absolute; top: 100%; left: 50%;
  transform: translateX(-50%); border: 7px solid transparent;
  border-top-color: var(--hero-bg);
}}
.info-tooltip:hover .info-tooltip-text,
.info-tooltip:focus .info-tooltip-text {{ display: block; }}

.fade-in {{ opacity: 0; transform: translateY(24px); transition: opacity 0.7s ease, transform 0.7s ease; }}
.fade-in.visible {{ opacity: 1; transform: translateY(0); }}

.contacts-section {{ background: var(--bg-card); border-radius: var(--radius); padding: 2rem; box-shadow: var(--shadow); margin-top: 2rem; }}
.contacts-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; }}
.contacts-col h4 {{ font-size: 0.72rem; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; color: var(--text-muted); margin-bottom: 0.75rem; }}
.contacts-col p, .contacts-col a {{ font-size: 0.88rem; line-height: 1.8; }}
.contacts-col a {{ color: var(--accent); text-decoration: none; border-bottom: 1px solid var(--accent-lighter); transition: border-color 0.2s; }}
.contacts-col a:hover {{ border-color: var(--accent); }}
.resource-link {{ display: block; padding: 0.4rem 0; }}

.footer {{ text-align: center; padding: 3rem 2rem; font-size: 0.78rem; color: var(--text-muted); border-top: 1px solid var(--border); }}

/* ── Trends Section ── */
.trend-chart-wrap {{
  background: var(--bg-card); border-radius: var(--radius); padding: 2rem;
  box-shadow: var(--shadow); margin-bottom: 1.5rem;
}}
.trend-chart-wrap h3 {{
  font-size: 0.72rem; font-weight: 600; letter-spacing: 0.12em;
  text-transform: uppercase; color: var(--text-muted); margin-bottom: 1.2rem;
}}
.trend-plotly {{ width: 100%; }}

.delta-table {{ width: 100%; border-collapse: separate; border-spacing: 0 2px; font-size: 0.85rem; }}
.delta-table th {{
  padding: 0.6rem 0.75rem; text-align: left; font-size: 0.7rem;
  letter-spacing: 0.08em; text-transform: uppercase; color: var(--text-muted);
  border-bottom: 2px solid var(--border);
}}
.delta-table td {{ padding: 0.55rem 0.75rem; }}
.delta-table tr:nth-child(even) td {{ background: rgba(239,226,209,0.3); border-radius: 6px; }}
.delta-up {{ color: var(--green); font-weight: 600; }}
.delta-down {{ color: var(--red); font-weight: 600; }}
.delta-flat {{ color: var(--text-muted); }}

@media (max-width: 768px) {{
  .bar-row {{ grid-template-columns: 120px 1fr 45px 18px; gap: 0.5rem; }}
  .bar-drawer-inner {{ margin-left: 120px; margin-right: 63px; gap: 1rem; }}
  .hero {{ padding: 3rem 1.5rem 2.5rem; }}
  .kpi-domains {{ grid-template-columns: 1fr; }}
  .heatmap-table {{ font-size: 0.75rem; }}
}}
@media (max-width: 480px) {{
  .bar-row {{ grid-template-columns: 100px 1fr 40px 16px; font-size: 0.82rem; }}
  .bar-drawer-inner {{ margin-left: 100px; margin-right: 56px; gap: 0.75rem; }}
}}
</style>
</head>
<body>

<div class="scroll-progress" id="scrollProgress"></div>

<nav class="sticky-nav" id="stickyNav">
  <div class="sticky-nav-inner">
    <a href="#hero">Overview</a>
    <a href="#kpi">KPIs</a>
    <a href="#trends">Trends</a>
    <a href="#metrics">Metrics</a>
    <a href="#stages">Journey Stages</a>
    <a href="#satisfaction">Satisfaction</a>
    <a href="#voices">User Voices</a>
    <a href="#contacts">Contacts</a>
  </div>
</nav>

<section class="hero" id="hero">
  <div class="hero-content">
    <div class="hero-label">Copilot Shopping &middot; {html.escape(wave_label)}</div>
    <h1>User Metrics Scorecard</h1>
    <p class="hero-sub">{n_metrics} metrics across 3 domains, measured from {n} completed survey responses. {html.escape(wave_date)}.</p>
    <div class="hero-score">
      <span class="hero-score-num">{overall}</span>
      <span class="hero-score-label">/100 Overall</span>
    </div>
  </div>
</section>

<hr class="chapter-divider">

<section id="kpi">
  <div class="container">
    <div class="fade-in">
      <p class="section-label">At a Glance</p>
      <h2 class="section-title">Domain Scores</h2>
      <p class="section-desc">Weighted composite of {n_metrics} retained metrics across three experience domains (Quality: 40%, Trust &amp; Confidence: 40%, Privacy &amp; Security: 20%). <span class="info-tooltip" tabindex="0" role="button" aria-label="Weighting rationale">i<span class="info-tooltip-text">Privacy &amp; Security is weighted lower because it functions as a foundational hygiene factor rather than a primary experience driver. It overlaps with trust and is less tied to task-level experience quality.</span></span></p>
    </div>
    <div class="kpi-hierarchy fade-in">
      <div class="kpi-overall">
        <div class="stat-card accent">
          <div class="stat-card-label">Overall Score</div>
          <div class="stat-card-number">{overall}</div>
          <div class="stat-card-sub">out of 100 &middot; weighted (40/40/20)</div>
        </div>
      </div>
      <div class="kpi-connector">
        <svg width="100%" height="32" viewBox="0 0 700 32" preserveAspectRatio="xMidYMid meet" style="max-width:700px">
          <line x1="350" y1="0" x2="117" y2="32" stroke="#D4C4AE" stroke-width="1.5"/>
          <line x1="350" y1="0" x2="350" y2="32" stroke="#D4C4AE" stroke-width="1.5"/>
          <line x1="350" y1="0" x2="583" y2="32" stroke="#D4C4AE" stroke-width="1.5"/>
        </svg>
      </div>
      <div class="kpi-domains">
        {domain_cards}
      </div>
    </div>
    <div class="fade-in">
      <div class="takeaway-grid">
        {takeaway_cards}
      </div>
    </div>
  </div>
</section>

{trends_html}

<hr class="chapter-divider">

<section id="metrics">
  <div class="container">
    <div class="fade-in">
      <p class="section-label">Deep Dive</p>
      <h2 class="section-title">All {n_metrics} Metrics</h2>
      <p class="section-desc">Scored on a 0&ndash;100 scale. <span style="display:inline-block;background:var(--accent);color:var(--hero-text);font-size:0.72rem;font-weight:600;padding:0.2rem 0.7rem;border-radius:12px;letter-spacing:0.04em;vertical-align:middle;margin-left:0.25rem;cursor:default">&#9654; Click any bar to expand details{"  &amp; qualitative themes" if has_themes else ""}</span></p>
    </div>
    <div class="legend fade-in">
      <div class="legend-chip"><div class="legend-dot" style="background:var(--domain-quality)"></div>Quality</div>
      <div class="legend-chip"><div class="legend-dot" style="background:var(--domain-trust)"></div>Trust &amp; Confidence</div>
      <div class="legend-chip"><div class="legend-dot" style="background:var(--domain-privacy)"></div>Privacy &amp; Security</div>
    </div>
    <div id="barChart" class="fade-in"></div>
  </div>
</section>

<hr class="chapter-divider">

<section id="stages">
  <div class="container-wide">
    <div class="fade-in">
      <p class="section-label">Segmentation</p>
      <h2 class="section-title">Scores by Journey Stage</h2>
      <p class="section-desc">How metrics vary across the four shopping journey stages.</p>
    </div>
    <div class="heatmap-wrap fade-in">
      <div class="legend" style="margin-bottom:1rem">
        <div class="legend-chip"><div class="legend-dot" style="background:rgba(58,125,68,0.18);border:1px solid #2D6B35"></div><span style="color:#2D6B35;font-weight:600">85+</span>&nbsp;Strong</div>
        <div class="legend-chip"><div class="legend-dot" style="background:rgba(192,125,16,0.15);border:1px solid #9A6508"></div><span style="color:#9A6508;font-weight:600">70&ndash;84</span>&nbsp;Moderate</div>
        <div class="legend-chip"><div class="legend-dot" style="background:rgba(184,66,51,0.15);border:1px solid #A03328"></div><span style="color:#A03328;font-weight:600">&lt;70</span>&nbsp;Needs Improvement</div>
        <div class="legend-chip"><div class="legend-dot" style="background:#B0B0B0;border:1px solid #999"></div>Insufficient data</div>
      </div>
      <table class="heatmap-table" id="heatmapTable">
        <thead>
          <tr>
            <th>Metric</th>
            {heatmap_headers}
          </tr>
        </thead>
        <tbody id="heatmapBody"></tbody>
      </table>
      {post_footnote}
    </div>
  </div>
</section>

<hr class="chapter-divider">

<section id="satisfaction">
  <div class="container">
    <div class="fade-in">
      <p class="section-label">Contextual KPI</p>
      <h2 class="section-title">Overall Satisfaction</h2>
      <p class="section-desc">Satisfaction is tracked as a contextual indicator alongside the composite score, not included in the overall metric.</p>
    </div>
    <div class="stat-row fade-in">
      <div class="stat-card accent">
        <div class="stat-card-label">Satisfaction Score <span class="metric-q-tip sat-q-tip" style="color:rgba(254,249,237,0.6)" data-question="Thinking about your interaction with Copilot during the shopping activity, how satisfied were you with your overall experience using Copilot for shopping?">i</span></div>
        <div class="stat-card-number">{sat_score}</div>
        <div class="stat-card-sub">mean {sat_mean} &middot; N = {sat_n}</div>
      </div>
    </div>
    <div class="sat-cards fade-in">
      {sat_stage_cards}
    </div>
    <div class="fade-in" style="margin-top:2.5rem">
      <h3 style="font-family:Georgia,serif;font-size:1.1rem;margin-bottom:1rem">Satisfaction Distribution</h3>
      <div id="satDistribution" style="display:flex;gap:1.5rem;align-items:flex-end;height:140px;max-width:500px;"></div>
    </div>
  </div>
</section>

<hr class="chapter-divider">

<section id="voices">
  <div class="container">
    <div class="fade-in">
      <p class="section-label">Qualitative Insights</p>
      <h2 class="section-title">In Their Own Words</h2>
      <p class="section-desc">Representative quotes from the satisfaction follow-up: &ldquo;Please explain why you gave Copilot that satisfaction rating for this shopping activity.&rdquo;</p>
    </div>
    <div class="fade-in">
      <h3 style="font-family:Georgia,serif;font-size:1.1rem;margin-bottom:1rem;color:var(--green)">Positive Experiences</h3>
      <div class="quotes-grid" id="quotesPos"></div>
    </div>
    <div class="fade-in" style="margin-top:2.5rem">
      <h3 style="font-family:Georgia,serif;font-size:1.1rem;margin-bottom:1rem;color:var(--red)">Pain Points</h3>
      <div class="quotes-grid" id="quotesNeg"></div>
    </div>
  </div>
</section>

<hr class="chapter-divider">

<section id="contacts">
  <div class="container">
    <div class="fade-in">
      <p class="section-label">Team &amp; Resources</p>
      <h2 class="section-title">Contacts &amp; Related Docs</h2>
    </div>
    <div class="contacts-section fade-in">
      <div class="contacts-grid">
        <div class="contacts-col">
          <h4>Contacts</h4>
          <p><strong>UXR:</strong> Prisca Obierefu<br>
          <a href="mailto:pobierefu@microsoft.com">pobierefu@microsoft.com</a></p>
          <p style="margin-top:0.5rem"><strong>Contributors:</strong> {contributor_list}</p>
        </div>
        <div class="contacts-col">
          <h4>Related Documents</h4>
          {docs_html}
        </div>
      </div>
    </div>
  </div>
</section>

<footer class="footer">
  Copilot Shopping User Metrics Scorecard &middot; {html.escape(wave_label)} &middot; {html.escape(wave_date)} &middot; N = {n}
</footer>

<script>
const DATA = {json.dumps(js_data, default=str)};

function domainClass(d) {{
  if (d === 'Quality') return 'quality';
  if (d === 'Trust & Confidence') return 'trust';
  return 'privacy';
}}

function scoreColor(score) {{
  if (score >= 85) return 'rgba(58,125,68,0.18)';
  if (score >= 70) return 'rgba(192,125,16,0.15)';
  return 'rgba(184,66,51,0.15)';
}}
function scoreTextColor(score) {{
  if (score >= 85) return '#2D6B35';
  if (score >= 70) return '#9A6508';
  return '#A03328';
}}

function buildBarChart() {{
  const container = document.getElementById('barChart');
  const domainOrder = ['Quality', 'Trust & Confidence', 'Privacy & Security'];
  const grouped = {{}};
  domainOrder.forEach(d => {{ grouped[d] = []; }});
  DATA.metrics.forEach(m => {{ grouped[m.domain].push(m); }});

  domainOrder.forEach(domain => {{
    const secDiv = document.createElement('div');
    secDiv.className = 'bar-section';
    const title = document.createElement('div');
    title.className = 'bar-section-title';
    title.textContent = domain;
    secDiv.appendChild(title);
    container.appendChild(secDiv);

    grouped[domain].forEach(m => {{
      const row = document.createElement('div');
      row.className = 'bar-row';
      const surveyQ = DATA.surveyQuestions[m.name] || '';
      const qTip = surveyQ ? `<span class="metric-q-tip" data-question="${{surveyQ}}">&#9432;</span>` : '';
      row.innerHTML = `
        <div class="bar-label">${{m.name}}${{qTip}}</div>
        <div class="bar-track">
          <div class="bar-fill ${{domainClass(m.domain)}}" data-width="${{m.score}}"></div>
        </div>
        <div class="bar-value">${{m.score}}</div>
        <div class="bar-chevron">&#9654;</div>
      `;

      const drawer = document.createElement('div');
      drawer.className = 'bar-drawer';
      let drawerContent = '';

      const dist = DATA.distributions[m.name];
      if (dist) {{
        const maxCount = Math.max(...Object.values(dist));
        drawerContent += '<div class="bar-drawer-inner">';
        for (let i = 1; i <= 5; i++) {{
          const count = dist[String(i)] || 0;
          const barH = maxCount > 0 ? Math.max(3, (count / maxCount) * 55) : 3;
          drawerContent += `
            <div class="dist-bar-wrap">
              <div class="dist-count">${{count}}</div>
              <div class="dist-bar" style="height:${{barH}}px;background:var(--domain-${{domainClass(m.domain)}})"></div>
              <div class="dist-label">${{i}}</div>
            </div>
          `;
        }}
        drawerContent += '</div>';
      }}

      // Qualitative themes split by rating (Wave 2)
      const themeData = DATA.qualitativeThemes[m.name];
      if (themeData) {{
        const domColor = m.domain === 'Quality' ? 'var(--domain-quality)' :
                         m.domain === 'Trust & Confidence' ? 'var(--domain-trust)' : 'var(--domain-privacy)';

        function renderThemeGroup(group, accentColor, icon) {{
          let h = `<div style="margin-bottom:0.5rem">`;
          h += `<div style="font-size:0.72rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:${{accentColor}};margin-bottom:0.5rem">${{icon}} ${{group.label}} (${{group.count}} responses)</div>`;
          group.themes.forEach(t => {{
            h += '<div class="theme-item">';
            h += `<div class="theme-label-row">`;
            h += `<div class="theme-dot" style="background:${{accentColor}}"></div>`;
            h += `<span class="theme-name">${{t.label}}</span>`;
            h += `<span class="theme-pct">${{t.pct}}%</span>`;
            h += `<span class="theme-count">(${{t.count}})</span>`;
            h += '</div>';
            if (t.quotes) {{
              t.quotes.forEach(q => {{
                h += `<div class="theme-quote">\\u201C${{q}}\\u201D</div>`;
              }});
            }}
            h += '</div>';
          }});
          h += '</div>';
          return h;
        }}

        drawerContent += '<div class="drawer-themes">';
        drawerContent += '<div class="drawer-themes-title">Why participants gave this rating</div>';
        if (themeData.high) {{
          drawerContent += renderThemeGroup(themeData.high, 'var(--green)', '&#9650;');
        }}
        if (themeData.low) {{
          drawerContent += renderThemeGroup(themeData.low, 'var(--red)', '&#9660;');
        }}
        drawerContent += '</div>';
      }}

      drawer.innerHTML = drawerContent;

      row.addEventListener('click', (e) => {{
        if (e.target.closest('.metric-q-tip')) return;
        const isOpen = drawer.classList.contains('open');
        document.querySelectorAll('.bar-drawer.open').forEach(d => d.classList.remove('open'));
        document.querySelectorAll('.bar-row.expanded').forEach(r => r.classList.remove('expanded'));
        if (!isOpen) {{
          drawer.classList.add('open');
          row.classList.add('expanded');
        }}
      }});

      secDiv.appendChild(row);
      secDiv.appendChild(drawer);
    }});
  }});
}}

function buildHeatmap() {{
  const tbody = document.getElementById('heatmapBody');
  const stages = ['Inspiration', 'Research', 'Ready to Purchase', 'Post-Purchase'];
  const domainOrder = ['Quality', 'Trust & Confidence', 'Privacy & Security'];
  const grouped = {{}};
  domainOrder.forEach(d => {{ grouped[d] = []; }});
  DATA.metrics.forEach(m => {{ grouped[m.domain].push(m); }});

  domainOrder.forEach(domain => {{
    const headerTr = document.createElement('tr');
    headerTr.innerHTML = `<td colspan="5" style="font-size:0.7rem;font-weight:600;letter-spacing:0.12em;text-transform:uppercase;color:var(--text-muted);padding-top:1.2rem;padding-bottom:0.4rem;border-bottom:1px solid var(--border);background:transparent !important">${{domain}}</td>`;
    tbody.appendChild(headerTr);

    grouped[domain].forEach(m => {{
      const tr = document.createElement('tr');
      let h = `<td>${{m.name}}</td>`;
      stages.forEach(stage => {{
        const val = DATA.stageData[stage]?.[m.name];
        const insufficient = (DATA.stageN[stage] || 0) < 30;
        if (val !== undefined) {{
          if (insufficient) {{ h += `<td class="heatmap-grey">${{val}}</td>`; }}
          else {{ h += `<td style="background:${{scoreColor(val)}};color:${{scoreTextColor(val)}};font-weight:600">${{val}}</td>`; }}
        }} else {{ h += '<td class="heatmap-grey">\u2014</td>'; }}
      }});
      tr.innerHTML = h;
      tbody.appendChild(tr);
    }});
  }});
}}

function buildQuotes(containerId, quotes, tagClass, tagText) {{
  const container = document.getElementById(containerId);
  quotes.forEach(q => {{
    const card = document.createElement('div');
    card.className = `quote-card${{tagClass === 'neg' ? ' negative' : tagClass === 'priv' ? ' privacy' : ''}}`;
    card.innerHTML = `
      <div class="quote-text">\\u201C${{q}}\\u201D</div>
      <span class="quote-tag ${{tagClass}}">${{tagText}}</span>
    `;
    container.appendChild(card);
  }});
}}

function initScrollAnimations() {{
  const observer = new IntersectionObserver((entries) => {{
    entries.forEach(entry => {{
      if (entry.isIntersecting) {{
        entry.target.classList.add('visible');
        entry.target.querySelectorAll('.bar-fill').forEach(bar => {{
          setTimeout(() => {{ bar.style.width = bar.dataset.width + '%'; }}, 100);
        }});
      }}
    }});
  }}, {{ threshold: 0.1, rootMargin: '0px 0px -50px 0px' }});
  document.querySelectorAll('.fade-in').forEach(el => observer.observe(el));
}}

function initStickyNav() {{
  const nav = document.getElementById('stickyNav');
  const hero = document.getElementById('hero');
  const links = nav.querySelectorAll('a');
  const sections = [];
  links.forEach(link => {{
    const id = link.getAttribute('href').substring(1);
    const section = document.getElementById(id);
    if (section) sections.push({{ id, el: section, link }});
  }});
  window.addEventListener('scroll', () => {{
    const scrollY = window.scrollY;
    const heroBottom = hero.offsetTop + hero.offsetHeight;
    nav.classList.toggle('visible', scrollY > heroBottom - 60);
    let current = sections[0]?.id;
    sections.forEach(s => {{ if (scrollY >= s.el.offsetTop - 100) current = s.id; }});
    links.forEach(link => {{ link.classList.toggle('active', link.getAttribute('href') === '#' + current); }});
    const docHeight = document.documentElement.scrollHeight - window.innerHeight;
    const progress = docHeight > 0 ? (scrollY / docHeight) * 100 : 0;
    document.getElementById('scrollProgress').style.width = progress + '%';
  }});
}}

function buildSatDistribution() {{
  const satDist = {sat_dist_json};
  const container = document.getElementById('satDistribution');
  const maxCount = Math.max(...Object.values(satDist));
  const labels = ['Very Dissatisfied','Dissatisfied','Neutral','Satisfied','Very Satisfied'];
  const maxBarH = 90;
  for (let i = 1; i <= 5; i++) {{
    const count = satDist[String(i)] || 0;
    const barH = maxCount > 0 ? Math.max(4, (count / maxCount) * maxBarH) : 4;
    const wrap = document.createElement('div');
    wrap.style.cssText = 'flex:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;height:100%';
    wrap.innerHTML = `
      <div style="font-size:0.85rem;color:var(--text);font-weight:600;margin-bottom:0.25rem;font-variant-numeric:tabular-nums">${{count}}</div>
      <div style="width:48px;border-radius:4px 4px 0 0;background:var(--accent);opacity:0.55;height:${{barH}}px"></div>
      <div style="font-size:0.72rem;color:var(--text-muted);margin-top:0.4rem;text-align:center;line-height:1.25">${{labels[i-1]}}</div>
    `;
    container.appendChild(wrap);
  }}
}}

document.addEventListener('DOMContentLoaded', () => {{
  // Create floating tooltip element
  const tip = document.createElement('div');
  tip.id = 'metricTooltip';
  document.body.appendChild(tip);

  document.addEventListener('mouseover', (e) => {{
    const qTip = e.target.closest('.metric-q-tip');
    if (qTip) {{
      const question = qTip.getAttribute('data-question');
      if (question) {{
        tip.textContent = question;
        const rect = qTip.getBoundingClientRect();
        tip.style.left = Math.max(10, rect.left - 100) + 'px';
        tip.style.top = (rect.top - tip.offsetHeight - 10) + 'px';
        tip.style.opacity = '1';
      }}
    }}
  }});
  document.addEventListener('mouseout', (e) => {{
    if (e.target.closest('.metric-q-tip')) {{
      tip.style.opacity = '0';
    }}
  }});

  buildBarChart();
  // Auto-expand the first metric bar to show that bars are interactive
  const firstRow = document.querySelector('.bar-row');
  const firstDrawer = document.querySelector('.bar-drawer');
  if (firstRow && firstDrawer) {{
    setTimeout(() => {{
      firstRow.classList.add('expanded');
      firstDrawer.classList.add('open');
    }}, 800);
  }}
  buildHeatmap();
  buildQuotes('quotesPos', DATA.quotesPos, 'pos', 'Satisfied');
  buildQuotes('quotesNeg', DATA.quotesNeg, 'neg', 'Dissatisfied');
  buildSatDistribution();
  initScrollAnimations();
  initStickyNav();
}});
</script>
</body>
</html>'''


def _build_trends_section(all_waves, current_wave_label):
    """Build HTML for the wave-over-wave trends section with Plotly.js charts and delta table."""

    domain_colors = {
        'Quality': '#2E4D4D',
        'Trust & Confidence': '#5B7E5B',
        'Privacy & Security': '#C07D10',
    }

    waves = sorted(all_waves, key=lambda w: w.get('wave_date', ''))
    n_waves = len(waves)
    wave_labels = [w.get('wave_label', f'Wave {i+1}') for i, w in enumerate(waves)]

    # ── Plotly data: Overall + Satisfaction ──
    overall_vals = [w.get('overall_score', 0) for w in waves]
    sat_vals = [w.get('sat_score', 0) for w in waves]

    overall_trace = json.dumps({
        'x': wave_labels, 'y': overall_vals,
        'mode': 'lines+markers', 'name': 'Overall',
        'line': {'color': '#3B230E', 'width': 3},
        'marker': {'size': 10, 'color': '#3B230E'},
    })
    sat_trace = json.dumps({
        'x': wave_labels, 'y': sat_vals,
        'mode': 'lines+markers', 'name': 'Satisfaction',
        'line': {'color': '#C07D10', 'width': 2, 'dash': 'dot'},
        'marker': {'size': 8, 'color': '#C07D10'},
    })

    plotly_layout = json.dumps({
        'paper_bgcolor': 'rgba(0,0,0,0)',
        'plot_bgcolor': 'rgba(0,0,0,0)',
        'font': {'family': 'Segoe UI, system-ui, sans-serif', 'color': '#3B230E', 'size': 13},
        'hoverlabel': {'bgcolor': '#EFE2D1', 'font_color': '#3B230E', 'font_size': 12, 'bordercolor': '#D4C4AE'},
        'yaxis': {'range': [0, 100], 'title': 'Score', 'gridcolor': '#E8DBC8', 'zeroline': False},
        'xaxis': {'showgrid': False},
        'legend': {'orientation': 'h', 'y': -0.15},
        'height': 350,
        'margin': {'l': 50, 'r': 20, 't': 20, 'b': 50},
        'showlegend': True,
    })

    # ── Plotly data: Domain Scores ──
    domain_traces = ''
    for domain, color in domain_colors.items():
        vals = []
        for w in waves:
            d = w.get('domains', {}).get(domain, {})
            vals.append(d.get('score_100', 0))
        trace = json.dumps({
            'x': wave_labels, 'y': vals,
            'mode': 'lines+markers', 'name': domain,
            'line': {'color': color, 'width': 2.5},
            'marker': {'size': 8, 'color': color},
        })
        domain_traces += f'{trace},'

    domain_layout = json.dumps({
        'paper_bgcolor': 'rgba(0,0,0,0)',
        'plot_bgcolor': 'rgba(0,0,0,0)',
        'font': {'family': 'Segoe UI, system-ui, sans-serif', 'color': '#3B230E', 'size': 13},
        'hoverlabel': {'bgcolor': '#EFE2D1', 'font_color': '#3B230E', 'font_size': 12, 'bordercolor': '#D4C4AE'},
        'yaxis': {'range': [0, 100], 'title': 'Score', 'gridcolor': '#E8DBC8', 'zeroline': False},
        'xaxis': {'showgrid': False},
        'legend': {'orientation': 'h', 'y': -0.15},
        'height': 350,
        'margin': {'l': 50, 'r': 20, 't': 20, 'b': 50},
        'showlegend': True,
    })

    # ── Delta Table: Current vs Previous ──
    prev_wave = None
    curr_wave = None
    for w in waves:
        if w.get('wave_label') == current_wave_label:
            curr_wave = w
        else:
            prev_wave = w

    if not curr_wave:
        curr_wave = waves[-1]
    if not prev_wave and len(waves) >= 2:
        prev_wave = waves[-2]

    delta_rows = ''
    if prev_wave and curr_wave:
        prev_metrics = {m['name']: m for m in prev_wave.get('metrics', [])}
        curr_metrics = {m['name']: m for m in curr_wave.get('metrics', [])}

        for m_name in [m['name'] for m in curr_wave.get('metrics', [])]:
            curr_m = curr_metrics.get(m_name, {})
            prev_m = prev_metrics.get(m_name, {})
            curr_score = curr_m.get('score_100', 0)
            prev_score = prev_m.get('score_100', 0)

            if prev_score:
                diff = round(curr_score - prev_score, 1)
                if diff > 0:
                    arrow = '&#9650;'
                    css = 'delta-up'
                elif diff < 0:
                    arrow = '&#9660;'
                    css = 'delta-down'
                else:
                    arrow = '&ndash;'
                    css = 'delta-flat'
                delta_rows += f'''
                <tr>
                  <td style="font-weight:500">{html.escape(m_name)}</td>
                  <td style="font-weight:500">{html.escape(curr_m.get('domain', ''))}</td>
                  <td style="text-align:center">{prev_score}</td>
                  <td style="text-align:center;font-weight:600">{curr_score}</td>
                  <td style="text-align:center" class="{css}">{arrow} {abs(diff)}</td>
                </tr>'''
            else:
                delta_rows += f'''
                <tr>
                  <td style="font-weight:500">{html.escape(m_name)}</td>
                  <td style="font-weight:500">{html.escape(curr_m.get('domain', ''))}</td>
                  <td style="text-align:center;color:#A89A88">&ndash;</td>
                  <td style="text-align:center;font-weight:600">{curr_score}</td>
                  <td style="text-align:center;color:#A89A88">New</td>
                </tr>'''

    prev_label = html.escape(prev_wave.get('wave_label', 'Previous')) if prev_wave else 'Previous'
    curr_label_esc = html.escape(current_wave_label)

    delta_table = ''
    if delta_rows:
        delta_table = f'''
    <div class="trend-chart-wrap fade-in">
      <h3>Metric Changes: {prev_label} &rarr; {curr_label_esc}</h3>
      <table class="delta-table">
        <thead>
          <tr>
            <th>Metric</th>
            <th>Domain</th>
            <th style="text-align:center">{prev_label}</th>
            <th style="text-align:center">{curr_label_esc}</th>
            <th style="text-align:center">Change</th>
          </tr>
        </thead>
        <tbody>
          {delta_rows}
        </tbody>
      </table>
    </div>'''

    return f'''
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<hr class="chapter-divider">

<section id="trends">
  <div class="container">
    <div class="fade-in">
      <p class="section-label">Historical</p>
      <h2 class="section-title">Trends</h2>
      <p class="section-desc">How scores have changed across {n_waves} measurement waves.</p>
    </div>

    <div class="trend-chart-wrap fade-in">
      <h3>Overall Score &amp; Satisfaction</h3>
      <p style="font-size:0.82rem;color:var(--text-muted);margin-bottom:1rem;line-height:1.6"><strong>Overall</strong> = weighted composite of 3 domains (Quality: 40%, Trust &amp; Confidence: 40%, Privacy &amp; Security: 20%) on a 0&ndash;100 scale.<br><strong>Satisfaction (CSAT)</strong> = standalone contextual KPI, tracked separately and not included in the Overall score.</p>
      <div id="trendOverallChart" class="trend-plotly"></div>
    </div>

    <div class="trend-chart-wrap fade-in">
      <h3>Domain Scores</h3>
      <div id="trendDomainChart" class="trend-plotly"></div>
    </div>

    {delta_table}
  </div>
</section>

<script>
Plotly.newPlot('trendOverallChart', [{overall_trace}, {sat_trace}], {plotly_layout}, {{responsive: true, displayModeBar: false}});
Plotly.newPlot('trendDomainChart', [{domain_traces.rstrip(',')}], {domain_layout}, {{responsive: true, displayModeBar: false}});
</script>'''

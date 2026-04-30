"""
Copilot Shopping User Metrics Dashboard — Stakeholder View
Read-only dashboard for viewing waves and trends.

Run with:
    streamlit run app_stakeholder.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
from io import BytesIO
import json
import zipfile

from data_processing import (
    process_wave, DOMAIN_ORDER, STAGE_ORDER, RETAINED_METRICS,
    SATISFACTION_LABELS,
)
from storage import (
    init_db, save_wave, get_all_waves, get_wave_scores,
    get_trend_data, delete_wave,
)

# ── Page config ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Copilot Shopping — User Metrics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Theme CSS ───────────────────────────────────────────────────────────────

THEME_CSS = """
<style>
:root {
    --bg: #FEF9ED;
    --bg-card: #EFE2D1;
    --text: #3B230E;
    --text-muted: #7A6A56;
    --accent: #2E4D4D;
    --green: #3A7D44;
    --amber: #C07D10;
    --red: #B84233;
    --border: #D4C4AE;
}

/* Global background */
.stApp, [data-testid="stAppViewContainer"], .main .block-container {
    background-color: #FEF9ED !important;
    color: #3B230E !important;
}
[data-testid="stHeader"] { background-color: #FEF9ED !important; }

/* Hide Material Icons — they render as text in this environment */
.material-symbols-rounded,
.material-symbols-outlined,
.material-icons,
.material-icons-outlined,
[class*="material-symbols"],
[class*="material-icons"],
[data-testid="stIconMaterial"],
[data-testid="stIcon"] {
    display: none !important;
    font-size: 0 !important;
    width: 0 !important;
    height: 0 !important;
    overflow: hidden !important;
}
[data-testid="StyledLinkIconContainer"] { display: none !important; }

/* Hide sidebar collapse/expand toggle across Streamlit versions */
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarNavCollapseButton"],
button[kind="header"],
button[kind="headerNoPadding"] {
    display: none !important;
    visibility: hidden !important;
    width: 0 !important;
    height: 0 !important;
    overflow: hidden !important;
    position: absolute !important;
    pointer-events: none !important;
}

/* Sidebar */
[data-testid="stSidebar"] { background-color: #3B230E !important; }
[data-testid="stSidebar"] * { color: #FEF9ED !important; }
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stRadio label,
[data-testid="stSidebar"] .stFileUploader label {
    color: rgba(254,249,237,0.6) !important;
    font-size: 0.75rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
}
[data-testid="stSidebar"] hr { border-color: rgba(254,249,237,0.12) !important; }

/* Sidebar selectbox — dark background to match sidebar */
[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background-color: rgba(254,249,237,0.08) !important;
    border-color: rgba(254,249,237,0.2) !important;
}

/* Typography */
h1, h2, h3 {
    font-family: Georgia, 'Times New Roman', serif !important;
    color: #3B230E !important;
    font-weight: 400 !important;
}
p, span, div, label {
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif !important;
}

/* Metric cards */
[data-testid="stMetric"] {
    background: #EFE2D1;
    border-radius: 12px;
    padding: 1.25rem;
    box-shadow: 0 2px 12px rgba(59,35,14,0.08);
}
[data-testid="stMetric"] label {
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    color: #7A6A56 !important;
}
[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-family: Georgia, serif !important;
    color: #3B230E !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] { gap: 0.25rem; border-bottom: 2px solid #D4C4AE; }
.stTabs [data-baseweb="tab"] {
    font-size: 0.85rem !important; font-weight: 500 !important;
    color: #7A6A56 !important; border-radius: 8px 8px 0 0;
    padding: 0.6rem 1.2rem !important;
}
.stTabs [aria-selected="true"] {
    color: #2E4D4D !important; border-bottom: 2px solid #2E4D4D !important;
}

/* Buttons */
.stButton > button {
    background: #2E4D4D !important; color: #FEF9ED !important;
    border: none !important; border-radius: 8px !important;
    font-weight: 500 !important; padding: 0.5rem 1.25rem !important;
}
.stButton > button:hover { background: #3D6B6B !important; }

.stDownloadButton > button {
    background: #EFE2D1 !important; color: #3B230E !important;
    border: 1px solid #D4C4AE !important; border-radius: 8px !important;
}

/* Section dividers */
hr {
    border: none !important; height: 2px !important;
    background: linear-gradient(90deg, #2E4D4D, #EFE2D1) !important;
    margin: 2rem 0 !important;
}

/* Plotly chart containers */
[data-testid="stPlotlyChart"] { margin-bottom: 0.5rem; }

/* Takeaway cards — warm theme (not blue st.info) */
.takeaway-card {
    background: #EFE2D1;
    border-radius: 12px;
    padding: 1.25rem;
    box-shadow: 0 2px 12px rgba(59,35,14,0.08);
}
.takeaway-num {
    font-family: Georgia, serif;
    font-size: 1.5rem;
    font-weight: 400;
    color: #2E4D4D;
    margin-bottom: 0.3rem;
}
.takeaway-text {
    font-size: 0.88rem;
    line-height: 1.6;
    color: #3B230E;
}
</style>
"""

st.markdown(THEME_CSS, unsafe_allow_html=True)

# ── Plotly shared config ────────────────────────────────────────────────────

PLOTLY_LAYOUT = dict(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    font=dict(family="Segoe UI, system-ui, sans-serif", color="#3B230E", size=13),
    hoverlabel=dict(bgcolor="#EFE2D1", font_color="#3B230E", font_size=12, bordercolor="#D4C4AE"),
)
DOMAIN_COLORS = {
    'Quality': '#2E4D4D',
    'Trust & Confidence': '#5B7E5B',
    'Privacy & Security': '#C07D10',
}
STAGE_COLORS = {
    'Inspiration': '#2E4D4D',
    'Research': '#5B7E5B',
    'Ready to Purchase': '#C07D10',
    'Post-Purchase': '#A89A88',
}


def score_color(score):
    if score >= 85: return '#3A7D44'
    if score >= 70: return '#C07D10'
    return '#B84233'


# ── Initialize DB ───────────────────────────────────────────────────────────
init_db()

# ── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### Copilot Shopping")
    st.caption("User Metrics Dashboard")
    st.markdown("---")

    page = st.radio(
        "NAVIGATE",
        ["Current Wave", "Trends"],
    )
    st.markdown("---")

    waves = get_all_waves()
    if waves:
        wave_options = {f"{w['wave_label']} ({w['wave_date']})": w['id'] for w in waves}
        selected_wave_label = st.selectbox("SELECT WAVE", list(wave_options.keys()), index=len(wave_options) - 1)
        selected_wave_id = wave_options[selected_wave_label]
    else:
        selected_wave_id = None
        st.info("No waves available yet. Data will appear here once uploaded by the research team.")


# ═══════════════════════════════════════════════════════════════════════════
# PAGE: CURRENT WAVE
# ═══════════════════════════════════════════════════════════════════════════

if page == "Current Wave" and selected_wave_id:
    scores = get_wave_scores(selected_wave_id)
    if not scores:
        st.error("Could not load wave data.")
        st.stop()

    prev_scores = None
    if len(waves) >= 2:
        current_idx = next((i for i, w in enumerate(waves) if w['id'] == selected_wave_id), 0)
        if current_idx > 0:
            prev_scores = get_wave_scores(waves[current_idx - 1]['id'])

    current_wave = next(w for w in waves if w['id'] == selected_wave_id)

    # ── Hero ───────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="background:#3B230E;color:#FEF9ED;padding:2.5rem 2rem;border-radius:16px;
                text-align:center;margin-bottom:2rem;position:relative;overflow:hidden">
        <div style="position:absolute;top:-50%;left:-50%;width:200%;height:200%;
                    background:radial-gradient(ellipse at 30% 50%,rgba(46,77,77,0.15) 0%,transparent 60%),
                    radial-gradient(ellipse at 70% 80%,rgba(192,125,16,0.08) 0%,transparent 50%)"></div>
        <div style="position:relative;z-index:1">
            <p style="font-size:0.72rem;font-weight:600;letter-spacing:0.15em;text-transform:uppercase;
                      color:rgba(254,249,237,0.5);margin-bottom:0.5rem">
                Copilot Shopping &middot; {current_wave['wave_label']}</p>
            <p style="font-family:Georgia,serif;color:#FEF9ED;
                       font-size:2.2rem;font-weight:400;margin-bottom:0.4rem;
                       text-shadow:0 2px 8px rgba(0,0,0,0.3);line-height:1.2">User Metrics Scorecard</p>
            <p style="color:rgba(254,249,237,0.6);font-size:0.92rem;margin-bottom:1rem">
                {len(scores.get('metrics', []))} metrics &middot; 3 domains &middot; {scores['n']} responses &middot; {current_wave['wave_date']}</p>
            <div style="display:inline-block;background:rgba(254,249,237,0.12);border:1px solid rgba(254,249,237,0.2);
                        border-radius:16px;padding:0.8rem 2rem">
                <span style="font-family:Georgia,serif;font-size:2.8rem;color:#FEF9ED;line-height:1">{scores['overall']}</span>
                <span style="font-size:0.8rem;color:rgba(254,249,237,0.6);margin-left:0.3rem">/100 Overall</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Domain KPI cards — custom HTML with domain-specific colors ───
    prev_o = prev_scores['overall'] if prev_scores else None
    delta_o_html = ''
    if prev_o:
        diff_o = round(scores['overall'] - prev_o, 1)
        arrow_o = '&#9650;' if diff_o > 0 else '&#9660;' if diff_o < 0 else '–'
        delta_o_html = f'<div style="font-size:0.82rem;color:rgba(254,249,237,0.7);margin-top:0.3rem">{arrow_o} {abs(diff_o)}</div>'

    domain_card_colors = {'Quality': '#2E4D4D', 'Trust & Confidence': '#5B7E5B', 'Privacy & Security': '#C07D10'}
    cards_row = ''
    for domain in DOMAIN_ORDER:
        d = scores['domains'].get(domain, {})
        bg = domain_card_colors[domain]
        prev_d = prev_scores['domains'].get(domain, {}).get('score_100') if prev_scores else None
        delta_html = ''
        if prev_d:
            diff = round(d['score_100'] - prev_d, 1)
            arrow = '&#9650;' if diff > 0 else '&#9660;' if diff < 0 else '–'
            delta_html = f'<div style="font-size:0.78rem;color:rgba(254,249,237,0.7);margin-top:0.2rem">{arrow} {abs(diff)}</div>'
        score_val = d.get("score_100", "—")
        n_met = d.get("n_metrics", 0)
        mean_val = d.get("mean_1_5", "—")
        cards_row += (
            f'<div style="background:{bg};color:#FEF9ED;border-radius:12px;padding:1.25rem;'
            f'text-align:center;box-shadow:0 2px 12px rgba(59,35,14,0.08)">'
            f'<div style="font-size:0.72rem;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;'
            f'color:rgba(254,249,237,0.6);margin-bottom:0.4rem">{domain}</div>'
            f'<div style="font-family:Georgia,serif;font-size:2.2rem;font-weight:400;color:#FEF9ED;line-height:1">{score_val}</div>'
            f'<div style="font-size:0.78rem;color:rgba(254,249,237,0.6);margin-top:0.3rem">{n_met} metrics &middot; mean {mean_val}</div>'
            f'{delta_html}</div>'
        )

    overall_val = scores["overall"]
    kpi_html = (
        '<div style="display:flex;justify-content:center;margin-bottom:1rem">'
        f'<div style="background:#3B230E;color:#FEF9ED;border-radius:12px;padding:1.5rem 2.5rem;'
        f'text-align:center;box-shadow:0 2px 12px rgba(59,35,14,0.08);max-width:340px;width:100%">'
        f'<div style="font-size:0.72rem;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;'
        f'color:rgba(254,249,237,0.5);margin-bottom:0.4rem">Overall Score</div>'
        f'<div style="font-family:Georgia,serif;font-size:2.4rem;font-weight:400;color:#FEF9ED;line-height:1">{overall_val} / 100</div>'
        f'{delta_o_html}</div></div>'
        f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:1rem;margin:0.5rem 0 1rem">'
        f'{cards_row}</div>'
    )
    st.markdown(kpi_html, unsafe_allow_html=True)

    # ── Key Takeaways — warm-themed cards ─────────────────────────────
    st.markdown("")
    metrics_sorted = sorted(scores['metrics'], key=lambda x: -x['score_100'])
    top3 = metrics_sorted[:3]
    bot3 = metrics_sorted[-3:]
    strongest = max(scores['domains'].items(), key=lambda x: x[1]['score_100'])
    weakest = min(scores['domains'].items(), key=lambda x: x[1]['score_100'])

    # Top metrics within the strongest domain
    sd_metrics = sorted(
        [m for m in scores['metrics'] if m['domain'] == strongest[0]],
        key=lambda x: -x['score_100']
    )
    sd_top1 = sd_metrics[0] if len(sd_metrics) > 0 else top3[0]
    sd_top2 = sd_metrics[1] if len(sd_metrics) > 1 else top3[1]

    tkdata = [
        f"Overall perception is <strong>strong at {scores['overall']}/100</strong>.",
        f"<strong>{strongest[0]} leads</strong> at {strongest[1]['score_100']}, driven by {sd_top1['name']} ({sd_top1['score_100']}) and {sd_top2['name']} ({sd_top2['score_100']}).",
        f"<strong>{weakest[0]} lags</strong> at {weakest[1]['score_100']} — especially {bot3[-1]['name']} ({bot3[-1]['score_100']}).",
        f"Top metrics: <strong>{top3[0]['name']}</strong> ({top3[0]['score_100']}), <strong>{top3[1]['name']}</strong> ({top3[1]['score_100']}), <strong>{top3[2]['name']}</strong> ({top3[2]['score_100']}).",
    ]

    # Render takeaway cards as styled HTML divs (warm theme, not blue st.info)
    cards_html = '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin:1rem 0 1.5rem">'
    for i, txt in enumerate(tkdata):
        cards_html += f'''
        <div class="takeaway-card">
            <div class="takeaway-num">{i+1}</div>
            <div class="takeaway-text">{txt}</div>
        </div>'''
    cards_html += '</div>'
    st.markdown(cards_html, unsafe_allow_html=True)

    st.markdown("---")

    # ── Tabs ───────────────────────────────────────────────────────────
    tab_metrics, tab_stages, tab_sat, tab_voices = st.tabs([
        f"All {len(scores.get('metrics', []))} Metrics", "Journey Stages", "Satisfaction", "User Voices"
    ])

    # ── TAB: METRICS ───────────────────────────────────────────────────
    with tab_metrics:
        st.caption("DEEP DIVE")
        st.markdown(f"## All {len(scores.get('metrics', []))} Metrics")
        st.markdown("")

        # Build the metrics section as HTML matching the report style
        survey_questions = {
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
        }

        domain_colors_map = {
            'Quality': '#2E4D4D',
            'Trust & Confidence': '#5B7E5B',
            'Privacy & Security': '#C07D10',
        }
        domain_css = {'Quality': 'quality', 'Trust & Confidence': 'trust', 'Privacy & Security': 'privacy'}

        # Build all bar rows HTML
        bars_html = ''
        for domain in DOMAIN_ORDER:
            domain_metrics = [m for m in scores['metrics'] if m['domain'] == domain]
            domain_metrics.sort(key=lambda x: -x['score_100'])
            color = domain_colors_map[domain]
            css_class = domain_css[domain]

            bars_html += f'<div class="bar-section"><div class="bar-section-title">{domain}</div>'

            for m in domain_metrics:
                sq = survey_questions.get(m['name'], '')
                q_tip = f'<span class="mq-tip" data-q="{sq}">&#9432;</span>' if sq else ''

                # Build drawer content
                drawer_content = ''

                # Distribution
                dist = scores.get('distributions', {}).get(m['name'], {})
                if dist:
                    max_count = max(dist.values()) if dist else 1
                    drawer_content += '<div class="bar-drawer-inner">'
                    for i in range(1, 6):
                        count = dist.get(i, dist.get(str(i), 0))
                        bar_h = max(3, int((count / max_count) * 55)) if max_count > 0 else 3
                        drawer_content += f'''
                        <div class="dist-bar-wrap">
                            <div class="dist-count">{count}</div>
                            <div class="dist-bar" style="height:{bar_h}px;background:{color}"></div>
                            <div class="dist-label">{i}</div>
                        </div>'''
                    drawer_content += '</div>'

                # Qualitative themes
                themes = scores.get('qualitative_themes', {}).get(m['name'], {})
                if themes:
                    drawer_content += '<div class="drawer-themes"><div class="drawer-themes-title">Why participants gave this rating</div>'
                    for key, accent, icon in [('high', '#3A7D44', '&#9650;'), ('low', '#B84233', '&#9660;')]:
                        g = themes.get(key)
                        if g:
                            drawer_content += f'<div style="margin-bottom:0.5rem"><div style="font-size:0.72rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:{accent};margin-bottom:0.5rem">{icon} {g["label"]} ({g["count"]} responses)</div>'
                            for t in g.get('themes', []):
                                drawer_content += f'<div class="theme-item"><div class="theme-label-row"><div class="theme-dot" style="background:{accent}"></div><span class="theme-name">{t["label"]}</span><span class="theme-pct">{t["pct"]}%</span><span class="theme-count">({t["count"]})</span></div>'
                                for q in t.get('quotes', []):
                                    import html as html_mod
                                    drawer_content += f'<div class="theme-quote">\u201C{html_mod.escape(q)}\u201D</div>'
                                drawer_content += '</div>'
                            drawer_content += '</div>'
                    drawer_content += '</div>'

                bars_html += f'''
                <div class="bar-row" onclick="toggleDrawer(this)">
                    <div class="bar-label">{m['name']} {q_tip}</div>
                    <div class="bar-track"><div class="bar-fill {css_class}" style="width:{m['score_100']}%"></div></div>
                    <div class="bar-value">{m['score_100']}</div>
                    <div class="bar-chevron">&#9654;</div>
                </div>
                <div class="bar-drawer">{drawer_content}</div>'''

            bars_html += '</div>'

        import streamlit.components.v1 as components

        # Calculate total height needed
        total_metrics = sum(1 for m in scores['metrics'])
        est_height = 200 + total_metrics * 55  # base + per-metric row height

        components.html(f'''
        <html>
        <head>
        <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', system-ui, sans-serif; color: #3B230E; background: transparent; padding: 0.5rem; }}
        .bar-section {{ margin-bottom: 1.5rem; }}
        .bar-section-title {{ font-size: 0.72rem; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; color: #7A6A56; margin-bottom: 0.75rem; padding-bottom: 0.5rem; border-bottom: 1px solid #D4C4AE; }}
        .bar-row {{ display: grid; grid-template-columns: 180px 1fr 55px 20px; align-items: center; gap: 1rem; padding: 0.55rem 0.5rem; cursor: pointer; border-radius: 6px; transition: background 0.2s; }}
        .bar-row:hover {{ background: rgba(46,77,77,0.12); }}
        .bar-row.expanded {{ background: rgba(46,77,77,0.12); }}
        .bar-label {{ font-size: 0.88rem; font-weight: 500; display: flex; align-items: center; gap: 0.3rem; }}
        .bar-chevron {{ font-size: 0.7rem; color: #7A6A56; transition: transform 0.3s; display: flex; align-items: center; justify-content: center; }}
        .bar-row.expanded .bar-chevron {{ transform: rotate(90deg); color: #2E4D4D; }}
        .bar-track {{ height: 28px; background: #E8DBC8; border-radius: 6px; overflow: hidden; }}
        .bar-fill {{ height: 100%; border-radius: 6px; }}
        .bar-fill.quality {{ background: #2E4D4D; }}
        .bar-fill.trust {{ background: #5B7E5B; }}
        .bar-fill.privacy {{ background: #C07D10; }}
        .bar-value {{ font-size: 0.88rem; font-weight: 600; text-align: right; }}
        .bar-drawer {{ max-height: 0; overflow: hidden; transition: max-height 0.5s ease; margin: 0 0.5rem; }}
        .bar-drawer.open {{ max-height: 2000px; }}
        .bar-drawer-inner {{ padding: 0.75rem 0; display: flex; gap: 1.5rem; align-items: flex-end; height: 80px; margin-left: 180px; margin-right: 75px; padding-left: 1rem; }}
        .dist-bar-wrap {{ display: flex; flex-direction: column; align-items: center; justify-content: flex-end; height: 100%; }}
        .dist-count {{ font-size: 0.78rem; color: #7A6A56; font-weight: 500; margin-bottom: 0.2rem; }}
        .dist-bar {{ width: 36px; border-radius: 4px 4px 0 0; opacity: 0.55; min-height: 3px; }}
        .dist-label {{ font-size: 0.72rem; color: #2E4D4D; margin-top: 0.25rem; font-weight: 600; }}
        .drawer-themes {{ margin: 0.5rem 0 0.25rem; padding: 0.75rem 1rem; background: #F5EBDB; border-radius: 8px; border-left: 3px solid #C07D10; }}
        .drawer-themes-title {{ font-size: 0.68rem; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; color: #7A6A56; margin-bottom: 0.6rem; }}
        .theme-item {{ margin-bottom: 0.6rem; padding-bottom: 0.5rem; border-bottom: 1px solid #D4C4AE; }}
        .theme-item:last-child {{ border-bottom: none; margin-bottom: 0; padding-bottom: 0; }}
        .theme-label-row {{ display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem; }}
        .theme-dot {{ width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }}
        .theme-name {{ font-weight: 600; font-size: 0.85rem; color: #3B230E; }}
        .theme-pct {{ font-weight: 700; font-size: 0.78rem; color: #2E4D4D; margin-left: auto; }}
        .theme-count {{ font-size: 0.72rem; color: #7A6A56; }}
        .theme-quote {{ font-size: 0.8rem; color: #7A6A56; font-style: italic; padding: 0.2rem 0 0.15rem 1.2rem; line-height: 1.5; border-left: 2px solid #D4C4AE; margin-top: 0.15rem; }}
        .mq-tip {{ position: relative; display: inline-flex; cursor: help; font-size: 0.78rem; color: #7A6A56; flex-shrink: 0; margin-left: 2px; }}
        .mq-tip:hover {{ color: #2E4D4D; }}
        #metricTip {{ position: fixed; z-index: 9999; pointer-events: none; max-width: 300px; padding: 0.75rem 1rem; background: #3B230E; color: #FEF9ED; border-radius: 8px; font-size: 0.82rem; line-height: 1.55; font-weight: 400; font-style: italic; box-shadow: 0 6px 24px rgba(0,0,0,0.35); opacity: 0; transition: opacity 0.15s; }}
        .legend-row {{ display: flex; gap: 1.2rem; flex-wrap: wrap; margin-bottom: 1.5rem; }}
        .legend-chip {{ display: flex; align-items: center; gap: 0.4rem; font-size: 0.75rem; color: #7A6A56; }}
        .legend-dot {{ width: 10px; height: 10px; border-radius: 3px; }}
        .intro {{ font-size: 0.95rem; color: #7A6A56; margin-bottom: 0.5rem; }}
        .badge {{ display: inline-block; background: #2E4D4D; color: #FEF9ED; font-size: 0.72rem; font-weight: 600; padding: 0.2rem 0.7rem; border-radius: 12px; letter-spacing: 0.04em; vertical-align: middle; margin-left: 0.25rem; }}
        </style>
        </head>
        <body>
        <p class="intro">Scored on a 0&ndash;100 scale. <span class="badge">&#9654; Click any bar to expand details &amp; qualitative themes</span></p>
        <div class="legend-row">
            <div class="legend-chip"><div class="legend-dot" style="background:#2E4D4D"></div>Quality</div>
            <div class="legend-chip"><div class="legend-dot" style="background:#5B7E5B"></div>Trust &amp; Confidence</div>
            <div class="legend-chip"><div class="legend-dot" style="background:#C07D10"></div>Privacy &amp; Security</div>
        </div>
        {bars_html}
        <div id="metricTip"></div>
        <script>
        function toggleDrawer(row) {{
            var drawer = row.nextElementSibling;
            var isOpen = drawer.classList.contains('open');
            document.querySelectorAll('.bar-drawer.open').forEach(function(d) {{ d.classList.remove('open'); }});
            document.querySelectorAll('.bar-row.expanded').forEach(function(r) {{ r.classList.remove('expanded'); }});
            if (!isOpen) {{ drawer.classList.add('open'); row.classList.add('expanded'); }}
            // Resize iframe to fit content
            setTimeout(function() {{
                window.parent.postMessage({{type:'streamlit:setFrameHeight', height: document.body.scrollHeight + 20}}, '*');
            }}, 600);
        }}
        var tip = document.getElementById('metricTip');
        document.addEventListener('mouseover', function(e) {{
            var qt = e.target.closest('.mq-tip');
            if (qt) {{
                tip.textContent = qt.getAttribute('data-q');
                var rect = qt.getBoundingClientRect();
                tip.style.left = Math.max(10, rect.left - 100) + 'px';
                tip.style.top = (rect.top - tip.offsetHeight - 10) + 'px';
                tip.style.opacity = '1';
            }}
        }});
        document.addEventListener('mouseout', function(e) {{
            if (e.target.closest('.mq-tip')) tip.style.opacity = '0';
        }});
        // Auto-expand first bar
        setTimeout(function() {{
            var firstRow = document.querySelector('.bar-row');
            var firstDrawer = document.querySelector('.bar-drawer');
            if (firstRow && firstDrawer) {{ firstRow.classList.add('expanded'); firstDrawer.classList.add('open'); }}
            // Set initial height
            window.parent.postMessage({{type:'streamlit:setFrameHeight', height: document.body.scrollHeight + 20}}, '*');
        }}, 300);
        </script>
        </body>
        </html>
        ''', height=est_height, scrolling=True)

    # ── TAB: JOURNEY STAGES ────────────────────────────────────────────
    with tab_stages:
        st.caption("SEGMENTATION")
        st.markdown("## Scores by Journey Stage")
        st.markdown("")

        # Legend
        lcol1, lcol2, lcol3, lcol4 = st.columns(4)
        lcol1.markdown("🟢 **85+** Strong")
        lcol2.markdown("🟡 **70–84** Moderate")
        lcol3.markdown("🔴 **<70** Needs Improvement")
        lcol4.markdown('<span style="color:#B0B0B0">⬤</span> **Insufficient data**', unsafe_allow_html=True)

        st.markdown("")

        # Build heatmap data
        stage_data = scores.get('stage_data', {})
        stage_n = scores.get('stage_n', {})

        rows = []
        for domain in DOMAIN_ORDER:
            domain_metrics = [m for m in scores['metrics'] if m['domain'] == domain]
            for m in domain_metrics:
                row = {'Domain': domain, 'Metric': m['name']}
                for stage in STAGE_ORDER:
                    val = stage_data.get(stage, {}).get(m['name'])
                    row[f"{stage}\n(n={stage_n.get(stage, 0)})"] = val if val is not None else None
                rows.append(row)

        heatmap_df = pd.DataFrame(rows)

        def _color_cell(val):
            if pd.isna(val): return ''
            if val >= 85: return 'background-color: rgba(58,125,68,0.18); color: #2D6B35; font-weight: 600'
            if val >= 70: return 'background-color: rgba(192,125,16,0.15); color: #9A6508; font-weight: 600'
            return 'background-color: rgba(184,66,51,0.15); color: #A03328; font-weight: 600'

        # Stages with n < 30 are shown greyed out (insufficient sample)
        _insufficient_stages = {stage for stage in STAGE_ORDER if stage_n.get(stage, 0) < 30}

        def _style_heatmap(styler):
            for col in heatmap_df.columns:
                if col in ('Domain', 'Metric'):
                    continue
                stage_name = col.split('\n')[0]
                if stage_name in _insufficient_stages:
                    styler = styler.map(
                        lambda v: 'background-color: rgba(122,106,86,0.08); color: #A89A88; font-weight: 400',
                        subset=[col]
                    )
                else:
                    styler = styler.map(_color_cell, subset=[col])
            return styler

        styled = heatmap_df.style.pipe(_style_heatmap).format(precision=1, na_rep="—")
        table_height = (len(heatmap_df) + 1) * 35 + 20
        st.dataframe(styled, use_container_width=True, hide_index=True, height=table_height)

        for stage in STAGE_ORDER:
            sn = stage_n.get(stage, 0)
            if 0 < sn < 30:
                st.caption(f"* {stage} has only {sn} respondent(s) (n < 30). Scores are directional only.")

        # Download heatmap as image
        st.markdown("")
        try:
            import matplotlib.pyplot as plt

            n_rows_hm = len(heatmap_df)
            fig_height = max(5, n_rows_hm * 0.45 + 1.5)
            fig, ax = plt.subplots(figsize=(14, fig_height))
            ax.axis('off')

            cell_text = []
            for _, row in heatmap_df.iterrows():
                formatted = []
                for col in heatmap_df.columns:
                    val = row[col]
                    if pd.isna(val):
                        formatted.append('—')
                    elif isinstance(val, (int, float)):
                        formatted.append(f'{val:.1f}')
                    else:
                        formatted.append(str(val))
                cell_text.append(formatted)

            col_labels = [c.replace('\n', ' ') for c in heatmap_df.columns]

            tbl = ax.table(
                cellText=cell_text,
                colLabels=col_labels,
                loc='center',
                cellLoc='center',
            )
            tbl.auto_set_font_size(False)
            tbl.set_fontsize(9)
            tbl.scale(1, 1.6)

            for i, row_data in enumerate(cell_text):
                for j in range(len(col_labels)):
                    cell = tbl[i + 1, j]
                    cell.set_edgecolor('#D4C4AE')
                    if j < 2:
                        cell.set_facecolor('#FEFAF0')
                        cell.set_text_props(ha='left')
                    else:
                        try:
                            v = float(row_data[j])
                            is_post = 'Post-Purchase' in heatmap_df.columns[j]
                            if is_post:
                                cell.set_facecolor('#F5F0E8')
                                cell.set_text_props(color='#A89A88')
                            elif v >= 85:
                                cell.set_facecolor('#E6F4E9')
                                cell.set_text_props(color='#2D6B35', fontweight='bold')
                            elif v >= 70:
                                cell.set_facecolor('#FDF2E0')
                                cell.set_text_props(color='#9A6508', fontweight='bold')
                            else:
                                cell.set_facecolor('#FBEAE8')
                                cell.set_text_props(color='#A03328', fontweight='bold')
                        except ValueError:
                            cell.set_facecolor('#FEFAF0')

            for j in range(len(col_labels)):
                hdr = tbl[0, j]
                hdr.set_facecolor('#EFE2D1')
                hdr.set_text_props(fontweight='bold', color='#7A6A56', fontsize=8)
                hdr.set_edgecolor('#D4C4AE')

            fig.patch.set_facecolor('#FEF9ED')
            plt.title('Scores by Journey Stage', fontfamily='Georgia', fontsize=14,
                      color='#3B230E', pad=20, loc='left', x=0.05)

            buf_img = BytesIO()
            fig.savefig(buf_img, format='png', dpi=200, bbox_inches='tight', facecolor='#FEF9ED')
            plt.close(fig)
            buf_img.seek(0)

            hm_slug = current_wave['wave_label'].replace(' ', '_')
            st.download_button(
                "Download Heatmap as Image",
                buf_img.getvalue(),
                f"heatmap_{hm_slug}.png",
                "image/png",
            )
        except Exception:
            pass

    # ── TAB: SATISFACTION ──────────────────────────────────────────────
    with tab_sat:
        st.caption("CONTEXTUAL KPI")
        st.markdown("## Overall Satisfaction")
        st.markdown("*Satisfaction is tracked as a contextual indicator (CSAT) alongside the composite score, not included in the overall metric.*")
        st.markdown("")

        if scores.get('sat_score') is not None:
            prev_sat = prev_scores.get('sat_score') if prev_scores else None

            delta_row = ''
            if prev_sat:
                diff_sat = round(scores['sat_score'] - prev_sat, 1)
                arrow_sat = '&#9650;' if diff_sat > 0 else '&#9660;' if diff_sat < 0 else '&ndash;'
                delta_row = f'<div style="font-size:0.82rem;color:rgba(254,249,237,0.7);margin-top:0.3rem">{arrow_sat} {abs(diff_sat)}</div>'

            # Build stage cards
            stage_sat = scores.get('stage_sat', {})
            stage_cards = ''
            for stage in STAGE_ORDER:
                sat = stage_sat.get(stage, {})
                sn = sat.get('n', stage_n.get(stage, 0))
                sv = sat.get('score', '&mdash;')
                op = '0.55' if sn < 30 else '1'
                stage_cards += f'''
                <div style="background:#EFE2D1;border-radius:12px;padding:1.25rem;text-align:center;box-shadow:0 2px 12px rgba(59,35,14,0.08);opacity:{op}">
                    <div style="font-size:0.68rem;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#7A6A56;margin-bottom:0.4rem;display:flex;align-items:center;justify-content:center;gap:0.3rem;white-space:nowrap">{stage} <span class="info-icon dark" data-tip="How well did Copilot help you accomplish this goal that you previously selected?">i</span></div>
                    <div style="font-family:Georgia,serif;font-size:2rem;font-weight:400;color:#3B230E;line-height:1">{sv}</div>
                    <div style="font-size:0.75rem;color:#7A6A56;margin-top:0.3rem">n = {sn}</div>
                </div>'''

            import streamlit.components.v1 as sat_components
            sat_components.html(f'''
            <html><head><style>
            * {{ margin:0; padding:0; box-sizing:border-box; }}
            body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: transparent; overflow: visible; padding-top: 0.5rem; }}
            .info-icon {{
                cursor: help; font-size: 0.6rem;
                border-radius: 50%; width: 14px; height: 14px;
                display: inline-flex; align-items: center; justify-content: center;
                font-weight: 700; font-style: normal; text-transform: lowercase;
            }}
            .info-icon.light {{
                color: rgba(254,249,237,0.7); border: 1.5px solid rgba(254,249,237,0.5);
            }}
            .info-icon.dark {{
                color: #3B230E; border: 1.5px solid #3B230E;
            }}
            #satTip {{
                position: absolute; z-index: 9999; pointer-events: none; max-width: 320px;
                padding: 0.75rem 1rem; background: #3B230E; color: #FEF9ED; border-radius: 8px;
                font-size: 0.82rem; line-height: 1.55; font-style: italic;
                box-shadow: 0 6px 24px rgba(0,0,0,0.35); opacity: 0; transition: opacity 0.15s;
                display: none;
            }}
            </style></head><body>

            <div style="display:flex;justify-content:center;margin-bottom:1.5rem">
                <div style="background:#2E4D4D;color:#FEF9ED;border-radius:12px;padding:1.5rem 2.5rem;text-align:center;box-shadow:0 2px 12px rgba(59,35,14,0.08);width:100%">
                    <div style="font-size:0.72rem;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:rgba(254,249,237,0.5);margin-bottom:0.4rem;display:flex;align-items:center;justify-content:center;gap:0.3rem">SATISFACTION SCORE <span class="info-icon light" data-tip="Thinking about your interaction with Copilot during the shopping activity, how satisfied were you with your overall experience using Copilot for shopping?">i</span></div>
                    <div style="font-family:Georgia,serif;font-size:2.8rem;font-weight:400;color:#FEF9ED;line-height:1">{scores['sat_score']}</div>
                    <div style="font-size:0.82rem;color:rgba(254,249,237,0.6);margin-top:0.3rem">mean {scores['sat_mean']} &middot; N = {scores['sat_n']}</div>
                    {delta_row}
                </div>
            </div>

            <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin-bottom:0.5rem">
                {stage_cards}
            </div>

            <div id="satTip"></div>
            <script>
            var tip = document.getElementById('satTip');
            document.querySelectorAll('.info-icon').forEach(function(el) {{
                el.addEventListener('mouseenter', function(e) {{
                    tip.textContent = el.getAttribute('data-tip');
                    tip.style.display = 'block';
                    var rect = el.getBoundingClientRect();
                    tip.style.left = Math.max(10, rect.left + window.scrollX - 100) + 'px';
                    tip.style.top = (rect.bottom + window.scrollY + 8) + 'px';
                    tip.style.opacity = '1';
                }});
                el.addEventListener('mouseleave', function() {{
                    tip.style.opacity = '0';
                    setTimeout(function() {{ tip.style.display = 'none'; }}, 150);
                }});
            }});
            </script>
            </body></html>
            ''', height=420, scrolling=False)

        st.markdown("### Satisfaction Distribution")

        sat_dist = scores.get('sat_dist', {})
        if sat_dist:
            labels = [SATISFACTION_LABELS.get(i, str(i)) for i in range(1, 6)]
            counts = [sat_dist.get(i, sat_dist.get(str(i), 0)) for i in range(1, 6)]

            fig_sat = go.Figure()
            fig_sat.add_trace(go.Bar(
                x=labels, y=counts,
                marker=dict(color='#2E4D4D', opacity=0.55, cornerradius=4),
                text=counts, textposition='outside',
                textfont=dict(size=14, color='#3B230E', family="Georgia, serif"),
                hovertemplate='%{x}: %{y} responses<extra></extra>',
            ))
            fig_sat.update_layout(
                **PLOTLY_LAYOUT,
                xaxis=dict(showgrid=False, tickfont=dict(size=11, color='#7A6A56')),
                yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
                height=350,
                margin=dict(l=20, r=20, t=50, b=60),
                bargap=0.4,
            )
            st.plotly_chart(fig_sat, use_container_width=True, key="sat_dist_chart")

    # ── TAB: VOICES ────────────────────────────────────────────────────
    with tab_voices:
        st.caption("QUALITATIVE INSIGHTS")
        st.markdown("## In Their Own Words")
        st.markdown("*From the satisfaction follow-up: \"Please explain why you gave Copilot that satisfaction rating for this shopping activity.\"*")
        st.markdown("")

        vcol1, vcol2 = st.columns(2)
        with vcol1:
            st.markdown("#### Positive Experiences")
            for q in scores.get('quotes_pos', []):
                st.success(f'*"{q}"*')

        with vcol2:
            st.markdown("#### Pain Points")
            for q in scores.get('quotes_neg', []):
                st.error(f'*"{q}"*')

    st.markdown("---")

    # ── Export section ─────────────────────────────────────────────────
    st.markdown("### Export")
    stage_data = scores.get('stage_data', {})
    wave_slug = current_wave['wave_label'].replace(' ', '_')

    # Build all_waves data for trends in report
    all_waves_for_report = []
    for w in waves:
        ws = get_wave_scores(w['id'])
        all_waves_for_report.append({
            'wave_label': w['wave_label'],
            'wave_date': w['wave_date'],
            'overall_score': w['overall_score'],
            'sat_score': w['sat_score'],
            'n_responses': w['n_responses'],
            'domains': ws.get('domains', {}),
            'metrics': ws.get('metrics', []),
        })

    # -- Download Report --
    st.markdown("##### Download Report")
    st.caption("Full scorecard report with all sections — KPIs, metrics, heatmap, satisfaction, and user voices.")
    report_cols = st.columns(2)

    with report_cols[0]:
        try:
            from report_template import generate_html_report
            html_report = generate_html_report(scores, current_wave['wave_label'], current_wave['wave_date'], all_waves=all_waves_for_report)
            st.download_button(
                "Download HTML Report",
                html_report.encode('utf-8'),
                f"scorecard_{wave_slug}.html",
                "text/html",
                use_container_width=True,
            )
            st.caption("Opens in any browser. Save as PDF via Print > Save as PDF.")
        except Exception as e:
            st.error(f"Report generation failed: {e}")

    with report_cols[1]:
        try:
            from report_template import generate_html_report
            html_for_pdf = generate_html_report(scores, current_wave['wave_label'], current_wave['wave_date'], all_waves=all_waves_for_report)
            print_additions = '''
<style>
@media print {
  .scroll-progress, .sticky-nav { display: none !important; }
  .fade-in { opacity: 1 !important; transform: none !important; }
  .bar-fill { width: var(--print-width) !important; transition: none !important; }
  section { padding: 2rem 0 !important; break-inside: avoid; }
  .hero { padding: 3rem 2rem 2rem !important; }
  body { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
}
</style>
<script>
document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('.bar-fill').forEach(function(bar) {
    bar.style.setProperty('--print-width', bar.dataset.width + '%');
    bar.style.width = bar.dataset.width + '%';
  });
  setTimeout(function() { window.print(); }, 800);
});
</script>'''
            html_for_pdf = html_for_pdf.replace('</head>', print_additions + '\n</head>')
            st.download_button(
                "Download PDF-Ready Report",
                html_for_pdf.encode('utf-8'),
                f"scorecard_{wave_slug}_print.html",
                "text/html",
                use_container_width=True,
            )
            st.caption("Opens and triggers Print dialog. Choose 'Save as PDF'.")
        except Exception as e:
            st.error(f"Report generation failed: {e}")

    # -- ZIP for VibeHub --
    try:
        from report_template import generate_html_report as _gen
        html_zip = _gen(scores, current_wave['wave_label'], current_wave['wave_date'], all_waves=all_waves_for_report)
        zip_buf = BytesIO()
        with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("index.html", html_zip)
        st.download_button(
            "Download as ZIP (for VibeHub)",
            zip_buf.getvalue(),
            f"scorecard_{wave_slug}.zip",
            "application/zip",
            use_container_width=True,
        )
    except Exception:
        pass

    st.markdown("")

    # -- Data Exports --
    st.markdown("##### Data Exports")
    data_cols = st.columns(3)

    with data_cols[0]:
        metrics_df = pd.DataFrame(scores['metrics'])[['name', 'domain', 'score_100', 'mean_1_5', 'sd', 'n']]
        metrics_df.columns = ['Metric', 'Domain', 'Score (0-100)', 'Mean (1-5)', 'SD', 'N']
        csv = metrics_df.to_csv(index=False).encode('utf-8')
        st.download_button("Metrics CSV", csv, f"metrics_{wave_slug}.csv", "text/csv",
                          use_container_width=True)

    with data_cols[1]:
        stage_rows = []
        for domain in DOMAIN_ORDER:
            dm = [m for m in scores['metrics'] if m['domain'] == domain]
            for m in dm:
                row = {'Domain': domain, 'Metric': m['name']}
                for stage in STAGE_ORDER:
                    row[stage] = stage_data.get(stage, {}).get(m['name'], '')
                stage_rows.append(row)
        stage_df = pd.DataFrame(stage_rows)
        csv2 = stage_df.to_csv(index=False).encode('utf-8')
        st.download_button("Stage Scores CSV", csv2, f"stages_{wave_slug}.csv", "text/csv",
                          use_container_width=True)

    with data_cols[2]:
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            metrics_df.to_excel(writer, sheet_name='Metrics', index=False)
            stage_df.to_excel(writer, sheet_name='Stage Scores', index=False)
            pd.DataFrame([{
                'Overall Score': scores['overall'],
                'Quality': scores['domains'].get('Quality', {}).get('score_100', ''),
                'Trust & Confidence': scores['domains'].get('Trust & Confidence', {}).get('score_100', ''),
                'Privacy & Security': scores['domains'].get('Privacy & Security', {}).get('score_100', ''),
                'Satisfaction': scores.get('sat_score', ''),
                'N': scores['n'],
            }]).to_excel(writer, sheet_name='Summary', index=False)
        st.download_button("Summary XLSX", buffer.getvalue(),
                          f"scorecard_{wave_slug}.xlsx",
                          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                          use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════
# PAGE: TRENDS
# ═══════════════════════════════════════════════════════════════════════════

elif page == "Trends":
    st.caption("HISTORICAL")
    st.markdown("## Trend Analysis")

    trend = get_trend_data()
    wave_list = trend['waves']

    if len(wave_list) < 2:
        st.info("Need at least 2 waves to show trends. Upload more datasets under **Upload & Manage**.")
        if len(wave_list) == 1:
            st.markdown(f"Currently have 1 wave: **{wave_list[0]['wave_label']}** ({wave_list[0]['wave_date']})")
    else:
        # Filters
        st.markdown("##### Filters")
        fcol1, fcol2, fcol3 = st.columns(3)
        with fcol1:
            agg = st.selectbox("View by", ["All Waves", "Monthly", "Quarterly", "Yearly"])
        with fcol2:
            date_from = st.date_input("From", value=datetime.fromisoformat(min(w['wave_date'] for w in wave_list)))
        with fcol3:
            date_to = st.date_input("To", value=datetime.fromisoformat(max(w['wave_date'] for w in wave_list)))

        filtered_waves = [w for w in wave_list if str(date_from) <= w['wave_date'] <= str(date_to)]
        if not filtered_waves:
            st.warning("No waves in selected date range.")
            st.stop()

        wave_dates = {w['wave_label']: w['wave_date'] for w in filtered_waves}
        st.markdown("---")

        # Overall & Satisfaction
        st.markdown("### Overall Score & Satisfaction")
        st.caption("**Overall** = weighted composite of 3 domains (Quality 40%, Trust & Confidence 40%, Privacy & Security 20%) on a 0–100 scale. Privacy & Security is weighted lower as a hygiene factor. **Satisfaction** = standalone contextual KPI, tracked separately and not included in the Overall score.")
        fig_o = go.Figure()
        fig_o.add_trace(go.Scatter(
            x=[w['wave_label'] for w in filtered_waves],
            y=[w['overall_score'] for w in filtered_waves],
            mode='lines+markers', name='Overall',
            line=dict(color='#2E4D4D', width=3), marker=dict(size=10, color='#2E4D4D'),
        ))
        fig_o.add_trace(go.Scatter(
            x=[w['wave_label'] for w in filtered_waves],
            y=[w['sat_score'] for w in filtered_waves],
            mode='lines+markers', name='Satisfaction',
            line=dict(color='#C07D10', width=2, dash='dot'), marker=dict(size=8, color='#C07D10'),
        ))
        fig_o.update_layout(**PLOTLY_LAYOUT,
            yaxis=dict(range=[0, 100], title='Score', gridcolor='#E8DBC8'),
            legend=dict(orientation='h', y=-0.15), height=350,
            margin=dict(l=40, r=20, t=30, b=40))
        st.plotly_chart(fig_o, use_container_width=True)

        # Domains
        st.markdown("### Domain Trends")
        domain_df = pd.DataFrame(trend['domain_trends'])
        domain_df = domain_df[domain_df['wave_label'].isin(wave_dates)]
        fig_d = go.Figure()
        for domain in DOMAIN_ORDER:
            dd = domain_df[domain_df['domain'] == domain]
            fig_d.add_trace(go.Scatter(
                x=dd['wave_label'], y=dd['score_100'],
                mode='lines+markers', name=domain,
                line=dict(color=DOMAIN_COLORS[domain], width=2.5),
                marker=dict(size=8, color=DOMAIN_COLORS[domain]),
            ))
        fig_d.update_layout(**PLOTLY_LAYOUT,
            yaxis=dict(range=[0, 100], title='Score', gridcolor='#E8DBC8'),
            legend=dict(orientation='h', y=-0.15), height=350,
            margin=dict(l=40, r=20, t=30, b=40))
        st.plotly_chart(fig_d, use_container_width=True)

        # Metrics
        st.markdown("### Metric Trends")
        metric_df = pd.DataFrame(trend['metric_trends'])
        metric_df = metric_df[metric_df['wave_label'].isin(wave_dates)]

        sel_domain = st.selectbox("Filter by domain", ["All"] + DOMAIN_ORDER, key="mt_dom")
        if sel_domain != "All":
            metric_df = metric_df[metric_df['domain'] == sel_domain]

        available = sorted(metric_df['metric'].unique().tolist())
        sel_metrics = st.multiselect("Select metrics", available, default=available[:5])
        if sel_metrics:
            colors = ['#2E4D4D','#5B7E5B','#C07D10','#3A7D44','#B84233','#3D6B6B','#7A6A56','#A89A88']
            fig_m = go.Figure()
            for i, met in enumerate(sel_metrics):
                md = metric_df[metric_df['metric'] == met]
                fig_m.add_trace(go.Scatter(
                    x=md['wave_label'], y=md['score_100'],
                    mode='lines+markers', name=met,
                    line=dict(color=colors[i % len(colors)], width=2), marker=dict(size=7),
                ))
            fig_m.update_layout(**PLOTLY_LAYOUT,
                yaxis=dict(range=[0, 100], title='Score', gridcolor='#E8DBC8'),
                legend=dict(orientation='h', y=-0.2), height=400,
                margin=dict(l=40, r=20, t=30, b=40))
            st.plotly_chart(fig_m, use_container_width=True)

        # Stage x Metric
        st.markdown("### Metric by Journey Stage")
        stage_met_df = pd.DataFrame(trend['stage_metric_trends'])
        stage_met_df = stage_met_df[stage_met_df['wave_label'].isin(wave_dates)]
        if not stage_met_df.empty:
            sm1, sm2 = st.columns(2)
            with sm1:
                sm_met = st.selectbox("Metric", sorted(stage_met_df['metric'].unique().tolist()), key="sm_m")
            with sm2:
                sm_stg = st.multiselect("Stages", STAGE_ORDER, default=STAGE_ORDER[:3], key="sm_s")
            sm_f = stage_met_df[(stage_met_df['metric'] == sm_met) & (stage_met_df['stage'].isin(sm_stg))]
            if not sm_f.empty:
                fig_sm = go.Figure()
                for stage in sm_stg:
                    sd = sm_f[sm_f['stage'] == stage]
                    fig_sm.add_trace(go.Scatter(
                        x=sd['wave_label'], y=sd['score_100'],
                        mode='lines+markers', name=stage,
                        line=dict(color=STAGE_COLORS.get(stage, '#7A6A56'), width=2), marker=dict(size=7),
                    ))
                fig_sm.update_layout(**PLOTLY_LAYOUT,
                    title=dict(text=f"{sm_met} by Stage", font=dict(size=14)),
                    yaxis=dict(range=[0, 100], title='Score', gridcolor='#E8DBC8'),
                    legend=dict(orientation='h', y=-0.15), height=350,
                    margin=dict(l=40, r=20, t=30, b=40))
                st.plotly_chart(fig_sm, use_container_width=True)

        st.markdown("---")
        st.markdown("### Export Trend Data")
        trend_csv = pd.DataFrame([{
            'Wave': w['wave_label'], 'Date': w['wave_date'],
            'Overall': w['overall_score'], 'Satisfaction': w['sat_score'], 'N': w['n_responses'],
        } for w in filtered_waves]).to_csv(index=False).encode('utf-8')
        st.download_button("Trend Data CSV", trend_csv, "trend_data.csv", "text/csv")


# ═══════════════════════════════════════════════════════════════════════════
# NO WAVE
# ═══════════════════════════════════════════════════════════════════════════

elif page == "Current Wave" and not selected_wave_id:
    st.markdown("")
    st.markdown("## User Metrics Dashboard")
    st.info("No wave data available yet. Please check back later.")

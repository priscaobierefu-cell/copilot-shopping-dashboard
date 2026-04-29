"""
Data processing module for Copilot Shopping User Metrics Dashboard.
Handles Qualtrics Excel ingestion, cleaning, Likert scoring, and metric computation.
"""

import re
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple

# ── Likert label maps ───────────────────────────────────────────────────────

def _blm(labels: list) -> dict:
    """Build Likert Map: first label = 5 (best), last = 1 (worst)."""
    return {labels[i]: 5 - i for i in range(len(labels))}

LIKERT_MAPS = {
    'Q10.1': _blm(['Very Accurate','Somewhat Accurate','Neither Accurate nor Inaccurate','Somewhat Inaccurate','Very Inaccurate']),
    'Q10.2': _blm(['Very Relevant','Somewhat Relevant','Neither Relevant nor Irrelevant','Somewhat Irrelevant','Very Irrelevant']),
    'Q10.3': _blm(['Very personalized','Somewhat personalized','Neither personalized nor unpersonalized','Somewhat unpersonalized','Very unpersonalized']),
    'Q10.5': _blm(['Very Trustworthy','Somewhat Trustworthy','Neither Trustworthy nor Untrustworthy','Somewhat Untrustworthy','Very Untrustworthy']),
    'Q10.8': _blm(['Very Protected','Somewhat Protected','Neither Protected nor Unprotected','Somewhat Unprotected','Very Unprotected']),
    'Q10.9': _blm(['Very Comfortable','Somewhat Comfortable','Neither Comfortable nor Uncomfortable','Somewhat Uncomfortable','Very Uncomfortable']),
    'Q10.12': {
        'Very Privacy-respecting': 5,
        'Slightly Privacy-respecting': 4,
        'Neither Privacy respecting Nor Non-privacy-respecting': 3,
        'Moderately Non-privacy-respecting': 2,
        'Extremely Non-privacy-respecting': 1,
    },
    'Q11.1': _blm(['Very Clear','Somewhat Clear','Neither Clear nor Unclear','Somewhat Unclear','Very Unclear']),
    'Q11.2': _blm(['Very Intuitive','Somewhat Intuitive','Neither Intuitive nor Counterintuitive','Somewhat Counterintuitive','Very Counterintuitive']),
    'Q11.5': _blm(['Very Easy','Somewhat Easy','Neither Easy nor Difficult','Somewhat Difficult','Very Difficult']),
    'Q12.3': _blm(['Very Helpful','Somewhat Helpful','Neither Helpful nor Unhelpful','Somewhat Unhelpful','Very Unhelpful']),
    'Q12.5': _blm(['Very Appealing','Somewhat Appealing','Neither Appealing nor Unappealing','Somewhat Unappealing','Very Unappealing']),
    'Q13.1': _blm(['Very satisfied','Satisfied','Neither satisfied nor dissatisfied','Dissatisfied','Very dissatisfied']),
}

# Wave 2 uses adverb-style Likert (applies to all metrics uniformly)
LIKERT_MAP_WAVE2 = {
    'Not at all': 1, 'Slightly': 2, 'Moderately': 3, 'Very': 4, 'Extremely': 5,
}

# Wave 2 column name -> (metric_name, domain) mapping
RETAINED_METRICS_WAVE2 = {
    'Clarity': ('Clarity', 'Quality'),
    'Intuitiveness': ('Intuitiveness', 'Quality'),
    'Ease of finding info': ('Ease of Finding Info', 'Quality'),
    'Helpfulness': ('Helpfulness', 'Quality'),
    'Visual appeal': ('Visual Appeal', 'Quality'),
    'Proactive': ('Proactiveness', 'Quality'),
    'Accuracy': ('Accuracy', 'Trust & Confidence'),
    'Relevancy': ('Relevance', 'Trust & Confidence'),
    'Personalized': ('Personalization', 'Trust & Confidence'),
    'Trustworthy': ('Trustworthiness', 'Trust & Confidence'),
    'Data protection': ('Data Protection', 'Privacy & Security'),
    'Comfort sharing info': ('Comfort Sharing Info', 'Privacy & Security'),
    'Privacy respect': ('Privacy-Respecting', 'Privacy & Security'),
}

# Wave 2 qualitative follow-up columns
FOLLOWUP_COLUMNS_WAVE2 = {
    'Accuracy': 'Accuracy_Follow_up',
    'Relevance': 'Relevancy_Follow_up',
    'Personalization': 'Personalized_followu',
    'Trustworthiness': 'Trustworthy_followup',
    'Data Protection': 'Data protect followu',
    'Comfort Sharing Info': 'Sharing info followu',
    'Privacy-Respecting': 'Privacy_respect foll',
    'Clarity': 'Clarity followup',
    'Intuitiveness': 'Intuitive_followup',
    'Ease of Finding Info': 'Ease of finding_foll',
    'Helpfulness': 'Hlepful_followup',
    'Visual Appeal': 'Visual appeal follow',
    'Proactiveness': 'Proactive_Follow_up',
}

# ── Metric framework ────────────────────────────────────────────────────────

RETAINED_METRICS = {
    'Q11.1': ('Clarity', 'Quality'),
    'Q11.2': ('Intuitiveness', 'Quality'),
    'Q11.5': ('Ease of Finding Info', 'Quality'),
    'Q12.3': ('Helpfulness', 'Quality'),
    'Q12.5': ('Visual Appeal', 'Quality'),
    'Q10.1': ('Accuracy', 'Trust & Confidence'),
    'Q10.2': ('Relevance', 'Trust & Confidence'),
    'Q10.3': ('Personalization', 'Trust & Confidence'),
    'Q10.5': ('Trustworthiness', 'Trust & Confidence'),
    'Q10.8': ('Data Protection', 'Privacy & Security'),
    'Q10.9': ('Comfort Sharing Info', 'Privacy & Security'),
    'Q10.12': ('Privacy-Respecting', 'Privacy & Security'),
}

# Extended metrics for waves that include Proactiveness
RETAINED_METRICS_WITH_PROACTIVE = {
    **RETAINED_METRICS,
    # Proactive is added dynamically when detected in Wave 2 format
}

DOMAIN_ORDER = ['Quality', 'Trust & Confidence', 'Privacy & Security']

STAGE_RENAME = {
    "I'm open to ideas or inspiration": "Inspiration",
    "I'm researching a product or service": "Research",
    "I'm ready to purchase": "Ready to Purchase",
    "I'm managing or using my purchase": "Post-Purchase",
}
STAGE_ORDER = ['Inspiration', 'Research', 'Ready to Purchase', 'Post-Purchase']

SATISFACTION_LABELS = {
    1: 'Very Dissatisfied',
    2: 'Dissatisfied',
    3: 'Neutral',
    4: 'Satisfied',
    5: 'Very Satisfied',
}

# ── Encoding fix ────────────────────────────────────────────────────────────

def fix_encoding(val):
    """Fix mojibake from Qualtrics UTF-8-as-CP1252 re-encoding."""
    if not isinstance(val, str):
        return val
    val = val.replace('\u2019', "'").replace('\u2018', "'")
    val = val.replace('\u201c', '"').replace('\u201d', '"')
    val = re.sub(r'\xe2\x80[\x98\x99\x9c\x9d\x93\x94]', "'", val)
    val = val.replace('a\u0302\u20ac\u2122', "'")
    val = re.sub(r'a\u0302\u20ac.', "'", val)
    val = val.replace('\xe2\x80\x99', "'").replace('\xe2\x80\x98', "'")
    val = val.replace('\xe2\x80\x9c', '"').replace('\xe2\x80\x9d', '"')
    val = val.replace('â\x80\x99', "'").replace('â\x80\x98', "'")
    val = val.replace('â€™', "'").replace('â€˜', "'")
    val = val.replace('â€œ', '"').replace('â€\x9d', '"')
    val = val.replace('Iâ€™m', "I'm")
    return val


def _to_100(mean_1_5: float) -> float:
    """Convert 1-5 mean to 0-100 scale."""
    return (mean_1_5 - 1) * 25


# ── Column resolution ───────────────────────────────────────────────────────

def _find_column(columns: list, question_id: str) -> Optional[str]:
    """Find column matching a question ID, resilient to minor naming differences."""
    exact = [c for c in columns if c == question_id]
    if exact:
        return exact[0]
    partial = [c for c in columns if str(c).startswith(question_id)]
    if partial:
        return partial[0]
    return None


# ── Main processing pipeline ────────────────────────────────────────────────

def load_and_clean(file_bytes_or_path, labels_row: Optional[pd.Series] = None) -> Tuple[pd.DataFrame, pd.Series, dict]:
    """
    Load a Qualtrics Excel or CSV export and clean it.
    Auto-detects Wave 1 (Excel, Q-code columns) vs Wave 2 (CSV/Excel, plain-text columns).

    Returns:
        (data, labels, cleaning_notes)
        - data: cleaned DataFrame with response rows
        - labels: Series mapping variable names to human-readable labels
        - cleaning_notes: dict of cleaning decisions made
    """
    notes = {}

    # Detect file type: Excel vs CSV
    is_csv = False
    if isinstance(file_bytes_or_path, str):
        is_csv = file_bytes_or_path.lower().endswith('.csv')
    else:
        # BytesIO — try reading as Excel first, fall back to CSV
        try:
            file_bytes_or_path.seek(0)
            pd.read_excel(file_bytes_or_path, header=None, nrows=1)
            file_bytes_or_path.seek(0)
        except Exception:
            is_csv = True
            file_bytes_or_path.seek(0)

    if is_csv:
        df_raw = pd.read_csv(file_bytes_or_path, header=0, dtype=str, encoding='utf-8-sig')
        # CSV: Row 1 is var names (header), Row 2 is labels, Row 3 may be metadata
        var_names = df_raw.columns.tolist()
        labels = pd.Series(var_names, index=var_names)
        if len(df_raw) > 1:
            labels = df_raw.iloc[0]
            labels.index = var_names
        # Drop metadata/label rows (Start Date labels, ImportId JSON rows)
        drop_idx = []
        for i in range(min(5, len(df_raw))):
            val = str(df_raw.iloc[i].get('StartDate', '')).strip()
            if val == '' or val.startswith('{') or val.startswith('Start Date') or 'ImportId' in val:
                drop_idx.append(df_raw.index[i])
        data = df_raw.drop(index=drop_idx).reset_index(drop=True)
    else:
        df_raw = pd.read_excel(file_bytes_or_path, header=None)
        var_names = df_raw.iloc[0].tolist()
        labels = df_raw.iloc[1]
        labels.index = var_names
        data = df_raw.iloc[3:].copy()
        data.columns = var_names
        data = data.reset_index(drop=True)

    notes['total_rows_raw'] = len(data)

    # Detect format: Wave 2 if plain-text metric columns exist
    cols = data.columns.tolist()
    wave2_markers = ['Accuracy', 'Relevancy', 'Proactive', 'Trustworthy']
    is_wave2 = sum(1 for m in wave2_markers if m in cols) >= 3
    notes['format'] = 'wave2' if is_wave2 else 'wave1'

    # Fix encoding across all string columns
    data = data.apply(lambda col: col.map(fix_encoding) if col.dtype == object else col)

    # Filter to completed responses if columns exist
    progress_col = _find_column(cols, 'Progress')
    finished_col = _find_column(cols, 'Finished')
    if progress_col and finished_col:
        before = len(data)
        progress_num = pd.to_numeric(data[progress_col], errors='coerce')
        # Finished can be True/False strings or 1/0
        finished_val = data[finished_col].astype(str).str.strip().str.lower()
        finished_ok = finished_val.isin(['1', 'true', '1.0'])
        data = data[
            (progress_num >= 100) & finished_ok
        ].reset_index(drop=True)
        notes['filtered_incomplete'] = before - len(data)
    notes['n_complete'] = len(data)

    return data, labels, notes


def compute_scores(data: pd.DataFrame, format_type: str = 'wave1') -> dict:
    """
    Compute all metric scores, domain scores, overall score,
    satisfaction, stage breakdowns, distributions, and qualitative themes.

    Args:
        data: cleaned DataFrame
        format_type: 'wave1' (Q-code columns) or 'wave2' (plain-text columns)

    Returns a dict with all computed results.
    """
    cols = data.columns.tolist()
    is_wave2 = format_type == 'wave2'

    if is_wave2:
        active_metrics = RETAINED_METRICS_WAVE2
        # Map plain-text Likert to numeric
        for col_name, (metric_name, domain) in active_metrics.items():
            if col_name in cols:
                data[f'{col_name}_num'] = data[col_name].map(LIKERT_MAP_WAVE2)
                # Case-insensitive fallback
                unmapped = data[col_name].dropna().loc[data[f'{col_name}_num'].isna() & data[col_name].notna()]
                if len(unmapped) > 0:
                    lower_map = {k.lower(): v for k, v in LIKERT_MAP_WAVE2.items()}
                    data[f'{col_name}_num'] = data[f'{col_name}_num'].fillna(
                        data[col_name].str.strip().str.lower().map(lower_map)
                    )
    else:
        active_metrics = None  # use RETAINED_METRICS
        # Map Likert labels to numeric 1-5 (Wave 1)
        for col_id in list(RETAINED_METRICS.keys()) + ['Q13.1']:
            real_col = _find_column(cols, col_id)
            if real_col and col_id in LIKERT_MAPS:
                data[f'{col_id}_num'] = data[real_col].map(LIKERT_MAPS[col_id])

    # ── Metric scores ──────────────────────────────────────────────────
    metrics = []
    if is_wave2:
        for col_name, (name, domain) in active_metrics.items():
            num_col = f'{col_name}_num'
            if num_col not in data.columns:
                continue
            v = data[num_col].dropna()
            if len(v) == 0:
                continue
            metrics.append({
                'name': name,
                'domain': domain,
                'col_id': col_name,
                'n': int(len(v)),
                'mean_1_5': round(float(v.mean()), 2),
                'sd': round(float(v.std()), 2),
                'score_100': round(float(_to_100(v.mean())), 1),
            })
    else:
        for col_id, (name, domain) in RETAINED_METRICS.items():
            num_col = f'{col_id}_num'
            if num_col not in data.columns:
                continue
            v = data[num_col].dropna()
            if len(v) == 0:
                continue
            metrics.append({
                'name': name,
                'domain': domain,
                'col_id': col_id,
                'n': int(len(v)),
                'mean_1_5': round(float(v.mean()), 2),
                'sd': round(float(v.std()), 2),
                'score_100': round(float(_to_100(v.mean())), 1),
            })
    metrics.sort(key=lambda x: -x['score_100'])

    # ── Distributions ──────────────────────────────────────────────────
    distributions = {}
    if is_wave2:
        for col_name, (name, _) in active_metrics.items():
            num_col = f'{col_name}_num'
            if num_col not in data.columns:
                continue
            vc = data[num_col].dropna().value_counts().sort_index()
            distributions[name] = {int(k): int(v) for k, v in vc.items()}
    else:
        for col_id, (name, _) in RETAINED_METRICS.items():
            num_col = f'{col_id}_num'
            if num_col not in data.columns:
                continue
            vc = data[num_col].dropna().value_counts().sort_index()
            distributions[name] = {int(k): int(v) for k, v in vc.items()}

    # ── Domain scores ──────────────────────────────────────────────────
    domains = {}
    for d in DOMAIN_ORDER:
        dm = [m for m in metrics if m['domain'] == d]
        if dm:
            domains[d] = {
                'score_100': round(float(np.mean([m['score_100'] for m in dm])), 1),
                'mean_1_5': round(float(np.mean([m['mean_1_5'] for m in dm])), 2),
                'n_metrics': len(dm),
            }

    # ── Overall score (weighted: Quality 40%, Trust & Confidence 40%, Privacy & Security 20%) ──
    DOMAIN_WEIGHTS = {'Quality': 0.40, 'Trust & Confidence': 0.40, 'Privacy & Security': 0.20}
    if domains:
        weighted_sum = sum(domains[d]['score_100'] * DOMAIN_WEIGHTS.get(d, 0) for d in domains if d in DOMAIN_WEIGHTS)
        weight_total = sum(DOMAIN_WEIGHTS.get(d, 0) for d in domains if d in DOMAIN_WEIGHTS)
        overall = round(float(weighted_sum / weight_total), 1) if weight_total > 0 else 0.0
    else:
        overall = 0.0

    # ── Satisfaction ───────────────────────────────────────────────────
    sat_col = 'Q13.1_num'
    if is_wave2:
        # Wave 2 satisfaction uses text labels
        sat_col_w2 = _find_column(cols, 'Q13.1')
        if sat_col_w2:
            sat_map_wave2 = {
                'Extremely satisfied': 5, 'Somewhat satisfied': 4,
                'Neither satisfied nor dissatisfied': 3,
                'Somewhat dissatisfied': 2, 'Extremely dissatisfied': 1,
            }
            data['Q13.1_num'] = data[sat_col_w2].map(sat_map_wave2)
    sat_data = data[sat_col].dropna() if sat_col in data.columns else pd.Series(dtype=float)
    sat_score = round(float(_to_100(sat_data.mean())), 1) if len(sat_data) > 0 else None
    sat_mean = round(float(sat_data.mean()), 2) if len(sat_data) > 0 else None
    sat_n = int(len(sat_data))

    # Satisfaction distribution
    sat_dist = {}
    if len(sat_data) > 0:
        vc = sat_data.value_counts().sort_index()
        sat_dist = {int(k): int(v) for k, v in vc.items()}

    # ── Journey stage breakdown ────────────────────────────────────────
    stage_col = _find_column(data.columns.tolist(), 'Q5.2')
    if not stage_col and is_wave2:
        # Wave 2: try common journey column names
        for candidate in ['Shopping journey', 'shopping journey', 'Q5.2']:
            stage_col = _find_column(data.columns.tolist(), candidate)
            if stage_col:
                break
    if stage_col:
        data['_stage'] = data[stage_col].apply(fix_encoding).map(STAGE_RENAME).fillna(data[stage_col])
    else:
        data['_stage'] = 'Unknown'

    stage_n = {}
    stage_data = {}
    stage_sat = {}

    for stage in STAGE_ORDER:
        sd = data[data['_stage'] == stage]
        stage_n[stage] = int(len(sd))
        if len(sd) == 0:
            continue

        # Metric scores by stage
        sm = {}
        if is_wave2:
            for col_name, (name, _) in active_metrics.items():
                num_col = f'{col_name}_num'
                if num_col not in sd.columns:
                    continue
                v = sd[num_col].dropna()
                if len(v) > 0:
                    sm[name] = round(float(_to_100(v.mean())), 1)
        else:
            for col_id, (name, _) in RETAINED_METRICS.items():
                num_col = f'{col_id}_num'
                if num_col not in sd.columns:
                    continue
                v = sd[num_col].dropna()
                if len(v) > 0:
                    sm[name] = round(float(_to_100(v.mean())), 1)
        stage_data[stage] = sm

        # Satisfaction by stage
        if sat_col in sd.columns:
            sv = sd[sat_col].dropna()
            if len(sv) > 0:
                stage_sat[stage] = {
                    'score': round(float(_to_100(sv.mean())), 1),
                    'n': int(len(sv)),
                }

    # ── Quotes ─────────────────────────────────────────────────────────
    def _get_quotes(df, col, n=5, max_len=250):
        real_col = _find_column(df.columns.tolist(), col)
        if not real_col:
            return []
        vals = df[real_col].dropna().astype(str)
        vals = vals[vals.str.len() >= 25]
        if max_len:
            vals = vals[vals.str.len() <= max_len]
        vals = vals[vals.str.contains(r'[a-zA-Z]', regex=True)]
        vals = vals[~vals.str.lower().str.match(r'^(n/?a|none|no|yes|idk)\.?$')]
        if len(vals) == 0:
            return []
        return [fix_encoding(v) for v in vals.sample(min(n, len(vals)), random_state=42).tolist()]

    def _get_detailed_quotes(df, col, n=5):
        """Get quotes without length limit — for detailed negative verbatims."""
        real_col = _find_column(df.columns.tolist(), col)
        if not real_col:
            return []
        vals = df[real_col].dropna().astype(str)
        vals = vals[vals.str.len() >= 30]
        vals = vals[vals.str.contains(r'[a-zA-Z]', regex=True)]
        vals = vals[~vals.str.lower().str.match(r'^(n/?a|none|no|yes|idk)\.?$')]
        # Prefer longer, more detailed responses
        vals = vals.iloc[vals.str.len().argsort()[::-1]]
        if len(vals) == 0:
            return []
        return [fix_encoding(v) for v in vals.head(n).tolist()]

    high_sat = data[data.get('Q13.1_num', pd.Series(dtype=float)) >= 4] if 'Q13.1_num' in data.columns else data.iloc[:0]
    low_sat = data[data.get('Q13.1_num', pd.Series(dtype=float)) <= 2] if 'Q13.1_num' in data.columns else data.iloc[:0]

    # Metric understanding quotes
    metric_quotes = {}
    if is_wave2:
        # Wave 2: extract quotes from follow-up columns for all metrics
        for metric_name, followup_col in FOLLOWUP_COLUMNS_WAVE2.items():
            metric_quotes[metric_name] = _get_quotes(data, followup_col, 5)
    else:
        quote_cols = {
            'Helpfulness': 'Q12.4',
            'Personalization': 'Q10.4',
            'Privacy-Respecting': 'Q10.13',
            'Intuitiveness': 'Q11.3',
        }
        for metric_name, qcol in quote_cols.items():
            metric_quotes[metric_name] = _get_quotes(data, qcol, 5)

    # ── Qualitative theme extraction (Wave 2) ─────────────────────────
    qualitative_themes = {}
    if is_wave2:
        qualitative_themes = _extract_all_themes(data)

    return {
        'n': int(len(data)),
        'overall': overall,
        'domains': domains,
        'metrics': metrics,
        'distributions': distributions,
        'sat_score': sat_score,
        'sat_mean': sat_mean,
        'sat_n': sat_n,
        'sat_dist': sat_dist,
        'stage_n': stage_n,
        'stage_data': stage_data,
        'stage_sat': stage_sat,
        'quotes_pos': _get_quotes(high_sat, 'Q13.2', 6),
        'quotes_neg': _get_detailed_quotes(low_sat, 'Q13.2', 6),
        'metric_quotes': metric_quotes,
        'qualitative_themes': qualitative_themes,
    }


def _extract_all_themes(data: pd.DataFrame) -> dict:
    """Extract qualitative themes from Wave 2 follow-up columns, split by high (4-5) and low (1-2) raters."""
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.cluster import KMeans
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError:
        return {}

    all_themes = {}
    for metric_name, followup_col in FOLLOWUP_COLUMNS_WAVE2.items():
        if followup_col not in data.columns:
            continue

        # Find the corresponding numeric score column
        score_col = None
        for col_name, (mname, _) in RETAINED_METRICS_WAVE2.items():
            if mname == metric_name:
                score_col = f'{col_name}_num'
                break
        if not score_col or score_col not in data.columns:
            continue

        # Get rows with both a score and a follow-up response
        mask_valid = data[followup_col].notna() & data[score_col].notna()
        subset = data.loc[mask_valid, [score_col, followup_col]].copy()
        subset[followup_col] = subset[followup_col].astype(str).str.strip()
        subset = subset[subset[followup_col].str.len() > 15]

        if len(subset) < 10:
            continue

        # Split into high (4-5) and low (1-2)
        high_mask = subset[score_col].isin([4, 5, 4.0, 5.0])
        low_mask = subset[score_col].isin([1, 2, 1.0, 2.0])

        high_responses = subset.loc[high_mask, followup_col].tolist()
        low_responses = subset.loc[low_mask, followup_col].tolist()

        metric_themes = {}

        # Extract themes for high raters
        high_themes = _extract_theme_group(high_responses, n_themes=3, n_quotes=2)
        if high_themes:
            metric_themes['high'] = {
                'label': 'Rated 4-5 (Positive)',
                'count': len(high_responses),
                'themes': high_themes,
            }

        # Extract themes for low raters (no truncation on quotes)
        low_themes = _extract_theme_group(low_responses, n_themes=3, n_quotes=2, truncate_quotes=False)
        if low_themes:
            metric_themes['low'] = {
                'label': 'Rated 1-2 (Negative)',
                'count': len(low_responses),
                'themes': low_themes,
            }

        if metric_themes:
            all_themes[metric_name] = metric_themes

    return all_themes


def _extract_theme_group(responses, n_themes=3, n_quotes=2, truncate_quotes=True):
    """Extract themes from a list of responses using TF-IDF + KMeans."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import KMeans
    from sklearn.metrics.pairwise import cosine_similarity

    valid = [r for r in responses if isinstance(r, str) and len(r.strip()) > 15]
    if len(valid) < 6:
        return []

    tfidf = TfidfVectorizer(
        max_features=500, stop_words='english',
        ngram_range=(1, 2), min_df=2, max_df=0.85,
    )
    try:
        X = tfidf.fit_transform(valid)
    except ValueError:
        return []

    n_clusters = min(n_themes, max(2, len(valid) // 10))
    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = km.fit_predict(X)
    feature_names = tfidf.get_feature_names_out()

    themes = []
    for cid in range(n_clusters):
        mask = labels == cid
        cluster_texts = [valid[i] for i in range(len(valid)) if mask[i]]
        count = len(cluster_texts)
        pct = round(count / len(valid) * 100, 1)

        center = km.cluster_centers_[cid]
        top_indices = center.argsort()[-8:][::-1]
        top_terms = [feature_names[i] for i in top_indices]

        cluster_X = X[mask]
        sims = cosine_similarity(cluster_X, center.reshape(1, -1)).flatten()
        top_q_idx = sims.argsort()[-n_quotes:][::-1]
        quotes = []
        for idx in top_q_idx:
            q = cluster_texts[idx]
            if truncate_quotes and len(q) > 200:
                q = q[:200] + "..."
            quotes.append(q)

        themes.append({
            'count': count, 'pct': pct,
            'top_terms': top_terms, 'quotes': quotes,
        })

    themes.sort(key=lambda x: x['count'], reverse=True)

    # Assign unique labels — ensure no duplicates
    used_labels = set()
    for theme in themes:
        label = _theme_label(theme['top_terms'], used_labels)
        theme['label'] = label
        theme['top_terms'] = theme['top_terms'][:4]
        used_labels.add(label)

    return themes


def _theme_label(top_terms, used_labels=None):
    """Generate a readable theme label from top TF-IDF terms, ensuring uniqueness."""
    if used_labels is None:
        used_labels = set()

    keyword_labels = {
        'links': 'Links & Source Verification', 'price': 'Pricing Information',
        'prices': 'Pricing & Value', 'products': 'Product Recommendations',
        'product': 'Product Discovery', 'options': 'Variety of Options',
        'easy': 'Ease of Use', 'helpful': 'Helpfulness & Guidance',
        'accurate': 'Accuracy of Information', 'information': 'Information Quality',
        'info': 'Information Depth', 'trust': 'Trust & Reliability',
        'privacy': 'Privacy Concerns', 'data': 'Data Handling Concerns',
        'personal': 'Personalization Experience', 'personalized': 'Tailored Recommendations',
        'style': 'Style & Preference Matching', 'search': 'Search Experience',
        'compare': 'Product Comparison', 'comparison': 'Side-by-Side Comparison',
        'clear': 'Clarity of Responses', 'visual': 'Visual Presentation',
        'images': 'Image Quality & Display', 'layout': 'Layout & Organization',
        'intuitive': 'Intuitive Navigation', 'proactive': 'Proactive Suggestions',
        'suggestions': 'Anticipation of Needs', 'recommend': 'Recommendation Quality',
        'share': 'Information Sharing Comfort', 'comfortable': 'Comfort & Confidence',
        'protect': 'Data Protection Perception', 'secure': 'Security Assurance',
        'ads': 'Advertising & Targeting Concerns', 'relevant': 'Relevance of Results',
        'navigate': 'Navigation Experience', 'find': 'Finding Information',
        'appeal': 'Visual Appeal', 'specific': 'Specificity of Results',
        'understand': 'Ease of Understanding', 'simple': 'Simplicity & Directness',
        'store': 'Store & Retailer Links', 'website': 'Website Integration',
        'buy': 'Purchase Facilitation', 'purchase': 'Purchasing Experience',
        'response': 'Response Quality', 'answer': 'Answer Completeness',
        'organized': 'Organization & Structure', 'format': 'Formatting & Readability',
        'chat': 'Conversational Experience', 'like': 'Preference Expression',
        'detailed': 'Detail & Thoroughness', 'general': 'Generality of Results',
        'didn': 'Unmet Expectations', 'lack': 'Missing Features or Depth',
        'wrong': 'Incorrect Information', 'confusing': 'Confusing Experience',
        'slow': 'Speed & Responsiveness', 'limited': 'Limited Scope',
    }

    # Try each top term, skip labels already used
    for term in top_terms:
        for keyword, label in keyword_labels.items():
            if keyword in term.lower() and label not in used_labels:
                return label

    # Fallback: build from top terms, ensuring uniqueness
    clean_terms = [t.replace('_', ' ').title() for t in top_terms[:4]]
    for i in range(len(clean_terms)):
        fallback = ' & '.join(clean_terms[:i+2])
        if fallback not in used_labels:
            return fallback

    # Last resort
    return f"Theme ({top_terms[0].title()})"


def process_wave(file_bytes_or_path) -> Tuple[dict, dict]:
    """
    End-to-end processing of a single wave Excel/CSV file.
    Returns (scores, cleaning_notes).
    """
    data, labels, notes = load_and_clean(file_bytes_or_path)
    format_type = notes.get('format', 'wave1')
    scores = compute_scores(data, format_type=format_type)
    notes['n_analyzed'] = scores['n']
    return scores, notes

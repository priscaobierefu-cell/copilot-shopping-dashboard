"""
Local storage layer using SQLite for historical wave tracking.
Stores wave-level summary results so trends persist across sessions.
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Optional, List, Dict

DB_PATH = os.path.join(os.path.dirname(__file__), 'waves.db')


def _get_conn(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(db_path: str = DB_PATH):
    """Create tables if they don't exist."""
    conn = _get_conn(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS waves (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wave_label TEXT NOT NULL,
            wave_date TEXT NOT NULL,
            filename TEXT,
            uploaded_at TEXT NOT NULL,
            n_responses INTEGER,
            overall_score REAL,
            sat_score REAL,
            scores_json TEXT NOT NULL,
            cleaning_notes_json TEXT
        );

        CREATE TABLE IF NOT EXISTS wave_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wave_id INTEGER NOT NULL,
            metric_name TEXT NOT NULL,
            domain TEXT NOT NULL,
            score_100 REAL,
            mean_1_5 REAL,
            sd REAL,
            n INTEGER,
            FOREIGN KEY (wave_id) REFERENCES waves(id)
        );

        CREATE TABLE IF NOT EXISTS wave_domains (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wave_id INTEGER NOT NULL,
            domain_name TEXT NOT NULL,
            score_100 REAL,
            mean_1_5 REAL,
            n_metrics INTEGER,
            FOREIGN KEY (wave_id) REFERENCES waves(id)
        );

        CREATE TABLE IF NOT EXISTS wave_stage_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wave_id INTEGER NOT NULL,
            stage TEXT NOT NULL,
            metric_name TEXT NOT NULL,
            score_100 REAL,
            FOREIGN KEY (wave_id) REFERENCES waves(id)
        );

        CREATE TABLE IF NOT EXISTS wave_stage_sat (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wave_id INTEGER NOT NULL,
            stage TEXT NOT NULL,
            score REAL,
            n INTEGER,
            FOREIGN KEY (wave_id) REFERENCES waves(id)
        );
    """)
    conn.commit()
    conn.close()


def save_wave(wave_label: str, wave_date: str, filename: str,
              scores: dict, cleaning_notes: dict, db_path: str = DB_PATH) -> int:
    """
    Save a processed wave to the database.
    Returns the wave_id.
    """
    init_db(db_path)
    conn = _get_conn(db_path)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO waves (wave_label, wave_date, filename, uploaded_at,
                           n_responses, overall_score, sat_score,
                           scores_json, cleaning_notes_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        wave_label,
        wave_date,
        filename,
        datetime.now().isoformat(),
        scores.get('n'),
        scores.get('overall'),
        scores.get('sat_score'),
        json.dumps(scores, default=str),
        json.dumps(cleaning_notes, default=str),
    ))
    wave_id = cur.lastrowid

    # Save metrics
    for m in scores.get('metrics', []):
        cur.execute("""
            INSERT INTO wave_metrics (wave_id, metric_name, domain, score_100, mean_1_5, sd, n)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (wave_id, m['name'], m['domain'], m['score_100'], m['mean_1_5'], m['sd'], m['n']))

    # Save domains
    for domain_name, d in scores.get('domains', {}).items():
        cur.execute("""
            INSERT INTO wave_domains (wave_id, domain_name, score_100, mean_1_5, n_metrics)
            VALUES (?, ?, ?, ?, ?)
        """, (wave_id, domain_name, d['score_100'], d['mean_1_5'], d['n_metrics']))

    # Save stage metrics
    for stage, stage_metrics in scores.get('stage_data', {}).items():
        for metric_name, score in stage_metrics.items():
            cur.execute("""
                INSERT INTO wave_stage_metrics (wave_id, stage, metric_name, score_100)
                VALUES (?, ?, ?, ?)
            """, (wave_id, stage, metric_name, score))

    # Save stage satisfaction
    for stage, sat in scores.get('stage_sat', {}).items():
        cur.execute("""
            INSERT INTO wave_stage_sat (wave_id, stage, score, n)
            VALUES (?, ?, ?, ?)
        """, (wave_id, stage, sat['score'], sat['n']))

    conn.commit()
    conn.close()
    return wave_id


def get_all_waves(db_path: str = DB_PATH) -> List[dict]:
    """Return all saved waves, ordered by wave_date."""
    init_db(db_path)
    conn = _get_conn(db_path)
    rows = conn.execute("SELECT * FROM waves ORDER BY wave_date ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_wave_scores(wave_id: int, db_path: str = DB_PATH) -> dict:
    """Load the full scores JSON for a wave."""
    conn = _get_conn(db_path)
    row = conn.execute("SELECT scores_json FROM waves WHERE id = ?", (wave_id,)).fetchone()
    conn.close()
    return json.loads(row['scores_json']) if row else {}


def get_trend_data(db_path: str = DB_PATH) -> Dict[str, list]:
    """
    Build trend data across all waves.
    Returns dict with lists for overall, satisfaction, domains, and metrics over time.
    """
    init_db(db_path)
    conn = _get_conn(db_path)

    waves = conn.execute("SELECT id, wave_label, wave_date, overall_score, sat_score, n_responses FROM waves ORDER BY wave_date ASC").fetchall()
    waves = [dict(w) for w in waves]

    # Domain trends
    domain_trends = []
    for w in waves:
        rows = conn.execute("SELECT domain_name, score_100 FROM wave_domains WHERE wave_id = ?", (w['id'],)).fetchall()
        for r in rows:
            domain_trends.append({
                'wave_label': w['wave_label'],
                'wave_date': w['wave_date'],
                'domain': r['domain_name'],
                'score_100': r['score_100'],
            })

    # Metric trends
    metric_trends = []
    for w in waves:
        rows = conn.execute("SELECT metric_name, domain, score_100, mean_1_5 FROM wave_metrics WHERE wave_id = ?", (w['id'],)).fetchall()
        for r in rows:
            metric_trends.append({
                'wave_label': w['wave_label'],
                'wave_date': w['wave_date'],
                'metric': r['metric_name'],
                'domain': r['domain'],
                'score_100': r['score_100'],
                'mean_1_5': r['mean_1_5'],
            })

    # Stage metric trends
    stage_metric_trends = []
    for w in waves:
        rows = conn.execute("SELECT stage, metric_name, score_100 FROM wave_stage_metrics WHERE wave_id = ?", (w['id'],)).fetchall()
        for r in rows:
            stage_metric_trends.append({
                'wave_label': w['wave_label'],
                'wave_date': w['wave_date'],
                'stage': r['stage'],
                'metric': r['metric_name'],
                'score_100': r['score_100'],
            })

    conn.close()

    return {
        'waves': waves,
        'domain_trends': domain_trends,
        'metric_trends': metric_trends,
        'stage_metric_trends': stage_metric_trends,
    }


def delete_wave(wave_id: int, db_path: str = DB_PATH):
    """Delete a wave and all its related data."""
    conn = _get_conn(db_path)
    conn.execute("DELETE FROM wave_stage_sat WHERE wave_id = ?", (wave_id,))
    conn.execute("DELETE FROM wave_stage_metrics WHERE wave_id = ?", (wave_id,))
    conn.execute("DELETE FROM wave_domains WHERE wave_id = ?", (wave_id,))
    conn.execute("DELETE FROM wave_metrics WHERE wave_id = ?", (wave_id,))
    conn.execute("DELETE FROM waves WHERE id = ?", (wave_id,))
    conn.commit()
    conn.close()

"""Import an external job feed (e.g. job-hunt-agent's data/apply_queue.json) into the jobs table.

Rows enter the normal pipeline (enrich -> score -> tailor -> cover letter). Jobs marked
apply_mode="manual" (e.g. LinkedIn) get apply_status="manual" so the automatic apply stage
never touches them; they are for you to submit by hand.
"""
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def load_feed(source: str) -> list[dict]:
    if source.startswith(("http://", "https://")):
        with urllib.request.urlopen(source, timeout=20) as r:  # noqa: S310 (user-supplied feed)
            data = json.load(r)
    else:
        data = json.loads(Path(source).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("feed must be a JSON list of jobs")
    return data


def import_jobs(conn, items: list[dict]) -> dict:
    """Insert feed items; returns {"added": n, "skipped": n}. Existing URLs are never overwritten."""
    now = datetime.now(timezone.utc).isoformat()
    added = skipped = 0
    for it in items:
        url = (it.get("apply_link") or "").strip()
        if not url.startswith("http") or not it.get("title"):
            skipped += 1
            continue
        manual = it.get("apply_mode") == "manual"
        cur = conn.execute(
            """INSERT OR IGNORE INTO jobs
               (url, title, description, location, site, strategy, discovered_at, apply_status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (url, it["title"], it.get("description_snippet", ""), it.get("location", ""),
             it.get("company", ""), "external_feed", it.get("queued_at") or now, "manual" if manual else None),
        )
        added += cur.rowcount
        skipped += 1 - cur.rowcount
    conn.commit()
    return {"added": added, "skipped": skipped}

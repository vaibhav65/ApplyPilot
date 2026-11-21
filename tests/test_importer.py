import json

from applypilot.database import init_db
from applypilot.importer import import_jobs, load_feed

FEED = [
    {"apply_link": "https://boards.greenhouse.io/acme/jobs/1", "title": "Lead Data Engineer", "company": "Acme",
     "location": "Hyderabad", "description_snippet": "AWS", "apply_mode": "auto"},
    {"apply_link": "https://www.linkedin.com/jobs/view/9", "title": "Data Architect", "company": "Beta",
     "apply_mode": "manual"},
    {"apply_link": "", "title": "no link"},
]


def test_import_adds_dedupes_and_protects_manual(tmp_path):
    conn = init_db(tmp_path / "t.db")
    assert import_jobs(conn, FEED) == {"added": 2, "skipped": 1}
    assert import_jobs(conn, FEED) == {"added": 0, "skipped": 3}  # idempotent
    rows = {r["url"]: r for r in conn.execute("SELECT * FROM jobs")}
    assert rows["https://boards.greenhouse.io/acme/jobs/1"]["apply_status"] is None
    assert rows["https://www.linkedin.com/jobs/view/9"]["apply_status"] == "manual"  # auto-apply skips it
    assert rows["https://boards.greenhouse.io/acme/jobs/1"]["strategy"] == "external_feed"


def test_load_feed_from_file(tmp_path):
    p = tmp_path / "q.json"
    p.write_text(json.dumps(FEED))
    assert len(load_feed(str(p))) == 3

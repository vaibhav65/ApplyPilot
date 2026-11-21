"""Free "apply kit": tailored resume + cover letter + an Apply button, delivered to Telegram."""
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx

API = "https://api.telegram.org/bot{token}/{method}"


def pending_kits(conn, min_score: int, limit: int) -> list:
    return conn.execute(
        """SELECT url, title, site, application_url, fit_score, tailored_resume_path, cover_letter_path
           FROM jobs
           WHERE fit_score >= ? AND tailored_resume_path IS NOT NULL AND cover_letter_path IS NOT NULL
             AND kit_sent_at IS NULL AND (apply_status IS NULL OR apply_status IN ('manual', 'failed'))
           ORDER BY fit_score DESC, discovered_at DESC LIMIT ?""",
        (min_score, limit),
    ).fetchall()


def send_pending_kits(conn, min_score: int = 8, limit: int = 10, dry_run: bool = False, client=None) -> int:
    token, chat = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    rows = pending_kits(conn, min_score, limit)
    if not dry_run and not (token and chat):
        raise RuntimeError("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to send kits.")
    client = client or httpx.Client(timeout=30)
    sent = 0
    for r in rows:
        link = r["application_url"] or r["url"]
        text = f"\U0001F4E6 Apply kit (fit {r['fit_score']}/10)\n{r['title']} - {r['site']}"
        if dry_run:
            print(text, link, r["tailored_resume_path"], r["cover_letter_path"], sep="\n  ")
            sent += 1
            continue
        button = {"inline_keyboard": [[{"text": "✅ Apply now", "url": link}]]}
        ok = client.post(API.format(token=token, method="sendMessage"),
                         json={"chat_id": chat, "text": text, "reply_markup": button}).status_code == 200
        for path in (r["tailored_resume_path"], r["cover_letter_path"]):
            f = Path(path)
            if ok and f.exists():
                with f.open("rb") as fh:
                    ok = client.post(API.format(token=token, method="sendDocument"),
                                     data={"chat_id": chat}, files={"document": (f.name, fh)}).status_code == 200
        if ok:
            conn.execute("UPDATE jobs SET kit_sent_at = ? WHERE url = ?",
                         (datetime.now(timezone.utc).isoformat(), r["url"]))
            conn.commit()
            sent += 1
    return sent

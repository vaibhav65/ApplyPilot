from applypilot.database import init_db
from applypilot.telegram_kit import send_pending_kits


class FakeClient:
    def __init__(self):
        self.calls = []

    def post(self, url, **kw):
        self.calls.append((url.rsplit("/", 1)[1], kw))
        return type("R", (), {"status_code": 200})()


def _seed(conn, tmp_path, url, score, manual=None):
    r, c = tmp_path / f"{score}r.txt", tmp_path / f"{score}c.txt"
    r.write_text("resume"); c.write_text("cover")
    conn.execute("""INSERT INTO jobs (url,title,site,fit_score,tailored_resume_path,cover_letter_path,apply_status)
                    VALUES (?,?,?,?,?,?,?)""", (url, "Lead DE", "Acme", score, str(r), str(c), manual))
    conn.commit()


def test_sends_only_qualifying_kits_once(tmp_path, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t"); monkeypatch.setenv("TELEGRAM_CHAT_ID", "c")
    conn = init_db(tmp_path / "t.db")
    _seed(conn, tmp_path, "https://a.com/1", 9)
    _seed(conn, tmp_path, "https://linkedin.com/2", 8, manual="manual")  # LinkedIn: you press the button
    _seed(conn, tmp_path, "https://a.com/3", 5)
    fc = FakeClient()
    assert send_pending_kits(conn, min_score=8, client=fc) == 2
    kinds = [k for k, _ in fc.calls]
    assert kinds.count("sendMessage") == 2 and kinds.count("sendDocument") == 4
    btn = fc.calls[0][1]["json"]["reply_markup"]["inline_keyboard"][0][0]
    assert btn["url"] == "https://a.com/1"
    assert send_pending_kits(conn, min_score=8, client=FakeClient()) == 0  # never re-sent

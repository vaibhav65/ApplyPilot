import json
from pathlib import Path

from typer.testing import CliRunner

from applypilot.cli import app

ROOT = Path(__file__).resolve().parents[1]
EX = json.loads((ROOT / "profile.example.json").read_text())
IN = json.loads((ROOT / "profile.india.example.json").read_text())


def test_india_template_has_same_sections_and_inr():
    assert set(EX) <= set(IN)
    assert IN["compensation"]["salary_currency"] == "INR" and IN["personal"]["country"] == "India"
    assert "notice_period" in IN["availability"]


def test_feed_command_is_registered():
    out = CliRunner().invoke(app, ["feed", "--help"])
    assert out.exit_code == 0 and "apply_queue.json" in out.output

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import common  # noqa: E402
import draw  # noqa: E402
import listen  # noqa: E402
import read  # noqa: E402

LOG = """# Журнал
```
## ГГГГ-ММ-ДД ЧЧ:ММ · скилл vX.Y
- часть: …
```
## 2026-10-15 08:00 · скилл v0.9
- часть: słuchanie
## 2026-10-14 08:00 · powtórka · скилл v0.8
## 2026-10-13 08:00 · скилл v0.7
"""


def test_vtt_rolling_captions_become_plain_text() -> None:
    vtt = ("WEBVTT\nKind: captions\nLanguage: pl\n\n00:00:00.199 --> 00:00:01.870\n"
           "Na<00:00:00.320><c> początek</c>\n\n00:00:01.870 --> 00:00:01.880\nNa początek\n\n"
           "00:00:01.880 --> 00:00:03.990\nNa początek\nzdrowia z lekarzami.\n")
    assert listen.vtt_to_text(vtt) == "Na początek zdrowia z lekarzami."


def test_feed_is_sorted_newest_first() -> None:
    xml = ("<rss><channel>"
           "<item><title>Stary</title><link>a</link><pubDate>Mon, 19 Feb 2018 10:00:00 +0100</pubDate></item>"
           "<item><title>Nowy &amp; ważny</title><link>b</link><pubDate>Tue, 13 Oct 2026 10:00:00 +0200</pubDate></item>"
           "</channel></rss>")
    assert read.parse_feed(xml) == [("2026-10-13", "Nowy & ważny", "b"), ("2018-02-19", "Stary", "a")]


def test_profile_and_part_history(tmp_path, monkeypatch) -> None:
    (tmp_path / "profile.md").write_text("# П\n- **уровень:** B2\n- **день занятий:** четверг\n", encoding="utf-8")
    (tmp_path / "log.md").write_text(LOG, encoding="utf-8")
    monkeypatch.setattr(common, "ROOT", tmp_path)
    assert common.profile() == {"уровень": "B2", "день занятий": "четверг"}
    history = draw.part_history()
    assert history["słuchanie"] == ["2026-10-15"]
    assert history["gramatyka"] == ["2026-10-14"]   # старая запись без «часть:» — по типу
    assert history["mówienie"] == ["2026-10-13"]
    assert draw.teacher_tomorrow(date(2026, 10, 14)) is True   # среда → занятие в четверг


def test_plan_without_debt_picks_longest_unpracticed_part(tmp_path, monkeypatch) -> None:
    (tmp_path / "log.md").write_text(LOG, encoding="utf-8")
    monkeypatch.setattr(common, "ROOT", tmp_path)
    monkeypatch.setattr(draw.srs, "queue", lambda today=None: [])
    route, why = draw.plan()
    assert route == "czytanie" and "ни разу" in why

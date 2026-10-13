import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import srs  # noqa: E402

TODAY = date(2026, 10, 20)


def row(when: str, rid: str, mark: str) -> list[str]:
    return [when, "/powtorka", rid, "x", "пропуск", mark, ""]


def test_error_climbs_one_box_per_session_not_per_item() -> None:
    rows = [row("2026-10-12", "E1", "✗")] + [row("2026-10-13 23:34", "E1", "✓")] * 5
    card = srs.build_card("E1", rows, today=TODAY)
    assert card.box == 2                      # пять ✓ в одном подходе — одна ступень
    assert card.due == date(2026, 10, 16)     # ступень 2 → через 3 дня
    assert card.state == "due"


def test_failed_session_drops_to_box_one() -> None:
    rows = [row("2026-10-01", "E1", "✗"), row("2026-10-02 10:00", "E1", "✓"),
            row("2026-10-05 10:00", "E1", "✓"), row("2026-10-12 10:00", "E1", "✓")]
    assert srs.build_card("E1", rows, today=TODAY).box == 4
    rows.append(row("2026-10-19 10:00", "E1", "✗"))
    rows.append(row("2026-10-19 10:00", "E1", "✓"))   # 1/2 < 80% — подход не засчитан
    card = srs.build_card("E1", rows, today=TODAY)
    assert card.box == 1 and card.due == date(2026, 10, 20)  # ступень 1 → назавтра


def test_word_starts_at_added_date() -> None:
    card = srs.build_card("W1", [], start="2026-10-12", today=TODAY)
    assert card.box == 1 and card.state == "due"
    card = srs.build_card("W1", [row("2026-10-19 10:00", "W1", "✓")], start="2026-10-12", today=TODAY)
    assert card.box == 2 and card.due == date(2026, 10, 22)


def test_one_off_old_error_sleeps_and_closed_is_skipped() -> None:
    old = [row("2026-09-01", "E1", "✗")]
    assert srs.build_card("E1", old, errors_count=1, today=TODAY).state == "sleeping"
    assert srs.build_card("E1", old, errors_count=2, today=TODAY).state == "due"
    assert srs.build_card("E1", old, closed=True, today=TODAY).state == "closed"

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import check  # noqa: E402
import common  # noqa: E402
import teacher_report  # noqa: E402


def test_check_describes_case_and_flags_unknown_forms() -> None:
    lines, unknown = check.check_text("uczta dla oczu wziąść")
    assert unknown == ["wziąść"]
    assert any("oczu ← oko" in line and "род.п" in line for line in lines)


def test_describe_maps_morfeusz_tags() -> None:
    assert check.describe("subst:pl:gen:n:col") == "сущ · мн · род.п · ср.р"
    assert check.describe("fin:sg:ter:imperf") == "глаг · ед · несов"


def test_last_report_reads_newest_date_and_metrics(tmp_path, monkeypatch) -> None:
    (tmp_path / "teacher-log.md").write_text(
        "# Лог\n\n## 2026-10-20 08:00 · сводка\n<!-- metrics: sessions=5 errors_open=20 -->\n\n"
        "## 2026-10-13 08:00 · сводка\n<!-- metrics: sessions=2 errors_open=16 -->\n",
        encoding="utf-8")
    monkeypatch.setattr(common, "ROOT", tmp_path)
    assert teacher_report.last_report() == ("2026-10-20 08:00", {"sessions": 5, "errors_open": 20})


def test_ratings_ignore_format_template(tmp_path, monkeypatch) -> None:
    (tmp_path / "log.md").write_text(
        "```\n## ГГГГ-ММ-ДД ЧЧ:ММ\n- зашло: 4/5 (или —)\n```\n\n## 2026-10-13 18:41 · скилл\n- зашло: 5/5\n",
        encoding="utf-8")
    monkeypatch.setattr(common, "ROOT", tmp_path)
    assert teacher_report.ratings_since("") == [5]

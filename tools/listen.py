"""Слушание: найти короткое польское видео и получить его текст по субтитрам (yt-dlp).

    .venv/bin/python tools/listen.py search "polsatnews zdrowie"      # до 5 роликов ≤ 8 минут
    .venv/bin/python tools/listen.py subs https://www.youtube.com/watch?v=…   # текст ролика
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import common  # noqa: F401  — UTF-8 вывод на Windows

MAX_SECONDS = 8 * 60
YTDLP = shutil.which("yt-dlp", path=str(Path(sys.executable).parent)) or "yt-dlp"


def vtt_to_text(vtt: str) -> str:
    """Субтитры YouTube «катятся»: каждая строка повторяется 2–3 раза. Убираем тайминги, теги и повторы."""
    lines: list[str] = []
    for raw in vtt.splitlines():
        line = re.sub(r"<[^>]+>", "", raw).strip()
        if not line or "-->" in line or line.startswith(("WEBVTT", "Kind:", "Language:")) or line.isdigit():
            continue
        if lines and line == lines[-1]:
            continue
        lines.append(line)
    text = " ".join(lines)
    return re.sub(r"\s+", " ", text).strip()


def search(query: str, limit: int = 5) -> list[tuple[str, str, int]]:
    out = subprocess.run([YTDLP, f"ytsearch{limit * 3}:{query}", "--flat-playlist",
                          "--print", "%(id)s\t%(title)s\t%(duration)s"],
                         capture_output=True, text=True, timeout=60).stdout
    found = []
    for line in out.splitlines():
        vid, title, dur = (line.split("\t") + ["", "", ""])[:3]
        seconds = int(float(dur)) if dur not in ("", "NA", "None") else 0
        if 0 < seconds <= MAX_SECONDS:
            found.append((vid, title, seconds))
    return found[:limit]


def subs(url: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run([YTDLP, url, "--skip-download", "--write-subs", "--write-auto-subs",
                        "--sub-langs", "pl", "--sub-format", "vtt", "-o", f"{tmp}/%(id)s"],
                       capture_output=True, text=True, timeout=90)
        files = sorted(Path(tmp).glob("*.vtt"))
        return vtt_to_text(files[0].read_text(encoding="utf-8")) if files else ""


def main() -> None:
    if len(sys.argv) < 3 or sys.argv[1] not in ("search", "subs"):
        print(__doc__)
        return
    if sys.argv[1] == "search":
        for vid, title, seconds in search(" ".join(sys.argv[2:])):
            print(f"https://www.youtube.com/watch?v={vid} · {seconds // 60}:{seconds % 60:02d} · {title}")
    else:
        text = subs(sys.argv[2])
        print(text or "Субтитров на польском нет — взять другой ролик.")


if __name__ == "__main__":
    main()

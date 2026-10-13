"""Собирает пакет Polski B2 для других: только система, без личных данных.

    .venv/bin/python tools/pack.py
→ dist/polish-b2-v<версия>.tar.gz и dist/polish-b2-install.sh (один файл: архив внутри, base64).
"""
import base64
import io
import re
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION = "1.0"
DIST = ROOT / "dist"
INCLUDE = [
    ".claude/skills/b2", ".claude/skills/powtorka", ".claude/skills/nauczyciel",
    "tools", "tests", "parts", "tasks/systemantics-check.md", "CHANGELOG.md",
    "sources/b2-standard.md", "sources/README.md",
]
RENAME = {"pack/README.md": "README.md", "pack/install.sh": "install.sh"}
PRIVATE = {"profile.md", "errors.md", "words.md", "reviews.md", "log.md", "topics.md", "grammar.md",
           "teacher.md", "teacher-log.md", "frame.md", "decisions.md", "backlog.md", "mvp.md", "architecture.md"}
SKIP_PARTS = {"__pycache__", ".pytest_cache"}


def files() -> list[tuple[Path, str]]:
    """[(источник, путь в пакете)]."""
    out = []
    for item in INCLUDE:
        src = ROOT / item
        paths = [src] if src.is_file() else sorted(p for p in src.rglob("*") if p.is_file())
        out += [(p, p.relative_to(ROOT).as_posix()) for p in paths if not SKIP_PARTS & set(p.parts)]
    out += [(ROOT / src, dst) for src, dst in RENAME.items()]
    return out


def content(path: Path, arcname: str) -> bytes:
    data = path.read_bytes()
    if arcname == "sources/README.md":  # ссылки на исследование не едут — оставляем текст без них
        text = data.decode("utf-8")
        text = re.sub(r"\s*\(\[\d{2}\]\(\.\./research/[^)]+\)\)", "", text)
        text = re.sub(r"\[(\d{2})\]\(\.\./research/[^)]+\)", r"исследованию \1", text)
        data = text.encode("utf-8")
    return data


def build() -> tuple[Path, Path]:
    pairs = files()
    leaked = [a for _, a in pairs if "/" not in a and a in PRIVATE]
    assert not leaked, f"в пакет попали личные файлы: {leaked}"
    DIST.mkdir(exist_ok=True)
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for path, arcname in pairs:
            data = content(path, arcname)
            info = tarfile.TarInfo(arcname)
            info.size = len(data)
            info.mode = 0o755 if arcname.endswith(".sh") else 0o644
            tar.addfile(info, io.BytesIO(data))
    archive = DIST / f"polish-b2-v{VERSION}.tar.gz"
    archive.write_bytes(buf.getvalue())
    payload = base64.encodebytes(buf.getvalue()).decode("ascii")
    installer = DIST / "polish-b2-install.sh"
    installer.write_text(f"""#!/usr/bin/env bash
# Polski B2 v{VERSION} — установщик одним файлом. Использование:
#   bash polish-b2-install.sh [папка]          (по умолчанию ./polish-b2)
#   curl -fsSL <адрес>/polish-b2-install.sh | bash -s -- [папка]
# Повторный запуск в ту же папку обновляет систему; твои данные (profile.md, журналы) не трогаются.
set -euo pipefail
TARGET="${{1:-polish-b2}}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
base64 --decode > "$TMP/polish-b2.tar.gz" <<'PAYLOAD'
{payload}PAYLOAD
mkdir -p "$TARGET"
(cd "$TARGET" && tar -xzf "$TMP/polish-b2.tar.gz")  # без -C: в Git Bash путь с «C:» tar принял бы за удалённый хост
echo "Polski B2 v{VERSION} распакован в $TARGET"
bash "$TARGET/install.sh"
""", encoding="utf-8", newline="\n")  # bash не переносит CRLF — важно при сборке на Windows
    installer.chmod(0o755)
    return archive, installer


if __name__ == "__main__":
    archive, installer = build()
    print(f"{archive.relative_to(ROOT)} · {archive.stat().st_size // 1024} КБ · файлов {len(files())}")
    print(f"{installer.relative_to(ROOT)} · {installer.stat().st_size // 1024} КБ")

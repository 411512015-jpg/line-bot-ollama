"""交件前的敏感資料檢查。

只掃描 git 追蹤的檔案，避免把本機的 .env／啟動腳本誤判成要交出的程式。
執行：
    python scripts/check_submission.py
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

TEXT_SUFFIXES = {
    ".py", ".js", ".gs", ".html", ".css", ".md", ".txt",
    ".json", ".yml", ".yaml", ".bat", ".ps1", ".example",
}

CHECKS = [
    (
        "Google Apps Script 部署網址",
        re.compile(r"https?://script\.google\.com/macros/s/[A-Za-z0-9_-]{8,}/(?:exec|dev)"),
    ),
    (
        "疑似 LINE / Gemini / ngrok 金鑰",
        re.compile(
            r"(?:LINE_CHANNEL_ACCESS_TOKEN|LINE_CHANNEL_SECRET|GEMINI_API_KEY|NGROK_AUTHTOKEN)"
            r"\s*[:=]\s*[\"']([^\"'\n]{20,})[\"']"
        ),
    ),
    (
        "疑似 Bearer token",
        re.compile(r"Bearer\s+[A-Za-z0-9+/=_-]{30,}"),
    ),
    (
        "疑似 Google API key",
        re.compile(r"AIza[0-9A-Za-z_-]{30,}"),
    ),
    (
        "ngrok authtoken 指令",
        re.compile(r"ngrok\s+config\s+add-authtoken\s+([A-Za-z0-9_\-]{10,})"),
    ),
]

PLACEHOLDER_HINTS = (
    "你的", "YOUR", "your", "xxxx", "XXXX", "example", "EXAMPLE",
    "os.environ", "$env:", "%", "${", "<", ">", "....",
)


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    )
    names = result.stdout.decode("utf-8", errors="replace").split("\0")
    return [ROOT / name for name in names if name]


def main() -> int:
    findings: list[tuple[str, Path, int, str]] = []

    for path in tracked_files():
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue

        for lineno, line in enumerate(lines, start=1):
            for label, pattern in CHECKS:
                match = pattern.search(line)
                if not match:
                    continue
                value = match.group(0)
                if any(hint in value for hint in PLACEHOLDER_HINTS):
                    continue
                findings.append((label, path, lineno, value[:90]))

    print(f"掃描 {len(tracked_files())} 個 git 追蹤檔案……")
    if not findings:
        print("OK：沒有發現金鑰、Bearer token、ngrok authtoken 或 Apps Script 部署網址。")
        print("提醒：報告／投影片／截圖仍要人工確認一次。")
        return 0

    print("發現疑似敏感資料：")
    for label, path, lineno, value in findings:
        relative = path.relative_to(ROOT)
        print(f"  - {relative}:{lineno}  [{label}]  {value}")
    return 1


if __name__ == "__main__":
    sys.exit(main())

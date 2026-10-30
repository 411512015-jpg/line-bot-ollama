"""把 Markdown 報告與 HTML 簡報輸出成 PDF，並產生簡報預覽圖。"""

from pathlib import Path

import markdown
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
SHOTS = DOCS / "screenshots"
SHOTS.mkdir(parents=True, exist_ok=True)

REPORT_CSS = """
@page { size: A4; margin: 18mm 17mm 18mm; }
* { box-sizing: border-box; }
body {
  margin: 0; color: #1c2a22; font-family: "Microsoft JhengHei", "Noto Sans TC", sans-serif;
  font-size: 10.2pt; line-height: 1.72; letter-spacing: .01em;
}
h1 { font-size: 27pt; line-height: 1.18; letter-spacing: -.04em; margin: 0 0 8mm; color: #122019; }
h2 {
  font-size: 16pt; line-height: 1.3; margin: 9mm 0 3mm; color: #075f31;
  border-bottom: 1.2pt solid #bfe9cb; padding-bottom: 1.5mm; page-break-after: avoid;
}
h3 { font-size: 12pt; margin: 6mm 0 2mm; color: #122019; page-break-after: avoid; }
p { margin: 0 0 3mm; text-align: justify; }
strong { color: #075f31; }
ul, ol { margin: 0 0 3.5mm 5.5mm; padding: 0; }
li { margin: 0 0 1.5mm; }
blockquote {
  margin: 4mm 0; padding: 3mm 4mm; background: #f0f8f2;
  border-left: 3pt solid #06c755; color: #315343; font-size: 9.6pt;
}
code {
  font-family: Consolas, "Cascadia Mono", monospace; font-size: 8.8pt;
  background: #eef4ef; color: #174d2c; padding: .5mm 1.2mm; border-radius: 2px;
}
pre {
  background: #14251c; color: #dff8e7; padding: 3.5mm 4mm; border-radius: 3mm;
  font-family: Consolas, "Cascadia Mono", monospace; font-size: 8.5pt; line-height: 1.55;
  white-space: pre-wrap; page-break-inside: avoid;
}
pre code { background: transparent; color: inherit; padding: 0; }
table {
  width: 100%; border-collapse: collapse; margin: 4mm 0 5mm; font-size: 9pt;
  page-break-inside: avoid;
}
th {
  background: #e4f7e9; color: #075f31; text-align: left; font-weight: 800;
  border: .6pt solid #cde6d5; padding: 1.8mm 2mm;
}
td { border: .6pt solid #dbe7de; padding: 1.7mm 2mm; vertical-align: top; }
tr:nth-child(even) td { background: #fbfdfb; }
img {
  display: block; max-width: 100%; height: auto; margin: 5mm auto;
  border: .6pt solid #dbe7de; border-radius: 2mm; page-break-inside: avoid;
}
hr { border: 0; border-top: .6pt solid #dbe7de; margin: 5mm 0; }
.cover {
  min-height: 244mm; display: flex; flex-direction: column; justify-content: center;
  page-break-after: always; padding-left: 8mm; border-left: 5mm solid #06c755;
}
.cover h1 { font-size: 30pt; max-width: 150mm; }
.cover p { font-size: 11pt; color: #66756c; margin: 3mm 0; }
.cover p strong { font-size: 13pt; color: #075f31; }
.cover::before {
  content: "MIDTERM PROJECT / 2026"; font-size: 8pt; font-weight: 800;
  letter-spacing: .18em; color: #06a948; margin-bottom: 5mm;
}
.small { font-size: 9pt; color: #66756c; }
"""


def render_markdown(md_path: Path, html_path: Path, cover: bool = False) -> None:
    text = md_path.read_text(encoding="utf-8")
    html = markdown.markdown(
        text,
        extensions=["tables", "fenced_code", "sane_lists", "nl2br"],
    )

    if cover and "<hr />" in html:
        head, tail = html.split("<hr />", 1)
        html = f'<section class="cover">{head}</section>{tail}'

    page = f"""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8">
<title>{md_path.stem}</title>
<style>{REPORT_CSS}</style></head>
<body>{html}</body></html>"""
    html_path.write_text(page, encoding="utf-8")


def main() -> None:
    render_markdown(DOCS / "專題報告.md", DOCS / "專題報告.html", cover=True)
    render_markdown(DOCS / "AI對話摘要.md", DOCS / "AI對話摘要.html", cover=False)

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page()

        for name in ["專題報告", "AI對話摘要"]:
            page.goto((DOCS / f"{name}.html").as_uri(), wait_until="networkidle")
            page.emulate_media(media="print")
            page.pdf(
                path=str(DOCS / f"{name}.pdf"),
                format="A4",
                print_background=True,
                margin={"top": "18mm", "right": "17mm", "bottom": "18mm", "left": "17mm"},
            )
            print(DOCS / f"{name}.pdf")

        page = browser.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=1)
        page.goto((DOCS / "簡報.html").as_uri(), wait_until="networkidle")
        page.emulate_media(media="print")
        slides = page.locator(".slide")
        for i in range(slides.count()):
            slides.nth(i).screenshot(path=str(SHOTS / f"slide-{i + 1}.png"))
        page.pdf(
            path=str(DOCS / "期中展示.pdf"),
            width="13.333in",
            height="7.5in",
            print_background=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
        print(DOCS / "期中展示.pdf")

        browser.close()


if __name__ == "__main__":
    main()

"""產生報告與簡報用的架構圖（不依賴外部服務）。"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)

W, H = 1600, 900
FONT_DIR = Path("C:/Windows/Fonts")

INK = "#122019"
MUTED = "#66756c"
CREAM = "#f4f0e6"
PAPER = "#fffdf8"
GREEN = "#06c755"
GREEN_DARK = "#049b43"
LIME = "#c7f9d8"
ORANGE = "#ff8a4c"
LINE = "#dfe8e1"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "msjhbd.ttc" if bold else "msjh.ttc"
    return ImageFont.truetype(str(FONT_DIR / name), size=size, index=0)


def text(draw, xy, value, size=30, color=INK, bold=False, anchor="la"):
    draw.text(xy, value, font=font(size, bold), fill=color, anchor=anchor)


def wrap(draw, value, xy, max_width, size=24, color=MUTED, bold=False, gap=8):
    f = font(size, bold)
    x, y = xy
    for paragraph in value.split("\n"):
        line = ""
        for char in paragraph:
            candidate = line + char
            if draw.textlength(candidate, font=f) > max_width and line:
                draw.text((x, y), line, font=f, fill=color)
                y += size + gap
                line = char
            else:
                line = candidate
        draw.text((x, y), line, font=f, fill=color)
        y += size + gap
    return y


def card(draw, box, fill=PAPER, radius=28, outline=LINE, shadow=True):
    x1, y1, x2, y2 = box
    if shadow:
        draw.rounded_rectangle((x1 + 8, y1 + 12, x2 + 8, y2 + 12), radius=radius, fill="#d9ded7")
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=2)


def arrow(draw, start, end, color=GREEN_DARK, width=5):
    draw.line([start, end], fill=color, width=width)
    x1, y1 = start
    x2, y2 = end
    if abs(x2 - x1) >= abs(y2 - y1):
        direction = 1 if x2 > x1 else -1
        pts = [(x2, y2), (x2 - 18 * direction, y2 - 11), (x2 - 18 * direction, y2 + 11)]
    else:
        direction = 1 if y2 > y1 else -1
        pts = [(x2, y2), (x2 - 11, y2 - 18 * direction), (x2 + 11, y2 - 18 * direction)]
    draw.polygon(pts, fill=color)


def number_badge(draw, xy, value, color=GREEN_DARK):
    x, y = xy
    draw.ellipse((x, y, x + 34, y + 34), fill=color)
    text(draw, (x + 17, y + 17), value, 18, "#ffffff", True, "mm")


def build_architecture():
    image = Image.new("RGB", (W, H), CREAM)
    draw = ImageDraw.Draw(image)

    # 背景格線
    for x in range(0, W, 40):
        draw.line((x, 0, x, H), fill="#e9e5da", width=1)
    for y in range(0, H, 40):
        draw.line((0, y, W, y), fill="#e9e5da", width=1)

    # 標題
    text(draw, (80, 62), "ARCHITECTURE / 一句話的旅程", 21, GREEN_DARK, True)
    text(draw, (80, 102), "LINE 訊息如何變成有來源的答案？", 52, INK, True)
    text(draw, (82, 172), "雲端只負責收發與轉接；搜尋、推論與回覆流程都留在自己的電腦。", 24, MUTED)

    # 四個主要節點
    y1, y2 = 300, 510
    boxes = [
        (90, y1, 360, y2),
        (455, y1, 790, y2),
        (885, y1, 1200, y2),
        (1295, y1, 1510, y2),
    ]
    card(draw, boxes[0], fill="#e8f9ed", outline="#bcefca")
    card(draw, boxes[1], fill="#14251c", outline="#14251c")
    card(draw, boxes[2], fill="#fff0e6", outline="#ffd2b8")
    card(draw, boxes[3], fill="#e8f9ed", outline="#bcefca")

    number_badge(draw, (112, 322), "1")
    number_badge(draw, (477, 322), "2", "#0b6f35")
    number_badge(draw, (907, 322), "3", "#c45c21")
    number_badge(draw, (1317, 322), "4")

    text(draw, (112, 382), "LINE", 40, INK, True)
    text(draw, (112, 435), "使用者輸入\n「查 …」或待辦", 22, "#345045")

    text(draw, (477, 382), "Apps Script", 36, "#ffffff", True)
    text(draw, (477, 435), "Webhook 收訊息\n分流／非同步轉接", 22, "#b8d3c3")

    text(draw, (907, 382), "Flask 轉接站", 34, "#8a3f12", True)
    text(draw, (907, 435), "搜尋＋整理 context\n背景執行緒回覆", 22, "#7c4e32")

    text(draw, (1317, 382), "Gemma 2", 36, INK, True)
    text(draw, (1317, 435), "Ollama · 2B\n本機 CPU 推論", 22, "#345045")

    arrow(draw, (365, 405), (447, 405))
    arrow(draw, (797, 405), (877, 405), color="#c45c21")
    arrow(draw, (1207, 405), (1287, 405))

    # 搜尋來源
    card(draw, (800, 615, 1285, 765), fill=PAPER, outline="#d8e6dc")
    text(draw, (830, 637), "SEARCH LAYER / 免金鑰", 18, GREEN_DARK, True)
    text(draw, (830, 672), "Google News RSS", 26, INK, True)
    text(draw, (830, 710), "中文 Wikipedia API", 26, INK, True)
    text(draw, (1080, 672), "新聞／時事", 18, MUTED)
    text(draw, (1080, 710), "知識／人物", 18, MUTED)
    arrow(draw, (1040, 610), (1040, 525), color="#c45c21", width=4)

    # 待辦分支
    card(draw, (380, 615, 760, 765), fill=PAPER, outline="#d8e6dc")
    text(draw, (408, 637), "TODO BRANCH / 其他訊息", 18, "#c45c21", True)
    text(draw, (408, 672), "「買牛奶」", 27, INK, True)
    text(draw, (408, 714), "→ 寫入 Google Sheet", 22, MUTED)
    arrow(draw, (580, 610), (580, 525), color="#c45c21", width=4)

    # 底部三個設計理由
    reasons = [
        ("為什麼用 Apps Script？", "不用自己養伺服器，\nLINE 驗證與轉接成本最低。"),
        ("為什麼用本機模型？", "免逐字計費、資料不送模型商；\n代價是電腦要開著。"),
        ("為什麼要附來源？", "把「相信我」變成\n「你可以自己查」。"),
    ]
    x = 90
    for title, body in reasons:
        draw.line((x, 823, x + 40, 823), fill=GREEN, width=5)
        text(draw, (x + 54, 808), title, 21, INK, True)
        text(draw, (x + 54, 842), body, 17, MUTED)
        x += 490

    image.save(OUT / "architecture.png", quality=95)
    print(OUT / "architecture.png")


if __name__ == "__main__":
    build_architecture()

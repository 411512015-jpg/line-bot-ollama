"""產生期中展示 PPTX（16:9，含講者備忘稿）。"""

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parent.parent
SHOTS = ROOT / "docs" / "screenshots"
OUT = ROOT / "docs" / "期中展示.pptx"

INK = RGBColor(0x12, 0x20, 0x19)
CREAM = RGBColor(0xF4, 0xF0, 0xE6)
PAPER = RGBColor(0xFF, 0xFD, 0xF8)
GREEN = RGBColor(0x06, 0xC7, 0x55)
GREEN_DARK = RGBColor(0x04, 0x9B, 0x43)
LIME = RGBColor(0xC7, 0xF9, 0xD8)
ORANGE = RGBColor(0xFF, 0x8A, 0x4C)
MUTED = RGBColor(0x66, 0x75, 0x6C)
DARK = RGBColor(0x14, 0x25, 0x1C)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
SOFT = RGBColor(0xB8, 0xD3, 0xC3)
LINE = RGBColor(0xDF, 0xE8, 0xE1)
FONT = "Microsoft JhengHei"

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)


def slide(bg=CREAM):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = bg
    return s


def rect(s, x, y, w, h, fill, line=None, radius=0.08, shape=MSO_SHAPE.ROUNDED_RECTANGLE):
    shp = s.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line
        shp.line.width = Pt(1)
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        try:
            shp.adjustments[0] = radius
        except Exception:
            pass
    return shp


def text(s, value, x, y, w, h, size=18, color=INK, bold=False,
         align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, spacing=1.0,
         margins=(0, 0, 0, 0), font=FONT):
    box = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left, tf.margin_top, tf.margin_right, tf.margin_bottom = [Inches(m) for m in margins]

    paragraphs = value.split("\n")
    for i, line in enumerate(paragraphs):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = spacing
        p.space_before = Pt(0)
        p.space_after = Pt(0)
        r = p.add_run()
        r.text = line
        r.font.name = font
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.color.rgb = color
    return box


def pill(s, value, x, y, w, h, fill, fg, size=10):
    rect(s, x, y, w, h, fill, None, radius=0.5)
    text(s, value, x, y + 0.02, w, h - 0.02, size, fg, True,
         PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)


def footer(s, n, dark=False):
    color = RGBColor(0x6F, 0x8A, 0x7B) if dark else RGBColor(0x8B, 0x9A, 0x91)
    text(s, "LINE Bot × Local LLM", 0.7, 7.12, 5.0, 0.22, 8, color, False)
    text(s, f"{n:02d}", 12.0, 7.12, 0.65, 0.22, 8, color, False, PP_ALIGN.RIGHT)


def notes(s, value):
    s.notes_slide.notes_text_frame.text = value


# ---------------------------------------------------------------- slide 1
s = slide(INK)
pill(s, "MIDTERM PROJECT · 2026", 0.72, 0.5, 2.85, 0.38, RGBColor(0x1C, 0x35, 0x28), LIME, 9)

text(s, "把 LINE 變成", 0.72, 1.12, 7.3, 0.8, 44, WHITE, True, spacing=0.95)
text(s, "會記帳的", 0.72, 1.92, 7.3, 0.8, 44, GREEN, True, spacing=0.95)
text(s, "AI 記帳小幫手", 0.72, 2.72, 7.3, 0.8, 44, WHITE, True, spacing=0.95)

text(s, "同一個聊天視窗，兩種工作流：\n「咖啡 45 元」自動記帳、分類、累計；「查 …」得到有來源的答案。",
     0.75, 3.95, 6.7, 1.0, 16, SOFT, spacing=1.45)

for i, (label, color) in enumerate([("記帳自動分類", GREEN), ("免 API 費用", ORANGE), ("今日＋本月累計", LIME)]):
    pill(s, label, 0.75 + i * 1.55, 5.2, 1.35, 0.38, RGBColor(0x1C, 0x35, 0x28), color, 9)

text(s, "90 秒 Demo：咖啡 45 元  →  Uber 60", 0.75, 6.55, 7.5, 0.35, 11,
     RGBColor(0x6F, 0x8A, 0x7B), True)

rect(s, 8.35, 0.72, 4.35, 5.95, PAPER, RGBColor(0x2C, 0x4A, 0x39), radius=0.04)
s.shapes.add_picture(str(SHOTS / "phone-demo.png"), Inches(8.48), Inches(0.85), height=Inches(5.7))
footer(s, 1, dark=True)
notes(s, "0:00–0:10｜開場。這是一個放在 LINE 裡的 AI 記帳小幫手；今天用展示頁跑給大家看，因為它和 LINE 版共用同一個流程，但不需要把 token 放進畫面。")

# ---------------------------------------------------------------- slide 2
s = slide(CREAM)
text(s, "01 / PROBLEM", 0.72, 0.55, 5.0, 0.3, 10, GREEN_DARK, True)
text(s, "記帳，本來就該很簡單。", 0.72, 0.95, 11.5, 1.0, 30, INK, True, spacing=1.12)

cards = [
    ("01", "記帳要開 App", "手動打類別、換工具、整理匯總。\n不想為每筆花費開一個 App。"),
    ("02", "查資料要切 App", "在 LINE 裡問，切到瀏覽器搜尋，看完再切回來。\n注意力被切成三段。"),
    ("03", "雲端 AI 有成本", "逐字計費、需要 API key；\n敏感內容也不一定想送出門。"),
]
for i, (num, head, body) in enumerate(cards):
    x = 0.72 + i * 4.1
    rect(s, x, 2.55, 3.78, 2.85, PAPER, LINE)
    text(s, num, x + 0.28, 2.78, 0.6, 0.45, 13, GREEN_DARK, True)
    text(s, head, x + 0.28, 3.2, 3.2, 0.45, 18, INK, True)
    text(s, body, x + 0.28, 3.77, 3.15, 1.35, 12, MUTED, spacing=1.35)

rect(s, 0.72, 5.85, 11.95, 0.85, DARK, None, radius=0.18)
text(s, "主要使用者：常用 LINE 的學生與小型團隊　·　設計目標：不離開聊天室、記帳免 API、累計即時",
     1.0, 5.95, 11.4, 0.55, 12, LIME, True, anchor=MSO_ANCHOR.MIDDLE)
footer(s, 2)
notes(s, "0:10–0:20｜問題有三個：記帳要開 App、查資料要切 App、雲端 AI 有費用與隱私顾虑。這個專案給誰用？主要是常用 LINE 的學生與小型團隊。")

# ---------------------------------------------------------------- slide 3
s = slide(CREAM)
text(s, "02 / SOLUTION", 0.72, 0.55, 5.0, 0.3, 10, GREEN_DARK, True)
text(s, "一個入口，兩種模式。", 0.72, 0.95, 8.0, 0.7, 30, INK, True)

rect(s, 0.72, 1.95, 7.35, 2.15, PAPER, GREEN, radius=0.06)
text(s, "查 …", 1.0, 2.15, 1.0, 0.45, 20, GREEN_DARK, True)
text(s, "先搜尋，再讓本機模型整理；答案最後附來源。", 1.0, 2.68, 6.7, 0.45, 15, INK, True)
text(s, "查 玉山有多高   →   3,950 公尺＋Wikipedia 來源",
     1.0, 3.18, 6.6, 0.7, 10.5, MUTED, spacing=1.4)

rect(s, 0.72, 4.35, 7.35, 1.85, PAPER, ORANGE, radius=0.06)
text(s, "咖啡 45 元", 1.0, 4.55, 1.5, 0.45, 20, RGBColor(0xC4, 0x5C, 0x21), True)
text(s, "本地解析 merchant＋amount，分類後累計今日／本月。", 1.0, 5.08, 6.6, 0.45, 15, INK, True)
text(s, "咖啡 45 元 → 已記帳（飲食），今日累計…　／　上個月累計…", 1.0, 5.55, 6.6, 0.35, 11, MUTED)

text(s, "同一套 /ask 流程；展示頁不需要 LINE token。", 0.75, 6.55, 7.2, 0.35, 10,
     GREEN_DARK, True)

rect(s, 8.35, 0.72, 4.35, 5.95, PAPER, LINE, radius=0.04)
s.shapes.add_picture(str(SHOTS / "phone-demo.png"), Inches(8.48), Inches(0.85), height=Inches(5.7))
footer(s, 3)
notes(s, "0:20–0:55｜先講兩種模式，再點『咖啡 45 元』。等待時指右側流程：Apps Script 收訊息、Flask 本地解析、累計、回覆。接著點『Uber 60』，讓累計加總。")

# ---------------------------------------------------------------- slide 4
s = slide(CREAM)
s.shapes.add_picture(str(SHOTS / "architecture.png"), Inches(0.35), Inches(0.2), width=Inches(12.63))
notes(s, "1:05–1:18｜雲端只負責收發與轉接，搜尋與推論在自己的電腦。三個設計理由：Apps Script 不用養伺服器；本機模型免逐字費用；附來源讓使用者可以查證。最大限制是電腦要開著。")

# ---------------------------------------------------------------- slide 5
s = slide(INK)
text(s, "03 / ENGINEERING", 0.72, 0.55, 5.0, 0.3, 10, GREEN, True)
text(s, "讓它能跑，而不是只看起來能跑。", 0.72, 0.95, 11.4, 0.7, 30, WHITE, True)

items = [
    ("01", "非同步 202", "Apps Script 先回 200，\nFlask 算完再直接呼叫 Reply API。", "避免 LINE Webhook 逾時"),
    ("02", "先搜尋，再生成", "Google News RSS＋Wikipedia\n只把前 3 筆放進 prompt。", "答案附來源，降低幻覺"),
    ("03", "2B＋暖機", "gemma2:2b、num_predict=220\n啟動時先 warm_up()。", "暖機後約 5.9 秒"),
    ("04", "不把祕密寫進程式", "本機用環境變數；\nApps Script 用指令碼屬性。", "交件前掃描 0 金鑰"),
]
for i, (num, head, body, tag) in enumerate(items):
    x = 0.72 + (i % 2) * 6.05
    y = 1.95 + (i // 2) * 2.28
    rect(s, x, y, 5.8, 2.0, RGBColor(0x1A, 0x2F, 0x23), RGBColor(0x2C, 0x4A, 0x39), radius=0.06)
    text(s, num, x + 0.28, y + 0.22, 0.55, 0.35, 11, GREEN, True)
    text(s, head, x + 0.28, y + 0.62, 4.9, 0.42, 18, WHITE, True)
    text(s, body, x + 0.28, y + 1.1, 4.9, 0.6, 11.5, SOFT, spacing=1.3)
    text(s, tag, x + 0.28, y + 1.66, 4.9, 0.25, 9, LIME, True)

footer(s, 5, dark=True)
notes(s, "1:18–1:25｜如果時間不夠，只講兩個：非同步避免逾時、先搜尋再生成所以有來源。2B 與暖機是為了在 CPU 上把延遲壓到可接受。")

# ---------------------------------------------------------------- slide 6
s = slide(CREAM)
text(s, "04 / EVIDENCE", 0.72, 0.55, 5.0, 0.3, 10, GREEN_DARK, True)
text(s, "測試：17/17，沒有僥倖。", 0.72, 0.95, 11.0, 0.7, 30, INK, True)

metrics = [
    ("17 / 17", "單元測試通過", "不需要 LINE token 或 Ollama"),
    ("0.3 秒", "暖機後記帳", "本地累計即時更新"),
    ("16.2 秒", "冷啟動", "模型載入是主要成本"),
    ("0", "敏感資料", "git 追蹤檔案掃描結果"),
]
for i, (big, label, small) in enumerate(metrics):
    x = 0.72 + i * 2.95
    rect(s, x, 1.95, 2.7, 1.55, PAPER, LINE)
    text(s, big, x + 0.2, 2.1, 2.3, 0.55, 25, GREEN_DARK, True)
    text(s, label, x + 0.2, 2.68, 2.3, 0.3, 10, INK, True)
    text(s, small, x + 0.2, 3.0, 2.3, 0.35, 8, MUTED)

text(s, "還沒解決的限制", 0.72, 3.95, 5.0, 0.4, 13, ORANGE, True)
limits = [
    "電腦要開著；休眠或 Ollama 沒開就查不到",
    "ngrok 免費網址會變，換了要更新設定",
    "只讀 RSS／摘要，沒有抓文章正文",
    "Webhook 尚未驗證 LINE 簽章",
]
for i, item in enumerate(limits):
    y = 4.42 + i * 0.48
    text(s, "—", 0.75, y, 0.3, 0.3, 12, ORANGE, True)
    text(s, item, 1.05, y, 10.8, 0.3, 11, MUTED)

rect(s, 0.72, 6.4, 11.95, 0.55, DARK, None, radius=0.18)
text(s, "LINE 端到端需要 token；交件前以同一個 /ask 流程的展示頁做回歸測試。",
     0.95, 6.46, 11.4, 0.4, 9.5, LIME, True, anchor=MSO_ANCHOR.MIDDLE)
footer(s, 6)
notes(s, "1:25–1:35｜17 個測試全過，暖機後記帳約 0.3 秒，掃描 0 金鑰。限制要主動講：電腦要開、網址會變、分類是 heuristic、Webhook 還沒驗簽章。")

# ---------------------------------------------------------------- slide 7
s = slide(INK)
text(s, "05 / NEXT", 0.72, 0.55, 5.0, 0.3, 10, GREEN, True)
text(s, "下一步：從課堂 demo\n變成每天可用的工具。", 0.72, 0.95, 7.2, 1.4, 30, WHITE, True, spacing=1.1)

roadmap = [
    ("01", "固定網域", "Cloudflare Tunnel\n取代會變的 ngrok"),
    ("02", "Webhook 簽章", "驗證 X-Line-Signature\n＋ allowlist"),
    ("03", "記帳進化", "AI 分類／預算警示\n或使用者自訂類別"),
    ("04", "檢索進化", "抓正文做 RAG\n＋雲端模型 fallback"),
]
for i, (num, head, body) in enumerate(roadmap):
    x = 0.72 + (i % 2) * 3.35
    y = 2.75 + (i // 2) * 1.65
    text(s, num, x, y, 0.5, 0.3, 10, GREEN, True)
    text(s, head, x + 0.45, y - 0.02, 2.6, 0.35, 14, WHITE, True)
    text(s, body, x + 0.45, y + 0.38, 2.7, 0.65, 9.5, SOFT, spacing=1.3)

text(s, "90 秒，", 8.7, 2.8, 3.8, 0.6, 28, LIME, True)
text(s, "讓它跑一次。", 8.7, 3.42, 3.8, 0.6, 28, WHITE, True)
text(s, "謝謝", 8.7, 4.55, 3.8, 0.9, 42, GREEN, True)
text(s, "問題與指教歡迎", 8.75, 5.55, 3.6, 0.35, 10, RGBColor(0x6F, 0x8A, 0x7B), True)

footer(s, 7, dark=True)
notes(s, "1:35–1:30｜收尾。下一步是固定網域、補 Webhook 簽章、記帳進化、檢索進化。最後說：90 秒，讓它跑一次，謝謝。")

prs.save(OUT)
print(OUT)

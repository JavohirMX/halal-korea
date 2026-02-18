"""
Generates a branded PNG timetable image for the full Ramadan month using Pillow.
Uses Inter for Latin text, Noto Naskh Arabic for Arabic script,
and arabic-reshaper + python-bidi for correct RTL glyph shaping.
Supports i18n: pass language code ('en', 'ko', 'uz') to generate localized images.
Renders at 2x resolution and downscales for crisp anti-aliased output.
"""
import io
import math
import os
import logging
from PIL import Image, ImageDraw, ImageFont
from django.conf import settings
from django.utils import translation
from django.utils.translation import gettext as _
from .ramadan_utils import is_lailatul_qadr_night

logger = logging.getLogger(__name__)

FONTS_DIR = os.path.join(settings.BASE_DIR, "static", "fonts")
INTER_REGULAR = os.path.join(FONTS_DIR, "Inter", "static", "Inter_18pt-Regular.ttf")
INTER_MEDIUM = os.path.join(FONTS_DIR, "Inter", "static", "Inter_18pt-Medium.ttf")
INTER_SEMIBOLD = os.path.join(FONTS_DIR, "Inter", "static", "Inter_18pt-SemiBold.ttf")
INTER_BOLD = os.path.join(FONTS_DIR, "Inter", "static", "Inter_18pt-Bold.ttf")
NOTO_ARABIC_REGULAR = os.path.join(FONTS_DIR, "Noto_Naskh_Arabic", "static", "NotoNaskhArabic-Regular.ttf")
NOTO_ARABIC_BOLD = os.path.join(FONTS_DIR, "Noto_Naskh_Arabic", "static", "NotoNaskhArabic-Bold.ttf")
NOTO_KR_REGULAR = os.path.join(FONTS_DIR, "Noto_Sans_KR", "static", "NotoSansKR-Regular.ttf")
NOTO_KR_MEDIUM = os.path.join(FONTS_DIR, "Noto_Sans_KR", "static", "NotoSansKR-Medium.ttf")
NOTO_KR_SEMIBOLD = os.path.join(FONTS_DIR, "Noto_Sans_KR", "static", "NotoSansKR-SemiBold.ttf")
NOTO_KR_BOLD = os.path.join(FONTS_DIR, "Noto_Sans_KR", "static", "NotoSansKR-Bold.ttf")

DEJAVU_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
DEJAVU_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

LOGO_PATH = os.path.join(settings.BASE_DIR, "static", "images", "logo-square.png")

SCALE = 2

IMG_WIDTH = 1200 * SCALE
ROW_HEIGHT = 40 * SCALE
HEADER_HEIGHT = 140 * SCALE
TABLE_HEADER_HEIGHT = 38 * SCALE
FOOTER_HEIGHT = 45 * SCALE
SIDE_PADDING = 30 * SCALE

OUTPUT_WIDTH = 1200

COLOR_BG = (255, 255, 255)
COLOR_HEADER_TOP = (6, 148, 103)
COLOR_HEADER_BOTTOM = (16, 185, 129)
COLOR_HEADER_TEXT = (255, 255, 255)
COLOR_HEADER_SUBTLE = (190, 245, 220)
COLOR_TABLE_HEADER_BG = (236, 253, 245)
COLOR_TABLE_HEADER_TEXT = (5, 150, 105)
COLOR_ROW_ALT = (249, 250, 251)
COLOR_ROW_LAILATUL_QADR = (255, 251, 235)
COLOR_ROW_FRIDAY = (255, 252, 239)
COLOR_TEXT = (55, 65, 81)
COLOR_ACCENT = (5, 150, 105)
COLOR_MUTED = (120, 130, 145)
COLOR_FRIDAY_TEXT = (180, 130, 30)
COLOR_FOOTER_BG = (243, 244, 246)
COLOR_FOOTER_TEXT = (107, 114, 128)
COLOR_BORDER = (229, 231, 235)
COLOR_DUA_BG = (240, 253, 244)
COLOR_DUA_BORDER = (167, 243, 208)
COLOR_DUA_LABEL = (5, 150, 105)
COLOR_DUA_DIVIDER = (200, 235, 215)
COLOR_LQ_STAR = (217, 119, 6)

SUHOOR_DUA_ARABIC = (
    "نويت أن أصوم صوم شهر رمضان من الفجر إلى المغرب خالصًا لله تعالى، الله أكبر"
)
SUHOOR_DUA_TRANS = (
    "Navaytu an asuvma sovma shahri Ramazona "
    "minal fajri ilal mag\u2019ribi, xolisan lillahi ta\u2019ala, Allohu akbar."
)

IFTAR_DUA_ARABIC = (
    "اللهم لك صمت وبك آمنت وعلى رزقك أفطرت فاغفر لي ما قدمت وما أخرت"
)
IFTAR_DUA_TRANS = (
    "Allohumma laka sumtu va bika amantu va a\u2019alayka tavakkaltu "
    "va \u2019ala rizqika aftartu, fag\u2019firli, ya G\u2019offaru "
    "ma qoddamtu va ma axxortu."
)

WEEKDAY_NAMES = {
    "en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    "ko": ["\uc6d4", "\ud654", "\uc218", "\ubaa9", "\uae08", "\ud1a0", "\uc77c"],
    "uz": ["Du", "Se", "Cho", "Pa", "Ju", "Sha", "Ya"],
}

MONTH_NAMES = {
    "en": {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
           7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"},
    "ko": {1: "1\uc6d4", 2: "2\uc6d4", 3: "3\uc6d4", 4: "4\uc6d4", 5: "5\uc6d4", 6: "6\uc6d4",
           7: "7\uc6d4", 8: "8\uc6d4", 9: "9\uc6d4", 10: "10\uc6d4", 11: "11\uc6d4", 12: "12\uc6d4"},
    "uz": {1: "Yan", 2: "Fev", 3: "Mar", 4: "Apr", 5: "May", 6: "Iyun",
           7: "Iyul", 8: "Avg", 9: "Sen", 10: "Okt", 11: "Noy", 12: "Dek"},
}


def _s(val):
    """Scale a value by the global SCALE factor."""
    return int(val * SCALE)


def _format_weekday(date_obj, lang):
    names = WEEKDAY_NAMES.get(lang, WEEKDAY_NAMES["en"])
    return names[date_obj.weekday()]


def _format_date_short(date_obj, lang):
    month = MONTH_NAMES.get(lang, MONTH_NAMES["en"]).get(date_obj.month, "")
    if lang == "ko":
        return f"{month} {date_obj.day}\uc77c"
    return f"{date_obj.day} {month}"


def _format_date_range(start, end, lang):
    sm = MONTH_NAMES.get(lang, MONTH_NAMES["en"]).get(start.month, "")
    em = MONTH_NAMES.get(lang, MONTH_NAMES["en"]).get(end.month, "")
    if lang == "ko":
        return f"{start.year}\ub144 {sm} {start.day}\uc77c \u2013 {em} {end.day}\uc77c"
    return f"{sm} {start.day} \u2013 {em} {end.day}, {end.year}"


def _prepare_arabic(text):
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except ImportError:
        logger.warning("arabic-reshaper or python-bidi not installed, Arabic may render incorrectly")
        return text
    except Exception as e:
        logger.warning(f"Arabic reshaping failed: {e}")
        return text


def _load_inter(weight="regular", size=14, lang="en"):
    scaled_size = size * SCALE
    if lang == "ko":
        kr_paths = {
            "regular": NOTO_KR_REGULAR,
            "medium": NOTO_KR_MEDIUM,
            "semibold": NOTO_KR_SEMIBOLD,
            "bold": NOTO_KR_BOLD,
        }
        kr_path = kr_paths.get(weight, NOTO_KR_REGULAR)
        try:
            return ImageFont.truetype(kr_path, scaled_size)
        except (OSError, IOError):
            pass

    paths = {
        "regular": INTER_REGULAR,
        "medium": INTER_MEDIUM,
        "semibold": INTER_SEMIBOLD,
        "bold": INTER_BOLD,
    }
    path = paths.get(weight, INTER_REGULAR)
    fallback = DEJAVU_BOLD if weight in ("bold", "semibold") else DEJAVU_REGULAR
    try:
        return ImageFont.truetype(path, scaled_size)
    except (OSError, IOError):
        try:
            return ImageFont.truetype(fallback, scaled_size)
        except (OSError, IOError):
            return ImageFont.load_default()


def _load_arabic(bold=False, size=18):
    scaled_size = size * SCALE
    path = NOTO_ARABIC_BOLD if bold else NOTO_ARABIC_REGULAR
    try:
        return ImageFont.truetype(path, scaled_size)
    except (OSError, IOError):
        try:
            return ImageFont.truetype(DEJAVU_REGULAR, scaled_size)
        except (OSError, IOError):
            return ImageFont.load_default()


def _load_logo(max_size=90):
    scaled_max = max_size * SCALE
    try:
        logo = Image.open(LOGO_PATH).convert("RGBA")
        logo.thumbnail((scaled_max, scaled_max), Image.LANCZOS)
        return logo
    except Exception as e:
        logger.warning(f"Could not load logo: {e}")
        return None


def _text_width(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def _draw_header_gradient(draw, width, height):
    for y_pos in range(height):
        ratio = y_pos / height
        r = int(COLOR_HEADER_TOP[0] + (COLOR_HEADER_BOTTOM[0] - COLOR_HEADER_TOP[0]) * ratio)
        g = int(COLOR_HEADER_TOP[1] + (COLOR_HEADER_BOTTOM[1] - COLOR_HEADER_TOP[1]) * ratio)
        b = int(COLOR_HEADER_TOP[2] + (COLOR_HEADER_BOTTOM[2] - COLOR_HEADER_TOP[2]) * ratio)
        draw.line([(0, y_pos), (width, y_pos)], fill=(r, g, b))


def _draw_star(draw, cx, cy, r, fill):
    points = []
    for i in range(8):
        angle = math.pi / 4 * i - math.pi / 2
        radius = r if i % 2 == 0 else r * 0.4
        points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    draw.polygon(points, fill=fill)


def _wrap_text(text, font, max_width, draw):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        if _text_width(draw, test, font) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _wrap_arabic(logical_text, font, max_width, draw):
    """Wrap logical (unprocessed) Arabic text into display-ready lines.

    Splits on word boundaries in logical order, then applies
    arabic-reshaper + bidi *per line* so each line's word order is
    correct and lines are returned in top-to-bottom reading order.
    """
    words = logical_text.split()
    lines = []
    current_words: list = []
    for word in words:
        test_words = current_words + [word]
        test_line = _prepare_arabic(" ".join(test_words))
        if _text_width(draw, test_line, font) <= max_width:
            current_words = test_words
        else:
            if current_words:
                lines.append(_prepare_arabic(" ".join(current_words)))
            current_words = [word]
    if current_words:
        lines.append(_prepare_arabic(" ".join(current_words)))
    return lines


def _measure_dua_column(draw, arabic_text, trans_text, f_arabic, f_trans, inner_w):
    label_h = _s(24)
    arabic_lines = _wrap_arabic(arabic_text, f_arabic, inner_w, draw)
    arabic_h = len(arabic_lines) * _s(28)
    gap = _s(8)
    trans_lines = _wrap_text(trans_text, f_trans, inner_w, draw)
    trans_h = len(trans_lines) * _s(18)
    return label_h + arabic_h + gap + trans_h


def generate_ramadan_timetable_image(config, city, country, calendar_data, language="en"):
    """
    Returns PNG bytes of the branded Ramadan timetable.
    Renders at 2x resolution then downscales for crisp output.
    """
    with translation.override(language):
        return _generate_image(config, city, country, calendar_data, language)


def _generate_image(config, city, country, calendar_data, lang):
    num_rows = len(calendar_data)

    f_dua_label = _load_inter("bold", 15, lang)
    f_dua_trans = _load_inter("regular", 12, lang)
    f_arabic = _load_arabic(bold=True, size=20)

    tmp_img = Image.new("RGB", (IMG_WIDTH, _s(100)), COLOR_BG)
    tmp_draw = ImageDraw.Draw(tmp_img)

    inner_w = (IMG_WIDTH // 2) - SIDE_PADDING - _s(44)
    left_h = _measure_dua_column(tmp_draw, SUHOOR_DUA_ARABIC, SUHOOR_DUA_TRANS, f_arabic, f_dua_trans, inner_w)
    right_h = _measure_dua_column(tmp_draw, IFTAR_DUA_ARABIC, IFTAR_DUA_TRANS, f_arabic, f_dua_trans, inner_w)
    dua_content_h = max(left_h, right_h)
    dua_section_height = dua_content_h + _s(40)

    img_height = (
        HEADER_HEIGHT + TABLE_HEADER_HEIGHT
        + (num_rows * ROW_HEIGHT)
        + dua_section_height + FOOTER_HEIGHT + _s(50)
    )

    img = Image.new("RGB", (IMG_WIDTH, img_height), COLOR_BG)
    draw = ImageDraw.Draw(img)

    f_title = _load_inter("bold", 28, lang)
    f_subtitle = _load_inter("medium", 16, lang)
    f_date_range = _load_inter("regular", 15, lang)
    f_brand = _load_inter("bold", 19, lang)
    f_brand_sub = _load_inter("regular", 13, lang)
    f_table_header = _load_inter("semibold", 13, lang)
    f_cell = _load_inter("regular", 13, lang)
    f_cell_accent = _load_inter("semibold", 13, lang)
    f_cell_friday = _load_inter("bold", 13, lang)
    f_footer = _load_inter("regular", 11, lang)

    # ── Header with gradient ──
    _draw_header_gradient(draw, IMG_WIDTH, HEADER_HEIGHT)

    logo = _load_logo(max_size=85)
    text_start_x = SIDE_PADDING
    if logo:
        logo_y = (HEADER_HEIGHT - logo.height) // 2
        img.paste(logo, (SIDE_PADDING, logo_y), logo)
        text_start_x = SIDE_PADDING + logo.width + _s(18)

    title_text = _("Ramadan %(hijri_year)s Timetable") % {"hijri_year": config.hijri_year}
    draw.text((text_start_x, _s(22)), title_text, fill=COLOR_HEADER_TEXT, font=f_title)
    draw.text((text_start_x, _s(56)), f"{city}, {country}", fill=COLOR_HEADER_TEXT, font=f_subtitle)

    date_range_str = _format_date_range(config.start_date, config.end_date, lang)
    draw.text((text_start_x, _s(80)), date_range_str, fill=COLOR_HEADER_SUBTLE, font=f_date_range)

    brand_text = "halal-korea.com"
    bw = _text_width(draw, brand_text, f_brand)
    draw.text((IMG_WIDTH - SIDE_PADDING - bw, _s(38)), brand_text, fill=COLOR_HEADER_TEXT, font=f_brand)
    sub_text = "Halal Korea"
    sw = _text_width(draw, sub_text, f_brand_sub)
    draw.text((IMG_WIDTH - SIDE_PADDING - sw, _s(64)), sub_text, fill=COLOR_HEADER_SUBTLE, font=f_brand_sub)

    # ── Column layout (base widths scaled) ──
    columns = [
        {"label": "#",             "width": _s(45),  "align": "center"},
        {"label": _("Date"),       "width": _s(130), "align": "left"},
        {"label": _("Day"),        "width": _s(60),  "align": "center"},
        {"label": _("Imsak"),      "width": _s(100), "align": "center", "accent": True},
        {"label": _("Fajr"),       "width": _s(100), "align": "center"},
        {"label": _("Dhuhr"),      "width": _s(100), "align": "center"},
        {"label": _("Asr"),        "width": _s(100), "align": "center"},
        {"label": _("Maghrib"),    "width": _s(110), "align": "center", "accent": True},
        {"label": _("Isha"),       "width": _s(100), "align": "center"},
    ]
    total_col_width = sum(c["width"] for c in columns)
    start_x = (IMG_WIDTH - total_col_width) // 2

    # ── Table header ──
    y = HEADER_HEIGHT
    draw.rectangle([(0, y), (IMG_WIDTH, y + TABLE_HEADER_HEIGHT)], fill=COLOR_TABLE_HEADER_BG)
    draw.line([(start_x, y + TABLE_HEADER_HEIGHT - 1),
               (start_x + total_col_width, y + TABLE_HEADER_HEIGHT - 1)],
              fill=COLOR_BORDER, width=SCALE)
    x = start_x
    for col in columns:
        cx = x + col["width"] // 2
        tw = _text_width(draw, col["label"], f_table_header)
        color = COLOR_ACCENT if col.get("accent") else COLOR_TABLE_HEADER_TEXT
        draw.text((cx - tw // 2, y + _s(11)), col["label"], fill=color, font=f_table_header)
        x += col["width"]

    # ── Data rows ──
    y += TABLE_HEADER_HEIGHT
    for day in calendar_data:
        date_obj = day["date"]
        weekday_str = _format_weekday(date_obj, lang)
        date_str = _format_date_short(date_obj, lang)
        is_lq = is_lailatul_qadr_night(day["day_number"])
        is_friday = date_obj.weekday() == 4

        if is_lq:
            row_bg = COLOR_ROW_LAILATUL_QADR
        elif is_friday:
            row_bg = COLOR_ROW_FRIDAY
        elif day["day_number"] % 2 == 0:
            row_bg = COLOR_ROW_ALT
        else:
            row_bg = COLOR_BG

        draw.rectangle([(0, y), (IMG_WIDTH, y + ROW_HEIGHT)], fill=row_bg)
        draw.line(
            [(start_x, y + ROW_HEIGHT - 1), (start_x + total_col_width, y + ROW_HEIGHT - 1)],
            fill=COLOR_BORDER,
        )

        t = day.get("timings") or {}
        cells = [
            str(day["day_number"]),
            date_str,
            weekday_str,
            t.get("Imsak", "--"),
            t.get("Fajr", "--"),
            t.get("Dhuhr", "--"),
            t.get("Asr", "--"),
            t.get("Maghrib", "--"),
            t.get("Isha", "--"),
        ]

        x = start_x
        for i, col in enumerate(columns):
            text = cells[i]

            if i == 2 and is_friday:
                font = f_cell_friday
                color = COLOR_FRIDAY_TEXT
            elif col.get("accent"):
                font = f_cell_accent
                color = COLOR_ACCENT
            else:
                font = f_cell
                color = COLOR_TEXT

            tw = _text_width(draw, text, font)
            if col["align"] == "center":
                tx = x + col["width"] // 2 - tw // 2
            elif col["align"] == "right":
                tx = x + col["width"] - tw - _s(4)
            else:
                tx = x + _s(4)

            draw.text((tx, y + _s(12)), text, fill=color, font=font)

            if i == 0 and is_lq:
                star_x = tx + tw + _s(5)
                star_y = y + ROW_HEIGHT // 2
                _draw_star(draw, star_x, star_y, _s(5), COLOR_LQ_STAR)

            x += col["width"]

        y += ROW_HEIGHT

    # ── Duas Section (auto-sized) ──
    y += _s(15)
    dua_y_start = y
    dua_box_h = dua_section_height

    draw.rounded_rectangle(
        [(SIDE_PADDING, y), (IMG_WIDTH - SIDE_PADDING, y + dua_box_h)],
        radius=_s(8), fill=COLOR_DUA_BG, outline=COLOR_DUA_BORDER, width=SCALE,
    )

    mid_x = IMG_WIDTH // 2
    draw.line([(mid_x, y + _s(12)), (mid_x, y + dua_box_h - _s(12))], fill=COLOR_DUA_DIVIDER, width=SCALE)

    left_x = SIDE_PADDING + _s(22)
    right_x = mid_x + _s(22)

    # -- Suhoor dua (left) --
    suhoor_label = _("Dua for Suhoor (Fasting Intention)")
    draw.text((left_x, y + _s(14)), suhoor_label, fill=COLOR_DUA_LABEL, font=f_dua_label)

    arabic_lines = _wrap_arabic(SUHOOR_DUA_ARABIC, f_arabic, inner_w, draw)
    ay = y + _s(40)
    for line in arabic_lines:
        # Right-align Arabic within the column (RTL)
        line_w = _text_width(draw, line, f_arabic)
        ax = left_x + inner_w - line_w
        draw.text((ax, ay), line, fill=COLOR_TEXT, font=f_arabic)
        ay += _s(28)

    trans_lines = _wrap_text(SUHOOR_DUA_TRANS, f_dua_trans, inner_w, draw)
    ty = ay + _s(8)
    for line in trans_lines:
        # Latin transliteration stays left-aligned
        draw.text((left_x, ty), line, fill=COLOR_MUTED, font=f_dua_trans)
        ty += _s(18)

    # -- Iftar dua (right) --
    iftar_label = _("Dua for Breaking Fast (Iftar)")
    draw.text((right_x, y + _s(14)), iftar_label, fill=COLOR_DUA_LABEL, font=f_dua_label)

    arabic_lines = _wrap_arabic(IFTAR_DUA_ARABIC, f_arabic, inner_w, draw)
    ay = y + _s(40)
    for line in arabic_lines:
        # Right-align Arabic within the column (RTL)
        line_w = _text_width(draw, line, f_arabic)
        ax = right_x + inner_w - line_w
        draw.text((ax, ay), line, fill=COLOR_TEXT, font=f_arabic)
        ay += _s(28)

    trans_lines = _wrap_text(IFTAR_DUA_TRANS, f_dua_trans, inner_w, draw)
    ty = ay + _s(8)
    for line in trans_lines:
        # Latin transliteration stays left-aligned
        draw.text((right_x, ty), line, fill=COLOR_MUTED, font=f_dua_trans)
        ty += _s(18)

    y = dua_y_start + dua_box_h

    # ── Footer ──
    y += _s(15)
    draw.rectangle([(0, y), (IMG_WIDTH, y + FOOTER_HEIGHT)], fill=COLOR_FOOTER_BG)
    draw.line([(0, y), (IMG_WIDTH, y)], fill=COLOR_BORDER, width=SCALE)

    footer_prefix = _(
        "Prayer times by aladhan.com"
    ) + "  \u00b7  " + _(
        "Dates per Korean Muslim Federation"
    ) + "  \u00b7  "
    draw.text((SIDE_PADDING, y + _s(8)), footer_prefix, fill=COLOR_FOOTER_TEXT, font=f_footer)
    prefix_w = _text_width(draw, footer_prefix, f_footer)
    star_fx = SIDE_PADDING + prefix_w + _s(5)
    _draw_star(draw, star_fx, y + _s(15), _s(4), COLOR_LQ_STAR)
    lq_label = "  " + _("Laylatul Qadr") + " " + _("night")
    draw.text((star_fx + _s(6), y + _s(8)), lq_label, fill=COLOR_FOOTER_TEXT, font=f_footer)

    footer_line2 = _("Generated by Halal Korea") + "  \u00b7  halal-korea.com"
    draw.text((SIDE_PADDING, y + _s(25)), footer_line2, fill=COLOR_FOOTER_TEXT, font=f_footer)

    # ── Downscale to output size ──
    output_height = int(img_height * OUTPUT_WIDTH / IMG_WIDTH)
    img = img.resize((OUTPUT_WIDTH, output_height), Image.LANCZOS)

    # ── Output ──
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()

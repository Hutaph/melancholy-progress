from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import app


ASSETS = ROOT / "docs" / "assets"
WIDTH = 940
HEIGHT = 308
README_SCALE = 2
SOCIAL_SCALE = 2
DEMO_SCALE = 1.5


def font(size: int, bold: bool = False, italic: bool = False) -> ImageFont.FreeTypeFont:
    fonts = Path("C:/Windows/Fonts")
    if bold:
        name = "seguisb.ttf"
    elif italic:
        name = "segoeuii.ttf"
    else:
        name = "segoeui.ttf"
    return ImageFont.truetype(str(fonts / name), size)


def lerp_color(start: str, end: str, ratio: float) -> tuple[int, int, int]:
    first = tuple(int(start[index : index + 2], 16) for index in (1, 3, 5))
    second = tuple(int(end[index : index + 2], 16) for index in (1, 3, 5))
    return tuple(round(a + (b - a) * ratio) for a, b in zip(first, second))


def fit_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: int,
    initial_size: int,
    *,
    bold: bool = False,
    italic: bool = False,
) -> ImageFont.FreeTypeFont:
    size = initial_size
    while size > 18:
        selected = font(size, bold=bold, italic=italic)
        if draw.textbbox((0, 0), text, font=selected)[2] <= max_width:
            return selected
        size -= 1
    return font(size, bold=bold, italic=italic)


def render_widget(
    theme_key: str,
    title: str,
    detail: str,
    ratio: float,
    quote: str | None = None,
    *,
    size: tuple[int, int] = (WIDTH, HEIGHT),
) -> Image.Image:
    theme = app.THEMES[theme_key]
    width, height = size
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    scale_x = width / WIDTH
    scale_y = height / HEIGHT
    text_scale = min(scale_x, scale_y)

    def scaled_font(size: int, *, bold: bool = False, italic: bool = False) -> ImageFont.FreeTypeFont:
        return font(max(14, round(size * text_scale)), bold=bold, italic=italic)

    def box(values: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        x1, y1, x2, y2 = values
        return (
            round(x1 * scale_x),
            round(y1 * scale_y),
            round(x2 * scale_x),
            round(y2 * scale_y),
        )

    draw.rounded_rectangle(
        box((4, 4, 936, 304)),
        radius=44,
        fill=theme.background,
        outline=theme.border,
        width=2,
    )
    draw.rounded_rectangle(
        box((24, 24, 916, 284)),
        radius=32,
        fill=theme.panel,
    )

    left = round(58 * scale_x)
    right = round(884 * scale_x)
    draw.text(
        (left, round(58 * scale_y)),
        title.upper(),
        font=fit_text(
            draw,
            title.upper(),
            round(560 * scale_x),
            max(18, round(28 * text_scale)),
            bold=True,
        ),
        fill=theme.text_muted,
    )
    percent = f"{ratio * 100:05.2f}%"
    percent_font = scaled_font(56, bold=True)
    percent_width = draw.textbbox((0, 0), percent, font=percent_font)[2]
    draw.text(
        (right - percent_width, round(54 * scale_y)),
        percent,
        font=percent_font,
        fill=theme.text_primary,
    )

    track = box((58, 132, 884, 166))
    radius = round(17 * scale_y)
    draw.rounded_rectangle(track, radius=radius, fill=theme.track)
    fill_width = max(0, round((track[2] - track[0]) * ratio))
    if fill_width:
        filled_right = track[0] + fill_width
        draw.rounded_rectangle(
            (track[0], track[1], max(filled_right, track[0] + radius * 2), track[3]),
            radius=radius,
            fill=theme.accent_start,
        )
        segment_count = min(48, max(fill_width, 1))
        for index in range(segment_count):
            segment_left = track[0] + round(fill_width * index / segment_count)
            segment_right = track[0] + round(fill_width * (index + 1) / segment_count)
            color = lerp_color(
                theme.accent_start,
                theme.accent_end,
                index / max(segment_count - 1, 1),
            )
            draw.rectangle(
                (segment_left, track[1] + 4, segment_right + 1, track[3] - 4),
                fill=color,
            )

    draw.text(
        (left, round(196 * scale_y)),
        detail,
        font=scaled_font(25),
        fill=theme.text_muted,
    )
    mood = quote or app.theme_quote(theme_key, "en")
    draw.text(
        (left, round(248 * scale_y)),
        mood,
        font=fit_text(
            draw,
            mood,
            right - left,
            max(17, round(24 * text_scale)),
            italic=True,
        ),
        fill=theme.text_faint,
    )
    return image


def backdrop(size: tuple[int, int]) -> Image.Image:
    width, height = size
    source = Image.open(ASSETS / "social-preview-background.png").convert("RGB")
    source_ratio = source.width / source.height
    target_ratio = width / height
    if source_ratio > target_ratio:
        cropped_width = round(source.height * target_ratio)
        offset = (source.width - cropped_width) // 2
        source = source.crop((offset, 0, offset + cropped_width, source.height))
    else:
        cropped_height = round(source.width / target_ratio)
        offset = (source.height - cropped_height) // 2
        source = source.crop((0, offset, source.width, offset + cropped_height))
    source = source.resize(size, Image.Resampling.LANCZOS)
    source = ImageEnhance.Brightness(source).enhance(0.4)
    return source.filter(ImageFilter.GaussianBlur(radius=1.2))


def custom_progress(title: str, days_elapsed: int, days_remaining: int) -> tuple[str, str, float]:
    total = days_elapsed + days_remaining
    ratio = days_elapsed / total
    detail = f"{days_elapsed} days elapsed   ·   {days_remaining} days remaining"
    return title, detail, ratio


def generate_social_preview() -> None:
    scale = SOCIAL_SCALE

    def point(x: int, y: int) -> tuple[int, int]:
        return round(x * scale), round(y * scale)

    def rect(values: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        return tuple(round(value * scale) for value in values)

    image = backdrop(point(1280, 640)).convert("RGBA")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(rect((80, 64, 1200, 576)), radius=round(42 * scale), fill=(6, 11, 19, 125))
    card = render_widget(
        "rainy_night",
        "JLPT N4",
        "12 days elapsed   ·   22 days remaining",
        0.3529,
        "Some nights, sorrow stays longer than the rain.",
        size=point(846, 277),
    )
    image.alpha_composite(card, point(217, 198))
    draw.text(point(106, 100), "quiet-progress", font=font(round(54 * scale), bold=True), fill="#f3f8fb")
    draw.text(
        point(110, 165),
        "A quiet Windows desktop widget for watching time pass.",
        font=font(round(23 * scale)),
        fill="#a7bac8",
    )
    draw.text(point(1090, 530), "WINDOWS", font=font(round(18 * scale), bold=True), fill="#718797")
    image = image.resize((1280, 640), Image.Resampling.LANCZOS)
    image.convert("RGB").save(ASSETS / "social-preview.png", quality=95)


def generate_themes() -> None:
    scale = README_SCALE

    def point(x: int, y: int) -> tuple[int, int]:
        return round(x * scale), round(y * scale)

    image = Image.new("RGB", point(1500, 1210), "#090e16")
    draw = ImageDraw.Draw(image)
    draw.text(point(70, 54), "Five quiet moods", font=font(round(46 * scale), bold=True), fill="#f3f8fb")
    draw.text(
        point(73, 112),
        "Choose a theme for the days that do not need to be loud.",
        font=font(round(24 * scale)),
        fill="#a7bac8",
    )
    cards = []
    details = "150 days elapsed   ·   214 days remaining"
    for key in app.THEMES:
        card = render_widget(
            key,
            app.theme_label(key, "en"),
            details,
            0.4128,
            app.theme_quote(key, "en"),
            size=point(650, 213),
        )
        cards.append((key, card))
    positions = [(70, 190), (780, 190), (70, 470), (780, 470), (425, 750)]
    for (key, card), position in zip(cards, positions):
        scaled_position = point(*position)
        image.paste(card, scaled_position, card)
        draw.text(
            point(position[0] + 18, position[1] + 232),
            app.theme_label(key, "en"),
            font=font(round(23 * scale), bold=True),
            fill="#c7d2de",
        )
    image.save(ASSETS / "themes.png", quality=95)


def generate_milestones() -> None:
    scale = README_SCALE

    def point(x: int, y: int) -> tuple[int, int]:
        return round(x * scale), round(y * scale)

    def rect(values: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        return tuple(round(value * scale) for value in values)

    image = backdrop(point(1500, 960)).convert("RGBA")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(rect((56, 55, 1444, 905)), radius=round(48 * scale), fill=(6, 11, 19, 185))
    draw.text(point(110, 105), "Custom milestones", font=font(round(50 * scale), bold=True), fill="#f3f8fb")
    draw.text(
        point(113, 168),
        "Track the chapters that matter to you, not only the calendar.",
        font=font(round(25 * scale)),
        fill="#a7bac8",
    )
    milestones = [
        (
            "JLPT N4",
            "12 days elapsed   ·   22 days remaining",
            0.3529,
            "rainy_night",
            "Some nights, sorrow stays longer than the rain.",
        ),
        (
            "Ship v1.0",
            "38 days elapsed   ·   7 days remaining",
            0.8444,
            "violet_memory",
            "Time does not heal; it only teaches us how to stay silent.",
        ),
    ]
    for index, (title, detail, ratio, theme, quote) in enumerate(milestones):
        card = render_widget(theme, title, detail, ratio, quote, size=point(1000, 328))
        image.alpha_composite(card, point(92, 245 + index * 320))
    menu_x = round(1135 * scale)
    draw.rounded_rectangle(rect((1135, 276, 1390, 616)), radius=round(20 * scale), fill="#17212e", outline="#34495e")
    draw.text((menu_x + round(24 * scale), round(304 * scale)), "Saved intervals", font=font(round(24 * scale), bold=True), fill="#f1f6fa")
    items = ["●  JLPT N4", "○  Ship v1.0", "+  Add interval", "   Edit selected", "   Delete selected"]
    for index, item in enumerate(items):
        color = "#73a9bf" if index == 0 else "#a7bac8"
        draw.text(
            (menu_x + round(24 * scale), round((358 + index * 46) * scale)),
            item,
            font=font(round(20 * scale)),
            fill=color,
        )
    image.convert("RGB").save(ASSETS / "custom-milestones.png", quality=95)


def generate_demo() -> None:
    scale = DEMO_SCALE

    def point(x: int, y: int) -> tuple[int, int]:
        return round(x * scale), round(y * scale)

    canvas_size = point(1120, 470)
    frames = []
    sequence = [
        ("rainy_night", "YEAR PROGRESS 2026", "150 days elapsed   ·   214 days remaining", 0.4128),
        ("cold_ash", "TODAY'S PROGRESS", "17 hr 21 min elapsed   ·   6 hr 38 min remaining", 0.7233),
        ("old_sunset", "JLPT N4", "12 days elapsed   ·   22 days remaining", 0.3529),
        ("deep_sea", "SHIP V1.0", "38 days elapsed   ·   7 days remaining", 0.8444),
        ("violet_memory", "STILL COUNTING", "Some chapters take longer to close.", 0.6120),
    ]
    for theme_key, title, detail, ratio in sequence:
        for _ in range(4):
            frame = backdrop(canvas_size).convert("RGBA")
            overlay = Image.new("RGBA", canvas_size, (5, 9, 16, 95))
            frame.alpha_composite(overlay)
            widget = render_widget(
                theme_key,
                title,
                detail,
                ratio,
                app.theme_quote(theme_key, "en"),
                size=point(940, 308),
            )
            frame.alpha_composite(widget, point(90, 82))
            frames.append(frame.convert("P", palette=Image.Palette.ADAPTIVE, colors=192))
    frames[0].save(
        ASSETS / "demo.gif",
        save_all=True,
        append_images=frames[1:],
        duration=600,
        loop=0,
        optimize=True,
        disposal=2,
    )


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    generate_social_preview()
    generate_themes()
    generate_milestones()
    generate_demo()
    for output in ("social-preview.png", "themes.png", "custom-milestones.png", "demo.gif"):
        path = ASSETS / output
        print(f"{output}: {path.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()

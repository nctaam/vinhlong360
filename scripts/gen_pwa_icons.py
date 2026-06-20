"""U2.1 — Generate PWA icons from favicon design.

Creates icon-192.png, icon-512.png, maskable-192.png, maskable-512.png,
and apple-touch-icon.png in web-nuxt/public/icons/.
"""
from PIL import Image, ImageDraw, ImageFont
import os

ICON_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "web-nuxt", "public", "icons")
BG_COLOR = (156, 61, 34)    # #9C3D22
TEXT_COLOR = (250, 245, 235) # #FAF5EB


def draw_icon(size, padding_ratio=0.0, corner_ratio=0.22):
    """Draw the VL icon at given size. padding_ratio adds safe zone for maskable."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    pad = int(size * padding_ratio)
    inner = size - 2 * pad
    radius = int(inner * corner_ratio)

    draw.rounded_rectangle(
        [pad, pad, pad + inner - 1, pad + inner - 1],
        radius=radius,
        fill=BG_COLOR
    )

    font_size = int(inner * 0.44)
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except (OSError, IOError):
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", font_size)
        except (OSError, IOError):
            font = ImageFont.load_default()

    text = "VL"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (size - tw) / 2
    y = (size - th) / 2 - bbox[1]
    draw.text((x, y), text, fill=TEXT_COLOR, font=font)

    return img


def draw_maskable(size):
    """Maskable icon: full bleed background with safe zone padding."""
    img = Image.new("RGBA", (size, size), BG_COLOR)
    draw = ImageDraw.Draw(img)

    font_size = int(size * 0.30)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", font_size)
    except (OSError, IOError):
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except (OSError, IOError):
            font = ImageFont.load_default()

    text = "VL"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (size - tw) / 2
    y = (size - th) / 2 - bbox[1]
    draw.text((x, y), text, fill=TEXT_COLOR, font=font)

    return img


def main():
    os.makedirs(ICON_DIR, exist_ok=True)

    icons = {
        "icon-192.png": draw_icon(192),
        "icon-512.png": draw_icon(512),
        "maskable-192.png": draw_maskable(192),
        "maskable-512.png": draw_maskable(512),
        "apple-touch-icon.png": draw_icon(180, padding_ratio=0.0, corner_ratio=0.0),
    }

    for name, img in icons.items():
        path = os.path.join(ICON_DIR, name)
        img.save(path, "PNG", optimize=True)
        fsize = os.path.getsize(path)
        print(f"  {name}: {img.size[0]}x{img.size[1]} ({fsize:,} bytes)")

    print(f"\nAll icons saved to {ICON_DIR}")


if __name__ == "__main__":
    main()

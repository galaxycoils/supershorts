"""Generate high-quality 400x400 character avatar images for each SuperShorts character."""
import math
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUTPUT_DIR = Path(__file__).parent.parent / "static" / "img"

CHARACTERS = {
    "adam": {
        "label": "A",
        "archetype": "Architect",
        "dark": (30, 58, 95),
        "light": (74, 144, 217),
    },
    "antoni": {
        "label": "An",
        "archetype": "Analyst",
        "dark": (26, 64, 64),
        "light": (45, 212, 191),
    },
    "amy": {
        "label": "Am",
        "archetype": "Runner",
        "dark": (74, 26, 0),
        "light": (249, 115, 22),
    },
    "arnold": {
        "label": "Ar",
        "archetype": "Guardian",
        "dark": (26, 58, 26),
        "light": (34, 197, 94),
    },
    "rachel": {
        "label": "R",
        "archetype": "Weaver",
        "dark": (45, 26, 74),
        "light": (168, 85, 247),
    },
    "joe": {
        "label": "J",
        "archetype": "Engineer",
        "dark": (58, 42, 0),
        "light": (234, 179, 8),
    },
    "kristin": {
        "label": "K",
        "archetype": "Visionary",
        "dark": (74, 26, 45),
        "light": (236, 72, 153),
    },
}

SIZE = 400
FONT_SIZE_LETTER = 140
FONT_SIZE_ARCHETYPE = 28
CIRCLE_RADIUS = 175
OUTLINE_WIDTH = 6


def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def make_radial_gradient(size, center_color, edge_color):
    """Create a radial gradient image from center_color to edge_color."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 255))
    cx, cy = size / 2, size / 2
    max_dist = math.sqrt(cx**2 + cy**2)
    pixels = img.load()
    for y in range(size):
        for x in range(size):
            dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            t = min(dist / max_dist, 1.0)
            r, g, b = lerp_color(center_color, edge_color, t)
            pixels[x, y] = (r, g, b, 255)
    return img


def make_circular_mask(size, radius, cx, cy):
    """Return a mask image with a filled white circle."""
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse(
        (cx - radius, cy - radius, cx + radius, cy + radius),
        fill=255,
    )
    return mask


def get_font(size):
    """Try to load a bold system font; fall back to default."""
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/liberation/LiberationSans-Bold.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def generate_avatar(name: str, cfg: dict) -> Path:
    dark = cfg["dark"]
    light = cfg["light"]
    label = cfg["label"]
    archetype = cfg["archetype"]

    # Radial gradient background: light center fading to dark edges
    bg = make_radial_gradient(SIZE, light, dark)

    # Circular avatar mask (clip everything outside the circle)
    cx, cy = SIZE // 2, SIZE // 2
    circle_mask = make_circular_mask(SIZE, CIRCLE_RADIUS, cx, cy)

    # Apply circular clip to background
    result = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    result.paste(bg, mask=circle_mask)

    draw = ImageDraw.Draw(result)

    # White circle outline
    draw.ellipse(
        (
            cx - CIRCLE_RADIUS,
            cy - CIRCLE_RADIUS,
            cx + CIRCLE_RADIUS,
            cy + CIRCLE_RADIUS,
        ),
        outline=(255, 255, 255, 220),
        width=OUTLINE_WIDTH,
    )

    # Center letter(s)
    font_letter = get_font(FONT_SIZE_LETTER)
    # Measure text for centering
    bbox = draw.textbbox((0, 0), label, font=font_letter)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = cx - tw // 2 - bbox[0]
    ty = cy - th // 2 - bbox[1] - 18  # slight upward nudge to leave room for archetype

    # Drop shadow
    shadow_offset = 4
    draw.text(
        (tx + shadow_offset, ty + shadow_offset),
        label,
        font=font_letter,
        fill=(0, 0, 0, 120),
    )
    # Letter
    draw.text((tx, ty), label, font=font_letter, fill=(255, 255, 255, 255))

    # Archetype label at bottom of circle
    font_arch = get_font(FONT_SIZE_ARCHETYPE)
    abbox = draw.textbbox((0, 0), archetype.upper(), font=font_arch)
    atw = abbox[2] - abbox[0]
    ath = abbox[3] - abbox[1]
    ax = cx - atw // 2 - abbox[0]
    ay = cy + CIRCLE_RADIUS - ath - 28

    # Pill background behind archetype text
    pad_x, pad_y = 14, 6
    pill_x0 = ax - pad_x + abbox[0]
    pill_y0 = ay - pad_y + abbox[1]
    pill_x1 = pill_x0 + atw + pad_x * 2
    pill_y1 = pill_y0 + ath + pad_y * 2
    pill_radius = (pill_y1 - pill_y0) // 2
    draw.rounded_rectangle(
        (pill_x0, pill_y0, pill_x1, pill_y1),
        radius=pill_radius,
        fill=(0, 0, 0, 140),
    )
    draw.text((ax, ay), archetype.upper(), font=font_arch, fill=(255, 255, 255, 230))

    # Composite onto white background so PNG looks correct in browsers
    final = Image.new("RGBA", (SIZE, SIZE), (255, 255, 255, 0))
    final.paste(result, mask=result.split()[3])

    out_path = OUTPUT_DIR / f"{name}_avatar.png"
    final.save(out_path, format="PNG", optimize=True)
    size_kb = out_path.stat().st_size // 1024
    print(f"  {name:10s} -> {out_path.name}  ({size_kb} KB)")
    return out_path


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Generating {len(CHARACTERS)} avatars to {OUTPUT_DIR}/")
    for name, cfg in CHARACTERS.items():
        generate_avatar(name, cfg)
    print("Done.")


if __name__ == "__main__":
    main()

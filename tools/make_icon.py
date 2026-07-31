"""Render the app's own brand mark to a multi-size .ico for the desktop shortcut.

The mark is the SVG in webapp/static/index.html: three rounded squares (two above, one
below) joined by connectors, white on the brand purple. Drawing it with PIL rather than
shipping a converted screenshot keeps it crisp at 16px, which is the size Windows actually
uses in the taskbar.
"""
from PIL import Image, ImageDraw
from pathlib import Path
import sys

OUT = Path(sys.argv[1])
PURPLE_TOP = (124, 92, 246)      # matches the gradient in style.css
PURPLE_BOT = (99, 70, 232)

SS = 8                            # supersample factor, then downscale for clean edges
SIZES = [256, 128, 64, 48, 32, 16]


def draw(size_px: int) -> Image.Image:
    S = size_px * SS
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # rounded-square background with a vertical gradient
    grad = Image.new("RGB", (1, S))
    for y in range(S):
        t = y / max(S - 1, 1)
        grad.putpixel((0, y), tuple(
            round(PURPLE_TOP[i] + (PURPLE_BOT[i] - PURPLE_TOP[i]) * t) for i in range(3)))
    grad = grad.resize((S, S))
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, S - 1, S - 1], radius=int(S * 0.22), fill=255)
    img.paste(grad, (0, 0), mask)

    # the glyph, in the SVG's own 24-unit coordinate space, inset so it breathes
    pad = S * 0.19
    span = S - 2 * pad
    u = span / 24.0
    def X(v): return pad + v * u

    w = max(1, int(u * 1.9))                      # stroke width, as in the SVG
    r = u * 1.5
    for (x, y) in ((3, 3), (14, 3), (8.5, 14)):
        d.rounded_rectangle([X(x), X(y), X(x + 7), X(y + 7)], radius=r,
                            outline=(255, 255, 255, 255), width=w)

    # connectors: down from each top square, across to the centre, then down to the lower one
    line = lambda pts: d.line([(X(a), X(b)) for a, b in pts], fill=(255, 255, 255, 255),
                              width=w, joint="curve")
    line([(6.5, 10), (6.5, 12.5), (12, 12.5)])
    line([(17.5, 10), (17.5, 12.5), (12, 12.5)])
    line([(12, 12.5), (12, 14)])

    return img.resize((size_px, size_px), Image.LANCZOS)


frames = [draw(s) for s in SIZES]
OUT.parent.mkdir(parents=True, exist_ok=True)
frames[0].save(OUT, format="ICO", sizes=[(s, s) for s in SIZES])
print(f"wrote {OUT}  sizes={SIZES}  bytes={OUT.stat().st_size}")

# Linux .desktop entries want a PNG, not an .ico
png = Path(str(OUT).replace(".ico", ".png"))
draw(256).save(png)
print(f"wrote {png}")

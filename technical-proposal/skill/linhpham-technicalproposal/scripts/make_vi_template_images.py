# -*- coding: utf-8 -*-
"""Build the Vietnamese versions of the pictures the proposal template ships.

The template's process pictures (Agile, development workflow, CI/CD, branching model, testing
pyramid) carry English text inside the image, so a Vietnamese proposal translated every
paragraph and still showed English figures. This script keeps each picture exactly as drawn
(boxes, arrows, colours) and replaces only the text: it finds the ink inside each listed region,
paints it out with the region's own background colour and writes the Vietnamese text in the same
place. Terms the Vietnamese document also keeps in English (Sprint Review, Pull Request, UAT,
Test Planning...) stay as they are, so a figure and its paragraph use the same words.

Pictures with only such terms (the environment strip, the testing-process flow) are not listed
and stay unchanged.

Run after the template changes:  python make_vi_template_images.py
Writes templates/vi/<sha1-12 of the original picture>.<ext> and templates/vi/index.json;
translate_vi.py swaps a picture whose bytes hash to a listed key.
"""
import hashlib
import io
import json
import sys
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE.parent / "templates" / "proposal_template.docx"
OUT = HERE.parent / "templates" / "vi"

FONTS = {
    "sans": ("arial.ttf", "arialbd.ttf"),
    "segoe": ("segoeui.ttf", "seguisb.ttf"),
    "serif": ("times.ttf", "timesbd.ttf"),
}


def font(family, size, bold=False):
    name = FONTS[family][1 if bold else 0]
    for root in ("C:/Windows/Fonts/", "/usr/share/fonts/truetype/msttcorefonts/",
                 "/usr/share/fonts/truetype/dejavu/"):
        p = Path(root) / name
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.truetype("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", size)


# region = (x0, y0, x1, y1) around the English text (approximate: the ink inside is measured),
# text (use \n for lines), family, size px, bold, colour, align ("c"|"l"|"r"), rotate degrees
# (counter-clockwise, for slanted labels), segments (list of (text, colour)) for mixed colour.
JOBS = {
    # Agile methodology
    "bed718792b40": [
        ((114, 318, 541, 384), "Đầu vào từ người dùng cuối, đội dự án,\nkhách hàng và các bên liên quan",
         "sans", 25, False, "#000000", "c", 0, {"avail": 470}),
        ((1255, 270, 1455, 308), "Sprint 2 tuần", "sans", 26, False, "#000000", "c", 0),
    ],
    # Development workflow (swimlanes)
    "e0b9ad96d051": [
        ((240, 60, 420, 96), "Phân tích task", "segoe", 22, False, "#333333", "c", 0),
        ((240, 690, 420, 727), "Phân tích task", "segoe", 22, False, "#333333", "c", 0),
        ((540, 60, 680, 96), "Thiết kế", "segoe", 22, False, "#333333", "c", 0),
        ((540, 690, 680, 727), "Thiết kế", "segoe", 22, False, "#333333", "c", 0),
        ((795, 45, 1035, 110), "Tạo branch mới\ntừ branch DEV", "segoe", 22, False, "#333333", "c", 0),
        ((628, 194, 690, 219), "Lỗi", "segoe", 16, False, "#333333", "c", 0),
        ((443, 231, 494, 254), "Đạt", "segoe", 16, False, "#333333", "c", 0),
        ((240, 226, 420, 294), "Tạo\nPull Request", "segoe", 22, False, "#333333", "c", 0),
        ((1362, 676, 1540, 744), "Tạo\nPull Request", "segoe", 22, False, "#333333", "c", 0),
        ((800, 243, 985, 279), "Chạy unit test", "segoe", 22, False, "#333333", "c", 0),
        ((1072, 243, 1272, 279), "Viết unit test", "segoe", 22, False, "#333333", "c", 0),
        ((1360, 243, 1543, 279), "Bắt đầu code", "segoe", 22, False, "#333333", "c", 0),
        ((694, 371, 758, 394), "Từ chối", "segoe", 16, False, "#333333", "l", 0),
        ((828, 835, 890, 859), "Từ chối", "segoe", 16, False, "#333333", "r", 0),
        ((863, 449, 942, 473), "Duyệt", "segoe", 16, False, "#333333", "r", 0),
        ((773, 917, 852, 941), "Duyệt", "segoe", 16, False, "#333333", "r", 0),
        ((955, 445, 1158, 509), "Merge code vào\nbranch DEV", "segoe", 22, False, "#333333", "c", 0),
        ((230, 915, 430, 979), "Merge code vào\nbranch DEV", "segoe", 22, False, "#333333", "c", 0),
        ((1176, 631, 1212, 653), "Có", "segoe", 16, False, "#333333", "c", 0),
        ((1251, 679, 1282, 701), "Không", "segoe", 16, False, "#333333", "l", 0, {"avail": 80}),
        ((1093, 745, 1243, 769), "Lỗi back-end?", "segoe", 16, False, "#333333", "c", 0),
        ((800, 678, 978, 742), "Bắt đầu code\nfront-end", "segoe", 22, False, "#333333", "c", 0),
    ],
    # CI/CD pipeline
    "f64d8f46bc1c": [
        ((345, 70, 1085, 92), "Từ Pull Request tới Production · chặn bởi test tự động, SAST, quét dependency và quét image",
         "segoe", 15, False, "#5f6b7a", "c", 0),
        ((205, 199, 290, 227), "≥ 2 approval\nreview chéo", "segoe", 11, False, "#333333", "c", 0),
        ((395, 196, 503, 212), "kiểm tra code style", "segoe", 11, False, "#333333", "c", 0),
        ((693, 200, 776, 215), "chất lượng code", "segoe", 11, False, "#333333", "c", 0),
        ((830, 196, 927, 212), "quét bảo mật", "segoe", 11, False, "#333333", "c", 0),
        ((972, 200, 1073, 215), "quét lỗ hổng", "segoe", 11, False, "#333333", "c", 0),
        ((1118, 199, 1215, 224), "build container\nbase đã hardened", "segoe", 11, False, "#333333", "c", 0),
        ((1262, 199, 1362, 215), "quét + ký image", "segoe", 11, False, "#333333", "c", 0),
        ((188, 433, 306, 459), "reconcile theo\ndesired state trong Git", "segoe", 11, False, "#333333", "c", 0),
        ((440, 430, 513, 454), "tự deploy\nsmoke test", "segoe", 11, False, "#333333", "c", 0),
        ((1228, 430, 1340, 454), "blue-green / canary\ntự rollback", "segoe", 11, False, "#333333", "c", 0),
        ((436, 564, 1006, 580),
         "Khi lỗi: bất kỳ cổng CI nào hoặc canary suy giảm → tự rollback → báo developer qua comment PR + chat",
         "segoe", 11, False, "#c62828", "c", 0),
    ],
    # Branching model
    "c0fec956029a": [
        ((2, 246, 158, 314), "Tạo branch mới\nkhi bắt đầu\ntính năng mới", "serif", 17, False, "#000000", "r", 0),
        ((0, 343, 158, 412), "Merge code vào\nbranch DEV\nkhi xong tính năng", "serif", 17, False, "#000000", "r", 0),
        ((585, 178, 747, 248), "Tạo branch hotfix\nđể sửa bug\ntrên Production", "serif", 17, False, "#000000", "r", 0),
        ((350, 331, 522, 377), [("Merge ", "#000000"), ("HOTFIX", "#e53935"), (" vào\nbranch DEV", "#000000")],
         "serif", 17, False, "#000000", "l", 0),
        ((815, 331, 942, 377), "Merge vào\nbranch Master", "serif", 17, False, "#000000", "c", 0),
        ((360, 444, 560, 497), "Sprint release lên Staging", "serif", 17, False, "#000000", "c", -8,
         {"clear_line": ((362, 458), (556, 486), 13)}),
        ((405, 561, 548, 630), "Merge code vào\nbranch Master\nđể release lên STA", "serif", 17, False, "#000000", "r", 0),
    ],
    # Testing pyramid
    "335420824629": [
        ((285, 88, 500, 130), "Kiểm thử thủ công", "segoe", 26, False, "#1a2a4a", "c", 0),
        ((80, 166, 165, 202), "Cao", "segoe", 28, False, "#ff6b6b", "c", 0),
        ((98, 1030, 168, 1066), "Thấp", "segoe", 28, False, "#ff6b6b", "c", 0),
        ((160, 515, 305, 581), "THỜI GIAN\nthực thi", "segoe", 21, True, "#1b6b3a", "l", 0),
        ((826, 233, 946, 271), "KHÁCH HÀNG", "segoe", 27, True, "#1a2a4a", "c", 0, {"avail": 230}),
        ((1162, 568, 1318, 606), "ĐỘI QA", "segoe", 27, True, "#1a2a4a", "c", 0),
        ((1240, 708, 1360, 826), "BẮT ĐẦU TEST", "segoe", 19, True, "#1a2a4a", "c", 40,
         {"clear_line": ((1247, 815), (1357, 719), 14)}),
        ((424, 1140, 760, 1182), "Kiểm thử hệ thống hoàn chỉnh", "segoe", 29, False, "#8a94a6", "l", 0, {"avail": 560}),
        ((484, 1245, 840, 1287), "Kiểm thử toàn bộ hệ thống", "segoe", 29, False, "#8a94a6", "l", 0),
        ((572, 1350, 1036, 1392), "Kiểm thử các thành phần đã tích hợp", "segoe", 29, False, "#8a94a6", "l", 0),
    ],
}


def background(im, box):
    """The colour around the text: the most common colour on the region's border."""
    x0, y0, x1, y1 = box
    px = []
    for x in range(x0, x1):
        px += [im.getpixel((x, y0)), im.getpixel((x, y1 - 1))]
    for y in range(y0, y1):
        px += [im.getpixel((x0, y)), im.getpixel((x1 - 1, y))]
    return max(set(px), key=px.count)


def ink_box(im, box, bg):
    """Bounding box of the pixels in the region that differ clearly from its background."""
    x0, y0, x1, y1 = box
    xs, ys = [], []
    for y in range(y0, y1):
        for x in range(x0, x1):
            p = im.getpixel((x, y))
            if sum(abs(a - b) for a, b in zip(p, bg)) > 90:
                xs.append(x)
                ys.append(y)
    if not xs:
        return box
    return min(xs), min(ys), max(xs) + 1, max(ys) + 1


def draw_lines(d, lines, f, x0, x1, cy, align, colour, spacing):
    """lines: list of lists of (text, colour) segments."""
    lh = f.size + spacing
    top = cy - lh * len(lines) / 2 + spacing / 2
    for k, segs in enumerate(lines):
        w = sum(d.textlength(t, font=f) for t, _c in segs)
        x = x0 if align == "l" else (x1 - w if align == "r" else (x0 + x1 - w) / 2)
        y = top + k * lh
        for t, c in segs:
            d.text((x, y), t, font=f, fill=c or colour)
            x += d.textlength(t, font=f)


def as_lines(text, colour):
    if isinstance(text, str):
        return [[(line, colour)] for line in text.split("\n")]
    lines, cur = [], []
    for t, c in text:
        parts = t.split("\n")
        for i, part in enumerate(parts):
            if i:
                lines.append(cur)
                cur = []
            if part:
                cur.append((part, c))
    lines.append(cur)
    return lines


def replace(im, job):
    box, text, family, size, bold, colour, align, rot = job[:8]
    opts = job[8] if len(job) > 8 else {}
    im = im.convert("RGB")
    bg = background(im, box)
    d = ImageDraw.Draw(im)
    if opts.get("clear_line"):
        # A slanted label: clear a band along its baseline, not the box around it, which
        # would also take the arrow or bracket it sits next to.
        (ax, ay), (bx, by), hh = opts["clear_line"]
        L = ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5
        nx, ny = -(by - ay) / L * hh, (bx - ax) / L * hh
        d.polygon([(ax - nx, ay - ny), (bx - nx, by - ny), (bx + nx, by + ny), (ax + nx, ay + ny)], fill=bg)
        mx, my = (ax + bx) / 2 - nx * 0.15, (ay + by) / 2 - ny * 0.15
        ib = (mx - 1, my - 1, mx + 1, my + 1)
    else:
        ib = ink_box(im, box, bg)
        d.rectangle((ib[0] - 2, ib[1] - 2, ib[2] + 2, ib[3] + 2), fill=bg)
    lines = as_lines(text, colour)
    f = font(family, size, bold)
    avail = opts.get("avail") or (max(box[2] - box[0], ib[2] - ib[0]) if not rot else 10 ** 6)
    while size > 8 and max(sum(d.textlength(t, font=f) for t, _ in l) for l in lines) > avail:
        size -= 1
        f = font(family, size, bold)
    cy = (ib[1] + ib[3]) / 2
    if not rot:
        x0 = box[0] if align != "r" else box[0]
        x1 = box[2] if align != "l" else box[2]
        if align == "r":
            x1 = ib[2]
        elif align == "l":
            x0 = ib[0]
        draw_lines(d, lines, f, x0, x1, cy, align, colour, max(3, size // 5))
        return im
    # slanted label: draw on its own layer, rotate, paste centred on the old text
    w = int(max(sum(d.textlength(t, font=f) for t, _ in l) for l in lines)) + 10
    h = int((f.size + 4) * len(lines)) + 10
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw_lines(ImageDraw.Draw(layer), lines, f, 0, w, h / 2, "c", colour, 4)
    layer = layer.rotate(rot, expand=True, resample=Image.BICUBIC)
    cx = (ib[0] + ib[2]) / 2
    im.paste(layer, (int(cx - layer.width / 2), int(cy - layer.height / 2)), layer)
    return im


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    d = Document(str(TEMPLATE))
    done = {}
    for blip in d.element.body.iter(qn("a:blip")):
        part = d.part.rels[blip.get(qn("r:embed"))].target_part
        key = hashlib.sha1(part.blob).hexdigest()[:12]
        if key not in JOBS or key in done:
            continue
        src = Image.open(io.BytesIO(part.blob))
        fmt = src.format or "PNG"
        im = src.convert("RGB")
        for job in JOBS[key]:
            im = replace(im, job)
        ext = "jpg" if fmt == "JPEG" else "png"
        out = OUT / f"{key}.{ext}"
        im.save(out, format=fmt, quality=95) if fmt == "JPEG" else im.save(out, format="PNG")
        done[key] = {"file": out.name, "template_part": part.partname, "format": fmt}
        print(f"{key}  {part.partname}  -> {out.name}")
    missing = sorted(set(JOBS) - set(done))
    (OUT / "index.json").write_text(json.dumps(done, indent=2), encoding="utf-8")
    if missing:
        sys.exit(f"template pictures not found (template changed?): {missing}")


if __name__ == "__main__":
    main()

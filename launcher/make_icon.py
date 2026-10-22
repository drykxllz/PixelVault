"""Generate icon.ico — the Game Launcher desktop icon.

Run with:
    python make_icon.py            # writes icon.ico using style "a"
    python make_icon.py b          # writes style "b"
    python make_icon.py compare    # writes a side-by-side preview of all styles

Styles:
    a = layered gradient card on a dark glassy tile (default)
    b = minimal neon play glyph with an ambient glow
    c = bento grid of vivid tiles with a floating play badge

Everything is drawn with pygame at 1024px and downscaled to each icon size,
so there are no extra dependencies.
"""

import math
import os
import random
import struct
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

ICON_PATH = Path(__file__).with_name("icon.ico")
PREVIEW_PATH = Path(__file__).with_name("icon.png")
COMPARE_PATH = Path(r"C:\Users\steph\AppData\Local\Temp\opencode\icon_compare.png")
SIZES = [16, 24, 32, 48, 64, 128, 256]
MASTER = 1024

BG_TOP = (11, 13, 19)
BG_BOTTOM = (21, 27, 41)
VIOLET = (124, 92, 255)
BLUE = (61, 139, 255)
MINT = (0, 229, 192)
WHITE = (255, 255, 255)


# --- small helpers ---------------------------------------------------------

def lerp(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def gradient_surface(w, h, colors, angle=-35):
    """Diagonal multi-stop gradient cropped to w x h."""
    diag = int(math.hypot(w, h)) + 4
    big = pygame.Surface((diag, diag), pygame.SRCALPHA)
    segments = len(colors) - 1
    for y in range(diag):
        t = y / (diag - 1) * segments
        index = min(int(t), segments - 1)
        color = lerp(colors[index], colors[index + 1], t - index)
        pygame.draw.line(big, color, (0, y), (diag, y))
    big = pygame.transform.rotate(big, angle)
    rect = pygame.Rect(0, 0, w, h)
    rect.center = big.get_rect().center
    return big.subsurface(rect).copy()


def radial_glow(canvas, center, radius, color, peak, falloff=2.2):
    """Soft additive glow sprite."""
    surface = pygame.Surface((canvas, canvas), pygame.SRCALPHA)
    cx, cy = center
    for y in range(canvas):
        for x in range(canvas):
            d = math.hypot(x - cx, y - cy) / radius
            if d >= 1:
                continue
            strength = (1 - d) ** falloff * peak
            surface.set_at((x, y), (
                round(color[0] * strength),
                round(color[1] * strength),
                round(color[2] * strength),
                255,
            ))
    return surface


def grain(size, alpha=8):
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    rng = random.Random(7)
    for y in range(size):
        for x in range(size):
            v = rng.randint(0, 255)
            surface.set_at((x, y), (v, v, v, alpha))
    return surface


def rounded_mask(size, radius):
    mask = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, size, size),
                     border_radius=radius)
    return mask


def play_points(cx, cy, w, h):
    return [(cx - w / 2, cy - h / 2),
            (cx - w / 2, cy + h / 2),
            (cx + w / 2, cy)]


def draw_play(surface, cx, cy, w, h, color, tip):
    points = play_points(cx, cy, w, h)
    pygame.draw.polygon(surface, color, points)
    for x, y in points:
        pygame.draw.circle(surface, color, (int(x), int(y)), tip)


def make_base(size, glow_scale=1.0):
    """Night gradient + ambient blooms + film grain."""
    tile = pygame.Surface((size, size), pygame.SRCALPHA)
    for y in range(size):
        pygame.draw.line(tile, lerp(BG_TOP, BG_BOTTOM, y / (size - 1)),
                         (0, y), (size, y))

    blooms = (
        (0.22, 0.20, 0.55, VIOLET, 0.55 * glow_scale),
        (0.82, 0.86, 0.48, (0, 205, 255), 0.32 * glow_scale),
    )
    for cx, cy, r, color, peak in blooms:
        glow = radial_glow(256, (cx * 256, cy * 256), r * 256, color, peak)
        tile.blit(pygame.transform.smoothscale(glow, (size, size)), (0, 0),
                  special_flags=pygame.BLEND_RGB_ADD)

    tile.blit(pygame.transform.smoothscale(grain(128), (size, size)), (0, 0))
    return tile


def finish(tile, size):
    """Outer glass rim then squircle silhouette."""
    outer = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.rect(outer, (255, 255, 255, 32), (1, 1, size - 2, size - 2),
                     width=max(2, size // 350),
                     border_radius=int(size * 0.235))
    tile.blit(outer, (0, 0))
    tile.blit(rounded_mask(size, int(size * 0.235)), (0, 0),
              special_flags=pygame.BLEND_RGBA_MULT)
    return tile


# --- style a: layered gradient card ---------------------------------------

def render_layered():
    s = MASTER
    tile = make_base(s)

    front_w = int(s * 0.54)
    front_rect = pygame.Rect(0, 0, front_w, front_w)
    front_rect.center = (s // 2, s // 2)

    # Soft shadow beneath the stack.
    mini = pygame.Surface((256, 256), pygame.SRCALPHA)
    shadow_rect = pygame.Rect(0, 0, front_w // 4, front_w // 4)
    shadow_rect.center = (front_rect.centerx // 4, front_rect.centery // 4 + 10)
    pygame.draw.rect(mini, (0, 0, 0, 165), shadow_rect,
                     border_radius=int(front_w * 0.20) // 4)
    tile.blit(pygame.transform.smoothscale(mini, (s, s)), (0, 0))

    # Tilted frosted card behind.
    back_w = int(s * 0.50)
    back = pygame.Surface((back_w, back_w), pygame.SRCALPHA)
    back_radius = int(back_w * 0.22)
    pygame.draw.rect(back, (255, 255, 255, 18), (0, 0, back_w, back_w),
                     border_radius=back_radius)
    pygame.draw.rect(back, (255, 255, 255, 38), (0, 0, back_w, back_w),
                     width=max(2, back_w // 200), border_radius=back_radius)
    back = pygame.transform.rotate(back, -10)
    tile.blit(back, back.get_rect(center=(int(s * 0.455), int(s * 0.45))))

    # Vivid gradient card with sheen and rim.
    radius = int(front_w * 0.20)
    card = pygame.Surface((front_w, front_w), pygame.SRCALPHA)
    card.blit(gradient_surface(front_w, front_w, [VIOLET, BLUE, MINT]), (0, 0))

    sheen = pygame.Surface((front_w, front_w), pygame.SRCALPHA)
    pygame.draw.ellipse(sheen, (255, 255, 255, 46),
                        (-front_w * 0.25, -front_w * 0.78,
                         front_w * 1.5, front_w * 1.2))
    card.blit(sheen, (0, 0))

    rim = pygame.Surface((front_w, front_w), pygame.SRCALPHA)
    pygame.draw.rect(rim, (255, 255, 255, 95), (0, 0, front_w, front_w),
                     width=max(2, front_w // 190), border_radius=radius)
    card.blit(rim, (0, 0))

    card.blit(rounded_mask(front_w, radius), (0, 0),
              special_flags=pygame.BLEND_RGBA_MULT)
    tile.blit(card, front_rect)

    # Play glyph with rounded corners and a shadow.
    glyph = pygame.Surface((front_w, front_w), pygame.SRCALPHA)
    cx, cy = front_w * 0.515, front_w * 0.5
    tri_w, tri_h = front_w * 0.30, front_w * 0.36
    tip = max(2, int(front_w * 0.030))

    shadow = [(x + front_w * 0.008, y + front_w * 0.018)
              for x, y in play_points(cx, cy, tri_w, tri_h)]
    pygame.draw.polygon(glyph, (6, 14, 38, 90), shadow)
    for x, y in shadow:
        pygame.draw.circle(glyph, (6, 14, 38, 90), (int(x), int(y)), tip)

    draw_play(glyph, cx, cy, tri_w, tri_h, WHITE, tip)
    tile.blit(glyph, front_rect)
    return finish(tile, s)


# --- style b: minimal neon glyph ------------------------------------------

def render_neon():
    s = MASTER
    tile = make_base(s, glow_scale=1.25)

    glow = radial_glow(320, (160, 160), 118, (0, 215, 255), 0.55)
    tile.blit(pygame.transform.smoothscale(glow, (s, s)), (0, 0),
              special_flags=pygame.BLEND_RGB_ADD)
    glow = radial_glow(320, (135, 120), 105, VIOLET, 0.65)
    tile.blit(pygame.transform.smoothscale(glow, (s, s)), (0, 0),
              special_flags=pygame.BLEND_RGB_ADD)

    cx, cy = s * 0.51, s * 0.5
    tri_w, tri_h = s * 0.30, s * 0.38
    tip = int(s * 0.036)
    points = play_points(cx, cy, tri_w, tri_h)

    mask = pygame.Surface((s, s), pygame.SRCALPHA)
    pygame.draw.polygon(mask, (255, 255, 255, 255), points)
    for x, y in points:
        pygame.draw.circle(mask, (255, 255, 255, 255), (int(x), int(y)), tip)

    glyph = gradient_surface(s, s, [VIOLET, BLUE, MINT], angle=-25)
    glyph.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    shadow = pygame.Surface((s, s), pygame.SRCALPHA)
    shadow_points = [(x + s * 0.004, y + s * 0.012) for x, y in points]
    pygame.draw.polygon(shadow, (0, 0, 0, 110), shadow_points)
    for x, y in shadow_points:
        pygame.draw.circle(shadow, (0, 0, 0, 110), (int(x), int(y)), tip)
    tile.blit(shadow, (0, 0))
    tile.blit(glyph, (0, 0))
    return finish(tile, s)


# --- style c: bento grid ---------------------------------------------------

def render_bento():
    s = MASTER
    tile = make_base(s, glow_scale=0.55)

    margin = int(s * 0.185)
    gap = int(s * 0.034)
    cell = (s - 2 * margin - gap) // 2
    radius = int(cell * 0.30)

    palettes = (
        ((124, 92, 255), (92, 116, 255)),    # violet
        ((0, 200, 255), (0, 229, 192)),      # cyan
        ((60, 224, 160), (0, 188, 138)),     # mint
        ((255, 130, 156), (255, 88, 108)),   # coral
    )

    for index, colors in enumerate(palettes):
        col, row = index % 2, index // 2
        x = margin + col * (cell + gap)
        y = margin + row * (cell + gap)
        tile_surface = pygame.Surface((cell, cell), pygame.SRCALPHA)
        tile_surface.blit(gradient_surface(cell, cell, list(colors), -20), (0, 0))

        sheen = pygame.Surface((cell, cell), pygame.SRCALPHA)
        pygame.draw.ellipse(sheen, (255, 255, 255, 44),
                            (-cell * 0.3, -cell * 0.8, cell * 1.6, cell * 1.1))
        tile_surface.blit(sheen, (0, 0))

        rim = pygame.Surface((cell, cell), pygame.SRCALPHA)
        pygame.draw.rect(rim, (255, 255, 255, 70), (0, 0, cell, cell),
                         width=max(2, cell // 180), border_radius=radius)
        tile_surface.blit(rim, (0, 0))

        tile_surface.blit(rounded_mask(cell, radius), (0, 0),
                          special_flags=pygame.BLEND_RGBA_MULT)
        tile.blit(tile_surface, (x, y))

    # Floating dark play badge over the middle.
    cx, cy = s // 2, s // 2
    badge_r = int(s * 0.115)
    badge = pygame.Surface((s, s), pygame.SRCALPHA)
    pygame.draw.circle(badge, (9, 12, 20, 240), (cx, cy), badge_r)
    pygame.draw.circle(badge, (255, 255, 255, 48), (cx, cy), badge_r,
                       width=max(2, s // 380))
    draw_play(badge, cx + badge_r * 0.06, cy, badge_r * 0.62, badge_r * 0.78,
              WHITE, max(2, int(badge_r * 0.09)))
    tile.blit(badge, (0, 0))
    return finish(tile, s)


RENDERERS = {"a": render_layered, "b": render_neon, "c": render_bento}
LABELS = {"a": "A  glass card", "b": "B  neon glyph", "c": "C  bento tiles"}


# --- output ----------------------------------------------------------------

def smart_scale(surface, size):
    current = surface
    while current.get_width() > size * 2:
        current = pygame.transform.smoothscale(
            current, (current.get_width() // 2, current.get_height() // 2))
    return pygame.transform.smoothscale(current, (size, size))


def png_bytes(surface):
    path = ICON_PATH.with_suffix(".tmp.png")
    pygame.image.save(surface, str(path))
    try:
        return path.read_bytes()
    finally:
        path.unlink(missing_ok=True)


def write_ico(path, surfaces):
    frames = [png_bytes(surface) for surface in surfaces]
    header = struct.pack("<HHH", 0, 1, len(surfaces))
    entries = bytearray()
    blob = bytearray()
    offset = len(header) + 16 * len(surfaces)

    for surface, data in zip(surfaces, frames):
        width = 0 if surface.get_width() >= 256 else surface.get_width()
        height = 0 if surface.get_height() >= 256 else surface.get_height()
        entries += struct.pack("<BBBBHHII", width, height, 0, 0, 1, 32,
                               len(data), offset)
        blob += data
        offset += len(data)

    path.write_bytes(header + bytes(entries) + bytes(blob))


def build_preview(frames, path):
    sheet = pygame.Surface((560, 330))
    sheet.fill((14, 17, 22))
    sheet.blit(frames[256], (24, 24))
    x = 320
    for size in (64, 48, 32, 24, 16):
        y = 48 + (64 - size) // 2
        sheet.blit(frames[size], (x, y))
        x += size + 26
    pygame.image.save(sheet, str(path))


def build_compare(masters):
    columns = len(masters)
    sheet = pygame.Surface((300 * columns, 470))
    sheet.fill((14, 17, 22))
    font = pygame.font.SysFont("segoeui", 22, bold=True)
    small_font = pygame.font.SysFont("segoeui", 14)

    for index, (key, master) in enumerate(masters.items()):
        x = 300 * index
        label = font.render(LABELS[key], True, (235, 238, 245))
        sheet.blit(label, (x + 24, 16))

        big = smart_scale(master, 232)
        sheet.blit(big, (x + 34, 54))

        row_y = 330
        row_x = x + 24
        for size in (64, 48, 32, 24, 16):
            icon = smart_scale(master, size)
            sheet.blit(icon, (row_x, row_y + (64 - size) // 2))
            row_x += size + 16

        sizes_label = small_font.render("on dark, actual pixel sizes", True,
                                        (130, 138, 155))
        sheet.blit(sizes_label, (x + 24, row_y + 74))

    pygame.image.save(sheet, str(COMPARE_PATH))


def main():
    style = sys.argv[1].lower() if len(sys.argv) > 1 else "a"
    pygame.init()
    pygame.display.set_mode((1, 1))

    if style == "compare":
        masters = {key: renderer() for key, renderer in RENDERERS.items()}
        build_compare(masters)
        pygame.quit()
        print(f"wrote {COMPARE_PATH}")
        return

    if style not in RENDERERS:
        pygame.quit()
        raise SystemExit(f"unknown style {style!r}; use a, b, c or compare")

    master = RENDERERS[style]()
    frames = {size: smart_scale(master, size) for size in SIZES}
    write_ico(ICON_PATH, [frames[size] for size in SIZES])
    build_preview(frames, PREVIEW_PATH)

    # The desktop shortcut uses a per-style filename so Explorer treats a
    # regenerated icon as new instead of serving its old cached copy.
    shortcut_icon = ICON_PATH.with_name(f"icon_{style}.ico")
    shortcut_icon.write_bytes(ICON_PATH.read_bytes())

    pygame.quit()
    print(f"wrote {ICON_PATH} with sizes {SIZES} (style {style})")
    print(f"wrote {shortcut_icon} (shortcut copy)")
    print(f"wrote {PREVIEW_PATH} preview")


if __name__ == "__main__":
    main()

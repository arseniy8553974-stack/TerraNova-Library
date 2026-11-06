# -*- coding: utf-8 -*-
"""Мелкие вспомогательные функции."""
from __future__ import annotations

import json
import math
import os
import shutil
from typing import Iterable

import pygame

_text_cache: dict[tuple, pygame.Surface] = {}


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    t = clamp(t, 0.0, 1.0)
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


def smoothstep(t):
    t = clamp(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def approach(value, target, delta):
    if value < target:
        return min(value + delta, target)
    return max(value - delta, target)


def sign(v):
    return 1 if v > 0 else -1 if v < 0 else 0


def shade(color, factor):
    return (
        int(clamp(color[0] * factor, 0, 255)),
        int(clamp(color[1] * factor, 0, 255)),
        int(clamp(color[2] * factor, 0, 255)),
    )


def hash2(x: int, y: int) -> int:
    h = (x * 374761393 + y * 668265263) & 0xFFFFFFFF
    h = (h ^ (h >> 13)) * 1274126177 & 0xFFFFFFFF
    return h ^ (h >> 16)


def render_cached(font: pygame.font.Font, text: str, color, outline: int = 0,
                  outline_color=(0, 0, 0)) -> pygame.Surface:
    key = (id(font), text, tuple(color), outline, tuple(outline_color))
    surf = _text_cache.get(key)
    if surf is not None:
        return surf
    if len(_text_cache) > 700:
        _text_cache.clear()
    base = font.render(text, True, color)
    if outline:
        w, h = base.get_size()
        surf = pygame.Surface((w + outline * 2, h + outline * 2), pygame.SRCALPHA)
        ol = font.render(text, True, outline_color)
        for dx in range(-outline, outline + 1):
            for dy in range(-outline, outline + 1):
                if dx * dx + dy * dy <= outline * outline + 1:
                    surf.blit(ol, (dx + outline, dy + outline))
        surf.blit(base, (outline, outline))
    else:
        surf = base
    _text_cache[key] = surf
    return surf


def draw_text(surf: pygame.Surface, text: str, font: pygame.font.Font, color,
              pos, anchor: str = "topleft", shadow: bool = False,
              outline: int = 0, shadow_color=(0, 0, 0), alpha: int = 255):
    if not text:
        return pygame.Rect(pos, (0, 0))
    img = render_cached(font, text, color, outline)
    rect = img.get_rect()
    setattr(rect, anchor, pos)
    if shadow:
        sh = render_cached(font, text, shadow_color, outline)
        srect = sh.get_rect()
        setattr(srect, anchor, pos)
        srect.x += 2
        srect.y += 3
        if alpha < 255:
            sh = sh.copy()
            sh.set_alpha(alpha)
        surf.blit(sh, srect)
    if alpha < 255:
        img = img.copy()
        img.set_alpha(alpha)
    surf.blit(img, rect)
    return rect


def wrap_text(font: pygame.font.Font, text: str, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        test = (current + " " + word).strip()
        if font.size(test)[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def panel(surf: pygame.Surface, rect: pygame.Rect, color=(24, 20, 22), alpha=220,
          border=(92, 72, 52), radius=14, border_width=2):
    layer = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(layer, (*color, alpha), layer.get_rect(), border_radius=radius)
    if border_width:
        pygame.draw.rect(layer, (*border, min(255, alpha + 20)), layer.get_rect(),
                         width=border_width, border_radius=radius)
    surf.blit(layer, rect.topleft)


def load_json(path: str, backup: bool = False):
    """Читает JSON. С backup=True при ошибке пробует файл .bak."""
    candidates = (path, path + ".bak") if backup else (path,)
    for candidate in candidates:
        try:
            with open(candidate, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            continue
    return None


def save_json(path: str, data) -> bool:
    """Атомарно сохраняет JSON и хранит предыдущую версию в .bak."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        if os.path.exists(path):
            try:
                shutil.copy2(path, path + ".bak")
            except OSError:
                pass
        os.replace(tmp, path)
        return True
    except OSError:
        return False


def rle_encode(rows: Iterable[Iterable[int]]) -> list[list[int]]:
    out: list[list[int]] = []
    last = None
    count = 0
    for row in rows:
        for tile in row:
            if tile == last:
                count += 1
            else:
                if last is not None:
                    out.append([int(last), count])
                last = tile
                count = 1
    if last is not None:
        out.append([int(last), count])
    return out


def rle_decode(data, width: int, height: int) -> list[bytearray]:
    flat = bytearray()
    for value, count in data:
        flat.extend(bytes([int(value)]) * int(count))
    expected = width * height
    if len(flat) < expected:
        flat.extend(b"\x00" * (expected - len(flat)))
    return [bytearray(flat[i * width:(i + 1) * width]) for i in range(height)]


def game_clock(time_fraction: float) -> str:
    """0.0 = 06:00, 0.25 = 12:00, 0.5 = 18:00, 0.75 = 00:00."""
    hours = (6.0 + time_fraction * 24.0) % 24.0
    minutes = int((hours % 1) * 60)
    return f"{int(hours):02d}:{minutes:02d}"


def plural_ru(n: int, one: str, few: str, many: str) -> str:
    n = abs(n)
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not (12 <= n % 100 <= 14):
        return few
    return many


def distance(ax, ay, bx, by):
    return math.hypot(ax - bx, ay - by)


def ease_out_cubic(t):
    t = clamp(t, 0.0, 1.0)
    return 1.0 - (1.0 - t) ** 3

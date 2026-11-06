# -*- coding: utf-8 -*-
"""Процедурная графика: текстуры тайлов, спрайты, иконки, шрифты."""
from __future__ import annotations

import math
import random

import pygame

from . import config
from .config import TILES


def _surf(w, h):
    return pygame.Surface((w, h), pygame.SRCALPHA)


def _outline(img: pygame.Surface, color=(16, 12, 12), width=1) -> pygame.Surface:
    mask = pygame.mask.from_surface(img)
    sil = mask.to_surface(setcolor=(*color, 255), unsetcolor=(0, 0, 0, 0))
    out = _surf(img.get_width() + width * 2, img.get_height() + width * 2)
    for dx in range(-width, width + 1):
        for dy in range(-width, width + 1):
            if dx * dx + dy * dy <= width * width + 1:
                out.blit(sil, (dx + width, dy + width))
    out.blit(img, (width, width))
    return out


def _noise_rect(surf, rng, base, amount=10, rect=None):
    rect = rect or surf.get_rect()
    # для 32x32 достаточно точечного шума
    for x in range(rect.x, rect.right):
        for y in range(rect.y, rect.bottom):
            d = rng.randint(-amount, amount)
            surf.set_at((x, y), (
                max(0, min(255, base[0] + d)),
                max(0, min(255, base[1] + d)),
                max(0, min(255, base[2] + d)),
                255,
            ))


def _speckles(surf, rng, color, count, size=(1, 2)):
    w, h = surf.get_size()
    for _ in range(count):
        x = rng.randrange(0, w)
        y = rng.randrange(0, h)
        s = rng.randint(size[0], size[1])
        surf.fill(color, (x, y, s, s))


def _dirt_texture(rng, grass=False):
    s = _surf(32, 32)
    _noise_rect(s, rng, (124, 86, 56), 11)
    # Крупные комья земли с бликом и тенью.
    for _ in range(7):
        x, y = rng.randrange(2, 27), rng.randrange(3, 28)
        w, h = rng.randint(3, 6), rng.randint(2, 4)
        col = rng.choice([(139, 98, 64), (110, 75, 49), (128, 90, 58)])
        pygame.draw.ellipse(s, (91, 61, 41), (x, y + 1, w, h))
        pygame.draw.ellipse(s, col, (x, y, w, max(2, h - 1)))
        pygame.draw.line(s, (155, 111, 74), (x + 1, y), (x + w - 2, y), 1)
    # Корни и мелкие камешки.
    for _ in range(3):
        x, y = rng.randrange(3, 27), rng.randrange(4, 26)
        points = [(x, y)]
        for _ in range(3):
            x += rng.randint(-3, 4)
            y += rng.randint(2, 5)
            points.append((x, y))
        pygame.draw.lines(s, (82, 56, 38), False, points, 1)
    _speckles(s, rng, (155, 113, 76), 8, (1, 1))
    _speckles(s, rng, (88, 58, 39), 8, (1, 2))
    if grass:
        # Многослойная травяная кромка с отдельными травинками.
        for x in range(32):
            depth = rng.randint(5, 8)
            s.set_at((x, 0), (77, 132, 54))
            for y in range(1, depth):
                c = rng.choice([(88, 149, 58), (102, 168, 68), (72, 128, 50)])
                s.set_at((x, y), c)
            s.set_at((x, max(1, depth - 1)), (122, 185, 78))
            if rng.random() < 0.55:
                pygame.draw.line(s, (135, 199, 86), (x, depth),
                                 (x + rng.randint(-1, 1), depth + rng.randint(2, 5)), 1)
        for _ in range(4):
            x = rng.randrange(3, 28)
            pygame.draw.line(s, (57, 108, 44), (x, 5), (x + rng.randint(-2, 2), 12), 1)
        for _ in range(2):
            x, y = rng.randrange(5, 27), rng.randint(2, 4)
            pygame.draw.circle(s, rng.choice([(238, 217, 128), (231, 158, 173)]), (x, y), 2)
            s.set_at((x, y), (255, 241, 181))
    # Лёгкая тень по краям.
    for x in range(32):
        s.set_at((x, 31), (70, 48, 33))
    for y in range(32):
        s.set_at((31, y), (83, 58, 39))
    return s


def _stone_texture(rng):
    s = _surf(32, 32)
    _noise_rect(s, rng, (98, 98, 110), 8)
    # Крупные каменные пластины с объёмной кромкой.
    for _ in range(5):
        cx, cy = rng.randrange(5, 28), rng.randrange(5, 28)
        w, h = rng.randint(7, 13), rng.randint(5, 9)
        pts = [(cx - w // 2, cy), (cx - w // 3, cy - h // 2),
               (cx + w // 3, cy - h // 2 + rng.randint(-1, 1)),
               (cx + w // 2, cy + 1), (cx + w // 4, cy + h // 2)]
        base = rng.choice([(108, 108, 121), (91, 91, 104), (116, 116, 128)])
        pygame.draw.polygon(s, (68, 68, 81), [(x + 1, y + 1) for x, y in pts])
        pygame.draw.polygon(s, base, pts)
        pygame.draw.lines(s, tuple(min(255, c + 26) for c in base), False, pts[:3], 1)
    # Трещины.
    for _ in range(4):
        x, y = rng.randrange(3, 28), rng.randrange(3, 27)
        points = [(x, y)]
        for _ in range(rng.randint(2, 4)):
            x += rng.randint(-5, 5)
            y += rng.randint(1, 6)
            points.append((x, y))
        pygame.draw.lines(s, (58, 58, 71), False, points, 1)
        pygame.draw.lines(s, (130, 130, 142), False,
                          [(px + 1, py + 1) for px, py in points[1:]], 1)
    _speckles(s, rng, (139, 139, 151), 10, (1, 1))
    _speckles(s, rng, (70, 70, 83), 9, (1, 2))
    return s


def _ore_texture(rng, metal, metal_light):
    s = _stone_texture(rng)
    dark_metal = tuple(max(0, int(c * 0.55)) for c in metal)
    for _ in range(7):
        x, y = rng.randrange(4, 27), rng.randrange(4, 27)
        r = rng.randint(2, 4)
        pts = [(x, y - r), (x + r, y - 1), (x + r - 1, y + r), (x - r, y + r - 1)]
        pygame.draw.polygon(s, dark_metal, [(px + 1, py + 1) for px, py in pts])
        pygame.draw.polygon(s, metal, pts)
        pygame.draw.line(s, metal_light, (x - 1, y - r + 2), (x + 1, y), 1)
        s.set_at((x - 1, y - r + 1), (255, 253, 231))
        if rng.random() < 0.5:
            s.set_at((x + r + 1, y - 1), metal_light)
    _speckles(s, rng, metal_light, 4, (1, 1))
    return s


def _plank_texture(rng):
    s = _surf(32, 32)
    _noise_rect(s, rng, (153, 111, 68), 8)
    for y in (0, 10, 21, 31):
        pygame.draw.line(s, (104, 72, 43), (0, y), (31, y))
        pygame.draw.line(s, (190, 146, 94), (0, min(31, y + 1)), (31, min(31, y + 1)))
    for row in range(3):
        y0 = row * 10 + 2
        for _ in range(4):
            x, y = rng.randrange(0, 30), rng.randrange(y0, y0 + 7)
            pygame.draw.line(s, (170, 126, 80), (x, y), (min(31, x + rng.randint(3, 9)), y))
        seam = rng.randrange(6, 26)
        pygame.draw.line(s, (113, 80, 48), (seam, y0), (seam, y0 + 7))
        pygame.draw.line(s, (85, 58, 36), (seam + 1, y0), (seam + 1, y0 + 7))
        # Сучок.
        if rng.random() < 0.7:
            kx, ky = rng.randrange(4, 27), rng.randrange(y0 + 1, y0 + 5)
            pygame.draw.ellipse(s, (96, 65, 41), (kx, ky, 5, 3))
            pygame.draw.ellipse(s, (176, 133, 84), (kx + 1, ky, 3, 1))
    for x, y in ((5, 5), (16, 15), (25, 26)):
        s.fill((208, 172, 118), (x, y, 2, 2))
        s.set_at((x, y + 1), (91, 63, 38))
    return s


def _trunk_texture(rng):
    s = _surf(32, 32)
    _noise_rect(s, rng, (105, 74, 46), 6)
    for x in (0, 5, 12, 20, 27, 31):
        pygame.draw.line(s, (75, 51, 31), (x, 0), (x, 31))
    for _ in range(6):
        x = rng.randrange(2, 29)
        y = rng.randrange(2, 27)
        pygame.draw.line(s, (128, 91, 58), (x, y), (x + rng.randint(1, 3), y + rng.randint(2, 5)))
    return s


def _tree_trunk_texture(rng, dead=False):
    """Узкий природный ствол с прозрачными краями — по нему можно пройти."""
    s = _surf(32, 32)
    if dead:
        edge = (40, 34, 35)
        base = (96, 79, 69)
        light = (127, 109, 94)
        dark = (63, 53, 52)
        left, right = 11, 21
    else:
        edge = (46, 32, 26)
        base = (111, 79, 48)
        light = (147, 107, 65)
        dark = (77, 53, 34)
        left, right = 10, 22
    # Слегка неровный, но непрерывный по вертикали силуэт.
    pygame.draw.rect(s, edge, (left - 1, 0, right - left + 2, 32))
    pygame.draw.rect(s, base, (left, 0, right - left, 32))
    pygame.draw.line(s, light, (left + 1, 0), (left + 1, 31), 2)
    pygame.draw.line(s, dark, (right - 2, 0), (right - 2, 31), 2)
    # Волокна коры.
    for _ in range(4):
        x = rng.randint(left + 3, right - 4)
        y = rng.randint(0, 27)
        pygame.draw.line(s, dark, (x, y), (x + rng.choice((-1, 0, 1)), y + rng.randint(3, 8)), 1)
    for _ in range(4):
        x = rng.randint(left + 3, right - 3)
        y = rng.randint(2, 27)
        pygame.draw.line(s, light, (x, y), (x, y + rng.randint(1, 4)), 1)
    # Зарубки и маленький сучок.
    knot_y = rng.randint(5, 24)
    pygame.draw.ellipse(s, dark, (left + 4, knot_y, 5, 3))
    s.set_at((left + 5, knot_y + 1), edge)
    if dead:
        pygame.draw.line(s, edge, (left + 3, 4), (left + 6, 12), 1)
        pygame.draw.line(s, edge, (right - 4, 18), (right - 6, 26), 1)
    return s


def _tree_cactus_texture(rng):
    """Природный кактус: узкий стебель, колючки и мягкие блики."""
    s = _surf(32, 32)
    edge = (31, 61, 36)
    dark = (55, 108, 54)
    base = (83, 148, 73)
    light = (122, 184, 94)
    pygame.draw.rect(s, edge, (12, 0, 9, 32), border_radius=4)
    pygame.draw.rect(s, base, (13, 0, 7, 32), border_radius=3)
    pygame.draw.rect(s, dark, (18, 0, 2, 32))
    pygame.draw.line(s, light, (15, 0), (15, 31), 1)
    for i in range(5):
        y = 3 + i * 6
        side = -1 if i % 2 else 1
        x = 17 if side > 0 else 14
        pygame.draw.line(s, (211, 207, 147), (x, y), (x + side * 3, y - 1), 1)
    pygame.draw.line(s, light, (16, 5), (16, 13), 1)
    return s


def _leaves_texture(rng):
    s = _surf(32, 32)
    # Глубокие тени по краям дают кроне объём, а не плоский зелёный квадрат.
    for _ in range(13):
        x = rng.randint(1, 30)
        y = rng.randint(1, 30)
        r = rng.randint(5, 9)
        c = rng.choice([(41, 84, 39), (46, 94, 42), (53, 103, 46)])
        pygame.draw.circle(s, c, (x, y), r)
    for _ in range(17):
        x = rng.randint(2, 29)
        y = rng.randint(2, 29)
        r = rng.randint(3, 7)
        c = rng.choice([(65, 127, 54), (75, 140, 60), (88, 155, 67)])
        pygame.draw.circle(s, c, (x, y), r)
    for _ in range(13):
        x = rng.randint(3, 28)
        y = rng.randint(3, 28)
        pygame.draw.circle(s, rng.choice([(103, 171, 79), (116, 181, 88)]), (x, y), rng.randint(1, 3))
    # Прожилки и отдельные листики.
    for _ in range(6):
        x = rng.randint(4, 26)
        y = rng.randint(4, 26)
        pygame.draw.line(s, (54, 110, 47), (x, y), (x + rng.randint(2, 5), y + rng.randint(1, 4)), 1)
    return s


def _brick_texture(rng):
    s = _surf(32, 32)
    s.fill((67, 59, 58))
    for row in range(4):
        y = row * 8
        offset = 0 if row % 2 == 0 else 8
        for col in range(-1, 3):
            x = offset + col * 16
            rect = pygame.Rect(x + 1, y + 1, 14, 6)
            color = rng.choice([(112, 100, 97), (120, 106, 100), (104, 94, 93)])
            pygame.draw.rect(s, color, rect)
            pygame.draw.line(s, (146, 129, 120), (rect.x, rect.y), (rect.right - 1, rect.y))
            pygame.draw.line(s, (94, 82, 79), (rect.x, rect.bottom - 1), (rect.right - 1, rect.bottom - 1))
            if rng.random() < 0.25:
                cx, cy = rng.randrange(rect.x + 1, rect.right - 2), rng.randrange(rect.y + 1, rect.bottom - 1)
                s.set_at((cx, cy), (79, 68, 66))
                s.set_at((cx + 1, cy), (138, 121, 113))
    return s


def _bedrock_texture(rng):
    s = _surf(32, 32)
    _noise_rect(s, rng, (48, 45, 55), 10)
    for _ in range(5):
        x, y = rng.randrange(0, 30), rng.randrange(0, 30)
        pygame.draw.line(s, (28, 26, 34), (x, y), (x + rng.randint(3, 9), y + rng.randint(3, 9)), 2)
    _speckles(s, rng, (65, 61, 73), 8, (1, 2))
    return s


def _sand_texture(rng):
    s = _surf(32, 32)
    _noise_rect(s, rng, (211, 183, 119), 13)
    # Дюнные волны с мягкой тенью и солнечным гребнем.
    for i in range(5):
        y = 4 + i * 7 + rng.randint(-2, 2)
        pts = [(x, y + int(round(math.sin(x * 0.3 + i * 0.9) * 1.6))) for x in range(32)]
        pygame.draw.lines(s, (178, 147, 90), False, pts, 1)
        pygame.draw.lines(s, (238, 214, 155), False,
                          [(x, py + 2) for x, py in pts], 1)
    for _ in range(5):
        x, y = rng.randrange(2, 29), rng.randrange(2, 29)
        pygame.draw.circle(s, (235, 224, 190), (x, y), 1)
        s.set_at((x + 1, y), (168, 136, 86))
    _speckles(s, rng, (163, 132, 82), 7, (1, 2))
    _speckles(s, rng, (245, 226, 174), 9, (1, 1))
    return s


def _sandstone_texture(rng):
    s = _surf(32, 32)
    for i in range(5):
        y = i * 7
        col = rng.choice([(180, 142, 87), (192, 154, 96), (170, 133, 81)])
        pygame.draw.rect(s, col, (0, y, 32, 7))
        pygame.draw.line(s, (211, 176, 114), (0, y + 1), (31, y + 1))
        pygame.draw.line(s, (208, 173, 111), (0, y + 2), (31, y + 2))
        pygame.draw.line(s, (138, 105, 65), (0, y + 6), (31, y + 6))
    for _ in range(6):
        x, y = rng.randrange(0, 30), rng.randrange(0, 28)
        pygame.draw.line(s, (151, 116, 72), (x, y), (x + rng.randint(2, 7), y), 1)
    for _ in range(4):
        x, y = rng.randrange(1, 28), rng.randrange(1, 28)
        pygame.draw.line(s, (219, 186, 124), (x, y), (x + rng.randint(1, 3), y + rng.randint(1, 3)), 1)
    return s


def _snow_texture(rng):
    s = _surf(32, 32)
    _noise_rect(s, rng, (228, 237, 244), 8)
    # Сугробы и голубые тени.
    for i in range(4):
        x = rng.randrange(1, 24)
        y = 4 + i * 7
        pygame.draw.ellipse(s, (205, 221, 234), (x, y, rng.randint(6, 12), 4))
        pygame.draw.ellipse(s, (241, 249, 253), (x + 1, y - 1, rng.randint(5, 10), 3))
    for _ in range(10):
        x, y = rng.randrange(0, 30), rng.randrange(1, 29)
        pygame.draw.circle(s, rng.choice([(247, 253, 255), (255, 255, 255)]), (x, y), 1)
    for _ in range(4):
        x, y = rng.randrange(2, 29), rng.randrange(4, 28)
        pygame.draw.line(s, (250, 254, 255), (x, y), (x + rng.randint(1, 4), y - 1), 1)
    return s


def _ice_texture(rng):
    s = _surf(32, 32)
    _noise_rect(s, rng, (156, 205, 230), 10)
    # Кристаллические грани.
    for _ in range(4):
        cx, cy = rng.randrange(5, 27), rng.randrange(5, 27)
        w, h = rng.randint(7, 14), rng.randint(6, 12)
        pts = [(cx, cy - h // 2), (cx + w // 2, cy), (cx, cy + h // 2), (cx - w // 2, cy)]
        pygame.draw.polygon(s, (135, 188, 218), pts)
        pygame.draw.lines(s, (211, 241, 252), False, pts[:3], 1)
    for _ in range(5):
        x = rng.randrange(1, 27)
        y = rng.randrange(1, 27)
        pygame.draw.line(s, (210, 238, 249), (x, y), (x + rng.randint(3, 9), y + rng.randint(3, 8)), 1)
        pygame.draw.line(s, (97, 156, 191), (x + 1, y + 1), (x + rng.randint(3, 7), y + rng.randint(2, 6)), 1)
    _speckles(s, rng, (228, 248, 253), 8, (1, 1))
    return s


def _corrupt_stone_texture(rng):
    s = _surf(32, 32)
    _noise_rect(s, rng, (77, 64, 85), 11)
    for _ in range(4):
        x, y = rng.randrange(2, 27), rng.randrange(2, 27)
        points = [(x, y)]
        for _ in range(rng.randint(2, 4)):
            x += rng.randint(-5, 5)
            y += rng.randint(1, 6)
            points.append((x, y))
        pygame.draw.lines(s, (47, 37, 55), False, points, 1)
    _speckles(s, rng, (126, 74, 136), 8, (1, 2))
    _speckles(s, rng, (50, 42, 58), 7, (1, 1))
    return s


def _corrupt_grass_texture(rng):
    s = _corrupt_stone_texture(rng)
    for x in range(32):
        depth = rng.randint(4, 8)
        for y in range(depth):
            c = rng.choice([(92, 54, 105), (117, 67, 127), (76, 45, 91)])
            s.set_at((x, y), c)
        if rng.random() < 0.35:
            pygame.draw.line(s, (140, 80, 145), (x, depth), (x + rng.randint(-1, 1), depth + 3), 1)
    return s


def _cactus_texture(rng):
    s = _surf(32, 32)
    pygame.draw.rect(s, (45, 91, 48), (9, 0, 14, 32), border_radius=5)
    pygame.draw.rect(s, (92, 153, 82), (10, 0, 10, 32), border_radius=4)
    pygame.draw.line(s, (132, 185, 102), (13, 2), (13, 29), 1)
    for _ in range(5):
        x = rng.randrange(8, 25)
        y = rng.randrange(3, 30)
        pygame.draw.line(s, (199, 203, 139), (x, y), (x + rng.choice((-3, 3)), y - 2), 1)
    pygame.draw.line(s, (48, 90, 49), (10, 10), (4, 4), 2)
    pygame.draw.line(s, (48, 90, 49), (22, 18), (28, 12), 2)
    return s


def _dead_wood_texture(rng):
    s = _surf(32, 32)
    _noise_rect(s, rng, (91, 75, 67), 8)
    for x in (2, 8, 15, 23, 29):
        pygame.draw.line(s, (58, 47, 44), (x, 0), (x + rng.randint(-2, 2), 31), 1)
    for _ in range(6):
        x, y = rng.randrange(2, 28), rng.randrange(2, 27)
        pygame.draw.line(s, (122, 104, 88), (x, y), (x + rng.randint(2, 6), y + rng.randint(1, 4)), 1)
    return s


def _glass_texture(rng):
    s = _surf(32, 32)
    s.fill((132, 187, 199, 42))
    pygame.draw.rect(s, (186, 224, 231, 200), (0, 0, 32, 32), 1)
    for _ in range(5):
        x, y = rng.randrange(3, 28), rng.randrange(3, 28)
        pygame.draw.line(s, (230, 251, 255, 150), (x, y), (x + rng.randint(3, 9), y - rng.randint(2, 7)), 1)
    return s


def _brick_texture_colored(rng, base, light, dark, mortar):
    s = _surf(32, 32)
    s.fill(mortar)
    for row in range(4):
        y = row * 8
        offset = 0 if row % 2 == 0 else 8
        for col in range(-1, 3):
            x = offset + col * 16
            rect = pygame.Rect(x + 1, y + 1, 14, 6)
            color = rng.choice([base, light, tuple(max(0, c - 6) for c in base)])
            pygame.draw.rect(s, color, rect)
            pygame.draw.line(s, light, (rect.x, rect.y), (rect.right - 1, rect.y))
            pygame.draw.line(s, dark, (rect.x, rect.bottom - 1), (rect.right - 1, rect.bottom - 1))
    return s


def _snow_brick_texture(rng):
    return _brick_texture_colored(rng, (181, 207, 222), (224, 241, 248),
                                  (133, 168, 189), (75, 99, 115))


def _sandstone_brick_texture(rng):
    return _brick_texture_colored(rng, (193, 157, 94), (220, 186, 120),
                                  (154, 119, 72), (110, 83, 53))


def _lava_texture(rng):
    s = _surf(32, 32)
    _noise_rect(s, rng, (205, 74, 28), 22)
    for _ in range(4):
        x, y = rng.randrange(0, 30), rng.randrange(0, 30)
        pygame.draw.circle(s, (250, 157, 44), (x, y), rng.randint(2, 4))
        pygame.draw.circle(s, (255, 220, 98), (x, y), 1)
    for _ in range(3):
        x = rng.randrange(0, 30)
        y = rng.randrange(0, 28)
        pygame.draw.line(s, (122, 35, 24), (x, y), (x + rng.randint(2, 6), y + rng.randint(-2, 2)), 1)
    return s


def _pine_leaves_texture(rng):
    s = _surf(32, 32)
    s.fill((0, 0, 0, 0))
    for _ in range(18):
        x = rng.randint(1, 30)
        y = rng.randint(1, 31)
        c = rng.choice([(38, 79, 64), (49, 99, 77), (63, 117, 91), (31, 66, 58)])
        pygame.draw.circle(s, c, (x, y), rng.randint(3, 6))
    return s


def _corrupt_leaves_texture(rng):
    s = _surf(32, 32)
    for _ in range(18):
        x = rng.randint(0, 31)
        y = rng.randint(0, 31)
        c = rng.choice([(77, 43, 88), (96, 55, 107), (113, 69, 122), (60, 38, 73)])
        pygame.draw.circle(s, c, (x, y), rng.randint(3, 7))
    return s


BOULDER_TILE_COLORS = {
    config.BOULDER: ((102, 99, 108), (146, 143, 151)),
    config.BOULDER_BOUNCY: ((132, 107, 91), (181, 144, 113)),
    config.BOULDER_LIFE: ((145, 65, 98), (226, 108, 153)),
    config.BOULDER_LAVA: ((120, 65, 44), (239, 111, 38)),
    config.BOULDER_SPIDER: ((88, 74, 91), (149, 130, 153)),
    config.BOULDER_RAINBOW: ((129, 105, 157), (215, 150, 220)),
    config.BOULDER_GHOST: ((107, 139, 153), (182, 226, 235)),
    config.BOULDER_ICE: ((145, 185, 207), (217, 245, 252)),
}


def _boulder_tile_texture(rng, base, light):
    s = _surf(32, 32)
    pygame.draw.ellipse(s, (25, 20, 20), (2, 8, 28, 23))
    pygame.draw.ellipse(s, base, (3, 6, 26, 23))
    pygame.draw.ellipse(s, light, (7, 8, 11, 8))
    for _ in range(3):
        x1 = rng.randrange(7, 24)
        y1 = rng.randrange(10, 24)
        pygame.draw.line(s, (55, 48, 50), (x1, y1), (x1 + rng.randint(2, 5), y1 + rng.randint(2, 5)), 1)
    _speckles(s, rng, tuple(max(0, c - 28) for c in base), 6, (1, 1))
    return s


def _workbench_texture(rng):
    s = _surf(32, 32)
    pygame.draw.rect(s, (95, 63, 39), (2, 9, 28, 6))
    pygame.draw.rect(s, (156, 112, 68), (2, 7, 28, 6))
    pygame.draw.line(s, (190, 148, 92), (2, 7), (29, 7))
    for x in (5, 24):
        pygame.draw.rect(s, (101, 69, 44), (x, 13, 3, 18))
    pygame.draw.rect(s, (82, 55, 35), (9, 26, 14, 3))
    # инструменты
    pygame.draw.rect(s, (117, 117, 128), (7, 2, 10, 3))
    pygame.draw.rect(s, (76, 48, 30), (11, 4, 2, 4))
    pygame.draw.line(s, (160, 160, 168), (21, 1), (26, 5), 2)
    return s


def _torch_texture(rng):
    s = _surf(32, 32)
    pygame.draw.line(s, (105, 70, 42), (16, 30), (16, 15), 3)
    pygame.draw.line(s, (62, 42, 28), (15, 30), (15, 15), 1)
    pygame.draw.circle(s, (237, 120, 38), (16, 10), 6)
    pygame.draw.circle(s, (250, 181, 54), (16, 10), 4)
    pygame.draw.circle(s, (255, 232, 139), (16, 9), 2)
    s.set_at((13, 5), (240, 150, 60))
    s.set_at((20, 6), (240, 150, 60))
    return s


def _crystal_texture(rng):
    s = _stone_texture(rng)
    for _ in range(3):
        x = rng.randint(6, 25)
        y = rng.randint(14, 27)
        h = rng.randint(7, 13)
        w = rng.randint(3, 5)
        pygame.draw.polygon(s, (92, 62, 128), [(x, y - h), (x + w, y), (x + w // 2, y + 3), (x - w, y)])
        pygame.draw.polygon(s, (166, 116, 210), [(x - 1, y - h + 2), (x + w - 2, y - 1), (x, y + 1), (x - w + 2, y - 1)])
        pygame.draw.line(s, (216, 179, 240), (x - 1, y - h + 3), (x + 1, y - 3))
    return s


def _life_crystal_texture(rng):
    s = _surf(32, 32)
    # тёмное основание
    pygame.draw.ellipse(s, (70, 40, 48), (7, 24, 18, 7))
    pts = [(16, 5), (24, 12), (21, 22), (16, 27), (11, 22), (8, 12)]
    pygame.draw.polygon(s, (147, 46, 86), pts)
    pygame.draw.polygon(s, (226, 90, 139), [(16, 7), (22, 13), (19, 21), (16, 25), (13, 20), (10, 13)])
    pygame.draw.polygon(s, (255, 166, 195), [(16, 8), (14, 14), (16, 20), (18, 14)])
    pygame.draw.line(s, (255, 218, 231), (15, 9), (15, 16))
    return s


def _palm_trunk_texture(rng):
    """Узкий ствол пальмы с кольцами и прозрачными краями."""
    s = _surf(32, 32)
    edge, base = (62, 42, 27), (136, 98, 60)
    light, dark = (190, 147, 94), (93, 65, 39)
    for y in range(32):
        off = int(round(math.sin(y * 0.23 + 0.7) * 1.2))
        pygame.draw.line(s, edge, (11 + off, y), (21 + off, y))
        pygame.draw.line(s, base, (12 + off, y), (20 + off, y))
    pygame.draw.line(s, light, (13, 0), (13, 31), 1)
    pygame.draw.line(s, dark, (20, 0), (20, 31), 1)
    for y in range(2, 32, 5):
        off = int(round(math.sin(y * 0.23 + 0.7) * 1.2))
        pygame.draw.line(s, dark, (12 + off, y), (20 + off, y), 1)
        pygame.draw.line(s, (164, 122, 75), (13 + off, y + 1), (19 + off, y + 1), 1)
    for _ in range(3):
        x, y = rng.randint(13, 19), rng.randint(3, 27)
        pygame.draw.line(s, edge, (x, y), (x + rng.choice((-1, 1)), y + rng.randint(2, 4)), 1)
    return s


def _palm_leaves_texture(rng):
    """Пальмовая крона: плотная масса перистых вай с бликами."""
    s = _surf(32, 32)
    # Плотная зелёная основа, чтобы крона не рассыпалась на отдельные пятна.
    s.fill((33, 88, 53))
    for _ in range(20):
        x = rng.randint(1, 30)
        y = rng.randint(1, 30)
        r = rng.randint(4, 7)
        pygame.draw.circle(s, rng.choice([(36, 96, 58), (44, 111, 65), (53, 126, 72)]), (x, y), r)
    center = (16, 16)
    for angle in range(0, 360, 20):
        rad = math.radians(angle + rng.uniform(-6, 6))
        length = rng.randint(12, 16)
        pts = []
        for i in range(1, length):
            x = center[0] + math.cos(rad) * i
            y = center[1] + math.sin(rad) * i * 0.82
            pts.append((int(round(x)), int(round(y))))
        if len(pts) > 2:
            pygame.draw.lines(s, (31, 84, 51), False, pts, 3)
            pygame.draw.lines(s, (68, 149, 83), False, pts, 2)
            pygame.draw.lines(s, (111, 190, 111), False, pts[1:], 1)
        for i in range(2, length - 1, 2):
            x, y = pts[i - 1]
            pygame.draw.line(s, (84, 167, 92), (x, y),
                             (x + rng.randint(-3, 3), y + rng.randint(-3, 3)), 1)
    pygame.draw.circle(s, (42, 103, 60), center, 5)
    pygame.draw.circle(s, (96, 170, 95), (center[0] - 1, center[1] - 1), 2)
    return s


def _water_texture(rng):
    """Полупрозрачная вода с бликами и волнистыми гребнями."""
    s = _surf(32, 32)
    s.fill((38, 112, 171, 188))
    for x in range(32):
        for y in range(32):
            d = rng.randint(-7, 7)
            s.set_at((x, y), (max(0, min(255, 38 + d)),
                              max(0, min(255, 112 + d)),
                              max(0, min(255, 171 + d)), 188))
    for i in range(4):
        base_y = 5 + i * 8
        pts = []
        for x in range(32):
            y = base_y + int(round(math.sin(x * 0.36 + i * 1.7) * 1.5))
            pts.append((x, max(0, min(31, y))))
        pygame.draw.lines(s, (70, 151, 203, 170), False, pts, 1)
        pygame.draw.lines(s, (121, 194, 226, 125), False,
                          [(x, y + 1) for x, y in pts], 1)
    for _ in range(5):
        x, y = rng.randrange(2, 28), rng.randrange(2, 28)
        pygame.draw.line(s, (180, 226, 241, 120), (x, y), (x + rng.randint(2, 5), y), 1)
    return s


def _cave_wall_texture(rng, base, dark, light, moss=None):
    """Фон пещеры: слоистая порода, трещины и редкие вкрапления."""
    s = _surf(32, 32)
    _noise_rect(s, rng, base, 9)
    for _ in range(3):
        y = rng.randrange(3, 29)
        points = [(0, y)]
        for x in range(0, 33, 6):
            points.append((x, y + rng.randint(-2, 2)))
        pygame.draw.lines(s, dark, False, points, 1)
        pygame.draw.lines(s, light, False, [(x, py + 1) for x, py in points], 1)
    for _ in range(3):
        x, y = rng.randrange(2, 27), rng.randrange(2, 26)
        points = [(x, y)]
        for _ in range(rng.randint(2, 4)):
            x += rng.randint(-5, 5)
            y += rng.randint(1, 6)
            points.append((x, y))
        pygame.draw.lines(s, dark, False, points, 1)
    _speckles(s, rng, light, 7, (1, 1))
    _speckles(s, rng, dark, 6, (1, 2))
    if moss:
        for _ in range(5):
            x, y = rng.randrange(1, 28), rng.randrange(1, 20)
            pygame.draw.circle(s, moss, (x, y), rng.randint(1, 2))
    return s


AUTOTILE_RIMS = {
    config.GRASS: ((156, 214, 98), (58, 99, 42)),
    config.DIRT: ((161, 116, 74), (76, 51, 34)),
    config.STONE: ((145, 145, 158), (57, 57, 69)),
    config.WOOD: ((142, 105, 65), (66, 48, 31)),
    config.COPPER: ((150, 142, 135), (57, 57, 69)),
    config.IRON: ((150, 142, 135), (57, 57, 69)),
    config.GOLD_TILE: ((150, 142, 135), (57, 57, 69)),
    config.PLANKS: ((196, 151, 98), (90, 61, 37)),
    config.BRICK: ((148, 133, 124), (66, 55, 53)),
    config.BEDROCK: ((74, 71, 84), (29, 27, 34)),
    config.CRYSTAL: ((188, 142, 226), (77, 51, 98)),
    config.SAND: ((243, 217, 155), (153, 124, 77)),
    config.SANDSTONE: ((224, 190, 126), (124, 93, 57)),
    config.SNOW: ((255, 255, 255), (146, 175, 195)),
    config.ICE: ((220, 245, 255), (91, 146, 177)),
    config.CORRUPT_GRASS: ((139, 87, 150), (55, 37, 65)),
    config.CORRUPT_STONE: ((111, 93, 122), (43, 35, 50)),
    config.CACTUS: ((134, 188, 107), (47, 89, 48)),
    config.DEAD_WOOD: ((133, 113, 99), (58, 48, 45)),
    config.GLASS: ((223, 244, 249), (91, 139, 149)),
    config.SNOW_BRICK: ((235, 248, 253), (105, 137, 154)),
    config.SANDSTONE_BRICK: ((222, 187, 123), (117, 87, 53)),
    config.TREE_TRUNK: ((150, 110, 67), (62, 45, 29)),
    config.TREE_DEAD: ((136, 116, 102), (54, 45, 42)),
}


class Assets:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self._font_cache: dict[tuple, pygame.font.Font] = {}
        self.tile_images: dict[int, list[pygame.Surface]] = {}
        self.wall_images: dict[str, list[pygame.Surface]] = {}
        self.item_icons: dict[str, pygame.Surface] = {}
        self.player_frames: dict[str, list[pygame.Surface]] = {}
        self.player_style: dict = dict(config.DEFAULT_APPEARANCE)
        self.boulder_images: dict[str, pygame.Surface] = {}
        self._light_cache: dict[tuple, pygame.Surface] = {}
        self._glow_cache: dict[tuple, pygame.Surface] = {}
        self._leaf_edge_cache: dict[tuple, pygame.Surface] = {}
        self._autotile_cache: dict[tuple, pygame.Surface] = {}
        self._water_cache: dict[tuple, pygame.Surface] = {}
        self._appearance_cache: dict[tuple, dict] = {}
        self.build_tiles()
        self.build_walls()
        self.build_player(self.player_style)
        self.build_boulders()
        self.build_guide()
        self.build_blacksmith()
        self.build_herbalist()
        self.build_icons()
        self.build_ui()

    # -------------------------------------------------------------- шрифты
    def font(self, size: int, bold: bool = False, italic: bool = False,
             title: bool = False) -> pygame.font.Font:
        key = (size, bold, italic, title)
        f = self._font_cache.get(key)
        if f is None:
            if title:
                names = "georgia,timesnewroman,segoeui,arial"
            else:
                names = "segoeui,trebuchetms,arial,dejavusans"
            try:
                f = pygame.font.SysFont(names, size, bold=bold, italic=italic)
            except Exception:
                f = pygame.font.Font(None, size)
            self._font_cache[key] = f
        return f

    # -------------------------------------------------------------- тайлы
    def build_tiles(self):
        builders = {
            config.DIRT: lambda r: _dirt_texture(r, False),
            config.GRASS: lambda r: _dirt_texture(r, True),
            config.STONE: _stone_texture,
            config.WOOD: _trunk_texture,
            config.LEAVES: _leaves_texture,
            config.COPPER: lambda r: _ore_texture(r, (166, 102, 67), (215, 146, 97)),
            config.IRON: lambda r: _ore_texture(r, (146, 142, 144), (202, 199, 199)),
            config.GOLD_TILE: lambda r: _ore_texture(r, (193, 154, 71), (241, 209, 117)),
            config.PLANKS: _plank_texture,
            config.WORKBENCH: _workbench_texture,
            config.TORCH: _torch_texture,
            config.BRICK: _brick_texture,
            config.BEDROCK: _bedrock_texture,
            config.CRYSTAL: _crystal_texture,
            config.LIFE_CRYSTAL: _life_crystal_texture,
            config.SAND: _sand_texture,
            config.SANDSTONE: _sandstone_texture,
            config.SNOW: _snow_texture,
            config.ICE: _ice_texture,
            config.CORRUPT_GRASS: _corrupt_grass_texture,
            config.CORRUPT_STONE: _corrupt_stone_texture,
            config.CACTUS: _cactus_texture,
            config.DEAD_WOOD: _dead_wood_texture,
            config.GLASS: _glass_texture,
            config.SNOW_BRICK: _snow_brick_texture,
            config.SANDSTONE_BRICK: _sandstone_brick_texture,
            config.LAVA: _lava_texture,
            config.PINE_LEAVES: _pine_leaves_texture,
            config.CORRUPT_LEAVES: _corrupt_leaves_texture,
            config.TREE_TRUNK: _tree_trunk_texture,
            config.TREE_DEAD: lambda r: _tree_trunk_texture(r, dead=True),
            config.CACTUS_PLANT: _tree_cactus_texture,
            config.WATER: _water_texture,
            config.PALM_TRUNK: _palm_trunk_texture,
            config.PALM_LEAVES: _palm_leaves_texture,
        }
        for tile_id, (base, light) in BOULDER_TILE_COLORS.items():
            builders[tile_id] = (lambda r, b=base, l=light: _boulder_tile_texture(r, b, l))
        for tile_id, builder in builders.items():
            variants = []
            for v in range(3):
                rng = random.Random(tile_id * 977 + v * 131)
                img = builder(rng)
                if pygame.display.get_surface():
                    img = img.convert_alpha()
                variants.append(img)
            self.tile_images[tile_id] = variants

    def tile_image(self, tile_id: int, variant: int = 0) -> pygame.Surface:
        imgs = self.tile_images.get(tile_id)
        if not imgs:
            imgs = self.tile_images[config.STONE]
        return imgs[variant % len(imgs)]

    def leaf_image(self, tile_id: int, neighbor_mask: int, variant: int = 0) -> pygame.Surface:
        """Крона с рваным контуром на границе с воздухом.

        Битовая маска: 1 — листва сверху, 2 — справа, 4 — снизу, 8 — слева.
        Внутри массива листвы края не обрезаются, поэтому крона остаётся цельной.
        """
        if tile_id not in config.LEAF_TILES:
            return self.tile_image(tile_id, variant)
        mask = int(neighbor_mask) & 15
        variant %= 3
        if mask == 15:
            return self.tile_image(tile_id, variant)
        key = (tile_id, mask, variant)
        cached = self._leaf_edge_cache.get(key)
        if cached is not None:
            return cached
        img = self.tile_image(tile_id, variant).copy()
        rng = random.Random(tile_id * 104729 + mask * 7919 + variant * 131)
        # Неровный край: небольшие вырезы и редкие глубокие зубцы.
        if not mask & 1:
            for x in range(32):
                depth = 1 + rng.randint(0, 3)
                if rng.random() < 0.22:
                    depth += rng.randint(2, 4)
                for y in range(depth):
                    img.set_at((x, y), (0, 0, 0, 0))
        if not mask & 2:
            for y in range(32):
                depth = 1 + rng.randint(0, 3)
                if rng.random() < 0.22:
                    depth += rng.randint(2, 4)
                for x in range(32 - depth, 32):
                    img.set_at((x, y), (0, 0, 0, 0))
        if not mask & 4:
            for x in range(32):
                depth = 1 + rng.randint(0, 3)
                if rng.random() < 0.22:
                    depth += rng.randint(2, 4)
                for y in range(32 - depth, 32):
                    img.set_at((x, y), (0, 0, 0, 0))
        if not mask & 8:
            for y in range(32):
                depth = 1 + rng.randint(0, 3)
                if rng.random() < 0.22:
                    depth += rng.randint(2, 4)
                for x in range(depth):
                    img.set_at((x, y), (0, 0, 0, 0))
        # Тёмная кромка делает силуэт выразительнее.
        rims = {
            config.LEAVES: (37, 77, 37),
            config.PINE_LEAVES: (27, 57, 49),
            config.CORRUPT_LEAVES: (55, 31, 65),
            config.PALM_LEAVES: (29, 74, 48),
        }
        rim = rims.get(tile_id, (46, 69, 45))
        for y in range(32):
            for x in range(32):
                color = img.get_at((x, y))
                if color.a == 0:
                    continue
                border = (x == 0 or y == 0 or x == 31 or y == 31)
                if not border:
                    border = any(img.get_at((x + dx, y + dy)).a == 0
                                 for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)))
                if border:
                    img.set_at((x, y), (*rim, color.a))
        self._leaf_edge_cache[key] = img
        return img

    # -------------------------------------------------------------- стены пещер
    def build_walls(self):
        specs = {
            "dirt": ((70, 53, 42), (43, 32, 28), (94, 72, 56), None),
            "stone": ((47, 46, 58), (28, 28, 37), (67, 66, 80), None),
            "deep": ((33, 31, 46), (19, 18, 29), (52, 49, 68), (56, 45, 74)),
            "sand": ((102, 83, 57), (64, 51, 37), (134, 110, 75), None),
            "snow": ((89, 110, 131), (53, 70, 89), (126, 153, 172), None),
            "corrupt": ((54, 40, 61), (31, 24, 39), (80, 59, 91), (99, 58, 107)),
        }
        for index, (kind, (base, dark, light, moss)) in enumerate(specs.items()):
            variants = []
            for v in range(3):
                rng = random.Random(7001 + index * 977 + v * 131)
                img = _cave_wall_texture(rng, base, dark, light, moss)
                if pygame.display.get_surface():
                    img = img.convert()
                variants.append(img)
            self.wall_images[kind] = variants

    def wall_image(self, kind: str, variant: int = 0) -> pygame.Surface:
        imgs = self.wall_images.get(kind) or self.wall_images.get("stone")
        return imgs[variant % len(imgs)]

    # -------------------------------------------------------------- автотайлинг
    def autotile_image(self, tile_id: int, neighbor_mask: int, variant: int = 0) -> pygame.Surface:
        """Объёмные кромки у блоков, выходящих к воздуху.

        Битовая маска: 1 — твёрдый блок сверху, 2 — справа, 4 — снизу, 8 — слева.
        """
        if not TILES[tile_id].solid:
            return self.tile_image(tile_id, variant)
        mask = int(neighbor_mask) & 15
        variant %= 3
        if mask == 15:
            return self.tile_image(tile_id, variant)
        key = (tile_id, mask, variant)
        cached = self._autotile_cache.get(key)
        if cached is not None:
            return cached
        img = self.tile_image(tile_id, variant).copy()
        base = TILES[tile_id].color
        light, dark = AUTOTILE_RIMS.get(
            tile_id,
            (tuple(min(255, int(c * 1.24 + 26)) for c in base),
             tuple(max(0, int(c * 0.58)) for c in base)),
        )
        mid = tuple((light[i] + base[i]) // 2 for i in range(3))
        if not mask & 1:
            pygame.draw.line(img, light, (0, 0), (31, 0), 1)
            pygame.draw.line(img, mid, (0, 1), (31, 1), 1)
        if not mask & 4:
            pygame.draw.line(img, dark, (0, 30), (31, 30), 2)
        if not mask & 8:
            pygame.draw.line(img, light, (0, 0), (0, 31), 1)
            pygame.draw.line(img, mid, (1, 1), (1, 31), 1)
        if not mask & 2:
            pygame.draw.line(img, dark, (30, 0), (30, 31), 2)
        # Скруглённые внешние углы: блоки не выглядят идеальными квадратами.
        cuts = ((0, 0, 1, 8), (31, 0, 1, 2), (0, 31, 4, 8), (31, 31, 4, 2))
        for x, y, a, b in cuts:
            if not mask & a and not mask & b:
                img.set_at((x, y), (0, 0, 0, 0))
        # Травяная кромка на открытых боках.
        if tile_id in (config.GRASS, config.CORRUPT_GRASS):
            side = (108, 171, 73) if tile_id == config.GRASS else (126, 73, 137)
            side_light = (137, 199, 91) if tile_id == config.GRASS else (151, 91, 159)
            if not mask & 8:
                for y in range(0, 8):
                    img.set_at((0, y), side)
                    img.set_at((1, y), side_light)
            if not mask & 2:
                for y in range(0, 8):
                    img.set_at((31, y), side)
                    img.set_at((30, y), side_light)
        self._autotile_cache[key] = img
        return img

    def water_image(self, variant: int = 0, surface: bool = False) -> pygame.Surface:
        """Вода; у верхнего слоя добавляются гребни и пена."""
        key = (variant % 3, bool(surface))
        cached = self._water_cache.get(key)
        if cached is not None:
            return cached
        img = self.tile_image(config.WATER, variant % 3).copy()
        if surface:
            for x in range(32):
                y = 1 + int(round(math.sin(x * 0.42 + variant * 1.9) * 1.3))
                img.set_at((x, max(0, y - 1)), (125, 204, 235, 210))
                img.set_at((x, y), (176, 231, 246, 220))
            for x in range(3, 30, 7):
                img.set_at((x, 4), (229, 247, 252, 210))
                img.set_at((x + 1, 4), (205, 238, 248, 180))
        self._water_cache[key] = img
        return img

    # -------------------------------------------------------------- игрок
    def build_player(self, appearance: dict | None = None):
        if appearance is not None:
            self.player_style = {
                "skin": int(appearance.get("skin", 1)),
                "hair": int(appearance.get("hair", 0)),
                "shirt": int(appearance.get("shirt", 0)),
                "pants": int(appearance.get("pants", 0)),
                "hair_style": int(appearance.get("hair_style", 0)),
            }
        walk = []
        for frame in range(6):
            walk.append(self._player_frame(frame / 6.0 * math.tau, "walk"))
        idle = [self._player_frame(0.0, "idle"), self._player_frame(math.pi, "idle")]
        jump = self._player_frame(0.0, "jump")
        fall = self._player_frame(0.0, "fall")
        self.player_frames = {"idle": idle, "walk": walk, "jump": [jump], "fall": [fall]}
        self.sword_sprite = self._make_sword()
        self.pickaxe_sprite = self._make_pickaxe()

    def set_player_style(self, appearance: dict):
        self.build_player(appearance)

    def frames_for_appearance(self, appearance: dict) -> dict:
        """Кадры чужого героя для сетевого кооператива (с кэшем)."""
        style = dict(config.DEFAULT_APPEARANCE)
        for key in style:
            try:
                style[key] = int(appearance.get(key, style[key]))
            except (TypeError, ValueError):
                pass
        cache_key = tuple(style[k] for k in
                          ("skin", "hair", "shirt", "pants", "hair_style"))
        cached = self._appearance_cache.get(cache_key)
        if cached is not None:
            return cached
        old = self.player_style
        self.player_style = style
        try:
            walk = [self._player_frame(frame / 6.0 * math.tau, "walk")
                    for frame in range(6)]
            idle = [self._player_frame(0.0, "idle"), self._player_frame(math.pi, "idle")]
            frames = {
                "idle": idle, "walk": walk,
                "jump": [self._player_frame(0.0, "jump")],
                "fall": [self._player_frame(0.0, "fall")],
            }
        finally:
            self.player_style = old
        if len(self._appearance_cache) > 8:
            self._appearance_cache.pop(next(iter(self._appearance_cache)))
        self._appearance_cache[cache_key] = frames
        return frames

    @staticmethod
    def _pick(palette, index):
        try:
            return palette[int(index) % len(palette)]
        except (IndexError, ValueError, TypeError):
            return palette[0]

    def _player_frame(self, phase: float, state: str) -> pygame.Surface:
        s = _surf(38, 64)
        style = self.player_style
        skin = self._pick(config.SKIN_TONES, style.get("skin", 1))
        hair = self._pick(config.HAIR_COLORS, style.get("hair", 0))
        shirt = self._pick(config.SHIRT_COLORS, style.get("shirt", 0))
        pants = self._pick(config.PANTS_COLORS, style.get("pants", 0))
        skin_dark = tuple(max(0, c - 30) for c in skin)
        skin_light = tuple(min(255, c + 18) for c in skin)
        shirt_light = tuple(min(255, int(c * 1.18) + 4) for c in shirt)
        shirt_dark = tuple(max(0, int(c * 0.70)) for c in shirt)
        pants_dark = tuple(max(0, int(c * 0.72)) for c in pants)
        hair_dark = tuple(max(0, int(c * 0.66)) for c in hair)
        hair_light = tuple(min(255, int(c * 1.20) + 8) for c in hair)
        boots = (58, 42, 33)
        boots_light = (88, 64, 47)
        outline = (27, 22, 24)
        belt = (74, 52, 37)
        scarf = (184, 65, 57)
        scarf_light = (218, 91, 75)
        scarf_dark = (126, 42, 42)
        hair_style = int(style.get("hair_style", 0)) % config.HAIR_STYLE_COUNT

        walking = state == "walk"
        air = state in ("jump", "fall")
        step = math.sin(phase)
        bob = 0
        if state == "idle":
            bob = int(math.sin(phase) > 0.2)
        elif walking:
            bob = int(abs(step) > 0.62)
        if air:
            bob = -2
        lift_l = int(max(0.0, step) * 2.4) if walking else 0
        lift_r = int(max(0.0, -step) * 2.4) if walking else 0
        arm_swing = int(round(step * 2.5)) if walking else 0

        # Задняя масса волос — рисуется до тела, поэтому не перекрывает лицо.
        if hair_style == 1:
            pygame.draw.rect(s, hair_dark, (7, 5, 25, 33), border_radius=10)
            pygame.draw.rect(s, hair, (8, 6, 23, 30), border_radius=9)
            pygame.draw.rect(s, hair_dark, (27, 12, 4, 22), border_radius=2)
        elif hair_style == 3:
            for bx in (5, 33):
                pygame.draw.circle(s, hair_dark, (bx, 19), 6)
                pygame.draw.circle(s, hair, (bx, 19), 5)

        # Шея и уши.
        pygame.draw.rect(s, outline, (15, 19, 9, 9))
        pygame.draw.rect(s, skin_dark, (16, 19, 7, 8))
        for ear_x in (6, 28):
            pygame.draw.rect(s, outline, (ear_x, 11, 5, 8), border_radius=3)
            pygame.draw.rect(s, skin_dark, (ear_x + 1, 12, 3, 6), border_radius=2)

        # Ноги: задняя — темнее, передняя — светлее.
        leg_y = 42 + bob
        if air:
            back_y, front_y = leg_y - 1, leg_y + 2
            back_h, front_h = 11, 9
        else:
            back_y, front_y = leg_y + lift_l, leg_y + lift_r
            back_h = front_h = 17
        pygame.draw.rect(s, outline, (11, back_y, 10, back_h + 3), border_radius=3)
        pygame.draw.rect(s, pants_dark, (12, back_y + 1, 8, back_h), border_radius=2)
        pygame.draw.rect(s, outline, (18, front_y, 10, front_h + 4), border_radius=3)
        pygame.draw.rect(s, pants, (19, front_y + 1, 8, front_h + 1), border_radius=2)
        pygame.draw.line(s, pants_dark, (25, front_y + 3), (25, front_y + 12), 1)
        # Ботинки.
        boot_back_y = back_y + back_h
        boot_front_y = front_y + front_h + 1
        pygame.draw.rect(s, outline, (10, boot_back_y, 11, 6), border_radius=3)
        pygame.draw.rect(s, boots, (11, boot_back_y + 1, 9, 4), border_radius=2)
        pygame.draw.rect(s, outline, (17, boot_front_y, 12, 6), border_radius=3)
        pygame.draw.rect(s, boots, (18, boot_front_y + 1, 10, 4), border_radius=2)
        pygame.draw.line(s, boots_light, (19, boot_front_y + 1), (26, boot_front_y + 1), 1)

        # Задняя рука.
        shoulder_y = 27 + bob
        if air:
            back_hand = (3, 34 + bob)
            front_hand = (34, 32 + bob)
        elif walking:
            back_hand = (6 - arm_swing, 39 + bob)
            front_hand = (31 + arm_swing, 39 + bob)
        else:
            back_hand = (7, 39 + bob)
            front_hand = (31, 39 + bob)

        def draw_arm(shoulder, hand, sleeve, hand_color):
            pygame.draw.line(s, outline, shoulder, hand, 7)
            pygame.draw.line(s, sleeve, shoulder, hand, 5)
            pygame.draw.line(s, tuple(min(255, c + 12) for c in sleeve),
                             (shoulder[0], shoulder[1] + 2), (hand[0], hand[1] - 2), 1)
            pygame.draw.circle(s, outline, hand, 4)
            pygame.draw.circle(s, hand_color, hand, 3)
            pygame.draw.circle(s, skin_light, (hand[0] - 1, hand[1] - 1), 1)

        draw_arm((12, shoulder_y), back_hand, shirt_dark, skin_dark)

        # Корпус с мягким объёмом и поясом.
        body_top = 23 + bob
        body_bottom = 43 + bob
        pygame.draw.polygon(s, outline, [(9, body_top), (29, body_top),
                                         (27, body_bottom), (11, body_bottom)])
        pygame.draw.polygon(s, shirt, [(10, body_top + 1), (28, body_top + 1),
                                       (26, body_bottom - 1), (12, body_bottom - 1)])
        pygame.draw.polygon(s, shirt_light, [(10, body_top + 2), (14, body_top + 2),
                                             (13, body_bottom - 2), (12, body_bottom - 1)])
        pygame.draw.polygon(s, shirt_dark, [(24, body_top + 2), (28, body_top + 2),
                                            (26, body_bottom - 1), (23, body_bottom - 2)])
        pygame.draw.line(s, shirt_dark, (18, body_top + 4), (18, body_bottom - 5), 1)
        pygame.draw.rect(s, outline, (11, body_bottom - 5, 16, 6))
        pygame.draw.rect(s, belt, (12, body_bottom - 4, 14, 4))
        pygame.draw.rect(s, (204, 158, 73), (18, body_bottom - 4, 3, 4))
        pygame.draw.rect(s, (248, 214, 126), (19, body_bottom - 3, 1, 1))

        # Хвост шарфа — позади передней руки.
        tail_sway = int(round(math.sin(phase + 0.7) * 1.5)) if not air else -3
        tail_outline = [(25, 24 + bob), (29, 25 + bob), (35, 29 + bob + tail_sway),
                        (32, 32 + bob + tail_sway), (27, 28 + bob)]
        tail_fill = [(26, 25 + bob), (29, 26 + bob), (33, 29 + bob + tail_sway),
                     (31, 30 + bob + tail_sway), (27, 28 + bob)]
        pygame.draw.polygon(s, outline, tail_outline)
        pygame.draw.polygon(s, scarf, tail_fill)
        pygame.draw.line(s, scarf_light, (28, 27 + bob), (32, 30 + bob + tail_sway), 1)

        # Передняя рука.
        draw_arm((26, shoulder_y), front_hand, shirt, skin)
        pygame.draw.line(s, outline, (front_hand[0] - 2, front_hand[1] + 3),
                         (front_hand[0] + 2, front_hand[1] + 3), 1)

        # Голова.
        head_y = 3 + bob
        pygame.draw.rect(s, outline, (9, head_y, 20, 21), border_radius=6)
        pygame.draw.rect(s, skin, (10, head_y + 1, 18, 19), border_radius=5)
        pygame.draw.rect(s, skin_dark, (25, head_y + 5, 3, 12), border_radius=1)
        pygame.draw.rect(s, skin_light, (13, head_y + 4, 5, 3), border_radius=1)
        pygame.draw.line(s, skin_dark, (17, head_y + 19), (23, head_y + 19), 1)

        # Причёски: короткая, длинная, взъерошенная и две косички.
        if hair_style == 0:
            pygame.draw.polygon(s, hair_dark, [(8, head_y + 8), (9, head_y + 2),
                                               (13, head_y - 1), (25, head_y - 1),
                                               (29, head_y + 2), (30, head_y + 9),
                                               (27, head_y + 6), (23, head_y + 5),
                                               (19, head_y + 7), (15, head_y + 5),
                                               (11, head_y + 7)])
            pygame.draw.polygon(s, hair, [(9, head_y + 7), (10, head_y + 2),
                                          (14, head_y + 1), (24, head_y + 1),
                                          (28, head_y + 3), (29, head_y + 8),
                                          (25, head_y + 5), (21, head_y + 5),
                                          (18, head_y + 7), (14, head_y + 5),
                                          (11, head_y + 6)])
            pygame.draw.polygon(s, hair_dark, [(9, head_y + 5), (12, head_y + 3),
                                               (13, head_y + 10), (10, head_y + 11)])
            pygame.draw.polygon(s, hair_dark, [(28, head_y + 5), (26, head_y + 8),
                                               (29, head_y + 12), (30, head_y + 7)])
            pygame.draw.line(s, hair_light, (13, head_y + 2), (22, head_y + 2), 1)
        elif hair_style == 1:
            pygame.draw.polygon(s, hair_dark, [(8, head_y + 8), (9, head_y + 1),
                                               (14, head_y - 2), (24, head_y - 2),
                                               (29, head_y + 1), (30, head_y + 9),
                                               (26, head_y + 7), (22, head_y + 10),
                                               (18, head_y + 7), (14, head_y + 10),
                                               (11, head_y + 7)])
            pygame.draw.polygon(s, hair, [(9, head_y + 7), (10, head_y + 2),
                                          (15, head_y), (23, head_y),
                                          (28, head_y + 2), (29, head_y + 8),
                                          (25, head_y + 6), (21, head_y + 8),
                                          (17, head_y + 6), (13, head_y + 8),
                                          (11, head_y + 6)])
            pygame.draw.line(s, hair_dark, (19, head_y), (19, head_y + 6), 1)
            pygame.draw.line(s, hair_light, (12, head_y + 2), (18, head_y + 2), 1)
            # Передние пряди поверх щёк.
            pygame.draw.polygon(s, hair_dark, [(7, head_y + 5), (11, head_y + 6),
                                               (10, head_y + 23), (8, head_y + 26),
                                               (7, head_y + 17)])
            pygame.draw.polygon(s, hair_dark, [(27, head_y + 6), (31, head_y + 5),
                                               (31, head_y + 18), (29, head_y + 25),
                                               (27, head_y + 22)])
            pygame.draw.polygon(s, hair, [(8, head_y + 7), (10, head_y + 7),
                                          (9, head_y + 22), (8, head_y + 24)])
            pygame.draw.polygon(s, hair, [(28, head_y + 7), (30, head_y + 7),
                                          (30, head_y + 22), (29, head_y + 23)])
        elif hair_style == 2:
            pygame.draw.polygon(s, hair_dark, [(8, head_y + 9), (7, head_y + 4),
                                               (12, head_y + 6), (13, head_y + 1),
                                               (17, head_y + 5), (19, head_y - 2),
                                               (22, head_y + 4), (25, head_y),
                                               (27, head_y + 6), (31, head_y + 4),
                                               (30, head_y + 10), (26, head_y + 8),
                                               (23, head_y + 6), (20, head_y + 9),
                                               (17, head_y + 6), (14, head_y + 9),
                                               (11, head_y + 6)])
            pygame.draw.polygon(s, hair, [(9, head_y + 8), (9, head_y + 5),
                                          (13, head_y + 6), (14, head_y + 2),
                                          (18, head_y + 5), (20, head_y + 1),
                                          (23, head_y + 5), (26, head_y + 2),
                                          (27, head_y + 7), (29, head_y + 6),
                                          (28, head_y + 9), (24, head_y + 7),
                                          (21, head_y + 6), (18, head_y + 8),
                                          (15, head_y + 6), (12, head_y + 8)])
            pygame.draw.line(s, hair_light, (12, head_y + 4), (17, head_y + 4), 1)
            pygame.draw.line(s, hair_light, (22, head_y + 3), (25, head_y + 5), 1)
            pygame.draw.polygon(s, hair_dark, [(8, head_y + 7), (11, head_y + 6),
                                               (11, head_y + 12), (9, head_y + 14)])
            pygame.draw.polygon(s, hair_dark, [(28, head_y + 7), (26, head_y + 7),
                                               (28, head_y + 13), (30, head_y + 12)])
        else:
            pygame.draw.polygon(s, hair_dark, [(8, head_y + 8), (9, head_y + 2),
                                               (14, head_y - 1), (18, head_y + 1),
                                               (20, head_y + 4), (22, head_y + 1),
                                               (26, head_y - 1), (29, head_y + 2),
                                               (30, head_y + 9), (26, head_y + 7),
                                               (22, head_y + 9), (18, head_y + 7),
                                               (13, head_y + 9), (10, head_y + 7)])
            pygame.draw.polygon(s, hair, [(9, head_y + 7), (10, head_y + 2),
                                          (14, head_y), (18, head_y + 2),
                                          (20, head_y + 5), (22, head_y + 2),
                                          (26, head_y), (28, head_y + 3),
                                          (29, head_y + 8), (26, head_y + 6),
                                          (22, head_y + 7), (18, head_y + 6),
                                          (13, head_y + 7), (11, head_y + 6)])
            pygame.draw.line(s, hair_dark, (19, head_y), (19, head_y + 5), 1)
            pygame.draw.line(s, hair_light, (12, head_y + 2), (17, head_y + 1), 1)
            for bx, tie_x in ((5, 8), (33, 30)):
                pygame.draw.ellipse(s, hair_dark, (bx - 5, head_y + 14, 10, 18))
                pygame.draw.ellipse(s, hair, (bx - 4, head_y + 15, 8, 16))
                pygame.draw.ellipse(s, hair_light, (bx - 3, head_y + 17, 3, 5))
                pygame.draw.rect(s, (202, 160, 76), (tie_x, head_y + 14, 3, 3))
                pygame.draw.rect(s, (235, 201, 113), (tie_x + 1, head_y + 14, 1, 1))

        # Лицо.
        eye_y = head_y + 9
        for ex in (13, 22):
            pygame.draw.rect(s, outline, (ex, eye_y, 4, 4), border_radius=1)
            pygame.draw.rect(s, (245, 242, 232), (ex + 1, eye_y + 1, 2, 2))
            pygame.draw.rect(s, (49, 43, 47), (ex + 1, eye_y + 1, 1, 2))
            pygame.draw.rect(s, (255, 255, 250), (ex + 2, eye_y + 1, 1, 1))
        pygame.draw.line(s, hair_dark, (13, eye_y - 2), (16, eye_y - 3), 1)
        pygame.draw.line(s, hair_dark, (22, eye_y - 3), (25, eye_y - 2), 1)
        pygame.draw.rect(s, skin_dark, (19, eye_y + 3, 1, 2))
        pygame.draw.line(s, (153, 91, 83), (17, eye_y + 7), (21, eye_y + 7), 1)
        pygame.draw.line(s, (225, 148, 127), (18, eye_y + 8), (20, eye_y + 8), 1)
        s.set_at((11, eye_y + 6), (219, 139, 126))
        s.set_at((27, eye_y + 6), (219, 139, 126))

        # Шарф поверх шеи.
        pygame.draw.polygon(s, outline, [(10, body_top + 1), (27, body_top + 1),
                                          (26, body_top + 5), (24, body_top + 7),
                                          (14, body_top + 7), (11, body_top + 5)])
        pygame.draw.polygon(s, scarf, [(11, body_top + 2), (26, body_top + 2),
                                        (25, body_top + 5), (23, body_top + 6),
                                        (15, body_top + 6), (12, body_top + 4)])
        pygame.draw.line(s, scarf_light, (12, body_top + 3), (24, body_top + 3), 1)
        pygame.draw.rect(s, (231, 177, 81), (18, body_top + 4, 2, 2))
        return s

    def _make_sword(self) -> pygame.Surface:
        s = _surf(56, 18)
        outline = (38, 30, 28)
        # Рукоять, навершие и обмотка.
        pygame.draw.circle(s, outline, (4, 9), 4)
        pygame.draw.circle(s, (121, 82, 49), (4, 9), 2)
        pygame.draw.line(s, outline, (5, 9), (16, 9), 7)
        pygame.draw.line(s, (91, 60, 38), (5, 9), (16, 9), 5)
        for x in (8, 11, 14):
            pygame.draw.line(s, (137, 95, 56), (x, 7), (x + 1, 11), 1)
        # Гарда.
        pygame.draw.rect(s, outline, (14, 3, 5, 12), border_radius=2)
        pygame.draw.rect(s, (207, 172, 83), (15, 4, 3, 10), border_radius=1)
        pygame.draw.line(s, (246, 217, 135), (16, 4), (16, 7), 1)
        # Клинок с тёмным контуром и долом.
        pygame.draw.polygon(s, outline, [(18, 4), (48, 4), (55, 9), (48, 14), (18, 14)])
        pygame.draw.polygon(s, (188, 201, 211), [(19, 5), (47, 5), (53, 9), (47, 13), (19, 13)])
        pygame.draw.polygon(s, (231, 240, 246), [(20, 6), (45, 6), (50, 9), (45, 8), (20, 8)])
        pygame.draw.line(s, (125, 140, 152), (20, 11), (47, 11), 1)
        pygame.draw.line(s, (245, 250, 255), (20, 7), (43, 7), 1)
        pygame.draw.polygon(s, (255, 255, 255), [(50, 9), (47, 7), (46, 9)])
        return s

    def _make_pickaxe(self) -> pygame.Surface:
        s = _surf(58, 20)
        outline = (38, 30, 28)
        # Деревянная рукоять.
        pygame.draw.line(s, outline, (4, 10), (40, 10), 7)
        pygame.draw.line(s, (99, 65, 40), (5, 10), (39, 10), 5)
        pygame.draw.line(s, (147, 102, 62), (7, 8), (36, 8), 1)
        pygame.draw.circle(s, outline, (4, 10), 4)
        pygame.draw.circle(s, (118, 79, 47), (4, 10), 2)
        # Голова кирки.
        pygame.draw.polygon(s, outline, [(31, 3), (45, 1), (55, 8), (54, 12),
                                          (45, 18), (34, 15), (39, 10), (35, 7)])
        pygame.draw.polygon(s, (164, 166, 178), [(33, 4), (45, 3), (53, 9), (52, 11),
                                                  (44, 16), (37, 14), (41, 10), (37, 7)])
        pygame.draw.polygon(s, (216, 220, 228), [(35, 5), (44, 4), (49, 8), (48, 10),
                                                  (43, 13), (39, 12), (42, 9)])
        pygame.draw.line(s, (125, 132, 143), (46, 4), (51, 8), 1)
        pygame.draw.line(s, (246, 249, 252), (35, 5), (42, 5), 1)
        return s

    # -------------------------------------------------------------- валуны
    def build_boulders(self):
        specs = {
            "normal": ((99, 96, 105), (148, 144, 151), (180, 177, 181)),
            "bouncy": ((132, 104, 83), (187, 149, 114), (222, 188, 143)),
            "life": ((128, 56, 88), (219, 102, 146), (255, 170, 195)),
            "lava": ((106, 57, 45), (222, 93, 38), (255, 196, 82)),
            "spider": ((77, 65, 84), (137, 117, 145), (190, 171, 194)),
            "rainbow": ((113, 89, 153), (208, 136, 214), (132, 214, 225)),
            "ghost": ((82, 125, 140), (151, 199, 212), (211, 247, 250)),
            "ice": ((119, 164, 192), (193, 232, 247), (237, 253, 255)),
        }
        for kind, (base, light, shine) in specs.items():
            s = _surf(60, 60)
            pygame.draw.ellipse(s, (18, 16, 19, 110), (4, 42, 52, 15))
            pygame.draw.circle(s, (28, 25, 29), (30, 31), 25)
            pygame.draw.circle(s, base, (30, 30), 23)
            pygame.draw.circle(s, light, (22, 22), 12)
            pygame.draw.ellipse(s, shine, (16, 16, 13, 8))
            rng = random.Random(sum(ord(c) for c in kind) * 31)
            for _ in range(5):
                x = rng.randrange(13, 47)
                y = rng.randrange(16, 46)
                pygame.draw.line(s, tuple(max(0, c - 36) for c in base),
                                 (x, y), (x + rng.randint(3, 8), y + rng.randint(2, 7)), 1)
            if kind == "bouncy":
                for y in (20, 31, 42):
                    pygame.draw.arc(s, (74, 51, 41), (10, y - 7, 40, 14), 3.3, 6.1, 2)
            elif kind == "life":
                pygame.draw.polygon(s, (255, 173, 200), [(30, 10), (37, 23), (34, 39), (30, 47),
                                                         (25, 39), (22, 23)])
                pygame.draw.line(s, (255, 232, 240), (29, 15), (29, 33), 1)
            elif kind == "lava":
                for a, b in ((15, 22), (24, 38), (39, 18), (43, 33)):
                    c = rng.choice([(255, 133, 38), (255, 196, 74)])
                    pygame.draw.line(s, c, (a, b), (a + 7, b + 5), 2)
            elif kind == "spider":
                for a, b in ((14, 14), (47, 15), (13, 42), (48, 41)):
                    pygame.draw.line(s, (220, 207, 224), (30, 30), (a, b), 1)
                pygame.draw.circle(s, (220, 207, 224), (30, 30), 2)
            elif kind == "rainbow":
                for i, col in enumerate([(238, 115, 120), (244, 196, 104), (119, 218, 134),
                                          (116, 176, 236), (188, 128, 230)]):
                    pygame.draw.arc(s, col, (11, 11, 38, 38), 3.55, 5.8, 2)
            elif kind == "ghost":
                veil = pygame.Surface((60, 60), pygame.SRCALPHA)
                pygame.draw.circle(veil, (210, 252, 255, 45), (30, 30), 26)
                s.blit(veil, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            elif kind == "ice":
                pygame.draw.line(s, (241, 255, 255), (18, 18), (24, 35), 1)
                pygame.draw.line(s, (241, 255, 255), (37, 16), (30, 34), 1)
                pygame.draw.line(s, (124, 191, 227), (22, 43), (35, 46), 1)
            if pygame.display.get_surface():
                s = s.convert_alpha()
            self.boulder_images[kind] = s

    def boulder_image(self, kind: str) -> pygame.Surface:
        return self.boulder_images.get(kind, self.boulder_images["normal"])

    # -------------------------------------------------------------- проводник
    def build_guide(self):
        frames = []
        for phase in (0.0, math.pi):
            s = _surf(46, 70)
            bob = int(math.sin(phase) > 0)
            outline = (24, 22, 27)
            robe = (44, 88, 100)
            robe_light = (67, 126, 133)
            robe_dark = (29, 59, 72)
            trim = (205, 166, 87)
            skin = (220, 174, 132)
            skin_dark = (170, 122, 90)
            beard = (214, 211, 194)
            beard_dark = (164, 157, 139)
            staff_wood = (92, 61, 39)
            # Посох за спиной.
            pygame.draw.line(s, outline, (34, 9 + bob), (40, 66), 5)
            pygame.draw.line(s, staff_wood, (34, 9 + bob), (39, 65), 3)
            pygame.draw.line(s, (139, 94, 56), (35, 14 + bob), (38, 59), 1)
            pygame.draw.circle(s, (36, 72, 91), (34, 8 + bob), 7)
            pygame.draw.circle(s, (103, 180, 202), (34, 8 + bob), 5)
            pygame.draw.circle(s, (197, 242, 245), (33, 7 + bob), 2)
            # Обувь.
            pygame.draw.rect(s, outline, (11, 61, 12, 7), border_radius=3)
            pygame.draw.rect(s, outline, (26, 61, 11, 7), border_radius=3)
            pygame.draw.rect(s, (64, 48, 38), (12, 62, 10, 5), border_radius=2)
            pygame.draw.rect(s, (64, 48, 38), (27, 62, 9, 5), border_radius=2)
            # Мантия с мягким силуэтом.
            pygame.draw.polygon(s, outline, [(14, 28 + bob), (33, 28 + bob),
                                              (36, 64), (9, 64)])
            pygame.draw.polygon(s, robe, [(15, 29 + bob), (32, 29 + bob),
                                          (35, 63), (10, 63)])
            pygame.draw.polygon(s, robe_light, [(16, 30 + bob), (21, 30 + bob),
                                                (18, 62), (12, 62)])
            pygame.draw.polygon(s, robe_dark, [(28, 30 + bob), (32, 30 + bob),
                                               (34, 62), (27, 62)])
            pygame.draw.line(s, robe_dark, (22, 32 + bob), (24, 62), 1)
            pygame.draw.line(s, robe_light, (19, 33 + bob), (18, 59), 1)
            # Пояс из шнура.
            pygame.draw.line(s, outline, (14, 45 + bob), (33, 45 + bob), 4)
            pygame.draw.line(s, trim, (15, 45 + bob), (32, 45 + bob), 2)
            pygame.draw.circle(s, (92, 65, 42), (24, 46 + bob), 3)
            # Рукава и руки.
            pygame.draw.polygon(s, outline, [(12, 31 + bob), (16, 30 + bob),
                                              (19, 45 + bob), (14, 47 + bob)])
            pygame.draw.polygon(s, robe_dark, [(13, 32 + bob), (16, 32 + bob),
                                                (18, 44 + bob), (15, 45 + bob)])
            pygame.draw.polygon(s, outline, [(31, 31 + bob), (35, 32 + bob),
                                              (38, 43 + bob), (34, 45 + bob)])
            pygame.draw.polygon(s, robe_light, [(32, 32 + bob), (34, 33 + bob),
                                                 (36, 42 + bob), (34, 43 + bob)])
            pygame.draw.circle(s, outline, (34, 44 + bob), 4)
            pygame.draw.circle(s, skin, (34, 44 + bob), 3)
            pygame.draw.circle(s, outline, (14, 46 + bob), 4)
            pygame.draw.circle(s, skin_dark, (14, 46 + bob), 3)
            # Голова, капюшон и борода.
            pygame.draw.rect(s, outline, (13, 11 + bob, 22, 26), border_radius=8)
            pygame.draw.rect(s, robe_dark, (14, 12 + bob, 20, 24), border_radius=7)
            pygame.draw.polygon(s, outline, [(15, 15 + bob), (23, 10 + bob),
                                              (33, 16 + bob), (32, 25 + bob),
                                              (28, 30 + bob), (18, 30 + bob),
                                              (14, 24 + bob)])
            pygame.draw.polygon(s, robe, [(16, 16 + bob), (23, 12 + bob),
                                           (31, 17 + bob), (30, 24 + bob),
                                           (27, 28 + bob), (19, 28 + bob),
                                           (15, 23 + bob)])
            pygame.draw.rect(s, outline, (17, 17 + bob, 15, 14), border_radius=5)
            pygame.draw.rect(s, skin_dark, (18, 18 + bob, 13, 12), border_radius=4)
            pygame.draw.rect(s, skin, (19, 18 + bob, 11, 10), border_radius=3)
            # Брови и глаза.
            pygame.draw.line(s, beard_dark, (20, 21 + bob), (23, 20 + bob), 1)
            pygame.draw.line(s, beard_dark, (26, 20 + bob), (29, 21 + bob), 1)
            pygame.draw.circle(s, (41, 37, 39), (22, 23 + bob), 2)
            pygame.draw.circle(s, (41, 37, 39), (27, 23 + bob), 2)
            pygame.draw.circle(s, (235, 239, 235), (22, 22 + bob), 1)
            pygame.draw.circle(s, (235, 239, 235), (26, 22 + bob), 1)
            pygame.draw.line(s, skin_dark, (24, 25 + bob), (26, 25 + bob), 1)
            # Послойная борода и усы.
            pygame.draw.polygon(s, outline, [(17, 28 + bob), (31, 28 + bob),
                                              (31, 35 + bob), (27, 40 + bob),
                                              (23, 37 + bob), (19, 40 + bob),
                                              (16, 34 + bob)])
            pygame.draw.polygon(s, beard, [(18, 29 + bob), (30, 29 + bob),
                                            (29, 34 + bob), (26, 38 + bob),
                                            (23, 35 + bob), (20, 38 + bob),
                                            (18, 33 + bob)])
            pygame.draw.line(s, beard_dark, (21, 31 + bob), (21, 35 + bob), 1)
            pygame.draw.line(s, beard_dark, (26, 31 + bob), (26, 35 + bob), 1)
            pygame.draw.line(s, (236, 233, 218), (19, 28 + bob), (23, 30 + bob), 1)
            pygame.draw.line(s, (236, 233, 218), (23, 30 + bob), (28, 28 + bob), 1)
            # Блик на капюшоне.
            pygame.draw.arc(s, (92, 151, 155), (16, 13 + bob, 20, 18), 3.3, 5.4, 1)
            if pygame.display.get_surface():
                s = s.convert_alpha()
            frames.append(s)
        self.guide_frames = frames

    # -------------------------------------------------------------- кузнец
    def build_blacksmith(self):
        frames = []
        for phase in (0.0, math.pi):
            s = _surf(56, 76)
            bob = int(math.sin(phase) > 0)
            outline = (26, 22, 21)
            skin = (228, 179, 133)
            skin_dark = (178, 126, 88)
            beard = (122, 73, 41)
            beard_light = (163, 104, 61)
            shirt = (94, 69, 51)
            shirt_dark = (63, 47, 38)
            apron = (112, 72, 45)
            apron_dark = (79, 49, 33)
            pants = (62, 54, 48)
            boots = (45, 35, 30)
            steel = (146, 150, 161)
            steel_light = (216, 221, 229)
            # тень и ноги
            pygame.draw.ellipse(s, (0, 0, 0, 70), (7, 66, 42, 9))
            for x in (18, 29):
                pygame.draw.rect(s, outline, (x, 51 + bob, 11, 18), border_radius=3)
                pygame.draw.rect(s, pants, (x + 1, 52 + bob, 9, 15), border_radius=2)
            pygame.draw.rect(s, outline, (16, 66, 14, 7), border_radius=3)
            pygame.draw.rect(s, outline, (28, 66, 14, 7), border_radius=3)
            pygame.draw.rect(s, boots, (17, 67, 12, 5), border_radius=2)
            pygame.draw.rect(s, boots, (29, 67, 12, 5), border_radius=2)
            # широкий корпус и фартук
            pygame.draw.polygon(s, outline, [(13, 26 + bob), (40, 26 + bob),
                                              (38, 54 + bob), (15, 54 + bob)])
            pygame.draw.polygon(s, shirt, [(14, 27 + bob), (39, 27 + bob),
                                            (37, 53 + bob), (16, 53 + bob)])
            pygame.draw.polygon(s, shirt_dark, [(28, 28 + bob), (39, 28 + bob),
                                                 (37, 53 + bob), (27, 53 + bob)])
            pygame.draw.polygon(s, outline, [(18, 31 + bob), (36, 31 + bob),
                                              (35, 61 + bob), (19, 61 + bob)])
            pygame.draw.polygon(s, apron, [(19, 32 + bob), (35, 32 + bob),
                                            (34, 60 + bob), (20, 60 + bob)])
            pygame.draw.line(s, apron_dark, (23, 36 + bob), (24, 59 + bob), 2)
            pygame.draw.rect(s, (54, 38, 28), (21, 34 + bob, 13, 4), border_radius=2)
            pygame.draw.circle(s, (198, 157, 80), (24, 36 + bob), 2)
            pygame.draw.circle(s, (198, 157, 80), (31, 36 + bob), 2)
            # руки: одна на поясе, вторая держит молот
            pygame.draw.rect(s, outline, (8, 29 + bob, 11, 24), border_radius=4)
            pygame.draw.rect(s, shirt_dark, (9, 30 + bob, 9, 18), border_radius=3)
            pygame.draw.circle(s, outline, (13, 53 + bob), 6)
            pygame.draw.circle(s, skin_dark, (13, 53 + bob), 4)
            pygame.draw.rect(s, outline, (40, 28 + bob, 10, 25), border_radius=4)
            pygame.draw.rect(s, shirt, (41, 29 + bob, 8, 18), border_radius=3)
            pygame.draw.circle(s, outline, (45, 52 + bob), 6)
            pygame.draw.circle(s, skin, (45, 52 + bob), 4)
            # голова: лысина, кустистые брови, борода
            pygame.draw.rect(s, outline, (15, 6 + bob, 27, 26), border_radius=8)
            pygame.draw.rect(s, skin_dark, (16, 7 + bob, 25, 24), border_radius=7)
            pygame.draw.rect(s, skin, (17, 7 + bob, 23, 20), border_radius=6)
            pygame.draw.ellipse(s, (247, 208, 166), (20, 7 + bob, 14, 7))
            pygame.draw.rect(s, outline, (14, 20 + bob, 29, 15), border_radius=6)
            pygame.draw.polygon(s, beard, [(16, 21 + bob), (41, 21 + bob),
                                            (39, 32 + bob), (34, 39 + bob),
                                            (28, 36 + bob), (22, 39 + bob),
                                            (16, 32 + bob)])
            pygame.draw.polygon(s, beard_light, [(18, 22 + bob), (38, 22 + bob),
                                                  (36, 28 + bob), (28, 31 + bob),
                                                  (20, 28 + bob)])
            pygame.draw.line(s, (94, 58, 34), (24, 27 + bob), (24, 35 + bob), 1)
            pygame.draw.line(s, (94, 58, 34), (32, 27 + bob), (32, 35 + bob), 1)
            pygame.draw.line(s, beard_light, (20, 20 + bob), (34, 20 + bob), 4)
            pygame.draw.rect(s, (62, 43, 34), (20, 16 + bob, 7, 2))
            pygame.draw.rect(s, (62, 43, 34), (29, 16 + bob, 7, 2))
            pygame.draw.circle(s, (39, 31, 30), (23, 18 + bob), 2)
            pygame.draw.circle(s, (39, 31, 30), (32, 18 + bob), 2)
            pygame.draw.circle(s, (255, 248, 226), (23, 17 + bob), 1)
            pygame.draw.circle(s, (255, 248, 226), (32, 17 + bob), 1)
            pygame.draw.rect(s, skin_dark, (26, 21 + bob, 5, 3), border_radius=2)
            # молот на плече
            pygame.draw.line(s, outline, (46, 16 + bob), (42, 4 + bob), 5)
            pygame.draw.line(s, (120, 79, 48), (45, 15 + bob), (42, 5 + bob), 3)
            pygame.draw.rect(s, outline, (31, 2 + bob, 23, 11), border_radius=3)
            pygame.draw.rect(s, steel, (33, 4 + bob, 19, 7), border_radius=2)
            pygame.draw.line(s, steel_light, (34, 4 + bob), (48, 4 + bob), 1)
            if pygame.display.get_surface():
                s = s.convert_alpha()
            frames.append(s)
        self.blacksmith_frames = frames

    # -------------------------------------------------------------- травница
    def build_herbalist(self):
        frames = []
        for phase in (0.0, math.pi):
            s = _surf(52, 74)
            bob = int(math.sin(phase) > 0)
            outline = (25, 24, 23)
            skin = (234, 187, 142)
            skin_dark = (185, 134, 97)
            robe = (75, 118, 76)
            robe_light = (105, 155, 99)
            robe_dark = (51, 84, 58)
            hat = (207, 179, 114)
            hat_dark = (159, 130, 75)
            hair = (141, 81, 44)
            hair_light = (187, 117, 64)
            basket = (148, 105, 58)
            # тень и ноги
            pygame.draw.ellipse(s, (0, 0, 0, 70), (7, 64, 39, 9))
            pygame.draw.rect(s, outline, (18, 54 + bob, 8, 16), border_radius=2)
            pygame.draw.rect(s, outline, (28, 55 + bob, 8, 15), border_radius=2)
            pygame.draw.rect(s, robe_dark, (19, 55 + bob, 6, 14), border_radius=2)
            pygame.draw.rect(s, robe_dark, (29, 56 + bob, 6, 13), border_radius=2)
            pygame.draw.rect(s, (73, 54, 39), (17, 65, 11, 5), border_radius=2)
            pygame.draw.rect(s, (73, 54, 39), (27, 66, 11, 5), border_radius=2)
            # платье
            pygame.draw.polygon(s, outline, [(15, 27 + bob), (36, 27 + bob),
                                              (40, 65), (11, 65)])
            pygame.draw.polygon(s, robe, [(16, 28 + bob), (35, 28 + bob),
                                          (39, 64), (12, 64)])
            pygame.draw.polygon(s, robe_light, [(17, 29 + bob), (22, 29 + bob),
                                                (19, 63), (15, 63)])
            pygame.draw.polygon(s, robe_dark, [(31, 29 + bob), (35, 29 + bob),
                                               (37, 63), (32, 63)])
            pygame.draw.line(s, (194, 170, 96), (14, 47 + bob), (37, 47 + bob), 2)
            pygame.draw.circle(s, (201, 156, 74), (26, 47 + bob), 3)
            # руки
            pygame.draw.polygon(s, outline, [(13, 29 + bob), (18, 29 + bob),
                                              (20, 48 + bob), (15, 49 + bob)])
            pygame.draw.polygon(s, robe_dark, [(14, 30 + bob), (17, 30 + bob),
                                                (18, 47 + bob), (15, 47 + bob)])
            pygame.draw.circle(s, outline, (16, 49 + bob), 4)
            pygame.draw.circle(s, skin_dark, (16, 49 + bob), 3)
            pygame.draw.polygon(s, outline, [(34, 29 + bob), (39, 29 + bob),
                                              (42, 47 + bob), (37, 48 + bob)])
            pygame.draw.polygon(s, robe, [(35, 30 + bob), (38, 30 + bob),
                                           (40, 46 + bob), (37, 46 + bob)])
            pygame.draw.circle(s, outline, (40, 48 + bob), 4)
            pygame.draw.circle(s, skin, (40, 48 + bob), 3)
            # корзина с травами
            pygame.draw.rect(s, outline, (36, 50 + bob, 13, 11), border_radius=3)
            pygame.draw.rect(s, basket, (37, 51 + bob, 11, 9), border_radius=2)
            for i in range(3):
                pygame.draw.line(s, (78, 132, 70), (38 + i * 4, 51 + bob),
                                 (36 + i * 4, 45 + bob), 1)
                pygame.draw.circle(s, (128, 188, 106), (36 + i * 4, 44 + bob), 2)
            # голова
            pygame.draw.rect(s, outline, (15, 8 + bob, 22, 23), border_radius=7)
            pygame.draw.rect(s, skin_dark, (16, 9 + bob, 20, 21), border_radius=6)
            pygame.draw.rect(s, skin, (17, 9 + bob, 18, 18), border_radius=5)
            # косы
            pygame.draw.ellipse(s, hair, (10, 14 + bob, 9, 27))
            pygame.draw.ellipse(s, hair, (34, 15 + bob, 8, 24))
            pygame.draw.line(s, hair_light, (13, 17 + bob), (12, 32 + bob), 1)
            pygame.draw.line(s, hair_light, (37, 18 + bob), (36, 30 + bob), 1)
            pygame.draw.circle(s, (202, 159, 77), (14, 34 + bob), 2)
            pygame.draw.circle(s, (202, 159, 77), (36, 32 + bob), 2)
            # соломенная шляпа
            pygame.draw.ellipse(s, outline, (7, 3 + bob, 39, 8))
            pygame.draw.ellipse(s, hat_dark, (8, 4 + bob, 37, 6))
            pygame.draw.ellipse(s, outline, (18, -2 + bob, 19, 14))
            pygame.draw.ellipse(s, hat, (19, -1 + bob, 17, 12))
            pygame.draw.line(s, (235, 209, 145), (21, 2 + bob), (33, 2 + bob), 1)
            pygame.draw.rect(s, (94, 134, 78), (21, 5 + bob, 15, 3), border_radius=1)
            # лицо
            pygame.draw.rect(s, (64, 45, 35), (21, 15 + bob, 5, 2))
            pygame.draw.rect(s, (64, 45, 35), (29, 15 + bob, 5, 2))
            pygame.draw.circle(s, (59, 50, 42), (23, 18 + bob), 2)
            pygame.draw.circle(s, (59, 50, 42), (31, 18 + bob), 2)
            pygame.draw.circle(s, (255, 250, 234), (23, 17 + bob), 1)
            pygame.draw.circle(s, (255, 250, 234), (31, 17 + bob), 1)
            pygame.draw.line(s, (180, 106, 92), (26, 24 + bob), (30, 24 + bob), 1)
            s.set_at((20, 22 + bob), (222, 147, 127))
            s.set_at((34, 22 + bob), (222, 147, 127))
            # цветок за лентой шляпы
            pygame.draw.circle(s, (216, 109, 142), (37, 6 + bob), 3)
            pygame.draw.circle(s, (246, 196, 121), (37, 6 + bob), 1)
            if pygame.display.get_surface():
                s = s.convert_alpha()
            frames.append(s)
        self.herbalist_frames = frames

    # -------------------------------------------------------------- иконки
    def build_icons(self):
        for item_id in config.ITEMS:
            if item_id in ("gel",):
                img = self._icon_gel()
            elif item_id in ("heal_potion",):
                img = self._icon_potion()
            elif item_id in ("slime_crown",):
                img = self._icon_crown()
            elif item_id in ("slime_core",):
                img = self._icon_slime_core()
            elif item_id in ("abyss_sigil",):
                img = self._icon_sigil()
            elif item_id in ("forest_idol",):
                img = self._icon_forest_idol()
            elif item_id == "forest_heart":
                img = self._icon_forest_heart()
            elif item_id in ("frost_diadem",):
                img = self._icon_frost_diadem()
            elif item_id == "frost_tear":
                img = self._icon_frost_tear()
            elif item_id in ("life_crystal",):
                img = pygame.transform.scale(self.tile_image(config.LIFE_CRYSTAL), (40, 40))
                img = _outline(img, width=1)
            else:
                tile = config.ITEMS[item_id].tile
                if tile is None:
                    img = _surf(40, 40)
                    pygame.draw.circle(img, (120, 120, 130), (20, 20), 14)
                else:
                    img = pygame.transform.scale(self.tile_image(tile), (40, 40))
                    img = _outline(img, width=1)
            if pygame.display.get_surface():
                img = img.convert_alpha()
            self.item_icons[item_id] = img

        self.pickaxe_icon = pygame.transform.smoothscale(self.pickaxe_sprite, (44, 14))
        self.sword_icon = pygame.transform.smoothscale(self.sword_sprite, (44, 13))

    def _icon_gel(self):
        s = _surf(44, 44)
        pygame.draw.ellipse(s, (28, 72, 50), (6, 11, 32, 27))
        pygame.draw.ellipse(s, (76, 196, 121), (7, 10, 30, 25))
        pygame.draw.ellipse(s, (117, 227, 151), (11, 13, 20, 15))
        pygame.draw.ellipse(s, (201, 255, 217), (13, 14, 8, 5))
        pygame.draw.circle(s, (58, 162, 96), (13, 29), 3)
        pygame.draw.circle(s, (58, 162, 96), (31, 26), 2)
        return _outline(s, width=1)

    def _icon_potion(self):
        s = _surf(44, 44)
        pygame.draw.rect(s, (69, 46, 32), (18, 4, 8, 5), border_radius=2)
        pygame.draw.rect(s, (208, 218, 224), (19, 8, 6, 8))
        pygame.draw.circle(s, (225, 232, 236), (22, 26), 12)
        pygame.draw.circle(s, (178, 44, 58), (22, 27), 9)
        pygame.draw.circle(s, (232, 81, 86), (20, 24), 5)
        pygame.draw.ellipse(s, (255, 183, 178), (17, 21, 5, 3))
        pygame.draw.circle(s, (225, 232, 236), (22, 26), 12, 1)
        return _outline(s, width=1)

    def _icon_crown(self):
        s = _surf(44, 44)
        pts = [(5, 30), (7, 12), (15, 21), (22, 7), (29, 21), (37, 12), (39, 30)]
        pygame.draw.polygon(s, (91, 57, 21), [(x + 1, y + 2) for x, y in pts])
        pygame.draw.polygon(s, (227, 177, 59), pts)
        pygame.draw.polygon(s, (250, 212, 103), [(8, 27), (9, 16), (17, 24), (22, 11), (27, 24), (35, 16), (36, 27)])
        pygame.draw.rect(s, (191, 138, 38), (8, 28, 28, 7), border_radius=2)
        pygame.draw.polygon(s, (208, 63, 108), [(22, 26), (27, 29), (22, 34), (17, 29)])
        pygame.draw.circle(s, (255, 157, 194), (22, 29), 2)
        pygame.draw.circle(s, (246, 226, 151), (9, 13), 2)
        pygame.draw.circle(s, (246, 226, 151), (35, 13), 2)
        return _outline(s, width=1)

    def _icon_slime_core(self):
        s = _surf(44, 44)
        pygame.draw.circle(s, (28, 63, 44), (22, 23), 16)
        pygame.draw.circle(s, (58, 157, 100), (22, 23), 13)
        pygame.draw.circle(s, (128, 232, 167), (18, 19), 6)
        pygame.draw.circle(s, (237, 255, 238), (17, 17), 2)
        pygame.draw.arc(s, (21, 78, 48), (12, 16, 20, 18), 3.2, 6.2, 2)
        pygame.draw.polygon(s, (245, 202, 94), [(13, 8), (16, 2), (22, 7), (27, 2), (30, 9),
                                                 (27, 12), (16, 12)])
        pygame.draw.circle(s, (221, 88, 137), (22, 9), 2)
        return _outline(s, width=1)

    def _icon_sigil(self):
        s = _surf(44, 44)
        pygame.draw.polygon(s, (27, 24, 34), [(22, 2), (38, 12), (34, 37), (22, 42), (10, 37), (6, 12)])
        pygame.draw.polygon(s, (80, 61, 105), [(22, 5), (34, 14), (31, 34), (22, 38), (13, 34), (10, 14)])
        pygame.draw.polygon(s, (126, 91, 164), [(22, 9), (30, 16), (28, 30), (22, 34), (16, 30), (14, 16)])
        pygame.draw.circle(s, (198, 139, 230), (22, 21), 7)
        pygame.draw.circle(s, (27, 24, 34), (22, 21), 4)
        pygame.draw.circle(s, (106, 226, 228), (22, 21), 2)
        for x, y in ((16, 11), (29, 12), (22, 37), (15, 30), (30, 27)):
            pygame.draw.circle(s, (213, 171, 240), (x, y), 1)
        return _outline(s, width=1)

    def _icon_forest_idol(self):
        s = _surf(44, 44)
        # Резной идол из тёмного дерева с зелёным сердцем.
        pygame.draw.polygon(s, (42, 30, 22), [(22, 2), (35, 9), (38, 30), (22, 42),
                                               (6, 30), (9, 9)])
        pygame.draw.polygon(s, (105, 71, 40), [(22, 5), (32, 11), (35, 28), (22, 38),
                                                (9, 28), (12, 11)])
        pygame.draw.polygon(s, (137, 96, 54), [(22, 8), (29, 12), (31, 26), (22, 33),
                                                (13, 26), (15, 12)])
        pygame.draw.line(s, (75, 49, 29), (22, 10), (22, 34), 1)
        pygame.draw.line(s, (75, 49, 29), (14, 18), (30, 18), 1)
        pygame.draw.ellipse(s, (36, 71, 44), (15, 14, 14, 16))
        pygame.draw.ellipse(s, (76, 161, 91), (17, 16, 10, 12))
        pygame.draw.circle(s, (179, 239, 168), (20, 18), 2)
        pygame.draw.arc(s, (62, 44, 27), (11, 8, 22, 20), 3.4, 6.0, 1)
        for x, y in ((11, 33), (33, 33), (22, 40)):
            pygame.draw.line(s, (69, 45, 28), (x, y), (x + (1 if x < 22 else -1), y + 3), 1)
        return _outline(s, width=1)

    def _icon_forest_heart(self):
        s = _surf(44, 44)
        pygame.draw.ellipse(s, (29, 55, 33), (6, 8, 32, 30))
        pygame.draw.ellipse(s, (54, 111, 63), (8, 9, 28, 26))
        pygame.draw.ellipse(s, (105, 183, 98), (13, 13, 18, 18))
        pygame.draw.ellipse(s, (198, 245, 175), (16, 15, 8, 6))
        # Прожилки-корни.
        for a in range(6):
            ang = a * math.tau / 6 + 0.3
            x1 = 22 + math.cos(ang) * 8
            y1 = 22 + math.sin(ang) * 8
            x2 = 22 + math.cos(ang) * 16
            y2 = 22 + math.sin(ang) * 15
            pygame.draw.line(s, (44, 92, 52), (x1, y1), (x2, y2), 2)
        pygame.draw.circle(s, (150, 220, 122), (22, 22), 4)
        pygame.draw.circle(s, (233, 255, 196), (20, 20), 1)
        pygame.draw.ellipse(s, (75, 138, 73), (12, 28, 20, 9), 1)
        return _outline(s, width=1)

    def _icon_frost_diadem(self):
        s = _surf(44, 44)
        pts = [(6, 31), (8, 13), (16, 22), (22, 6), (28, 22), (36, 13), (38, 31)]
        pygame.draw.polygon(s, (27, 53, 78), [(x + 1, y + 2) for x, y in pts])
        pygame.draw.polygon(s, (171, 217, 243), pts)
        pygame.draw.polygon(s, (221, 246, 255), [(10, 28), (11, 18), (18, 25), (22, 11),
                                                  (26, 25), (33, 18), (34, 28)])
        pygame.draw.rect(s, (95, 158, 206), (10, 29, 24, 6), border_radius=2)
        pygame.draw.polygon(s, (128, 220, 238), [(22, 25), (27, 29), (22, 36), (17, 29)])
        pygame.draw.circle(s, (241, 255, 255), (22, 30), 2)
        for x, y in ((10, 14), (36, 14), (14, 30), (30, 30)):
            pygame.draw.circle(s, (244, 255, 255), (x, y), 2)
        pygame.draw.line(s, (245, 255, 255), (16, 10), (18, 15), 1)
        return _outline(s, width=1)

    def _icon_frost_tear(self):
        s = _surf(44, 44)
        pygame.draw.polygon(s, (27, 49, 73), [(22, 3), (33, 19), (30, 32), (22, 41), (14, 32), (11, 19)])
        pygame.draw.polygon(s, (131, 196, 232), [(22, 6), (30, 20), (28, 30), (22, 37),
                                                  (16, 30), (14, 20)])
        pygame.draw.polygon(s, (211, 243, 255), [(22, 9), (26, 19), (22, 27), (18, 19)])
        pygame.draw.line(s, (245, 254, 255), (19, 13), (17, 22), 1)
        pygame.draw.circle(s, (255, 255, 255), (25, 15), 2)
        # Морозные лучи вокруг.
        for ang in (0.2, 1.1, 2.3, 4.0, 5.3):
            x1 = 22 + math.cos(ang) * 13
            y1 = 22 + math.sin(ang) * 16
            x2 = 22 + math.cos(ang) * 19
            y2 = 22 + math.sin(ang) * 20
            pygame.draw.line(s, (200, 241, 255), (x1, y1), (x2, y2), 1)
        return _outline(s, width=1)

    def icon(self, item_id: str) -> pygame.Surface:
        return self.item_icons.get(item_id, self.item_icons["stone"])

    # -------------------------------------------------------------- UI
    def build_ui(self):
        self.heart_full = self._heart((214, 57, 71), (255, 128, 132))
        self.heart_half = self._heart((214, 57, 71), (255, 128, 132), half=True)
        self.heart_empty = self._heart((71, 49, 54), (98, 66, 70))
        self.sun = self._sun()
        self.moon = self._moon()

    def _heart(self, base, light, half=False):
        s = _surf(22, 20)
        pygame.draw.polygon(s, (36, 22, 24), [(2, 10), (4, 5), (8, 2), (11, 4), (14, 2), (18, 5), (20, 10),
                                               (18, 15), (11, 19), (4, 15)])
        pygame.draw.polygon(s, base, [(3, 9), (5, 5), (8, 3), (11, 5), (14, 3), (17, 5), (19, 9),
                                      (17, 14), (11, 17), (5, 14)])
        pygame.draw.polygon(s, light, [(5, 6), (8, 4), (10, 6), (8, 9), (5, 8)])
        pygame.draw.circle(s, (255, 244, 238), (7, 6), 1)
        if half:
            for x in range(11, 22):
                pygame.draw.line(s, (0, 0, 0, 0), (x, 0), (x, 20))
            mask = pygame.Surface((22, 20), pygame.SRCALPHA)
            mask.fill((0, 0, 0, 0))
            pygame.draw.polygon(mask, (255, 255, 255, 255), [(2, 10), (4, 5), (8, 2), (11, 4),
                                                             (11, 17), (5, 14)])
            s.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        return s

    def _sun(self):
        s = _surf(120, 120)
        for r, a in ((58, 25), (48, 40), (40, 65), (32, 255)):
            pygame.draw.circle(s, (255, 219, 128, a), (60, 60), r)
        pygame.draw.circle(s, (255, 244, 188), (60, 60), 26)
        pygame.draw.circle(s, (255, 255, 236), (55, 54), 12)
        return s

    def _moon(self):
        s = _surf(110, 110)
        pygame.draw.circle(s, (228, 232, 244, 35), (55, 55), 47)
        pygame.draw.circle(s, (226, 231, 243), (55, 55), 34)
        pygame.draw.circle(s, (201, 208, 226), (44, 46), 7)
        pygame.draw.circle(s, (208, 214, 230), (66, 66), 5)
        pygame.draw.circle(s, (214, 219, 234), (62, 38), 4)
        return s

    # -------------------------------------------------------------- свет
    def light_mask(self, radius: int) -> pygame.Surface:
        radius = max(8, int(radius))
        radius = (radius // 8) * 8
        key = ("mask", radius)
        surf = self._light_cache.get(key)
        if surf is not None:
            return surf
        size = radius * 2
        surf = _surf(size, size)
        steps = max(32, radius)
        for i in range(steps, 0, -1):
            r = int(radius * i / steps)
            alpha = int(255 * (1.0 - i / steps) ** 1.4)
            pygame.draw.circle(surf, (255, 255, 255, alpha), (radius, radius), r)
        self._light_cache[key] = surf
        return surf

    def glow(self, radius: int, color=(255, 170, 80)) -> pygame.Surface:
        radius = max(8, int(radius))
        radius = (radius // 8) * 8
        key = ("glow", radius, color)
        surf = self._glow_cache.get(key)
        if surf is not None:
            return surf
        size = radius * 2
        # Непрозрачная поверхность для аддитивного смешивания: яркость
        # нарастает к центру, но не выжигает пиксели в сплошной оранжевый диск.
        surf = pygame.Surface((size, size))
        surf.fill((0, 0, 0))
        steps = max(32, radius // 2)
        for i in range(steps, 0, -1):
            r = int(radius * i / steps)
            f = (1.0 - i / steps) ** 1.8
            c = (int(color[0] * 0.30 * f), int(color[1] * 0.30 * f), int(color[2] * 0.30 * f))
            pygame.draw.circle(surf, c, (radius, radius), r)
        self._glow_cache[key] = surf
        return surf

    def draw_item(self, surf: pygame.Surface, item_id: str, rect: pygame.Rect, scale: float = 1.0):
        icon = self.icon(item_id)
        if scale != 1.0:
            w = max(1, int(icon.get_width() * scale))
            h = max(1, int(icon.get_height() * scale))
            icon = pygame.transform.smoothscale(icon, (w, h))
        r = icon.get_rect(center=rect.center)
        surf.blit(icon, r)

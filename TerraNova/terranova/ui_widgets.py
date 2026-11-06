# -*- coding: utf-8 -*-
"""Фон, кнопки, слайдеры и мелкие элементы интерфейса."""
from __future__ import annotations

import math
import random

import pygame

from . import config
from .config import WIDTH, HEIGHT
from .utils import clamp, lerp, lerp_color, draw_text


SKY_STOPS = [
    (0.00, (33, 30, 62), (204, 113, 101), 0.55),
    (0.08, (64, 112, 178), (236, 190, 155), 0.08),
    (0.20, (74, 146, 218), (173, 221, 243), 0.0),
    (0.40, (70, 130, 200), (210, 219, 226), 0.0),
    (0.48, (55, 77, 133), (233, 132, 94), 0.35),
    (0.54, (27, 36, 77), (105, 78, 112), 0.72),
    (0.62, (8, 13, 35), (30, 38, 74), 1.0),
    (0.88, (9, 15, 38), (35, 43, 82), 0.95),
    (0.96, (40, 40, 78), (126, 85, 112), 0.62),
    (1.00, (33, 30, 62), (204, 113, 101), 0.55),
]


def sky_values(t: float):
    t = t % 1.0
    for i in range(len(SKY_STOPS) - 1):
        t0, top0, bot0, night0 = SKY_STOPS[i]
        t1, top1, bot1, night1 = SKY_STOPS[i + 1]
        if t0 <= t <= t1:
            f = (t - t0) / max(1e-6, t1 - t0)
            return (lerp_color(top0, top1, f), lerp_color(bot0, bot1, f),
                    lerp(night0, night1, f))
    return SKY_STOPS[-1][1], SKY_STOPS[-1][2], SKY_STOPS[-1][3]


class Backdrop:
    def __init__(self):
        rng = random.Random(90210)
        self.stars = [(rng.randrange(0, WIDTH), rng.randrange(8, 420),
                       rng.random() * math.tau, rng.choice([1, 1, 1, 2])) for _ in range(110)]
        self.cloud_images = []
        for _ in range(5):
            self.cloud_images.append(self._make_cloud(rng, rng.uniform(0.7, 1.5)))
        self.clouds = []
        for _ in range(9):
            self.clouds.append({
                "x": rng.randrange(0, WIDTH + 500),
                "y": rng.randrange(65, 300),
                "img": rng.choice(self.cloud_images),
                "speed": rng.uniform(3.0, 8.0),
                "alpha": rng.randint(55, 125),
            })
        self.fireflies = [{
            "x": rng.randrange(620, 1250), "y": rng.randrange(400, 690),
            "phase": rng.random() * math.tau, "speed": rng.uniform(0.5, 1.4),
            "amp": rng.uniform(12, 40),
        } for _ in range(24)]
        self.time = 0.0
        self._hero_sil = None
        self._menu_sun = None
        self._silhouettes = {}

    @staticmethod
    def _make_cloud(rng, scale):
        w, h = int(180 * scale), int(58 * scale)
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        color = (236, 241, 245, 160)
        for i in range(7):
            cx = int(w * (0.12 + 0.12 * i) + rng.randint(-5, 5))
            cy = int(h * (0.55 + rng.uniform(-0.16, 0.12)))
            rx = int(w * rng.uniform(0.11, 0.2))
            ry = int(h * rng.uniform(0.28, 0.45))
            pygame.draw.ellipse(s, color, (cx - rx, cy - ry, rx * 2, ry * 2))
        return s

    def update(self, dt):
        self.time += dt

    def _celestial(self, surf, assets, t, menu):
        if menu:
            # Утреннее солнце над лесом — как на классическом меню Terraria,
            # но с мягким тёплым ореолом и лучами.
            if self._menu_sun is None:
                self._menu_sun = pygame.transform.smoothscale(assets.sun, (138, 138))
            sx, sy = 1012, 174
            halo = self._menu_glow(164, (255, 212, 120), 46)
            surf.blit(halo, (sx - 164, sy - 164))
            surf.blit(self._menu_sun, (sx - 69, sy - 69))
            return
        if t < 0.5:
            p = t / 0.5
            x = -140 + p * (WIDTH + 280)
            y = 430 - math.sin(p * math.pi) * 380
            img = assets.sun.copy()
            img.set_alpha(int(255 * clamp(math.sin(p * math.pi) * 2.0, 0, 1)))
            surf.blit(img, (x - 60, y - 60))
        else:
            p = (t - 0.5) / 0.5
            x = -140 + p * (WIDTH + 280)
            y = 430 - math.sin(p * math.pi) * 380
            img = assets.moon.copy()
            img.set_alpha(int(255 * clamp(math.sin(p * math.pi) * 2.0, 0, 1)))
            surf.blit(img, (x - 55, y - 55))

    def draw(self, surf, assets, t, cam_x=0.0, underground=0.0, menu=False):
        top, bottom, night = sky_values(0.60 if menu else t)
        if menu:
            top, bottom, night = (63, 139, 205), (181, 220, 201), 0.0
        bands = 28
        for i in range(bands):
            c = lerp_color(top, bottom, i / (bands - 1))
            pygame.draw.rect(surf, c, (0, i * HEIGHT / bands, WIDTH, HEIGHT / bands + 2))

        if night > 0.02:
            for x, y, ph, size in self.stars:
                tw = 0.55 + 0.45 * math.sin(self.time * 1.7 + ph)
                a = int(230 * night * tw)
                if a <= 2:
                    continue
                star = pygame.Surface((size * 3, size * 3), pygame.SRCALPHA)
                pygame.draw.circle(star, (232, 238, 255, a), (size * 3 // 2, size * 3 // 2), size)
                sx = (x - cam_x * 0.015) % (WIDTH + 20) - 10
                surf.blit(star, (int(sx), y), special_flags=pygame.BLEND_RGBA_ADD)

        self._celestial(surf, assets, 0.60 if menu else t, menu)

        for cl in self.clouds:
            sx = (cl["x"] - cam_x * 0.12 - self.time * cl["speed"]) % (WIDTH + 600) - 300
            img = cl["img"].copy()
            a = int(cl["alpha"] * (1.35 if menu else 1.0) * (1.0 - night * 0.4))
            img.set_alpha(max(20, a))
            surf.blit(img, (int(sx), cl["y"]))

        if underground < 0.75 and not menu:
            for layer, (base, amp) in enumerate(((450, 34), (545, 52))):
                factor = 0.22 + layer * 0.15
                ph = 1.2 + layer * 2.1
                col = lerp_color(lerp_color(bottom, (20, 30, 35), 0.55 + layer * 0.16),
                                 (12, 14, 20), night * 0.45)
                if menu:
                    col = (22, 28, 35) if layer == 0 else (15, 20, 26)
                pts = [(-40, HEIGHT + 40)]
                for x in range(-40, WIDTH + 64, 26):
                    wx = x + cam_x * factor
                    y = (base if not menu else base + 110) + math.sin(wx * 0.0038 + ph) * amp \
                        + math.sin(wx * 0.011 + ph * 2.7) * amp * 0.28
                    pts.append((x, int(y)))
                pts.append((WIDTH + 40, HEIGHT + 40))
                pygame.draw.polygon(surf, col, pts)

        if menu:
            self._draw_menu_scene(surf, assets)
        elif underground > 0.01:
            a = int(255 * clamp(underground, 0, 1))
            for i in range(24):
                c = lerp_color((30, 23, 22), (7, 6, 9), i / 23)
                band = pygame.Surface((WIDTH, HEIGHT // 24 + 2), pygame.SRCALPHA)
                band.fill((*c, a))
                surf.blit(band, (0, i * HEIGHT // 24))

    def _menu_glow(self, radius, color, max_alpha=40):
        key = ("glow", radius, color, max_alpha)
        cached = self._silhouettes.get(key)
        if cached is not None:
            return cached
        glow = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        for r in range(radius, 0, -2):
            t = r / radius
            a = max(1, int(max_alpha * (1.0 - t * t)))
            pygame.draw.circle(glow, (*color, a), (radius, radius), r)
        self._silhouettes[key] = glow
        return glow

    def _menu_silhouette(self, frame, color, scale=1.0):
        key = (id(frame), color, round(scale, 2))
        cached = self._silhouettes.get(key)
        if cached is not None:
            return cached
        mask = pygame.mask.from_surface(frame)
        sil = mask.to_surface(setcolor=(*color, 255), unsetcolor=(0, 0, 0, 0))
        if scale != 1.0:
            sil = pygame.transform.smoothscale(
                sil, (max(1, int(frame.get_width() * scale)),
                      max(1, int(frame.get_height() * scale)))
            )
        self._silhouettes[key] = sil
        return sil

    @staticmethod
    def _menu_pine(surf, x, base_y, height, color, trunk_color=None):
        trunk_color = trunk_color or color
        pygame.draw.rect(surf, trunk_color, (x - 3, base_y - height * 0.18,
                                           6, height * 0.2))
        for i in range(4):
            top = base_y - height + i * height * 0.19
            half = height * (0.13 + i * 0.075)
            pygame.draw.polygon(surf, color, [
                (x, top), (x - half, top + height * 0.42),
                (x - half * 0.55, top + height * 0.34),
                (x + half * 0.55, top + height * 0.34),
                (x + half, top + height * 0.42),
            ])

    def _draw_menu_scene(self, surf, assets):
        def ridge(base, amp, phase, color):
            pts = [(-60, HEIGHT + 30)]
            for x in range(-60, WIDTH + 80, 30):
                y = (base + math.sin(x * 0.0042 + phase) * amp
                     + math.sin(x * 0.012 + phase * 2.1) * amp * 0.24)
                pts.append((x, int(y)))
            pts.append((WIDTH + 60, HEIGHT + 30))
            pygame.draw.polygon(surf, color, pts)

        # Три плана гор и леса дают эффект глубины даже в 2D-меню.
        ridge(392, 46, 0.7, (121, 171, 165))
        ridge(468, 54, 1.7, (88, 141, 124))
        ridge(540, 46, 3.1, (56, 108, 83))

        pines = [
            (548, 505, 88, (59, 113, 84)), (592, 512, 64, (54, 107, 79)),
            (631, 500, 100, (48, 100, 74)), (678, 514, 58, (57, 111, 82)),
            (735, 500, 86, (47, 98, 71)), (808, 508, 64, (54, 106, 78)),
            (868, 500, 94, (47, 98, 71)), (930, 512, 66, (56, 109, 80)),
            (1030, 498, 96, (45, 95, 68)), (1198, 505, 76, (46, 98, 70)),
            (1256, 512, 58, (54, 107, 79)),
        ]
        for x, base, h, col in pines:
            self._menu_pine(surf, x, base, h, col, (37, 82, 62))

        # Большое дерево на правом склоне.
        trunk = (32, 63, 43)
        pygame.draw.polygon(surf, trunk, [(1146, 710), (1132, 448), (1120, 372),
                                          (1162, 382), (1172, 462), (1196, 710)])
        for bx, by, ang, ln in ((1150, 424, -0.5, 92), (1154, 492, 0.4, 82),
                                (1144, 354, -0.8, 72)):
            pygame.draw.line(surf, trunk, (bx, by),
                             (bx + math.cos(ang) * ln, by + math.sin(ang) * ln), 12)
        canopy = [(1090, 358, 80), (1178, 326, 94), (1258, 382, 74),
                  (1140, 278, 82), (1218, 258, 68), (1052, 286, 54)]
        for x, y, r in canopy:
            pygame.draw.circle(surf, (34, 70, 44), (x, y), r)
            pygame.draw.circle(surf, (46, 88, 52),
                               (int(x - r * 0.18), int(y - r * 0.22)), int(r * 0.68))
            pygame.draw.circle(surf, (58, 106, 60),
                               (int(x - r * 0.31), int(y - r * 0.40)), int(r * 0.40))

        # Передний травяной склон.
        pygame.draw.polygon(surf, (39, 82, 50), [(-60, 648), (130, 628), (330, 642),
                                                  (560, 620), (790, 638), (1040, 616),
                                                  (1330, 642), (1330, 790), (-60, 790)])
        pygame.draw.polygon(surf, (53, 99, 58), [(-60, 647), (130, 627), (330, 641),
                                                  (560, 619), (790, 637), (1040, 615),
                                                  (1330, 641), (1330, 647), (-60, 653)])
        for i in range(64):
            gx = 500 + i * 13 + (i * 37) % 11
            gy = 628 + (i * 17) % 14
            pygame.draw.line(surf, (31, 70, 44), (gx, gy), (gx + 3, gy - 8 - (i % 4) * 3), 2)

        # Кострище и тёплый свет — центр маленькой сцены.
        fx, fy = 782, 660
        for i in range(7):
            ang = i * math.tau / 7
            sx = fx + math.cos(ang) * 25
            sy = fy + math.sin(ang) * 8 + 1
            pygame.draw.circle(surf, (78, 76, 65), (int(sx), int(sy)), 5)
            pygame.draw.circle(surf, (102, 100, 83), (int(sx) - 1, int(sy) - 2), 2)
        pygame.draw.line(surf, (66, 40, 26), (fx - 18, fy), (fx + 17, fy - 5), 5)
        pygame.draw.line(surf, (79, 50, 30), (fx - 19, fy - 5), (fx + 16, fy), 4)
        flame = 1.0 + math.sin(self.time * 5.2) * 0.12
        pygame.draw.circle(surf, (198, 77, 34), (fx, fy - 8), int(11 * flame))
        pygame.draw.circle(surf, (246, 153, 57), (fx, fy - 10), int(7 * flame))
        pygame.draw.circle(surf, (255, 228, 126), (fx + 1, fy - 13), int(3 * flame))
        glow = self._menu_glow(104, (255, 150, 68), 34)
        surf.blit(glow, (fx - 104, fy - 105))

        # Дым от костра.
        for i in range(3):
            p = (self.time * 0.16 + i / 3.0) % 1.0
            alpha = int(26 * (1.0 - p))
            puff = pygame.Surface((36, 36), pygame.SRCALPHA)
            pygame.draw.circle(puff, (210, 220, 205, alpha), (18, 18),
                               int(7 + p * 13))
            surf.blit(puff, (fx - 18 + math.sin(self.time * 0.6 + i * 2) * 6,
                             fy - 22 - int(p * 86)))

        # Жители и герой: Проводник, Бран и Мирра у костра.
        scenes = [
            (assets.guide_frames[0], 1.68, 706, 668, -1),
            (assets.blacksmith_frames[0], 1.78, 968, 670, -1),
            (assets.herbalist_frames[0], 1.66, 1052, 670, -1),
        ]
        for frame, scale, x, ground, facing in scenes:
            img = pygame.transform.smoothscale(
                frame, (int(frame.get_width() * scale), int(frame.get_height() * scale)))
            if facing > 0:
                img = pygame.transform.flip(img, True, False)
            shadow = pygame.Surface((img.get_width() + 16, 12), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow, (16, 34, 20, 95), shadow.get_rect())
            surf.blit(shadow, (x - shadow.get_width() // 2, ground + 2))
            surf.blit(img, (x - img.get_width() // 2, ground - img.get_height() + 4))

        hero_frame = assets.player_frames["idle"][0]
        hero = pygame.transform.smoothscale(
            hero_frame, (int(hero_frame.get_width() * 2.05),
                         int(hero_frame.get_height() * 2.05)))
        hx, hy = 872, 666
        shadow = pygame.Surface((hero.get_width() + 16, 12), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (16, 34, 20, 100), shadow.get_rect())
        surf.blit(shadow, (hx - shadow.get_width() // 2, hy + 2))
        surf.blit(hero, (hx - hero.get_width() // 2, hy - hero.get_height() + 4))
        pygame.draw.line(surf, (64, 53, 43), (hx + 16, hy - 64), (hx + 68, hy - 132), 7)
        pygame.draw.line(surf, (206, 196, 172), (hx + 17, hy - 65), (hx + 66, hy - 130), 2)

        # Лёгкая подсветка от костра на силуэтах.
        warm = self._menu_glow(92, (255, 170, 92), 16)
        surf.blit(warm, (fx - 92, fy - 92))

        # Пыльца и светлячки над травой.
        for f in self.fireflies:
            x = f["x"] + math.sin(self.time * f["speed"] + f["phase"]) * f["amp"]
            y = f["y"] + math.cos(self.time * f["speed"] * 0.7 + f["phase"]) * 14
            a = int(70 + 80 * (0.5 + 0.5 * math.sin(self.time * 2.3 + f["phase"])))
            dot = pygame.Surface((12, 12), pygame.SRCALPHA)
            pygame.draw.circle(dot, (255, 246, 175, a), (6, 6), 2)
            surf.blit(dot, (x - 6, y - 6), special_flags=pygame.BLEND_RGBA_ADD)


class Button:
    def __init__(self, text, rect, on_click, enabled=True, accent=False, subtitle="",
                 font_size=26):
        self.text = text
        self.rect = pygame.Rect(rect)
        self.on_click = on_click
        self.enabled = enabled
        self.accent = accent
        self.subtitle = subtitle
        self.font_size = font_size
        self.hover = 0.0
        self.offset = 0.0

    def update(self, dt, mouse):
        inside = self.enabled and self.rect.collidepoint(mouse)
        target = 1.0 if inside else 0.0
        self.hover += (target - self.hover) * min(1.0, dt * 12)
        self.offset = -3 * self.hover

    def handle_event(self, event) -> bool:
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            if self.on_click:
                self.on_click()
            return True
        return False

    def draw(self, surf, assets):
        r = self.rect.move(0, int(self.offset))
        base = (58, 43, 35) if self.enabled else (36, 33, 34)
        if self.hover:
            base = lerp_color(base, (86, 63, 42), self.hover)
        layer = pygame.Surface(r.size, pygame.SRCALPHA)
        pygame.draw.rect(layer, (*base, 238), layer.get_rect(), border_radius=10)
        border = config.GOLD if (self.accent or self.hover > 0.3) and self.enabled else (99, 78, 56)
        pygame.draw.rect(layer, (*border, 255), layer.get_rect(), width=2, border_radius=10)
        pygame.draw.line(layer, (122, 97, 70, 90), (12, 2), (r.width - 12, 2), 1)
        surf.blit(layer, r.topleft)
        col = config.CREAM if self.enabled else (112, 108, 103)
        text_size = min(self.font_size, 22) if self.subtitle else self.font_size
        draw_text(surf, self.text, assets.font(text_size, bold=True), col,
                  (r.x + 22, r.y + (8 if self.subtitle else r.height // 2)),
                  "topleft" if self.subtitle else "midleft", shadow=True)
        if self.subtitle:
            draw_text(surf, self.subtitle, assets.font(13), (163, 151, 133),
                      (r.x + 22, r.y + 33), "topleft")
        if self.enabled and self.hover > 0.2:
            draw_text(surf, "›", assets.font(30, bold=True), config.GOLD,
                      (r.right - 24, r.centery + 1), "center", alpha=int(255 * self.hover))


class Slider:
    def __init__(self, label, rect, value, on_change):
        self.label = label
        self.rect = pygame.Rect(rect)
        self.value = clamp(value, 0.0, 1.0)
        self.on_change = on_change
        self.dragging = False

    def handle_event(self, event):
        hit = self.rect.inflate(22, 24)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and hit.collidepoint(event.pos):
            self.dragging = True
            self._set_from_x(event.pos[0])
            return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        if event.type == pygame.MOUSEMOTION and self.dragging:
            self._set_from_x(event.pos[0])
            return True
        return False

    def _set_from_x(self, x):
        value = clamp((x - self.rect.x) / max(1, self.rect.w), 0.0, 1.0)
        self.value = value
        if self.on_change:
            self.on_change(value)

    def draw(self, surf, assets):
        draw_text(surf, self.label, assets.font(21, bold=True), config.CREAM,
                  (self.rect.x, self.rect.y - 30), "topleft")
        draw_text(surf, f"{int(self.value * 100)}%", assets.font(18), (185, 171, 148),
                  (self.rect.right, self.rect.y - 30), "topright")
        pygame.draw.rect(surf, (24, 20, 21), self.rect, border_radius=5)
        fill = pygame.Rect(self.rect.x, self.rect.y, int(self.rect.w * self.value), self.rect.h)
        pygame.draw.rect(surf, (190, 146, 67), fill, border_radius=5)
        pygame.draw.line(surf, (238, 198, 106), (self.rect.x + 3, self.rect.y + 2),
                         (max(self.rect.x + 3, fill.right - 3), self.rect.y + 2), 1)
        kx = self.rect.x + int(self.rect.w * self.value)
        pygame.draw.circle(surf, (46, 34, 29), (kx, self.rect.centery), 11)
        pygame.draw.circle(surf, config.GOLD, (kx, self.rect.centery), 8)
        pygame.draw.circle(surf, (255, 231, 160), (kx - 2, self.rect.centery - 2), 3)


def key_chip(surf, assets, x, y, key, width=None):
    font = assets.font(15, bold=True)
    w = width or max(42, font.size(key)[0] + 16)
    rect = pygame.Rect(x, y, w, 26)
    pygame.draw.rect(surf, (28, 24, 24), rect, border_radius=5)
    pygame.draw.rect(surf, (105, 88, 67), rect, width=1, border_radius=5)
    draw_text(surf, key, font, (235, 219, 189), rect.center, "center")
    return rect

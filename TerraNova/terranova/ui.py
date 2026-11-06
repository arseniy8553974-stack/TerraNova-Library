# -*- coding: utf-8 -*-
"""Экраны меню, пауза, смерть и победа."""
from __future__ import annotations

import math
import random

import pygame

from . import config, crafting
from .config import WIDTH, HEIGHT, ITEMS, RARITY_COLORS
from .utils import draw_text, panel, lerp_color, clamp, wrap_text, game_clock
from .ui_widgets import Button, Slider, key_chip


class TextInput:
    """Однострочное поле ввода без сторонних зависимостей."""

    def __init__(self, rect, label, text="", placeholder="", max_len=32,
                 numeric=False, font_size=19):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.text = str(text)
        self.placeholder = placeholder
        self.max_len = max_len
        self.numeric = numeric
        self.font_size = font_size
        self.active = False
        self.cursor_time = 0.0

    def handle_event(self, event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.active = self.rect.collidepoint(event.pos)
            return self.active
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
                return True
            if event.key == pygame.K_DELETE:
                self.text = ""
                return True
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_TAB):
                self.active = False
                return False
            ch = event.unicode
            if ch and ch.isprintable() and len(self.text) < self.max_len:
                if self.numeric and not ch.isdigit():
                    return False
                self.text += ch
                return True
        return False

    def update(self, dt):
        self.cursor_time += dt

    def draw(self, surf, assets):
        draw_text(surf, self.label, assets.font(15, bold=True), (205, 178, 126),
                  (self.rect.x, self.rect.y - 23), "topleft")
        base = (43, 36, 34) if self.active else (32, 28, 28)
        pygame.draw.rect(surf, base, self.rect, border_radius=8)
        border = config.GOLD if self.active else (88, 70, 54)
        pygame.draw.rect(surf, border, self.rect, width=2 if self.active else 1,
                         border_radius=8)
        font = assets.font(self.font_size)
        shown = self.text or self.placeholder
        color = (239, 226, 199) if self.text else (125, 117, 107)
        draw_text(surf, shown, font, color, (self.rect.x + 14, self.rect.centery),
                  "midleft")
        if self.active and int(self.cursor_time * 2.4) % 2 == 0:
            cx = self.rect.x + 15 + font.size(self.text)[0]
            pygame.draw.line(surf, config.GOLD, (cx, self.rect.y + 11),
                             (cx, self.rect.bottom - 12), 2)


class MainMenu:
    def __init__(self, game):
        self.game = game
        self.buttons = []
        self.time = 0.0
        self.refresh()

    def refresh(self):
        game = self.game
        has_save = game.has_save()
        x, y, w, h = 96, 330, 318, 56
        self.buttons = [
            Button("Новая игра", (x, y, w, h), game.open_world_create, accent=True),
            Button("Продолжить", (x, y + h + 10, w, h), game.continue_game, enabled=has_save,
                   subtitle="" if has_save else "Сохранение не найдено"),
            Button("Сетевая игра", (x, y + 2 * (h + 10), w, h), game.open_network),
            Button("Персонаж", (x, y + 2 * (h + 10) + h + 16, 100, 44),
                   lambda: game.open_character("menu"), font_size=17),
            Button("Управление", (x + 109, y + 2 * (h + 10) + h + 16, 100, 44),
                   game.open_controls, font_size=16),
            Button("Кодекс", (x + 218, y + 2 * (h + 10) + h + 16, 100, 44),
                   lambda: game.open_codex("menu"), font_size=17),
            Button("Настройки", (x, y + 2 * (h + 10) + h + 70, 150, 44),
                   game.open_settings, font_size=19),
            Button("Выход", (x + 164, y + 2 * (h + 10) + h + 70, 154, 44),
                   game.quit_game, font_size=19),
        ]
        self.has_save = has_save

    def update(self, dt):
        self.time += dt
        mouse = pygame.mouse.get_pos()
        for b in self.buttons:
            b.update(dt, mouse)

    def handle_event(self, event):
        for b in self.buttons:
            if b.handle_event(event):
                self.game.audio.sfx("click", 0.7)
                return
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.game.audio.sfx("click", 0.7)
                if self.has_save:
                    self.game.continue_game()
                else:
                    self.game.open_world_create()
            elif event.key == pygame.K_ESCAPE:
                self.game.quit_game()
            elif event.key == pygame.K_k:
                self.game.audio.sfx("click", 0.5)
                self.game.open_codex("menu")

    def draw(self, surf):
        assets = self.game.assets
        # заголовок
        tag_font = assets.font(17, bold=True)
        draw_text(surf, "2D П Р И К Л Ю Ч Е Н И Е", tag_font, (207, 174, 118),
                  (98, 96), "topleft", shadow=True)
        title_font = assets.font(94, bold=True, title=True)
        draw_text(surf, "TERRA", title_font, (243, 205, 118), (90, 118), "topleft",
                  outline=3, shadow=True, shadow_color=(24, 19, 16))
        draw_text(surf, "NOVA", title_font, (243, 205, 118), (90, 210), "topleft",
                  outline=3, shadow=True, shadow_color=(24, 19, 16))
        assets.font(27, italic=True)
        draw_text(surf, "Хроники расколотого мира", assets.font(25, italic=True),
                  (226, 212, 186), (98, 298), "topleft", shadow=True)
        pygame.draw.line(surf, (147, 113, 63), (96, 330), (330, 330), 2)
        pygame.draw.polygon(surf, config.GOLD, [(396, 330), (402, 336), (396, 342), (390, 336)])

        for b in self.buttons:
            b.draw(surf, assets)

        # информация внизу
        draw_text(surf, "v1.0  •  Python + pygame", assets.font(15), (205, 220, 195),
                  (96, HEIGHT - 38), "topleft", shadow=True, shadow_color=(29, 49, 36))
        if self.has_save:
            draw_text(surf, "Enter — продолжить приключение", assets.font(15), (224, 234, 203),
                      (96, HEIGHT - 62), "topleft", shadow=True, shadow_color=(29, 49, 36))
        draw_text(surf, "K — достижения и бестиарий", assets.font(14), (205, 215, 185),
                  (96, HEIGHT - 86), "topleft", shadow=True, shadow_color=(29, 49, 36))


class WorldCreateScreen:
    """Выбор размера мира, имени и семени перед генерацией."""

    SIZE_ORDER = ("small", "medium", "large")
    SIZE_TIMES = {"small": "1–2 сек", "medium": "2–4 сек", "large": "4–8 сек"}

    def __init__(self, game):
        self.game = game
        self.size_key = game.settings.get("world_size", config.DEFAULT_WORLD_SIZE)
        self.name_input = TextInput((214, 150, 470, 44), "НАЗВАНИЕ МИРА",
                                    "Изумрудный мир", "Например, Терра Нова", max_len=28)
        self.seed_input = TextInput((746, 150, 324, 44), "СЕМЯ (НЕОБЯЗАТЕЛЬНО)",
                                    "", "случайное", max_len=10, numeric=True)
        self.card_rects = []
        self.random_seed_btn = Button("Случайное", (912, 204, 158, 30),
                                      self._random_seed, font_size=15)
        self.back_btn = Button("Назад", (180, 570, 190, 48), self._back, font_size=20)
        self.hero_btn = Button("Изменить героя", (806, 570, 214, 48), self._hero,
                               font_size=19)
        self.create_btn = Button("Создать мир", (510, 568, 260, 52), self._create,
                                 accent=True, font_size=22)
        self.error = ""
        self.refresh()

    def refresh(self, keep_fields=False):
        self.size_key = self.game.settings.get("world_size", config.DEFAULT_WORLD_SIZE)
        if not keep_fields:
            self.name_input.text = "Изумрудный мир"
            self.seed_input.text = ""
        self.name_input.active = False
        self.seed_input.active = False
        self.error = ""
        x0, gap, w = 188, 20, 288
        self.card_rects = [pygame.Rect(x0 + i * (w + gap), 244, w, 198)
                           for i in range(3)]

    def _random_seed(self):
        self.seed_input.text = str(random.randrange(1, 2_000_000_000))
        self.seed_input.active = False
        self.error = ""
        self.game.audio.sfx("click", 0.55)

    def _choose_size(self, key):
        if key != self.size_key:
            self.size_key = key
            self.game.audio.sfx("click", 0.55)

    def _hero(self):
        self.game.audio.sfx("click", 0.6)
        self.game.open_character("world_create")

    def _back(self):
        self.game.audio.sfx("click", 0.6)
        self.game.back_to_menu()

    def _create(self):
        name = self.name_input.text.strip() or "Новый мир"
        seed_text = self.seed_input.text.strip()
        try:
            seed = int(seed_text) if seed_text else None
        except ValueError:
            self.error = "Семя должно состоять из цифр."
            return
        self.error = ""
        self.game.settings["world_size"] = self.size_key
        self.game.save_settings()
        self.game.audio.sfx("summon", 0.45)
        self.game.start_new_world(self.size_key, seed, name)

    def update(self, dt):
        self.name_input.update(dt)
        self.seed_input.update(dt)
        mouse = pygame.mouse.get_pos()
        for b in (self.random_seed_btn, self.back_btn, self.hero_btn, self.create_btn):
            b.update(dt, mouse)

    def handle_event(self, event):
        consumed = False
        for field in (self.name_input, self.seed_input):
            if field.handle_event(event):
                consumed = True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._back()
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(self.card_rects):
                if rect.collidepoint(event.pos):
                    self._choose_size(self.SIZE_ORDER[i])
                    return
        for b in (self.random_seed_btn, self.back_btn, self.hero_btn, self.create_btn):
            if b.handle_event(event):
                self.game.audio.sfx("click", 0.65) if b is not self.create_btn else None
                return
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if not consumed and not self.name_input.active and not self.seed_input.active:
                self._create()

    def draw(self, surf):
        assets = self.game.assets
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((7, 10, 14, 231))
        surf.blit(veil, (0, 0))
        # декоративные контуры мира
        for i in range(5):
            y = 42 + i * 14
            pygame.draw.line(surf, (24 + i, 31 + i, 38 + i), (0, y), (WIDTH, y), 1)
        panel(surf, pygame.Rect(110, 30, 1060, 660), (27, 23, 24), 252,
              (104, 82, 56), 16)
        draw_text(surf, "СОЗДАНИЕ МИРА", assets.font(38, bold=True, title=True),
                  config.GOLD, (WIDTH // 2, 57), "center", outline=2)
        draw_text(surf, "Выберите масштаб приключения — мир будет создан заново",
                  assets.font(16, italic=True), (172, 160, 143),
                  (WIDTH // 2, 94), "center")

        self.name_input.draw(surf, assets)
        self.seed_input.draw(surf, assets)
        self.random_seed_btn.rect.topleft = (self.seed_input.rect.right - 158,
                                             self.seed_input.rect.bottom + 8)
        self.random_seed_btn.draw(surf, assets)
        draw_text(surf, "Семя задаёт рельеф и биомы. Пустое поле — случайный мир.",
                  assets.font(13), (126, 119, 106), (214, 203), "topleft")

        draw_text(surf, "РАЗМЕР МИРА", assets.font(16, bold=True), (218, 181, 113),
                  (188, 221), "topleft")
        mouse = pygame.mouse.get_pos()
        for i, key in enumerate(self.SIZE_ORDER):
            preset = config.WORLD_SIZES[key]
            rect = self.card_rects[i]
            selected = key == self.size_key
            hover = rect.collidepoint(mouse)
            base = (52, 40, 32) if selected else (37, 32, 31) if hover else (31, 27, 27)
            pygame.draw.rect(surf, base, rect, border_radius=11)
            border = config.GOLD if selected else (105, 83, 59) if hover else (67, 57, 48)
            pygame.draw.rect(surf, border, rect, width=2 if selected else 1, border_radius=11)
            # миниатюра ландшафта
            mini = pygame.Rect(rect.x + 18, rect.y + 16, rect.w - 36, 64)
            pygame.draw.rect(surf, (20, 28, 31), mini, border_radius=7)
            for band in range(5):
                col = lerp_color((45, 78, 91), (25, 37, 38), band / 4)
                pygame.draw.rect(surf, col, (mini.x, mini.y + band * 13, mini.w, 14))
            peaks = 1 if key == "small" else 2 if key == "medium" else 3
            for p_i in range(peaks):
                px = mini.x + 28 + p_i * 66
                pygame.draw.polygon(surf, (42, 61, 54),
                                    [(px, mini.bottom - 4), (px + 32, mini.y + 20),
                                     (px + 70, mini.bottom - 4)])
                pygame.draw.polygon(surf, (78, 103, 77),
                                    [(px + 22, mini.y + 35), (px + 32, mini.y + 20),
                                     (px + 47, mini.y + 42)])
            if selected:
                pygame.draw.circle(surf, config.GOLD, (rect.right - 22, rect.y + 72), 11)
                pygame.draw.lines(surf, (52, 40, 26), False,
                                  [(rect.right - 27, rect.y + 72),
                                   (rect.right - 23, rect.y + 77),
                                   (rect.right - 16, rect.y + 66)], 2)
            draw_text(surf, preset["name"].upper(), assets.font(24, bold=True),
                      config.CREAM if selected else (215, 202, 178),
                      (rect.x + 18, rect.y + 92), "topleft")
            draw_text(surf, f"{preset['w']} × {preset['h']} тайлов", assets.font(15, bold=True),
                      config.GOLD if selected else (164, 148, 123),
                      (rect.x + 18, rect.y + 124), "topleft")
            desc_lines = wrap_text(assets.font(13), preset["desc"], rect.w - 36)
            for j, line in enumerate(desc_lines[:2]):
                draw_text(surf, line, assets.font(13), (158, 147, 128),
                          (rect.x + 18, rect.y + 148 + j * 18))
            draw_text(surf, "генерация " + self.SIZE_TIMES[key], assets.font(12),
                      (117, 108, 95), (rect.right - 16, rect.bottom - 10), "bottomright")

        # герой
        strip = pygame.Rect(190, 452, 900, 78)
        panel(surf, strip, (33, 28, 28), 225, (75, 62, 48), 10)
        frame = assets.player_frames["idle"][int(self.game.time * 1.5) % 2]
        frame = pygame.transform.smoothscale(frame, (36, 60))
        surf.blit(frame, (strip.x + 16, strip.y + 9))
        draw_text(surf, "ВАШ ГЕРОЙ", assets.font(14, bold=True), (210, 176, 108),
                  (strip.x + 64, strip.y + 12))
        draw_text(surf, "Внешность можно изменить до создания мира.",
                  assets.font(14), (154, 143, 125), (strip.x + 64, strip.y + 35))

        self.back_btn.draw(surf, assets)
        self.hero_btn.draw(surf, assets)
        self.create_btn.draw(surf, assets)
        if self.error:
            draw_text(surf, self.error, assets.font(14, bold=True), config.RED,
                      (WIDTH // 2, 636), "center")
        else:
            draw_text(surf, "Автосохранение начнётся сразу после генерации",
                      assets.font(13), (124, 117, 104), (WIDTH // 2, 636), "center")


class CharacterScreen:
    """Кастомизация внешности героя с живым предпросмотром."""

    ROWS = (
        ("skin", "ТОН КОЖИ", config.SKIN_TONES),
        ("hair", "ЦВЕТ ВОЛОС", config.HAIR_COLORS),
        ("shirt", "ЦВЕТ РУБАШКИ", config.SHIRT_COLORS),
        ("pants", "ЦВЕТ ШТАНОВ", config.PANTS_COLORS),
    )

    def __init__(self, game):
        self.game = game
        self.return_state = "menu"
        self.style = dict(config.DEFAULT_APPEARANCE)
        self.original = dict(config.DEFAULT_APPEARANCE)
        self.time = 0.0
        self.rows = []
        self.hair_rects = []
        self._build_rects()
        self.random_btn = Button("Случайно", (500, 608, 150, 46), self._randomize,
                                 font_size=18)
        self.reset_btn = Button("Сброс", (664, 608, 132, 46), self._reset, font_size=18)
        self.back_btn = Button("Назад", (810, 608, 132, 46), self._back, font_size=18)
        self.done_btn = Button("Сохранить", (956, 608, 196, 46), self._save, accent=True,
                               font_size=20)

    def _build_rects(self):
        self.rows = []
        y = 154
        for key, label, palette in self.ROWS:
            swatches = []
            for i in range(len(palette)):
                col = i % 8
                row = i // 8
                swatches.append((i, pygame.Rect(500 + col * 52, y + 26 + row * 46, 40, 40)))
            self.rows.append((key, label, palette, swatches))
            y += 78 if len(palette) <= 8 else 122
        self.hair_rects = [pygame.Rect(500 + i * 120, 515, 108, 58) for i in range(4)]

    def refresh(self):
        self.style = dict(self.game.player_style)
        self.original = dict(self.style)
        self.game.assets.set_player_style(self.style)
        self.time = 0.0

    def _apply(self, key, index):
        self.style[key] = int(index)
        self.game.assets.set_player_style(self.style)
        self.game.audio.sfx("click", 0.4)

    def _randomize(self):
        self.style = {
            "skin": random.randrange(len(config.SKIN_TONES)),
            "hair": random.randrange(len(config.HAIR_COLORS)),
            "shirt": random.randrange(len(config.SHIRT_COLORS)),
            "pants": random.randrange(len(config.PANTS_COLORS)),
            "hair_style": random.randrange(config.HAIR_STYLE_COUNT),
        }
        self.game.assets.set_player_style(self.style)
        self.game.audio.sfx("craft", 0.4)

    def _reset(self):
        self.style = dict(config.DEFAULT_APPEARANCE)
        self.game.assets.set_player_style(self.style)
        self.game.audio.sfx("click", 0.55)

    def _leave(self, save):
        if save:
            self.game.set_player_appearance(self.style)
            self.game.audio.sfx("save", 0.6)
        else:
            self.game.assets.set_player_style(self.original)
            self.game.player_style = dict(self.original)
        if self.return_state == "world_create":
            self.game.state = "world_create"
            self.game.world_create.refresh(keep_fields=True)
        else:
            self.game.back_to_menu()

    def _back(self):
        self._leave(False)

    def _save(self):
        self._leave(True)

    def update(self, dt):
        self.time += dt
        mouse = pygame.mouse.get_pos()
        for b in (self.random_btn, self.reset_btn, self.back_btn, self.done_btn):
            b.update(dt, mouse)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._back()
            return
        for b in (self.random_btn, self.reset_btn, self.back_btn, self.done_btn):
            if b.handle_event(event):
                self.game.audio.sfx("click", 0.55)
                return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for key, _label, palette, swatches in self.rows:
                for index, rect in swatches:
                    if rect.collidepoint(event.pos):
                        self._apply(key, index)
                        return
            for i, rect in enumerate(self.hair_rects):
                if rect.collidepoint(event.pos):
                    self.style["hair_style"] = i
                    self.game.assets.set_player_style(self.style)
                    self.game.audio.sfx("click", 0.45)
                    return

    def _draw_hair_icon(self, surf, rect, style_index):
        skin = config.SKIN_TONES[self.style["skin"] % len(config.SKIN_TONES)]
        hair = config.HAIR_COLORS[self.style["hair"] % len(config.HAIR_COLORS)]
        cx, cy = rect.centerx, rect.centery + 2
        pygame.draw.circle(surf, (28, 24, 25), (cx, cy), 19)
        pygame.draw.circle(surf, skin, (cx, cy), 17)
        if style_index == 0:
            pygame.draw.arc(surf, hair, (cx - 18, cy - 21, 36, 30), 3.25, 6.18, 8)
            pygame.draw.rect(surf, hair, (cx - 18, cy - 14, 8, 14), border_radius=3)
        elif style_index == 1:
            pygame.draw.rect(surf, hair, (cx - 18, cy - 19, 36, 13), border_radius=6)
            pygame.draw.rect(surf, hair, (cx - 18, cy - 10, 7, 22), border_radius=2)
            pygame.draw.rect(surf, hair, (cx + 11, cy - 10, 7, 22), border_radius=2)
            pygame.draw.circle(surf, hair, (cx + 14, cy + 12), 7)
        elif style_index == 2:
            for i in range(5):
                x = cx - 16 + i * 8
                pygame.draw.line(surf, hair, (x, cy - 14), (x + 4, cy - 25), 6)
            pygame.draw.rect(surf, hair, (cx - 18, cy - 18, 36, 8), border_radius=4)
        else:
            pygame.draw.ellipse(surf, hair, (cx - 20, cy - 24, 40, 19))
            pygame.draw.circle(surf, hair, (cx - 18, cy - 2), 8)
            pygame.draw.circle(surf, hair, (cx + 18, cy - 2), 8)
        pygame.draw.circle(surf, (37, 30, 30), (cx - 6, cy - 2), 2)
        pygame.draw.circle(surf, (37, 30, 30), (cx + 6, cy - 2), 2)

    def draw(self, surf):
        assets = self.game.assets
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((7, 9, 13, 233))
        surf.blit(veil, (0, 0))
        panel(surf, pygame.Rect(100, 28, 1080, 664), (28, 23, 24), 252,
              (106, 83, 57), 16)
        draw_text(surf, "ГЕРОЙ", assets.font(38, bold=True, title=True), config.GOLD,
                  (WIDTH // 2, 57), "center", outline=2)
        draw_text(surf, "Соберите образ, с которым отправитесь в расколотый мир",
                  assets.font(16, italic=True), (173, 160, 142),
                  (WIDTH // 2, 94), "center")

        # панель предпросмотра
        preview = pygame.Rect(140, 122, 326, 440)
        panel(surf, preview, (18, 23, 25), 238, (82, 68, 51), 12)
        for band in range(9):
            col = lerp_color((38, 62, 61), (15, 21, 25), band / 8)
            pygame.draw.rect(surf, col, (preview.x + 2, preview.y + 2 + band * 44,
                                         preview.w - 4, 45))
        pygame.draw.ellipse(surf, (21, 27, 24), (preview.x + 28, 474, 270, 60))
        for i in range(13):
            gx = preview.x + 28 + i * 21
            gh = 9 + (i * 7) % 17
            pygame.draw.line(surf, (35, 47, 37), (gx, 486), (gx + 2, 486 - gh), 2)
        frame = assets.player_frames["idle"][int(self.time * 1.5) % 2]
        big = pygame.transform.smoothscale(frame, (152, 256))
        surf.blit(big, (preview.centerx - 76, 468 - big.get_height()))
        # пылинки
        for i in range(7):
            ang = self.time * (0.2 + i * 0.04) + i * 1.7
            px = preview.centerx + math.cos(ang) * (64 + i * 12)
            py = 330 + math.sin(ang * 1.4) * 82
            pygame.draw.circle(surf, (201, 183, 121), (int(px), int(py)), 1)
        draw_text(surf, "ПРЕДПРОСМОТР", assets.font(13, bold=True), (213, 183, 116),
                  (preview.centerx, preview.y + 18), "center")
        draw_text(surf, "Герой Терра Новы", assets.font(20, bold=True), config.CREAM,
                  (preview.centerx, 518), "center")
        draw_text(surf, "Изменения появятся в мире", assets.font(13),
                  (140, 135, 121), (preview.centerx, 543), "center")

        # палитры
        mouse = pygame.mouse.get_pos()
        for key, label, palette, swatches in self.rows:
            y = swatches[0][1].y - 33
            draw_text(surf, label, assets.font(15, bold=True), (215, 183, 119),
                      (500, y), "topleft")
            for index, rect in swatches:
                color = palette[index]
                selected = self.style.get(key) == index
                hover = rect.collidepoint(mouse)
                if hover and not selected:
                    rect = rect.inflate(4, 4)
                pygame.draw.circle(surf, (21, 18, 19), rect.center, rect.w // 2 + 2)
                pygame.draw.circle(surf, color, rect.center, rect.w // 2)
                pygame.draw.circle(surf, (255, 239, 199) if selected else (77, 65, 53),
                                   rect.center, rect.w // 2, 2 if selected else 1)
                if selected:
                    pygame.draw.lines(surf, (42, 34, 24), False,
                                      [(rect.centerx - 6, rect.centery),
                                       (rect.centerx - 2, rect.centery + 5),
                                       (rect.centerx + 7, rect.centery - 6)], 2)

        draw_text(surf, "ПРИЧЁСКА", assets.font(15, bold=True), (215, 183, 119),
                  (500, 482), "topleft")
        for i, rect in enumerate(self.hair_rects):
            selected = self.style.get("hair_style", 0) == i
            hover = rect.collidepoint(mouse)
            pygame.draw.rect(surf, (51, 40, 33) if selected else (36, 31, 30), rect,
                             border_radius=9)
            pygame.draw.rect(surf, config.GOLD if selected else
                             (111, 88, 63) if hover else (65, 55, 47),
                             rect, width=2 if selected else 1, border_radius=9)
            self._draw_hair_icon(surf, rect, i)
            draw_text(surf, str(i + 1), assets.font(12, bold=True),
                      (217, 190, 133) if selected else (131, 120, 104),
                      (rect.right - 10, rect.bottom - 7), "bottomright")

        self.random_btn.draw(surf, assets)
        self.reset_btn.draw(surf, assets)
        self.back_btn.draw(surf, assets)
        self.done_btn.draw(surf, assets)


class NetworkScreen:
    """Экран LAN-кооператива: хостинг или подключение по IP."""

    SIZE_ORDER = ("small", "medium", "large")

    def __init__(self, game):
        self.game = game
        self.time = 0.0
        self.size_key = game.settings.get("world_size", config.DEFAULT_WORLD_SIZE)
        self.name_input = TextInput((438, 132, 404, 42), "ВАШЕ ИМЯ",
                                    game.network_name, "Герой", max_len=20)
        self.host_port = TextInput((176, 378, 158, 42), "ПОРТ СЕРВЕРА",
                                   str(config.NETWORK_PORT), "47831", max_len=5,
                                   numeric=True, font_size=18)
        self.join_ip = TextInput((691, 306, 238, 42), "IP ХОСТА",
                                 "127.0.0.1", "192.168.1.10", max_len=48,
                                 font_size=18)
        self.join_port = TextInput((947, 306, 131, 42), "ПОРТ",
                                   str(config.NETWORK_PORT), "47831", max_len=5,
                                   numeric=True, font_size=18)
        self.host_btn = Button("Создать сервер", (176, 452, 412, 48),
                               self._host, accent=True, font_size=21)
        self.join_btn = Button("Подключиться", (691, 452, 412, 48),
                               self._join, font_size=21)
        self.back_btn = Button("Назад", (540, 624, 200, 46), self._back,
                               font_size=19)
        self.size_rects = [pygame.Rect(176 + i * 140, 294, 130, 36) for i in range(3)]
        self.error = ""

    def refresh(self):
        self.size_key = self.game.settings.get("world_size", config.DEFAULT_WORLD_SIZE)
        self.name_input.text = self.game.network_name
        self.name_input.active = False
        self.host_port.active = False
        self.join_ip.active = False
        self.join_port.active = False
        self.error = ""

    def _choose_size(self, key):
        self.size_key = key
        self.game.settings["world_size"] = key
        self.game.audio.sfx("click", 0.45)

    def _local_name(self):
        name = self.name_input.text.strip() or "Герой"
        self.game.network_name = name[:20]
        return self.game.network_name

    def _host(self):
        self.game.audio.sfx("click", 0.6)
        name = self._local_name()
        if not self.host_port.text.isdigit() or not (1024 <= int(self.host_port.text) <= 65535):
            self.error = "Порт должен быть числом от 1024 до 65535."
            return
        self.error = ""
        self.game.audio.sfx("click", 0.6)
        self.game.host_network(self.size_key, int(self.host_port.text), name)

    def _join(self):
        self.game.audio.sfx("click", 0.6)
        name = self._local_name()
        address = self.join_ip.text.strip()
        if not address:
            self.error = "Введите IP-адрес хоста."
            return
        if not self.join_port.text.isdigit() or not (1024 <= int(self.join_port.text) <= 65535):
            self.error = "Порт должен быть числом от 1024 до 65535."
            return
        self.error = ""
        self.game.join_network(address, int(self.join_port.text), name)

    def _back(self):
        self.game.audio.sfx("click", 0.6)
        self.game.leave_network_screen()

    def update(self, dt):
        self.time += dt
        for field in (self.name_input, self.host_port, self.join_ip, self.join_port):
            field.update(dt)
        connecting = self.game.network.status == "connecting"
        self.host_btn.enabled = not connecting
        self.join_btn.enabled = not connecting
        mouse = pygame.mouse.get_pos()
        for b in (self.host_btn, self.join_btn, self.back_btn):
            b.update(dt, mouse)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._back()
            return
        for field in (self.name_input, self.host_port, self.join_ip, self.join_port):
            field.handle_event(event)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(self.size_rects):
                if rect.collidepoint(event.pos):
                    self._choose_size(self.SIZE_ORDER[i])
                    return
        for b in (self.host_btn, self.join_btn, self.back_btn):
            if b.handle_event(event):
                return

    def draw(self, surf):
        assets = self.game.assets
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((7, 10, 14, 234))
        surf.blit(veil, (0, 0))
        panel(surf, pygame.Rect(100, 24, 1080, 672), (27, 23, 24), 252,
              (104, 82, 56), 16)
        draw_text(surf, "СЕТЕВАЯ ИГРА", assets.font(38, bold=True, title=True),
                  config.GOLD, (WIDTH // 2, 48), "center", outline=2)
        draw_text(surf, "Локальная сеть: один хост и один гость — исследуйте мир вместе",
                  assets.font(16, italic=True), (173, 160, 142),
                  (WIDTH // 2, 88), "center")
        self.name_input.draw(surf, assets)

        # карточка хоста
        host_card = pygame.Rect(150, 198, 465, 322)
        join_card = pygame.Rect(665, 198, 465, 322)
        panel(surf, host_card, (31, 29, 30), 235, (86, 69, 51), 11)
        panel(surf, join_card, (31, 29, 30), 235, (86, 69, 51), 11)
        draw_text(surf, "СОЗДАТЬ СЕРВЕР", assets.font(22, bold=True), (227, 190, 112),
                  (176, 214), "topleft")
        draw_text(surf, "Мир создастся у вас и полностью передастся гостю.",
                  assets.font(13), (159, 147, 128), (176, 246), "topleft")
        draw_text(surf, "Размер мира", assets.font(13, bold=True), (184, 157, 109),
                  (176, 273), "topleft")
        mouse = pygame.mouse.get_pos()
        for i, key in enumerate(self.SIZE_ORDER):
            rect = self.size_rects[i]
            selected = key == self.size_key
            hover = rect.collidepoint(mouse)
            pygame.draw.rect(surf, (72, 53, 36) if selected else
                             (41, 35, 33) if hover else (35, 31, 30),
                             rect, border_radius=6)
            pygame.draw.rect(surf, config.GOLD if selected else (92, 75, 57),
                             rect, width=2 if selected else 1, border_radius=6)
            draw_text(surf, config.WORLD_SIZES[key]["name"], assets.font(14, bold=True),
                      (243, 226, 196) if selected else (181, 168, 148),
                      rect.center, "center")
        self.host_port.draw(surf, assets)
        draw_text(surf, f"Ваш IP: {self.game.network.local_host} — передайте его гостю",
                  assets.font(13, bold=True), (150, 211, 175), (176, 426), "topleft")
        self.host_btn.draw(surf, assets)

        # карточка подключения
        draw_text(surf, "ПОДКЛЮЧИТЬСЯ", assets.font(22, bold=True), (194, 211, 228),
                  (691, 214), "topleft")
        draw_text(surf, "Введите адрес компьютера, который создал сервер.",
                  assets.font(13), (159, 147, 128), (691, 246), "topleft")
        self.join_ip.draw(surf, assets)
        self.join_port.draw(surf, assets)
        draw_text(surf, "Сначала хост должен нажать «Создать сервер» и дождаться",
                  assets.font(13), (150, 140, 123), (691, 366), "topleft")
        draw_text(surf, "сообщения о запуске. Оба игрока — в одной Wi-Fi сети.",
                  assets.font(13), (150, 140, 123), (691, 385), "topleft")
        draw_text(surf, "Windows может спросить разрешение брандмауэра — разрешите.",
                  assets.font(12), (132, 125, 112), (691, 411), "topleft")
        self.join_btn.draw(surf, assets)

        # статус
        net = self.game.network
        status_rect = pygame.Rect(150, 538, 980, 62)
        panel(surf, status_rect, (24, 22, 23), 225, (74, 63, 49), 9)
        if net.status == "connecting":
            dots = "." * (1 + int(self.time * 2) % 3)
            text = f"Подключение к {net.local_host}:{net.port}{dots}"
            color = (226, 190, 113)
        elif net.status == "error":
            text = net.status_text()
            color = (224, 110, 104)
        else:
            text = "Готово к подключению. Сохранения у каждого игрока свои."
            color = (177, 166, 145)
        if self.error:
            text, color = self.error, (224, 110, 104)
        draw_text(surf, text, assets.font(16, bold=True), color,
                  (status_rect.centerx, status_rect.centery), "center")
        self.back_btn.draw(surf, assets)


class SettingsScreen:
    def __init__(self, game):
        self.game = game
        self.music = Slider("Музыка", (390, 260, 500, 10), game.settings.get("music", 0.55),
                            self._music_changed)
        self.sfx = Slider("Звуки", (390, 340, 500, 10), game.settings.get("sfx", 0.75),
                          self._sfx_changed)
        self.fullscreen = Button("Полный экран", (390, 400, 250, 48), self._toggle_fullscreen,
                                 font_size=20)
        self.shake = Button("Тряска экрана", (660, 400, 230, 48), self._toggle_shake,
                            font_size=20)
        self.back = Button("Назад", (530, 540, 220, 50), self._back, accent=True)

    def refresh(self):
        self.music.value = self.game.settings.get("music", 0.55)
        self.sfx.value = self.game.settings.get("sfx", 0.75)
        self._update_labels()

    def _update_labels(self):
        self.fullscreen.text = "Полный экран: вкл" if self.game.settings.get("fullscreen") else "Полный экран: выкл"
        self.shake.text = "Тряска: вкл" if self.game.settings.get("shake", True) else "Тряска: выкл"

    def _music_changed(self, v):
        self.game.set_music_volume(v)

    def _sfx_changed(self, v):
        self.game.set_sfx_volume(v)

    def _toggle_fullscreen(self):
        self.game.audio.sfx("click", 0.6)
        self.game.toggle_fullscreen()
        self._update_labels()

    def _toggle_shake(self):
        self.game.audio.sfx("click", 0.6)
        self.game.settings["shake"] = not self.game.settings.get("shake", True)
        self.game.save_settings()
        self._update_labels()

    def _back(self):
        self.game.back_to_menu()

    def update(self, dt):
        mouse = pygame.mouse.get_pos()
        for b in (self.fullscreen, self.shake, self.back):
            b.update(dt, mouse)

    def handle_event(self, event):
        if self.music.handle_event(event) or self.sfx.handle_event(event):
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.game.audio.sfx("click", 0.6)
            self.game.back_to_menu()
            return
        for b in (self.fullscreen, self.shake, self.back):
            if b.handle_event(event):
                if b is self.back:
                    self.game.audio.sfx("click", 0.6)
                return

    def draw(self, surf):
        assets = self.game.assets
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((8, 8, 12, 178))
        surf.blit(veil, (0, 0))
        rect = pygame.Rect(310, 100, 660, 520)
        panel(surf, rect, (28, 23, 23), 246, (111, 86, 58), 16)
        draw_text(surf, "НАСТРОЙКИ", assets.font(40, bold=True), config.GOLD,
                  (WIDTH // 2, 140), "center", outline=2)
        pygame.draw.line(surf, (100, 78, 54), (390, 188), (890, 188), 1)
        self.music.draw(surf, assets)
        self.sfx.draw(surf, assets)
        self.fullscreen.draw(surf, assets)
        self.shake.draw(surf, assets)
        draw_text(surf, "Изменения сохраняются автоматически",
                  assets.font(15), (148, 138, 122), (WIDTH // 2, 500), "center")
        self.back.draw(surf, assets)


class ControlsScreen:
    def __init__(self, game):
        self.game = game
        self.back = Button("Назад", (540, 604, 200, 46), self._back, accent=True)
        self.controls_left = [
            ("A / D", "движение"),
            ("Space", "прыжок"),
            ("ЛКМ", "копать / атаковать"),
            ("ПКМ", "поставить / использовать"),
            ("Колесо", "выбор хотбара"),
            ("R", "поговорить с жителем"),
        ]
        self.controls_right = [
            ("1 … 0", "слоты хотбара"),
            ("Tab / C", "инвентарь и крафт"),
            ("Q", "выбросить предмет"),
            ("H", "подсказки"),
            ("Esc", "пауза"),
            ("F11", "полный экран"),
        ]

    def _back(self):
        self.game.back_to_menu()

    def update(self, dt):
        self.back.update(dt, pygame.mouse.get_pos())

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.game.audio.sfx("click", 0.6)
            self.game.back_to_menu()
            return
        if self.back.handle_event(event):
            self.game.audio.sfx("click", 0.6)

    def draw(self, surf):
        assets = self.game.assets
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((8, 8, 12, 185))
        surf.blit(veil, (0, 0))
        rect = pygame.Rect(180, 38, 920, 638)
        panel(surf, rect, (27, 22, 22), 247, (111, 86, 58), 16)
        draw_text(surf, "УПРАВЛЕНИЕ", assets.font(40, bold=True), config.GOLD,
                  (WIDTH // 2, 70), "center", outline=2)
        draw_text(surf, "Всё, что нужно для выживания в расколотом мире",
                  assets.font(18, italic=True), (183, 169, 145),
                  (WIDTH // 2, 111), "center")

        font = assets.font(20)
        for column, controls in enumerate((self.controls_left, self.controls_right)):
            x = 240 + column * 455
            y = 158
            for key, desc in controls:
                key_chip(surf, assets, x, y, key, width=96 if len(key) > 4 else 66)
                draw_text(surf, desc, font, (225, 214, 192), (x + 112, y + 12), "midleft")
                y += 44

        pygame.draw.line(surf, (94, 74, 53), (240, 438), (1050, 438), 1)
        draw_text(surf, "СОВЕТЫ", assets.font(19, bold=True), (220, 174, 93),
                  (240, 454), "topleft")
        tips = [
            "Четыре биома и четыре босса: король, колосс, королева и Страж Бездны.",
            "Бран и Мирра ждут у точки появления: R — поговорить, подарки — раз в день.",
            "Валуны — ловушки. Разбейте катящийся камень мечом или увернитесь.",
        ]
        for i, tip in enumerate(tips):
            draw_text(surf, f"• {tip}", assets.font(15), (190, 178, 158),
                      (250, 484 + i * 25), "topleft")
        self.back.draw(surf, assets)


class PauseMenu:
    def __init__(self, game):
        self.game = game
        self.buttons = [
            Button("Продолжить", (430, 330, 420, 52), self._resume, accent=True),
            Button("Сохранить игру", (430, 394, 420, 52), self._save),
            Button("Кодекс и бестиарий", (430, 458, 420, 46), self._codex, font_size=22),
            Button("В главное меню", (430, 516, 420, 46), self._menu, font_size=22),
        ]
        self.saved_timer = 0.0

    def _resume(self):
        self.game.resume_game()

    def _save(self):
        if self.game.save_game():
            self.game.audio.sfx("save")
            self.buttons[1].text = "Сохранено ✓"
            self.saved_timer = 1.5

    def _codex(self):
        self.game.open_codex("paused")

    def _menu(self):
        self.game.to_menu()

    def update(self, dt):
        mouse = pygame.mouse.get_pos()
        for b in self.buttons:
            b.update(dt, mouse)
        if self.saved_timer > 0:
            self.saved_timer -= dt
            if self.saved_timer <= 0:
                self.buttons[1].text = "Сохранить игру"

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_p):
            self.game.audio.sfx("click", 0.5)
            self.game.resume_game()
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_k:
            self.game.audio.sfx("click", 0.5)
            self.game.open_codex("paused")
            return
        for b in self.buttons:
            if b.handle_event(event):
                self.game.audio.sfx("click", 0.6)
                return

    def draw(self, surf):
        assets = self.game.assets
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((6, 7, 10, 165))
        surf.blit(veil, (0, 0))
        rect = pygame.Rect(380, 155, 520, 450)
        panel(surf, rect, (28, 23, 23), 246, (113, 87, 58), 16)
        draw_text(surf, "ПАУЗА", assets.font(44, bold=True), config.GOLD,
                  (WIDTH // 2, 202), "center", outline=2)
        game = self.game
        if game.world and game.player:
            day = game.day
            depth = max(0, int(game.world.depth_tiles(game.player.cx, game.player.cy)))
            draw_text(surf, f"День {day}  •  {game_clock(game.time_of_day)}  •  {depth} м",
                      assets.font(17), (178, 166, 146), (WIDTH // 2, 250), "center")
            draw_text(surf, f"Побед над боссом: {game.player.stats.get('bosses', 0)}   •   Семя: {game.world.seed}",
                      assets.font(14), (128, 121, 112), (WIDTH // 2, 277), "center")
        for b in self.buttons:
            b.draw(surf, assets)
        draw_text(surf, "Esc — вернуться в игру   •   K — кодекс", assets.font(14), (132, 124, 111),
                  (WIDTH // 2, 578), "center")


class DeathScreen:
    def __init__(self, game):
        self.game = game
        self.respawn = Button("Возродиться", (455, 420, 370, 54), self._respawn, accent=True)
        self.menu = Button("В главное меню", (505, 488, 270, 44), self._menu, font_size=20)

    def _respawn(self):
        self.game.respawn()

    def _menu(self):
        self.game.to_menu()

    def update(self, dt):
        mouse = pygame.mouse.get_pos()
        self.respawn.update(dt, mouse)
        self.menu.update(dt, mouse)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_r, pygame.K_RETURN):
            self.game.audio.sfx("click", 0.6)
            self._respawn()
            return
        for b in (self.respawn, self.menu):
            if b.handle_event(event):
                self.game.audio.sfx("click", 0.6)
                return

    def draw(self, surf):
        assets = self.game.assets
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((38, 6, 10, 170))
        surf.blit(veil, (0, 0))
        draw_text(surf, "ВЫ ПОГИБЛИ", assets.font(64, bold=True, title=True),
                  (223, 78, 82), (WIDTH // 2, 250), "center", outline=3)
        draw_text(surf, "Мир оказался сильнее. Но приключение продолжается.",
                  assets.font(20, italic=True), (222, 188, 174), (WIDTH // 2, 310), "center")
        if self.game.player:
            p = self.game.player
            draw_text(surf, f"Добыто камня: {p.stats.get('stone', 0)}   •   Побеждено врагов: {p.stats.get('kills', 0)}",
                      assets.font(17), (194, 164, 153), (WIDTH // 2, 354), "center")
        self.respawn.draw(surf, assets)
        self.menu.draw(surf, assets)
        draw_text(surf, "R — возродиться", assets.font(14), (155, 135, 127),
                  (WIDTH // 2, 552), "center")


class VictoryScreen:
    def __init__(self, game):
        self.game = game
        self.finish_btn = Button("Закончить игру · Лазурный берег", (360, 452, 560, 56),
                                 self._finish, accent=True, font_size=24)
        self.continue_btn = Button("Продолжить песочницу", (450, 520, 380, 40),
                                   self._continue, font_size=18)
        self.menu = Button("В главное меню", (535, 568, 210, 36), self._menu, font_size=17)
        self.confetti = []
        self.spawned = False

    def show(self):
        self.spawned = True
        self.confetti = [{
            "x": random.uniform(0, WIDTH), "y": random.uniform(-HEIGHT, 0),
            "vx": random.uniform(-40, 40), "vy": random.uniform(70, 190),
            "size": random.randint(3, 7), "phase": random.random() * math.tau,
            "color": random.choice([(243, 200, 103), (116, 215, 135), (234, 112, 141),
                                    (117, 178, 233), (238, 231, 202)]),
        } for _ in range(90)]

    def _finish(self):
        self.game.start_beach_epilogue()

    def _continue(self):
        self.game.resume_after_victory()

    def _menu(self):
        self.game.to_menu()

    def update(self, dt):
        mouse = pygame.mouse.get_pos()
        self.finish_btn.update(dt, mouse)
        self.continue_btn.update(dt, mouse)
        self.menu.update(dt, mouse)
        for c in self.confetti:
            c["x"] += (c["vx"] + math.sin(self.game.time * 2 + c["phase"]) * 20) * dt
            c["y"] += c["vy"] * dt
            if c["y"] > HEIGHT + 20:
                c["y"] = -20
                c["x"] = random.uniform(0, WIDTH)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self._finish()
            return
        for b in (self.finish_btn, self.continue_btn, self.menu):
            if b.handle_event(event):
                self.game.audio.sfx("click", 0.6)
                return

    def draw(self, surf):
        assets = self.game.assets
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((8, 15, 16, 190))
        surf.blit(veil, (0, 0))
        for c in self.confetti:
            pygame.draw.rect(surf, c["color"], (int(c["x"]), int(c["y"]), c["size"], c["size"] * 2),
                             border_radius=1)
        rect = pygame.Rect(300, 90, 680, 530)
        panel(surf, rect, (29, 25, 23), 245, (226, 180, 89), 18, 3)
        draw_text(surf, "ПОБЕДА", assets.font(58, bold=True, title=True), config.GOLD,
                  (WIDTH // 2, 145), "center", outline=3)
        sigil = assets.icon("abyss_sigil")
        sigil = pygame.transform.smoothscale(sigil, (112, 112))
        surf.blit(sigil, (WIDTH // 2 - 56, 188))
        draw_text(surf, "Страж Бездны повержен!", assets.font(31, bold=True), (168, 221, 191),
                  (WIDTH // 2, 320), "center")
        p = self.game.player
        stats = p.stats if p else {}
        draw_text(surf, "Четыре стража пали. Бездна замолчала, а мир снова открыт.",
                  assets.font(18, italic=True), (212, 197, 171),
                  (WIDTH // 2, 356), "center")
        draw_text(surf, f"Побеждено врагов: {stats.get('kills', 0)}   •   Время в игре: {self.game.playtime_text()}",
                  assets.font(17), (190, 176, 154), (WIDTH // 2, 392), "center")
        draw_text(surf, "Завершите поход: все жители уже ждут вас на Лазурном берегу.",
                  assets.font(16, italic=True), (174, 214, 200), (WIDTH // 2, 424), "center")
        self.finish_btn.draw(surf, assets)
        self.continue_btn.draw(surf, assets)
        self.menu.draw(surf, assets)


# ===================================================================== инвентарь
class InventoryOverlay:
    def __init__(self, game):
        self.game = game
        self.held: list | None = None
        self.scroll = 0.0
        self.hover_slot = -1
        self.hover_recipe = -1
        self.slot_rects: list[pygame.Rect] = []
        self.recipe_rects: list[tuple] = []
        self.close_rect = pygame.Rect(1162, 52, 44, 38)
        self._build_slot_rects()

    def _build_slot_rects(self):
        self.slot_rects = []
        x0, y0, size, gap = 92, 168, 52, 7
        for i in range(config.INV_SLOTS):
            row, col = divmod(i, 10)
            self.slot_rects.append(pygame.Rect(x0 + col * (size + gap),
                                               y0 + row * (size + gap + 3), size, size))

    def open(self):
        self.scroll = 0.0
        self.hover_slot = -1
        if self.held:
            self._return_held()

    def close(self):
        self._return_held()
        self.game.close_inventory()

    def _return_held(self):
        if not self.held:
            self.held = None
            return
        item_id, count = self.held
        left = self.game.player.add_item(item_id, count)
        if left:
            self.game.spawn_drop(item_id, left, self.game.player.cx, self.game.player.cy - 20)
        self.held = None

    def _click_slot(self, index):
        inv = self.game.player.inventory
        if index < 0 or index >= len(inv):
            return
        slot = inv[index]
        if self.held:
            if slot is None:
                inv[index] = self.held
                self.held = None
            elif slot[0] == self.held[0]:
                take = min(config.MAX_STACK - slot[1], self.held[1])
                slot[1] += take
                self.held[1] -= take
                if self.held[1] <= 0:
                    self.held = None
            else:
                inv[index] = self.held
                self.held = slot
        else:
            if slot:
                self.held = slot
                inv[index] = None
        self.game.audio.sfx("click", 0.35)

    def _recipe_rows(self):
        view = pygame.Rect(728, 152, 460, 452)
        row_h = 82
        rows = []
        for idx, recipe in enumerate(crafting.RECIPES):
            y = view.y + idx * row_h - int(self.scroll)
            if y + row_h - 8 < view.top or y > view.bottom:
                continue
            rect = pygame.Rect(view.x, y, view.w, row_h - 8)
            can, reason = crafting.recipe_state(recipe, self.game.player, self.game.world)
            rows.append((recipe, rect, can, reason))
        return view, rows

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_TAB, pygame.K_ESCAPE, pygame.K_i, pygame.K_e, pygame.K_c):
                self.close()
            elif event.key == pygame.K_q and self.held:
                item_id, count = self.held
                self.game.spawn_drop(item_id, count, self.game.player.cx, self.game.player.cy - 26)
                self.held = None
            return
        view, rows = self._recipe_rows()
        max_scroll = max(0, len(crafting.RECIPES) * 82 - view.h)
        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            if view.collidepoint(mx, my) or mx > 700:
                self.scroll = clamp(self.scroll - event.y * 68, 0, max_scroll)
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.close_rect.collidepoint(event.pos):
                self.close()
                return
            for i, r in enumerate(self.slot_rects):
                if r.collidepoint(event.pos):
                    self._click_slot(i)
                    return
            for recipe, rect, can, reason in rows:
                button = pygame.Rect(rect.right - 110, rect.centery - 16, 92, 32)
                if (rect.collidepoint(event.pos) or button.collidepoint(event.pos)) and can:
                    crafting.craft(self.game, recipe)
                    return
                elif rect.collidepoint(event.pos):
                    self.game.audio.sfx("click", 0.4)
                    return

    def update(self, dt):
        mouse = pygame.mouse.get_pos()
        self.hover_slot = -1
        for i, r in enumerate(self.slot_rects):
            if r.collidepoint(mouse):
                self.hover_slot = i
                break
        _, rows = self._recipe_rows()
        self.hover_recipe = -1
        for i, (recipe, rect, can, reason) in enumerate(rows):
            if rect.collidepoint(mouse):
                self.hover_recipe = crafting.RECIPES.index(recipe)
                break

    def draw(self, surf):
        assets = self.game.assets
        player = self.game.player
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((7, 8, 11, 190))
        surf.blit(veil, (0, 0))
        panel(surf, pygame.Rect(56, 38, 1168, 644), (26, 22, 22), 249, (107, 83, 56), 18)

        draw_text(surf, "ИНВЕНТАРЬ", assets.font(32, bold=True), config.GOLD, (92, 64))
        draw_text(surf, "30 слотов • первые 10 — хотбар", assets.font(15), (155, 144, 126),
                  (92, 108))
        draw_text(surf, "ЛКМ — взять / положить", assets.font(15), (140, 130, 114),
                  (92, 138))

        mouse = pygame.mouse.get_pos()
        for i, rect in enumerate(self.slot_rects):
            hover = i == self.hover_slot
            selected = i == player.hotbar_index
            base = (50, 40, 34) if hover else (34, 29, 29)
            pygame.draw.rect(surf, base, rect, border_radius=6)
            border = config.GOLD if selected else (95, 77, 59) if hover else (65, 54, 46)
            pygame.draw.rect(surf, border, rect, width=2, border_radius=6)
            slot = player.inventory[i]
            if slot:
                assets.draw_item(surf, slot[0], rect, 0.92)
                if slot[1] > 1:
                    draw_text(surf, str(slot[1]), assets.font(14, bold=True), (246, 238, 216),
                              (rect.right - 5, rect.bottom - 3), "bottomright", shadow=True)
            if i < 10:
                draw_text(surf, str((i + 1) % 10), assets.font(12), (127, 116, 101),
                          (rect.x + 5, rect.y + 3))

        # снаряжение
        eq = pygame.Rect(92, 372, 583, 126)
        panel(surf, eq, (32, 27, 26), 230, (82, 66, 49), 10)
        draw_text(surf, "СНАРЯЖЕНИЕ", assets.font(18, bold=True), (224, 186, 104),
                  (112, 386))
        p_icon = pygame.transform.smoothscale(assets.pickaxe_icon, (42, 14))
        s_icon = pygame.transform.smoothscale(assets.sword_icon, (42, 13))
        surf.blit(p_icon, (112, 424))
        surf.blit(s_icon, (112, 456))
        draw_text(surf, f"{config.PICKAXE_NAMES[player.mining_level]}  •  скорость ×{player.mining_power:.1f}",
                  assets.font(16), (218, 207, 187), (168, 417))
        draw_text(surf, f"{config.SWORD_NAMES[player.sword_level]}  •  урон {player.sword_damage}",
                  assets.font(16), (218, 207, 187), (168, 449))
        total = sum(s[1] for s in player.inventory if s)
        draw_text(surf, f"Всего предметов: {total}   •   Убито врагов: {player.stats['kills']}",
                  assets.font(14), (138, 130, 117), (112, 476))

        # крафт
        draw_text(surf, "КРАФТ", assets.font(32, bold=True), config.GOLD, (728, 64))
        near = crafting.station_available(self.game.world, player)
        status = "Верстак рядом" if near else "Верстак не найден — доступны простые рецепты"
        draw_text(surf, status, assets.font(15), (126, 207, 130) if near else (174, 154, 128),
                  (728, 116))
        pygame.draw.rect(surf, (16, 14, 15), (728, 152, 460, 452), border_radius=8)
        view, rows = self._recipe_rows()
        surf.set_clip(view)
        for recipe, rect, can, reason in rows:
            hover = rect.collidepoint(mouse)
            bg = (53, 43, 37) if hover else (36, 31, 30)
            pygame.draw.rect(surf, bg, rect, border_radius=7)
            border = (120, 95, 61) if can else (63, 53, 48)
            if hover:
                border = config.GOLD if can else (104, 84, 64)
            pygame.draw.rect(surf, border, rect, width=1, border_radius=7)
            icon_rect = pygame.Rect(rect.x + 8, rect.y + 8, 44, 44)
            pygame.draw.rect(surf, (26, 22, 22), icon_rect, border_radius=5)
            assets.draw_item(surf, recipe.icon, icon_rect, 0.8)
            draw_text(surf, recipe.name, assets.font(18, bold=True),
                      (238, 224, 198) if can else (153, 143, 128),
                      (rect.x + 61, rect.y + 7))
            ing = crafting.ingredients_text(recipe)
            draw_text(surf, ing, assets.font(13), (183, 171, 150),
                      (rect.x + 61, rect.y + 31))
            sub = reason if not can else recipe.note
            color = (198, 111, 100) if not can else (151, 141, 124)
            draw_text(surf, sub, assets.font(12), color, (rect.x + 61, rect.y + 51))
            btn = pygame.Rect(rect.right - 110, rect.centery - 16, 92, 32)
            pygame.draw.rect(surf, (94, 72, 40) if can else (45, 40, 37), btn, border_radius=6)
            pygame.draw.rect(surf, (211, 169, 84) if can else (78, 67, 57), btn,
                             width=1, border_radius=6)
            draw_text(surf, "Создать", assets.font(14, bold=True),
                      (247, 232, 193) if can else (112, 104, 92), btn.center, "center")
        surf.set_clip(None)

        # полоса прокрутки
        total_h = len(crafting.RECIPES) * 82
        if total_h > view.h:
            track = pygame.Rect(1192, view.y, 6, view.h)
            pygame.draw.rect(surf, (24, 20, 21), track, border_radius=3)
            frac = view.h / total_h
            bar_h = max(34, int(view.h * frac))
            max_scroll = total_h - view.h
            pos = 0 if max_scroll <= 0 else self.scroll / max_scroll
            bar = pygame.Rect(track.x, view.y + int((view.h - bar_h) * pos), 6, bar_h)
            pygame.draw.rect(surf, (157, 123, 68), bar, border_radius=3)

        pygame.draw.rect(surf, (104, 83, 57), self.close_rect, border_radius=7)
        draw_text(surf, "×", assets.font(30, bold=True), (232, 214, 184),
                  self.close_rect.center, "center")
        draw_text(surf, "Tab — закрыть   •   Q — выбросить предмет",
                  assets.font(14), (137, 127, 112), (92, 642))

        # предмет на курсоре
        if self.held:
            icon = assets.icon(self.held[0])
            icon = pygame.transform.smoothscale(icon, (42, 42))
            surf.blit(icon, (mouse[0] + 9, mouse[1] + 7))
            if self.held[1] > 1:
                draw_text(surf, str(self.held[1]), assets.font(15, bold=True), config.WHITE,
                          (mouse[0] + 50, mouse[1] + 48), "bottomright", shadow=True)

        # подсказка по предмету
        if self.hover_slot >= 0 and not self.held:
            slot = player.inventory[self.hover_slot]
            if slot:
                item = ITEMS[slot[0]]
                name_col = RARITY_COLORS.get(item.rarity, config.CREAM)
                f_name = assets.font(18, bold=True)
                f_desc = assets.font(14)
                lines = wrap_text(f_desc, item.desc, 240)
                w = max(240, f_name.size(item.name)[0] + 30)
                h = 38 + len(lines) * 19
                tx = clamp(mouse[0] + 18, 8, WIDTH - w - 8)
                ty = clamp(mouse[1] + 18, 8, HEIGHT - h - 8)
                tooltip_rect = pygame.Rect(tx, ty, w, h)
                panel(surf, tooltip_rect, (22, 19, 20), 248, (92, 76, 57), 8)
                draw_text(surf, item.name, f_name, name_col, (tx + 12, ty + 8))
                for j, line in enumerate(lines):
                    draw_text(surf, line, f_desc, (194, 183, 165), (tx + 12, ty + 31 + j * 19))


# ===================================================================== HUD
ROMAN = ["", "I", "II", "III", "IV", "V", "VI", "VII"]


def _draw_hearts(surf, game):
    assets = game.assets
    p = game.player
    max_hearts = max(10, int(math.ceil(p.max_hp / 10)))
    for i in range(max_hearts):
        value = p.hp - i * 10
        if value >= 10:
            img = assets.heart_full
        elif value >= 5:
            img = assets.heart_half
        else:
            img = assets.heart_empty
        x = 28 + (i % 10) * 25
        y = 22 + (i // 10) * 23
        surf.blit(img, (x, y))
    draw_text(surf, f"{p.hp}/{p.max_hp}", assets.font(14, bold=True), (243, 225, 205),
              (28 + min(10, max_hearts) * 25 + 4, 24), "topleft", shadow=True)

    # инструменты
    y = 72 if max_hearts <= 10 else 96
    roman_max = len(ROMAN) - 1
    for i, (icon, label) in enumerate((
            (assets.pickaxe_icon, f"{config.PICKAXE_NAMES[p.mining_level]} {ROMAN[min(roman_max, p.mining_level)]}"),
            (assets.sword_icon, f"{config.SWORD_NAMES[p.sword_level]} {ROMAN[min(roman_max, p.sword_level)]}"))):
        rect = pygame.Rect(28, y + i * 36, 254, 30)
        panel(surf, rect, (22, 19, 20), 155, (78, 63, 47), 7)
        img = pygame.transform.smoothscale(icon, (32, 11))
        surf.blit(img, (rect.x + 8, rect.centery - 5))
        draw_text(surf, label, assets.font(13), (203, 192, 172),
                  (rect.x + 48, rect.centery), "midleft")


def _draw_hotbar(surf, game):
    assets = game.assets
    p = game.player
    size, gap = 52, 6
    total = 10 * size + 9 * gap
    x0 = (WIDTH - total) // 2
    y0 = HEIGHT - 72
    # фон панели
    panel(surf, pygame.Rect(x0 - 10, y0 - 9, total + 20, size + 18), (20, 17, 18), 200,
          (79, 64, 47), 10)
    for i in range(10):
        rect = pygame.Rect(x0 + i * (size + gap), y0, size, size)
        selected = i == p.hotbar_index
        pygame.draw.rect(surf, (65, 49, 35) if selected else (35, 30, 29), rect, border_radius=5)
        pygame.draw.rect(surf, config.GOLD if selected else (83, 69, 55), rect,
                         width=2 if selected else 1, border_radius=5)
        slot = p.inventory[i] if i < len(p.inventory) else None
        if slot:
            assets.draw_item(surf, slot[0], rect, 0.86)
            if slot[1] > 1:
                draw_text(surf, str(slot[1]), assets.font(13, bold=True), (245, 236, 213),
                          (rect.right - 4, rect.bottom - 2), "bottomright", shadow=True)
        draw_text(surf, str((i + 1) % 10), assets.font(11), (135, 122, 105),
                  (rect.x + 4, rect.y + 2))
    name = p.selected_name()
    if name and p.selected_time > 0:
        alpha = int(255 * min(1.0, p.selected_time / 0.5))
        draw_text(surf, name, assets.font(17, bold=True), config.CREAM,
                  (WIDTH // 2, y0 - 20), "center", outline=1, alpha=alpha)


def _draw_quests(surf, game):
    assets = game.assets
    p = game.player
    quests = crafting.visible_quests(p, 4)
    x, y, w = WIDTH - 354, 62, 326
    h = 44 + len(quests) * 29
    panel(surf, pygame.Rect(x, y, w, h), (24, 20, 21), 190, (79, 64, 47), 9)
    all_quests = crafting.get_quests(p)
    total_done = sum(1 for q in all_quests if q["done"])
    draw_text(surf, "ЦЕЛИ", assets.font(17, bold=True), config.GOLD, (x + 14, y + 10))
    draw_text(surf, f"{total_done}/{len(all_quests)}", assets.font(13), (146, 135, 118),
              (x + w - 14, y + 13), "topright")
    for i, q in enumerate(quests):
        yy = y + 38 + i * 29
        box = pygame.Rect(x + 14, yy + 3, 13, 13)
        pygame.draw.rect(surf, (34, 29, 28), box, border_radius=3)
        if q["done"]:
            pygame.draw.rect(surf, (91, 187, 109), box, border_radius=3)
            pygame.draw.lines(surf, (235, 250, 226), False,
                              [(box.x + 3, box.y + 7), (box.x + 6, box.y + 10), (box.x + 10, box.y + 4)], 2)
            color = (128, 165, 126)
        else:
            pygame.draw.rect(surf, (150, 125, 84), box, width=1, border_radius=3)
            color = (209, 197, 175)
        draw_text(surf, q["text"], assets.font(14), color, (x + 36, yy + 2))
        if q["progress"] and not q["done"]:
            draw_text(surf, q["progress"], assets.font(12), (148, 136, 117),
                      (x + w - 14, yy + 4), "topright")


def _draw_boss_bar(surf, game):
    boss = game.boss
    if not boss or not boss.alive:
        return
    assets = game.assets
    w = 470
    x = (WIDTH - w) // 2
    y = 36
    draw_text(surf, boss.name.upper(), assets.font(20, bold=True), (238, 213, 171),
              (WIDTH // 2, y - 10), "midbottom", outline=2)
    panel(surf, pygame.Rect(x - 4, y - 4, w + 8, 26), (22, 18, 20), 210, (91, 70, 50), 8)
    pygame.draw.rect(surf, (48, 35, 34), (x, y, w, 18), border_radius=6)
    ratio = clamp(boss.hp / boss.max_hp, 0, 1)
    fill = pygame.Rect(x + 2, y + 2, int((w - 4) * ratio), 14)
    pygame.draw.rect(surf, (184, 61, 77), fill, border_radius=5)
    pygame.draw.line(surf, (238, 129, 134), (fill.x + 3, fill.y + 2),
                     (max(fill.x + 3, fill.right - 3), fill.y + 2), 1)
    for t in (0.33, 0.66):
        tx = x + int(w * t)
        pygame.draw.line(surf, (61, 44, 42), (tx, y + 1), (tx, y + 17), 1)
    draw_text(surf, f"{max(0, boss.hp)} / {boss.max_hp}", assets.font(12, bold=True),
              (247, 230, 207), (WIDTH // 2, y + 9), "center")


def _draw_info(surf, game):
    assets = game.assets
    p = game.player
    depth = int(max(0, game.world.depth_tiles(p.cx, p.cy)))
    depth_text = "поверхность" if depth < 3 else f"глубина {depth} м"
    biome = config.BIOME_SHORT.get(game.world.biome_at(p.cx), "Лес")
    text = f"{biome}  •  День {game.day}  •  {game_clock(game.time_of_day)}  •  {depth_text}"
    font = assets.font(14)
    w = font.size(text)[0] + 28
    rect = pygame.Rect(WIDTH - max(354, w), 20, max(326, w), 32)
    panel(surf, rect, (20, 18, 19), 185, (72, 59, 45), 8)
    draw_text(surf, text, font, (211, 199, 177), rect.center, "center")


def _draw_toasts(surf, game):
    assets = game.assets
    font = assets.font(15, bold=True)
    y = HEIGHT - 116
    for toast in reversed(game.toasts[-4:]):
        life = toast["life"]
        alpha = int(255 * clamp(life / 0.5, 0, 1))
        text = toast["text"]
        w = font.size(text)[0] + 30
        rect = pygame.Rect(WIDTH // 2 - w // 2, y, w, 30)
        layer = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(layer, (21, 18, 19, int(205 * alpha / 255)), layer.get_rect(), border_radius=8)
        pygame.draw.rect(layer, (*toast.get("color", config.CREAM), alpha), layer.get_rect(),
                         width=1, border_radius=8)
        surf.blit(layer, rect.topleft)
        draw_text(surf, text, font, toast.get("color", config.CREAM), rect.center,
                  "center", alpha=alpha)
        y -= 36


def _draw_tutorial(surf, game):
    if not game.show_tutorial or game.tutorial_timer <= 0:
        return
    assets = game.assets
    alpha = int(255 * clamp(game.tutorial_timer / 3.0, 0, 1))
    rect = pygame.Rect(24, HEIGHT - 260, 322, 194)
    layer = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(layer, (21, 18, 19, int(185 * alpha / 255)), layer.get_rect(), border_radius=10)
    pygame.draw.rect(layer, (92, 76, 56, alpha), layer.get_rect(), width=1, border_radius=10)
    surf.blit(layer, rect.topleft)
    draw_text(surf, "УПРАВЛЕНИЕ", assets.font(14, bold=True), (226, 188, 104),
              (rect.x + 14, rect.y + 10), alpha=alpha)
    lines = [
        "A / D — идти, Space — прыжок",
        "ЛКМ — копать и атаковать",
        "ПКМ — поставить блок / использовать",
        "Tab — инвентарь и крафт",
        "1–0 или колесо — выбор слота",
        "R — поговорить с жителем",
        "H — скрыть подсказки",
    ]
    for i, line in enumerate(lines):
        draw_text(surf, line, assets.font(13), (206, 195, 175),
                  (rect.x + 14, rect.y + 34 + i * 21), alpha=alpha)
    draw_text(surf, "H", assets.font(10, bold=True), (130, 119, 103),
              (rect.right - 18, rect.y + 12), "topright", alpha=alpha)


def draw_hud(surf, game):
    assets = game.assets
    _draw_info(surf, game)
    _draw_hearts(surf, game)
    _draw_quests(surf, game)
    _draw_boss_bar(surf, game)
    _draw_hotbar(surf, game)
    _draw_tutorial(surf, game)
    if game.state not in ("dialog", "victory"):
        _draw_toasts(surf, game)

    if game.damage_flash > 0:
        flash = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        flash.fill((156, 21, 28, int(70 * clamp(game.damage_flash, 0, 1))))
        surf.blit(flash, (0, 0))

    if game.player and game.player.hp / max(1, game.player.max_hp) < 0.3:
        pulse = 0.5 + 0.5 * math.sin(game.time * 6)
        alpha = int(50 + 55 * pulse)
        vign = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for i in range(8):
            a = int(alpha * (8 - i) / 8)
            pygame.draw.rect(vign, (120, 16, 20, a), (0, i * 14, WIDTH, 14))
            pygame.draw.rect(vign, (120, 16, 20, a), (0, HEIGHT - (i + 1) * 14, WIDTH, 14))
            pygame.draw.rect(vign, (120, 16, 20, a), (i * 14, 0, 14, HEIGHT))
            pygame.draw.rect(vign, (120, 16, 20, a), (WIDTH - (i + 1) * 14, 0, 14, HEIGHT))
        surf.blit(vign, (0, 0))


def draw_guide_dialog(surf, game):
    """Диалог Проводника поверх замершего мира."""
    if not game.dialog_lines:
        return
    assets = game.assets
    veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    veil.fill((4, 5, 9, 55))
    surf.blit(veil, (0, 0))
    rect = pygame.Rect(156, 478, 968, 214)
    panel(surf, rect, (24, 20, 21), 246, (190, 148, 75), 14, 2)
    pygame.draw.line(surf, (92, 73, 52), (rect.x + 18, rect.y + 54),
                     (rect.right - 18, rect.y + 54), 1)
    # портрет
    portrait = pygame.Rect(rect.x + 18, rect.y + 16, 104, 104)
    panel(surf, portrait, (34, 42, 44), 230, (86, 102, 99), 10)
    frames = getattr(assets, getattr(game, "dialog_frames_attr", "guide_frames"),
                     assets.guide_frames)
    frame = frames[int(game.time * 1.4) % len(frames)]
    face = pygame.transform.smoothscale(frame, (52, 78))
    surf.blit(face, (portrait.centerx - 26, portrait.y + 14))
    speaker = game.dialog_speaker or "Проводник"
    draw_text(surf, speaker, assets.font(16, bold=True), (220, 190, 126),
              (rect.x + 140, rect.y + 14))
    draw_text(surf, str(game.dialog_index + 1) + " / " + str(len(game.dialog_lines)),
              assets.font(13), (137, 127, 111),
              (rect.right - 22, rect.y + 17), "topright")
    role = getattr(game, "dialog_role", "Хранитель Терра Новы").upper()
    draw_text(surf, role, assets.font(12, bold=True), (156, 185, 151),
              (rect.x + 140, rect.y + 37))

    line = game.dialog_lines[min(game.dialog_index, len(game.dialog_lines) - 1)]
    text_lines = wrap_text(assets.font(19), line, rect.w - 180)
    for i, ln in enumerate(text_lines[:4]):
        draw_text(surf, ln, assets.font(19), (230, 219, 198),
                  (rect.x + 140, rect.y + 68 + i * 27))
    draw_text(surf, "Enter / ЛКМ — далее     Esc — закрыть",
              assets.font(13), (151, 138, 119),
              (rect.right - 22, rect.bottom - 18), "bottomright")
    # уголки
    for cx, cy, dx, dy in ((rect.x + 10, rect.y + 10, 1, 1),
                           (rect.right - 10, rect.y + 10, -1, 1),
                           (rect.x + 10, rect.bottom - 10, 1, -1),
                           (rect.right - 10, rect.bottom - 10, -1, -1)):
        pygame.draw.line(surf, config.GOLD, (cx, cy), (cx + 18 * dx, cy), 1)
        pygame.draw.line(surf, config.GOLD, (cx, cy), (cx, cy + 18 * dy), 1)


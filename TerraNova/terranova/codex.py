# -*- coding: utf-8 -*-
"""Экран кодекса: достижения и бестиарий."""
from __future__ import annotations

import pygame

from . import config, progression
from .config import WIDTH, HEIGHT
from .utils import clamp, draw_text, panel
from .ui_widgets import Button

TAB_ACHIEVEMENTS = 0
TAB_BESTIARY = 1

VIEW = pygame.Rect(96, 174, 1088, 444)
ROW_HEIGHT = 58
CARD_HEIGHT = 52
CARD_GAP = 6


def _ellipsize(font: pygame.font.Font, text: str, width: int) -> str:
    if font.size(text)[0] <= width:
        return text
    tail = "…"
    while text and font.size(text + tail)[0] > width:
        text = text[:-1]
    return (text + tail) if text else tail


class CodexScreen:
    """Достижения и бестиарий в одном окне."""

    def __init__(self, game):
        self.game = game
        self.tab = TAB_ACHIEVEMENTS
        self.scroll = 0.0
        self.max_scroll = 0.0
        self.tab_rects = [
            pygame.Rect(96, 120, 286, 40),
            pygame.Rect(394, 120, 286, 40),
        ]
        self.back_button = Button("Назад", (1046, 52, 154, 38),
                                  self.game.close_codex, font_size=18)
        self.close_rect = self.back_button.rect

    def refresh(self):
        self.scroll = 0.0
        self.tab = TAB_ACHIEVEMENTS

    def _switch_tab(self, tab: int):
        if tab == self.tab:
            return
        self.tab = tab
        self.scroll = 0.0
        self.game.audio.sfx("click", 0.4)

    def _rows(self):
        if self.tab == TAB_ACHIEVEMENTS:
            return list(progression.ACHIEVEMENTS)
        return list(progression.BESTIARY)

    def _content_height(self):
        columns = 2
        count = len(self._rows())
        rows = (count + columns - 1) // columns
        return rows * ROW_HEIGHT + 8

    def _refresh_scroll(self):
        self.max_scroll = max(0.0, self._content_height() - VIEW.h)
        self.scroll = clamp(self.scroll, 0.0, self.max_scroll)

    def _card_rect(self, index: int) -> pygame.Rect:
        column = index % 2
        row = index // 2
        width = VIEW.w // 2 - CARD_GAP
        x = VIEW.x + column * (VIEW.w // 2 + CARD_GAP)
        y = VIEW.y + 4 + row * ROW_HEIGHT - int(self.scroll)
        return pygame.Rect(x, y, width, CARD_HEIGHT)

    def _screen_rect(self) -> pygame.Rect:
        return pygame.Rect(56, 38, 1168, 644)

    def update(self, dt):
        self.back_button.update(dt, pygame.mouse.get_pos())

    def handle_event(self, event):
        self._refresh_scroll()
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_k):
                self.game.close_codex()
            elif event.key in (pygame.K_TAB, pygame.K_RIGHT, pygame.K_d):
                self._switch_tab(1 - self.tab)
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                self._switch_tab(1 - self.tab)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.scroll = clamp(self.scroll + 52, 0, self.max_scroll)
            elif event.key in (pygame.K_UP, pygame.K_w):
                self.scroll = clamp(self.scroll - 52, 0, self.max_scroll)
            elif event.key in (pygame.K_PAGEUP, pygame.K_PAGEDOWN):
                step = VIEW.h - ROW_HEIGHT
                self.scroll = clamp(
                    self.scroll + (step if event.key == pygame.K_PAGEDOWN else -step),
                    0, self.max_scroll)
            return
        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            if VIEW.collidepoint(mx, my):
                self.scroll = clamp(self.scroll - event.y * 62, 0, self.max_scroll)
            return
        if self.back_button.handle_event(event):
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for index, rect in enumerate(self.tab_rects):
                if rect.collidepoint(event.pos):
                    self._switch_tab(index)
                    return

    # ------------------------------------------------------------------ отрисовка
    def draw(self, surf):
        assets = self.game.assets
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((7, 8, 12, 176))
        surf.blit(veil, (0, 0))
        panel(surf, self._screen_rect(), (26, 22, 22), 250, (107, 83, 56), 18)

        draw_text(surf, "КОДЕКС", assets.font(36, bold=True, title=True), config.GOLD,
                  (96, 50), "topleft", outline=2)
        draw_text(surf, "Достижения, рекорды и обитатели Терра Новы",
                  assets.font(15), (164, 151, 132), (98, 94), "topleft")
        self._draw_tabs(surf)
        self._draw_content(surf)
        self._draw_scrollbar(surf)
        self.back_button.draw(surf, assets)
        draw_text(surf, "Tab / ← → — вкладка   •   колесо мыши — прокрутка   •   Esc — назад",
                  assets.font(14), (137, 127, 112), (96, 646), "topleft")

    def _draw_tabs(self, surf):
        assets = self.game.assets
        unlocked = len(self.game.achievements)
        seen = sum(1 for count in (self.game.player.bestiary.values()
                                   if self.game.player else []) if count > 0)
        labels = [
            f"Достижения   {unlocked}/{len(progression.ACHIEVEMENTS)}",
            f"Бестиарий   {seen}/{len(progression.BESTIARY)}",
        ]
        mouse = pygame.mouse.get_pos()
        for index, rect in enumerate(self.tab_rects):
            active = index == self.tab
            hover = rect.collidepoint(mouse)
            bg = (62, 47, 36) if active else (52, 43, 39) if hover else (34, 30, 30)
            border = config.GOLD if active else (89, 72, 56) if hover else (63, 53, 47)
            pygame.draw.rect(surf, bg, rect, border_radius=8)
            pygame.draw.rect(surf, border, rect, width=2 if active else 1, border_radius=8)
            draw_text(surf, labels[index], assets.font(17, bold=active),
                      config.CREAM if active else (172, 160, 141),
                      rect.center, "center")

    def _draw_content(self, surf):
        self._refresh_scroll()
        assets = self.game.assets
        pygame.draw.rect(surf, (17, 15, 16), VIEW, border_radius=8)
        pygame.draw.rect(surf, (57, 48, 43), VIEW, width=1, border_radius=8)
        surf.set_clip(VIEW)
        if self.tab == TAB_ACHIEVEMENTS:
            for index, achievement in enumerate(progression.ACHIEVEMENTS):
                rect = self._card_rect(index)
                if rect.bottom >= VIEW.top and rect.top <= VIEW.bottom:
                    self._draw_achievement_card(surf, rect, achievement)
        else:
            for index, entry in enumerate(progression.BESTIARY):
                rect = self._card_rect(index)
                if rect.bottom >= VIEW.top and rect.top <= VIEW.bottom:
                    self._draw_bestiary_card(surf, rect, entry)
        surf.set_clip(None)
        if self.tab == TAB_ACHIEVEMENTS:
            note = "Достижения открываются автоматически. Скрытые отмечены знаком вопроса."
        else:
            note = "Бестиарий заполняется, когда вы побеждаете существ. Боссы отмечены золотом."
        draw_text(surf, note, assets.font(13), (126, 117, 104),
                  (VIEW.x + 2, VIEW.bottom + 10), "topleft")

    def _draw_achievement_card(self, surf, rect, achievement):
        assets = self.game.assets
        unlocked = achievement.id in self.game.achievements
        value = progression.achievement_value(self.game, achievement.stat)
        ratio = clamp(value / max(1, achievement.need), 0.0, 1.0)
        hidden = achievement.hidden and not unlocked

        bg = (47, 39, 31) if unlocked else (32, 29, 29)
        border = achievement.color if unlocked else (62, 53, 46)
        pygame.draw.rect(surf, bg, rect, border_radius=7)
        pygame.draw.rect(surf, border, rect, width=2 if unlocked else 1, border_radius=7)

        icon_center = (rect.x + 23, rect.centery)
        pygame.draw.circle(surf, (26, 23, 22), icon_center, 13)
        pygame.draw.circle(surf, achievement.color if unlocked else (83, 73, 64),
                           icon_center, 13, width=2)
        if unlocked:
            pygame.draw.line(surf, (248, 238, 207),
                             (rect.x + 16, rect.centery + 1),
                             (rect.x + 21, rect.centery + 6), 2)
            pygame.draw.line(surf, (248, 238, 207),
                             (rect.x + 21, rect.centery + 6),
                             (rect.x + 30, rect.centery - 6), 2)
        else:
            draw_text(surf, "?", assets.font(15, bold=True), (126, 115, 102),
                      icon_center, "center")

        title = "Скрытое достижение" if hidden else achievement.title
        desc = "Продолжайте исследовать мир." if hidden else achievement.desc
        title_col = achievement.color if unlocked else (190, 179, 160)
        desc_col = (167, 157, 140) if unlocked else (121, 113, 103)
        draw_text(surf, _ellipsize(assets.font(16, bold=True), title, rect.w - 220),
                  assets.font(16, bold=True), title_col, (rect.x + 44, rect.y + 6), "topleft")
        draw_text(surf, _ellipsize(assets.font(12), desc, rect.w - 230),
                  assets.font(12), desc_col, (rect.x + 44, rect.y + 27), "topleft")

        progress = "???" if hidden else progression.progress_text(achievement, self.game)
        draw_text(surf, progress, assets.font(13, bold=True),
                  achievement.color if unlocked else (143, 133, 119),
                  (rect.right - 14, rect.y + 7), "topright")
        bar = pygame.Rect(rect.right - 104, rect.y + 38, 90, 5)
        pygame.draw.rect(surf, (22, 20, 20), bar, border_radius=2)
        fill = bar.copy()
        fill.w = max(0, int(bar.w * (1.0 if unlocked else ratio)))
        if fill.w:
            pygame.draw.rect(surf, achievement.color if unlocked else (116, 95, 63),
                             fill, border_radius=2)

    def _draw_bestiary_card(self, surf, rect, entry):
        assets = self.game.assets
        count = 0
        if self.game.player:
            count = int(self.game.player.bestiary.get(entry.key, 0))
        seen = count > 0
        bg = (41, 36, 34) if seen else (30, 28, 28)
        border = (151, 119, 65) if entry.boss and seen else (62, 53, 46)
        pygame.draw.rect(surf, bg, rect, border_radius=7)
        pygame.draw.rect(surf, border, rect, width=2 if entry.boss and seen else 1,
                         border_radius=7)

        icon_center = (rect.x + 23, rect.centery)
        pygame.draw.circle(surf, (24, 22, 22), icon_center, 14)
        color = entry.color if seen else (67, 63, 60)
        pygame.draw.circle(surf, color, icon_center, 11)
        pygame.draw.circle(surf, tuple(max(0, c - 45) for c in color), icon_center, 11, width=2)
        if seen:
            pygame.draw.circle(surf, (245, 238, 214), (icon_center[0] - 3, icon_center[1] - 2), 2)
            pygame.draw.circle(surf, (245, 238, 214), (icon_center[0] + 4, icon_center[1] - 2), 2)
        else:
            draw_text(surf, "?", assets.font(15, bold=True), (128, 120, 108),
                      icon_center, "center")

        name = entry.name if seen else "Неизвестное существо"
        danger = "★" * entry.danger + "☆" * (5 - entry.danger)
        if seen:
            subtitle = f"{entry.biome}   •   опасность {danger}"
            desc = entry.desc
        else:
            subtitle = "Бестиарий не заполнен"
            desc = "Победите это существо, чтобы узнать подробности."
        draw_text(surf, _ellipsize(assets.font(16, bold=True), name, rect.w - 200),
                  assets.font(16, bold=True),
                  (234, 214, 172) if seen else (158, 149, 135),
                  (rect.x + 44, rect.y + 5), "topleft")
        draw_text(surf, _ellipsize(assets.font(12), subtitle, rect.w - 200),
                  assets.font(12), (176, 157, 122) if seen else (119, 112, 102),
                  (rect.x + 44, rect.y + 25), "topleft")
        draw_text(surf, _ellipsize(assets.font(11), desc, rect.w - 60),
                  assets.font(11), (150, 141, 126) if seen else (104, 98, 91),
                  (rect.x + 44, rect.y + 40), "topleft")
        if seen:
            tag = "БОСС" if entry.boss else f"×{count}"
            tag_col = (241, 197, 105) if entry.boss else (154, 199, 151)
            draw_text(surf, tag, assets.font(13, bold=True), tag_col,
                      (rect.right - 14, rect.y + 7), "topright")
            if entry.boss:
                draw_text(surf, f"×{count}", assets.font(11), (150, 141, 126),
                          (rect.right - 14, rect.y + 25), "topright")

    def _draw_scrollbar(self, surf):
        if self.max_scroll <= 0:
            return
        track = pygame.Rect(1192, VIEW.y, 6, VIEW.h)
        pygame.draw.rect(surf, (24, 20, 21), track, border_radius=3)
        frac = VIEW.h / max(1.0, self._content_height())
        bar_h = max(34, int(VIEW.h * frac))
        pos = self.scroll / self.max_scroll
        bar = pygame.Rect(track.x, VIEW.y + int((VIEW.h - bar_h) * pos), 6, bar_h)
        pygame.draw.rect(surf, (157, 123, 68), bar, border_radius=3)

# -*- coding: utf-8 -*-
"""Основной класс игры: состояния, игровой цикл, рендер и сохранения."""
from __future__ import annotations

import math
import os
import random
import time

import pygame

from . import config, crafting, progression
from .config import (
    WIDTH, HEIGHT, TILE, FPS, DAY_LENGTH, TILES, ITEMS, AIR, LEAVES,
    WORKBENCH, TORCH, LIFE_CRYSTAL, CRYSTAL, WOOD, LAVA, BOULDER_TILES,
    WATER, BIOME_FOREST, BIOME_DESERT, BIOME_SNOW, BIOME_CORRUPT,
    BIOME_BEACH, BIOME_TINTS, BIOME_SHORT, BOULDER_LAVA, BOULDER_LIFE,
    BOULDER_RAINBOW,
)
from .assets import Assets
from .audio import AudioManager
from .entities import (
    Player, ItemDrop, GelShot, VoidBolt, Slime, SlimeKing, AbyssWarden,
    ForestColossus, FrostQueen, TownNPC, Boulder, BOULDER_INFO,
    make_enemy, make_town_npcs, burst, Particle, FloatingText,
)
from .world import World
from .network import NetworkManager
from .ui import (
    MainMenu, SettingsScreen, ControlsScreen, PauseMenu, DeathScreen,
    VictoryScreen, InventoryOverlay, WorldCreateScreen, CharacterScreen,
    NetworkScreen, draw_hud, draw_guide_dialog,
)
from .codex import CodexScreen
from .ui_widgets import Backdrop, sky_values
from .utils import clamp, load_json, save_json, draw_text, panel, game_clock


class RemotePlayer:
    """Визуальная копия второго игрока в LAN-мире."""

    W = 26
    H = 56

    def __init__(self):
        self.active = False
        self.name = "Игрок"
        self.appearance: dict = {}
        self.x = 0.0
        self.y = 0.0
        self.target_x = 0.0
        self.target_y = 0.0
        self.hp = 100
        self.max_hp = 100
        self.facing = 1
        self.moving = False
        self.anim = 0.0
        self.step_phase = 0.0
        self.inited = False

    @property
    def cx(self):
        return self.x + self.W / 2

    @property
    def bottom(self):
        return self.y + self.H

    def bind(self, name="Игрок", appearance=None, state=None):
        self.active = True
        if name:
            self.name = str(name)[:24]
        if isinstance(appearance, dict):
            self.appearance = dict(appearance)
        self.inited = False
        if state:
            self.apply_state(state)

    def apply_state(self, data: dict):
        self.active = True
        if data.get("name"):
            self.name = str(data["name"])[:24]
        if isinstance(data.get("appearance"), dict):
            self.appearance = dict(data["appearance"])
        try:
            self.target_x = float(data.get("x", self.target_x))
            self.target_y = float(data.get("y", self.target_y))
            self.hp = int(data.get("hp", self.hp))
            self.max_hp = int(data.get("max_hp", self.max_hp))
            self.facing = 1 if int(data.get("facing", self.facing)) >= 0 else -1
            self.moving = bool(data.get("moving", self.moving))
        except (TypeError, ValueError):
            return
        if not self.inited:
            self.x, self.y = self.target_x, self.target_y
            self.inited = True

    def update(self, dt):
        self.anim += dt
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        if abs(dx) > 600 or abs(dy) > 600:
            self.x, self.y = self.target_x, self.target_y
        else:
            f = min(1.0, dt * 13.0)
            self.x += dx * f
            self.y += dy * f
        if self.moving:
            self.step_phase += dt * 7.0

    def draw(self, surf, cam, assets):
        if not self.active:
            return
        frames = assets.frames_for_appearance(self.appearance)
        if self.moving:
            frame = frames["walk"][int(self.step_phase) % len(frames["walk"])]
        else:
            frame = frames["idle"][int(self.anim * 1.4) % len(frames["idle"])]
        if self.facing < 0:
            frame = pygame.transform.flip(frame, True, False)
        sx = int(self.cx - cam[0])
        top = int(self.bottom - 62 - cam[1])
        shadow = pygame.Surface((44, 13), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 70), shadow.get_rect())
        surf.blit(shadow, (sx - 22, int(self.bottom - cam[1]) - 8))
        surf.blit(frame, (sx - frame.get_width() // 2, top))
        name = self.name
        draw_text(surf, name, assets.font(12, bold=True), (187, 224, 245),
                  (sx, top - 17), "midbottom", outline=1)
        w = 52
        ratio = clamp(self.hp / max(1, self.max_hp), 0, 1)
        bar = pygame.Rect(sx - w // 2, top - 12, w, 5)
        pygame.draw.rect(surf, (30, 28, 33), bar, border_radius=2)
        if ratio > 0:
            pygame.draw.rect(surf, (92, 192, 163),
                             (bar.x + 1, bar.y + 1, int((w - 2) * ratio), 3),
                             border_radius=1)


DEFAULT_SETTINGS = {
    "music": 0.55,
    "sfx": 0.75,
    "fullscreen": False,
    "shake": True,
    "tutorial": True,
    "world_size": config.DEFAULT_WORLD_SIZE,
    "appearance": dict(config.DEFAULT_APPEARANCE),
}


class Game:
    def __init__(self):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        pygame.display.set_caption("TERRA NOVA — 2D приключение")
        loaded = load_json(config.SETTINGS_PATH)
        self.settings = dict(DEFAULT_SETTINGS)
        self.settings["appearance"] = dict(config.DEFAULT_APPEARANCE)
        if isinstance(loaded, dict):
            for k in DEFAULT_SETTINGS:
                if k in loaded and k != "appearance":
                    self.settings[k] = loaded[k]
            appearance = loaded.get("appearance")
            if isinstance(appearance, dict):
                for key in config.DEFAULT_APPEARANCE:
                    if key in appearance:
                        self.settings["appearance"][key] = appearance[key]
        self.player_style = dict(self.settings.get("appearance", config.DEFAULT_APPEARANCE))
        self.running = True
        self.screen = None
        self._apply_display(initial=True)
        self._set_icon()

        self.running = True
        self.state = "menu"
        self.active_save_path = config.SAVE_PATH
        self.time = 0.0
        self.playtime = 0.0
        self.world: World | None = None
        self.player: Player | None = None
        self.enemies = []
        self.drops: list[ItemDrop] = []
        self.projectiles: list = []
        self.particles: list[Particle] = []
        self.floaters: list[FloatingText] = []
        self.toasts: list[dict] = []
        self.boulders: list[Boulder] = []
        self.npcs: list[TownNPC] = []
        self.boss: SlimeKing | ForestColossus | FrostQueen | AbyssWarden | None = None
        self.network = NetworkManager()
        self.remote_player = RemotePlayer()
        self.network_name = "Герой"
        self.dialog_lines: list[str] = []
        self.dialog_index = 0
        self.dialog_speaker = "Проводник"
        self.dialog_role = "Хранитель Терра Новы"
        self.dialog_frames_attr = "guide_frames"
        self.time_of_day = 0.20
        self.day = 1
        self.camera = [0.0, 0.0]
        self.shake_amount = 0.0
        self.damage_flash = 0.0
        self.mining_target = None
        self.mining_progress = 0.0
        self.mining_active = False
        self.attack_cd = 0.0
        self.mine_sound_timer = 0.0
        self.spawn_timer = 5.0
        self.save_timer = 45.0
        self.tutorial_timer = 0.0
        self.show_tutorial = True
        self.quest_seen: set[str] = set()
        self.achievements: set[str] = set()
        self._last_player_tile: tuple[int, int] | None = None
        self.beach_epilogue = False
        self.beach_banner = 0.0

        self._boot_screen()
        self.audio = AudioManager(self.settings, self._loading_progress)
        self.assets = Assets(self.screen)
        self.backdrop = Backdrop()

        self.menu = MainMenu(self)
        self.settings_screen = SettingsScreen(self)
        self.controls_screen = ControlsScreen(self)
        self.pause = PauseMenu(self)
        self.death = DeathScreen(self)
        self.victory = VictoryScreen(self)
        self.inventory = InventoryOverlay(self)
        self.world_create = WorldCreateScreen(self)
        self.character_screen = CharacterScreen(self)
        self.network_screen = NetworkScreen(self)
        self.codex = CodexScreen(self)
        self.codex_return = "menu"
        self.audio.play_music("menu")

    # ------------------------------------------------------------------ окно
    def _apply_display(self, initial=False):
        fs = bool(self.settings.get("fullscreen"))
        dummy = os.environ.get("SDL_VIDEODRIVER") == "dummy"
        flags = 0
        if fs and not dummy:
            flags = pygame.FULLSCREEN | pygame.SCALED
        try:
            self.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        except pygame.error:
            self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        if not initial and hasattr(self, "assets"):
            self.assets.screen = self.screen

    def toggle_fullscreen(self):
        self.settings["fullscreen"] = not self.settings.get("fullscreen", False)
        self._apply_display()
        self.save_settings()
        if hasattr(self, "settings_screen"):
            self.settings_screen._update_labels()

    def _set_icon(self):
        s = pygame.Surface((32, 32), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (53, 118, 67), (3, 7, 26, 21))
        pygame.draw.ellipse(s, (90, 196, 104), (4, 6, 24, 19))
        pygame.draw.ellipse(s, (158, 235, 159), (8, 9, 9, 6))
        pygame.draw.circle(s, (28, 44, 30), (11, 17), 2)
        pygame.draw.circle(s, (28, 44, 30), (21, 17), 2)
        pygame.display.set_icon(s)

    def _boot_screen(self):
        if not self.screen:
            return
        self.screen.fill((11, 13, 19))
        font = pygame.font.SysFont("georgia,timesnewroman,arial", 54, bold=True)
        small = pygame.font.SysFont("segoeui,arial", 20)
        img = font.render("TERRA NOVA", True, (236, 197, 105))
        self.screen.blit(img, (WIDTH // 2 - img.get_width() // 2, HEIGHT // 2 - 80))
        img2 = small.render("Подготовка мира и звуков...", True, (180, 170, 150))
        self.screen.blit(img2, (WIDTH // 2 - img2.get_width() // 2, HEIGHT // 2 + 5))
        pygame.display.flip()
        pygame.event.pump()

    def _loading_progress(self, fraction: float, label: str):
        if not self.screen:
            return
        try:
            self.screen.fill((11, 13, 19))
            font = pygame.font.SysFont("georgia,timesnewroman,arial", 46, bold=True)
            small = pygame.font.SysFont("segoeui,arial", 18)
            img = font.render("TERRA NOVA", True, (236, 197, 105))
            self.screen.blit(img, (WIDTH // 2 - img.get_width() // 2, HEIGHT // 2 - 100))
            img2 = small.render(label, True, (178, 168, 148))
            self.screen.blit(img2, (WIDTH // 2 - img2.get_width() // 2, HEIGHT // 2 + 8))
            bar = pygame.Rect(WIDTH // 2 - 220, HEIGHT // 2 + 46, 440, 12)
            pygame.draw.rect(self.screen, (34, 30, 30), bar, border_radius=6)
            fill = bar.copy()
            fill.w = max(2, int(bar.w * clamp(fraction, 0, 1)))
            pygame.draw.rect(self.screen, (196, 153, 72), fill, border_radius=6)
            pygame.display.flip()
            pygame.event.pump()
        except pygame.error:
            pass

    # ------------------------------------------------------------------ настройки
    def save_settings(self):
        self.settings["appearance"] = dict(self.player_style)
        save_json(config.SETTINGS_PATH, self.settings)

    def set_player_appearance(self, appearance: dict):
        self.player_style = dict(appearance)
        self.settings["appearance"] = dict(appearance)
        self.assets.set_player_style(self.player_style)
        if self.player:
            self.player.appearance = dict(appearance)
        self.save_settings()

    def set_music_volume(self, value):
        self.settings["music"] = clamp(value, 0, 1)
        self.audio.set_music_volume(value)
        self.save_settings()

    def set_sfx_volume(self, value):
        self.settings["sfx"] = clamp(value, 0, 1)
        self.audio.set_sfx_volume(value)
        self.save_settings()

    # ------------------------------------------------------------------ сохранения
    def has_save(self) -> bool:
        return os.path.exists(config.SAVE_PATH)

    def save_game(self, show=False) -> bool:
        if not self.world or not self.player:
            return False
        p = self.player
        data = {
            "version": 2,
            "world": self.world.to_data(),
            "player": {
                "x": p.x, "y": p.y, "hp": p.hp, "max_hp": p.max_hp,
                "sword_level": p.sword_level, "mining_level": p.mining_level,
                "inventory": p.inventory, "stats": p.stats,
                "crafted": sorted(p.crafted), "hotbar": p.hotbar_index,
                "appearance": p.appearance, "bestiary": p.bestiary,
            },
            "time_of_day": self.time_of_day,
            "day": self.day,
            "playtime": self.playtime,
            "tutorial_timer": self.tutorial_timer,
            "quest_seen": sorted(self.quest_seen),
            "achievements": sorted(self.achievements),
            "show_tutorial": self.show_tutorial,
            "epilogue": bool(getattr(self, "beach_epilogue", False)),
        }
        ok = save_json(getattr(self, "active_save_path", config.SAVE_PATH), data)
        self.save_timer = 45.0
        if show:
            if ok:
                self.toast("Игра сохранена", config.GREEN)
            else:
                self.toast("Не удалось сохранить игру", config.RED)
        return ok

    def load_game(self) -> bool:
        data = load_json(config.SAVE_PATH, backup=True)
        if not isinstance(data, dict) or "world" not in data:
            return False
        try:
            world = World.from_data(data["world"])
            player = Player(world)
            pd = data.get("player", {})
            player.x = float(pd.get("x", world.spawn_x - player.w / 2))
            player.y = float(pd.get("y", world.spawn_y - player.h))
            player.max_hp = int(clamp(int(pd.get("max_hp", 100)), 100, 200))
            player.hp = int(clamp(int(pd.get("hp", 100)), 0, player.max_hp))
            player.sword_level = int(clamp(int(pd.get("sword_level", 1)), 1, len(config.SWORD_DAMAGE) - 1))
            player.mining_level = int(clamp(int(pd.get("mining_level", 1)), 1, len(config.PICKAXE_POWER) - 1))
            player.stats.update(pd.get("stats", {}))
            player.crafted = set(pd.get("crafted", []))
            bestiary = pd.get("bestiary")
            if isinstance(bestiary, dict):
                player.bestiary = {
                    str(key): max(0, int(value))
                    for key, value in bestiary.items()
                    if isinstance(value, (int, float))
                }
            appearance = pd.get("appearance")
            if isinstance(appearance, dict):
                merged = dict(config.DEFAULT_APPEARANCE)
                for key in merged:
                    if key in appearance:
                        merged[key] = appearance[key]
                player.appearance = merged
            else:
                player.appearance = dict(self.player_style)
            inv = pd.get("inventory")
            if isinstance(inv, list):
                restored = [None] * config.INV_SLOTS
                for i, slot in enumerate(inv[:config.INV_SLOTS]):
                    if isinstance(slot, list) and len(slot) >= 2 and slot[0] in ITEMS:
                        restored[i] = [slot[0], max(1, int(slot[1]))]
                player.inventory = restored
            player.hotbar_index = int(pd.get("hotbar", 0)) % 10
            if world.rect_collides(player.rect):
                player.x = world.spawn_x - player.w / 2
                player.y = world.spawn_y - player.h - 4
        except Exception:
            return False
        self.world = world
        self.player = player
        self.active_save_path = config.SAVE_PATH
        self.player_style = dict(player.appearance)
        self.settings["appearance"] = dict(player.appearance)
        self.assets.set_player_style(player.appearance)
        self.enemies = []
        self.drops = []
        self.projectiles = []
        self.particles = []
        self.floaters = []
        self.toasts = []
        self.boulders = []
        self.npcs = make_town_npcs(world)
        self.boss = None
        self.time_of_day = float(data.get("time_of_day", 0.2)) % 1.0
        self.day = max(1, int(data.get("day", 1)))
        self.playtime = float(data.get("playtime", 0.0))
        self.show_tutorial = bool(data.get("show_tutorial", True))
        self.tutorial_timer = 0.0
        self.quest_seen = set(data.get("quest_seen", []))
        for q in crafting.get_quests(player):
            if q["done"]:
                self.quest_seen.add(q["id"])
        self.achievements = set(data.get("achievements", []))
        self._last_player_tile = None
        self.beach_epilogue = bool(data.get("epilogue", False))
        self.beach_banner = 0.0
        self.mining_target = None
        self.mining_progress = 0.0
        self.state = "playing"
        self.spawn_timer = 4.0
        self.save_timer = 45.0
        if self.beach_epilogue:
            self.world.ensure_beach()
            self._place_beach_npcs()
        self._snap_camera()
        self._update_music(force=True)
        self.check_achievements(notify=False)
        self.toast("Приключение продолжается", config.CREAM)
        return True

    # ------------------------------------------------------------------ переходы
    def start_new_world(self, size_key: str, seed: int | None, name: str):
        self._draw_generation_splash(size_key, seed, name)
        self.new_game(seed=seed, size_key=size_key, name=name)

    def _draw_generation_splash(self, size_key: str, seed: int | None, name: str):
        if not self.screen:
            return
        preset = config.WORLD_SIZES.get(size_key, config.WORLD_SIZES[config.DEFAULT_WORLD_SIZE])
        self.screen.fill((10, 13, 18))
        backdrop = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for i in range(20):
            c = (18 + i, 24 + i, 31 + i)
            pygame.draw.rect(backdrop, c, (0, i * 36, WIDTH, 38), border_radius=0)
        self.screen.blit(backdrop, (0, 0))
        draw_text(self.screen, "СОЗДАНИЕ МИРА", self.assets.font(44, bold=True, title=True),
                  config.GOLD, (WIDTH // 2, HEIGHT // 2 - 128), "center", outline=2)
        draw_text(self.screen, name or "Новый мир", self.assets.font(26, bold=True),
                  config.CREAM, (WIDTH // 2, HEIGHT // 2 - 66), "center")
        draw_text(self.screen, f"{preset['name']}  •  {preset['w']} × {preset['h']} тайлов",
                  self.assets.font(19), (183, 170, 147), (WIDTH // 2, HEIGHT // 2 - 24), "center")
        draw_text(self.screen, "Генерируем биомы, пещеры, руды и валуны...",
                  self.assets.font(16), (149, 142, 128), (WIDTH // 2, HEIGHT // 2 + 42), "center")
        bar = pygame.Rect(WIDTH // 2 - 230, HEIGHT // 2 + 82, 460, 8)
        pygame.draw.rect(self.screen, (34, 30, 30), bar, border_radius=4)
        pygame.draw.rect(self.screen, config.GOLD, (bar.x, bar.y, bar.w // 2, bar.h), border_radius=4)
        pygame.display.flip()
        pygame.event.pump()

    def new_game(self, seed: int | None = None, size_key: str | None = None, name: str | None = None,
                 save_path: str | None = None):
        size_key = size_key if size_key in config.WORLD_SIZES else self.settings.get("world_size",
                                                                                    config.DEFAULT_WORLD_SIZE)
        self.active_save_path = save_path or config.SAVE_PATH
        self.world = World(seed=seed, size_key=size_key)
        self.world.name = name or "Новый мир"
        self.player = Player(self.world)
        self.player.appearance = dict(self.player_style)
        self.assets.set_player_style(self.player.appearance)
        self.player.y = self.world.spawn_y - self.player.h
        self.player.x = self.world.spawn_x - self.player.w / 2
        self.enemies = []
        self.drops = []
        self.projectiles = []
        self.particles = []
        self.floaters = []
        self.toasts = []
        self.boulders = []
        self.npcs = make_town_npcs(self.world)
        self.boss = None
        self.time_of_day = 0.22
        self.day = 1
        self.playtime = 0.0
        self.damage_flash = 0.0
        self.shake_amount = 0.0
        self.mining_target = None
        self.mining_progress = 0.0
        self.attack_cd = 0.0
        self.spawn_timer = 5.0
        self.save_timer = 45.0
        self.quest_seen = set()
        self.achievements = set()
        self._last_player_tile = None
        self.show_tutorial = bool(self.settings.get("tutorial", True))
        self.tutorial_timer = 45.0 if self.show_tutorial else 0.0
        self.beach_epilogue = False
        self.beach_banner = 0.0
        self.settings["world_size"] = size_key
        self.state = "playing"
        self._snap_camera()
        self.save_game()
        self._update_music(force=True)
        self.toast("Добро пожаловать в TERRA NOVA!", config.GOLD)
        self.toast("Срубите дерево и создайте верстак (Tab)", config.CREAM)
        self.toast("Проводник рядом: R — поговорить", config.CREAM)

    def continue_game(self):
        if self.load_game():
            self.audio.sfx("click", 0.6)

    def to_menu(self):
        self.network.close()
        self.remote_player.active = False
        if self.world and self.player:
            if self.player.hp <= 0:
                self.player.hp = self.player.max_hp
            self.save_game()
        self.state = "menu"
        self.world = None
        self.player = None
        self.enemies = []
        self.drops = []
        self.projectiles = []
        self.particles = []
        self.floaters = []
        self.toasts = []
        self.boulders = []
        self.npcs = []
        self.boss = None
        self.dialog_lines = []
        self.mining_active = False
        self.beach_epilogue = False
        self.beach_banner = 0.0
        self.menu.refresh()
        self.audio.play_music("menu")

    def quit_game(self):
        self.network.close()
        if self.world and self.player:
            if self.player.hp <= 0:
                self.player.hp = self.player.max_hp
            self.save_game()
        self.running = False

    def open_settings(self):
        self.state = "settings"
        self.settings_screen.refresh()

    def open_controls(self):
        self.state = "controls"

    def open_world_create(self):
        self.state = "world_create"
        self.world_create.refresh()

    def open_character(self, return_state="menu"):
        self.state = "character"
        self.character_screen.return_state = return_state
        self.character_screen.refresh()

    def open_codex(self, return_state="menu"):
        self.codex_return = return_state
        self.codex.refresh()
        self.state = "codex"
        self.audio.sfx("click", 0.5)

    def close_codex(self):
        if self.codex_return in ("paused", "playing") and self.world and self.player:
            self.state = self.codex_return
        else:
            self.state = "menu"
        self.audio.sfx("click", 0.45)

    # ------------------------------------------------------------------ сеть
    def open_network(self):
        if self.network.active:
            self.network.close()
        self.remote_player.active = False
        self.state = "network"
        self.network_screen.refresh()

    def leave_network_screen(self):
        self.network.close()
        self.remote_player.active = False
        self.back_to_menu()

    def _local_network_info(self) -> dict:
        p = self.player
        appearance = dict(p.appearance if p else self.player_style)
        if not p:
            return {
                "name": self.network_name,
                "appearance": appearance,
                "x": 0, "y": 0, "hp": 100, "max_hp": 100,
                "facing": 1, "moving": False,
                "time_of_day": self.time_of_day, "day": self.day,
            }
        return {
            "name": self.network_name or "Игрок",
            "appearance": appearance,
            "x": p.x, "y": p.y,
            "hp": p.hp, "max_hp": p.max_hp,
            "facing": p.facing,
            "moving": abs(p.vx) > 25 or not p.on_ground,
            "time_of_day": self.time_of_day, "day": self.day,
        }

    def host_network(self, size_key: str, port: int, name: str):
        name = (name or "Хост").strip()[:20]
        self.network_name = name
        if not self.network.bind_host(port):
            self.network_screen.error = self.network.error
            self.network_screen.refresh()
            self.network_screen.error = self.network.error
            self.state = "network"
            return
        seed = random.randrange(1, 2_000_000_000)
        try:
            self.new_game(seed=seed, size_key=size_key, name=f"LAN-мир · {name}",
                          save_path=config.NETWORK_SAVE_PATH)
        except Exception:
            self.network.close()
            self.state = "network"
            self.network_screen.error = "Не удалось создать мир для сервера."
            return
        self.network.launch_host(self.world.to_data(), self._local_network_info())
        self.toast(f"Сервер запущен: {self.network.local_host}:{port}", config.GREEN)
        self.toast("Ожидание второго игрока в локальной сети...", config.CREAM)

    def join_network(self, address: str, port: int, name: str):
        self.network_name = (name or "Гость").strip()[:20]
        self.network_screen.error = ""
        self.network.join_async(address, port, self._local_network_info())

    def start_network_client(self, welcome: dict):
        try:
            world_data = welcome["world"]
            world = World.from_data(world_data)
        except Exception:
            self.network.close()
            self.state = "network"
            self.network_screen.error = "Не удалось загрузить мир хоста."
            return
        self.world = world
        self.world.name = world.name or "LAN-мир"
        self.active_save_path = config.NETWORK_SAVE_PATH
        self.player = Player(world)
        self.player.appearance = dict(self.player_style)
        self.assets.set_player_style(self.player.appearance)
        self.player.y = world.spawn_y - self.player.h
        self.player.x = world.spawn_x - self.player.w / 2
        # Появляемся рядом с хостом, если место свободно.
        hx = float(welcome.get("x", world.spawn_x))
        hy = float(welcome.get("y", world.spawn_y - self.player.h))
        test = pygame.Rect(int(hx + 58), int(hy), self.player.w, self.player.h)
        if not world.rect_collides(test):
            self.player.x = hx + 58
            self.player.y = hy
        self.enemies = []
        self.drops = []
        self.projectiles = []
        self.particles = []
        self.floaters = []
        self.toasts = []
        self.boulders = []
        self.npcs = make_town_npcs(world)
        self.boss = None
        self.time_of_day = float(welcome.get("time_of_day", 0.22)) % 1.0
        self.day = max(1, int(welcome.get("day", 1)))
        self.playtime = 0.0
        self.damage_flash = 0.0
        self.shake_amount = 0.0
        self.mining_target = None
        self.mining_progress = 0.0
        self.attack_cd = 0.0
        self.spawn_timer = 5.0
        self.save_timer = 45.0
        self.quest_seen = set()
        self.achievements = set()
        self._last_player_tile = None
        self.show_tutorial = bool(self.settings.get("tutorial", True))
        self.tutorial_timer = 20.0 if self.show_tutorial else 0.0
        self.beach_epilogue = False
        self.beach_banner = 0.0
        self.state = "playing"
        self.remote_player.bind(
            self.network.remote_name or welcome.get("name", "Хост"),
            self.network.remote_appearance or welcome.get("appearance", {}),
            self.network.remote_state,
        )
        self._snap_camera()
        self._update_music(force=True)
        self.save_game()
        self.toast(f"Вы подключились к миру {self.network.remote_name or 'хоста'}!", config.GREEN)
        self.toast("Изменения блоков синхронизируются между игроками", config.CREAM)

    def _poll_network(self):
        for event_name, payload in self.network.poll():
            if event_name == "joined":
                if isinstance(payload, dict) and self.state == "network":
                    self.start_network_client(payload.get("welcome", {}))
            elif event_name == "connected":
                self.remote_player.bind(self.network.remote_name or "Гость",
                                        self.network.remote_appearance,
                                        self.network.remote_state)
                if self.state in ("playing", "paused", "inventory", "dialog"):
                    self.toast("Игрок подключился к вашему миру!", config.GREEN)
            elif event_name == "disconnected":
                was_active = self.remote_player.active
                self.remote_player.active = False
                if was_active and self.state != "menu":
                    self.toast(f"Сеть: {payload}", config.RED)
            elif event_name == "error":
                text = str(payload)
                if self.state == "network":
                    self.network_screen.error = text
                elif self.state != "menu":
                    self.toast("Сеть: " + text, config.RED)
            elif event_name == "message" and isinstance(payload, dict):
                self._handle_network_message(payload)

    def _handle_network_message(self, msg: dict):
        kind = msg.get("type")
        if kind in ("hello", "state"):
            self.remote_player.apply_state(msg)
        elif kind == "tile" and self.world:
            try:
                tx = int(msg["x"])
                ty = int(msg["y"])
                tile = int(msg["tile"])
            except (KeyError, TypeError, ValueError):
                return
            if 0 <= tx < self.world.w and 0 <= ty < self.world.h:
                if self.world.get(tx, ty) != tile:
                    self.world.set(tx, ty, tile)
                    if tile == AIR:
                        self.burst(tx * TILE + TILE / 2, ty * TILE + TILE / 2,
                                   (142, 136, 123), 4, speed=60, gravity=300,
                                   life=0.35, size=2)
        elif kind == "chat":
            text = str(msg.get("text", ""))[:120]
            if text:
                self.toast(f"{self.remote_player.name}: {text}", (190, 218, 237))
        elif kind == "bye":
            self.remote_player.active = False

    def back_to_menu(self):
        self.network.close()
        self.remote_player.active = False
        self.state = "menu"
        self.menu.refresh()
        self.audio.play_music("menu")

    def open_dialog(self, lines: list[str], speaker="Проводник", role=None, frames_attr=None):
        self.dialog_lines = [line for line in lines if line]
        self.dialog_index = 0
        self.dialog_speaker = speaker
        self.dialog_role = role or "Хранитель Терра Новы"
        self.dialog_frames_attr = frames_attr or "guide_frames"
        if self.dialog_lines:
            self.state = "dialog"
            self.audio.sfx("click", 0.45)

    def advance_dialog(self):
        if not self.dialog_lines:
            return
        self.dialog_index += 1
        if self.dialog_index >= len(self.dialog_lines):
            self.dialog_lines = []
            self.dialog_index = 0
            if self.world and self.player:
                self.state = "playing"
        else:
            self.audio.sfx("click", 0.35)

    def close_dialog(self):
        self.dialog_lines = []
        self.dialog_index = 0
        if self.world and self.player:
            self.state = "playing"

    def talk_to_guide(self):
        if not self.player:
            return
        nearest = None
        nearest_dist = 1e9
        for npc in self.npcs:
            if not npc.alive:
                continue
            d = math.hypot(npc.cx - self.player.cx, npc.cy - self.player.cy)
            if d < 140 and d < nearest_dist:
                nearest = npc
                nearest_dist = d
        if nearest is None:
            return
        lines = nearest.dialogue(self)
        self.open_dialog(lines, nearest.name, getattr(nearest, "role", "Житель"),
                         getattr(nearest, "frames_attr", "guide_frames"))

    def _guide_lines(self) -> list[str]:
        p = self.player
        s = p.stats
        lines = []
        if "workbench" not in p.crafted:
            lines.append("Привет, путник! Сруби дерево, сделай доски и верстак. "
                         "Без верстака не выйдет достойного снаряжения.")
        elif p.mining_level < 3:
            lines.append("У тебя уже есть верстак. Медная кирка откроет путь к камню, "
                         "а каменная — к железным жилам.")
        elif s["iron"] < 8:
            lines.append("Под землёй пахнет железом. Ищи серые прожилки в камне, "
                         "а факелы не дай тьме погасить.")
        elif s["gel"] < 20:
            lines.append("Слизни дают липкую слизь. Собери двадцать — и сможешь "
                         "сковать Корону слизи, но не призывай короля без меча получше.")
        elif "slime_crown" not in p.crafted:
            lines.append("Корона слизи куётся на верстаке из слизи, золота и кристаллов. "
                         "Надень её и используй под открытым небом.")
        elif s["bosses"] < 1:
            lines.append("Король слизи силён, но его ядро — ключ к Бездне. "
                         "Не стой под прыжками и бей, когда он приземляется.")
        elif "forest_idol" not in p.crafted:
            lines.append("Ядро короля у тебя. Теперь вырежи Лесного идола из древесины, "
                         "слизи и золота — он разбудит хозяина Изумрудного леса.")
        elif s["bosses"] < 2:
            lines.append("Лесной колосс медлителен, но его семена отскакивают от земли. "
                         "Держись подальше и атакуй после прыжка.")
        elif "frost_diadem" not in p.crafted:
            lines.append("Сердце леса добыто! Выкуй Морозный венец из льда и снежного "
                         "камня. Ледяная королева ждёт в Снежных пиках.")
        elif s["bosses"] < 3:
            lines.append("Королева парит и швыряет веера осколков. Следи за телепортом "
                         "и не дай загнать себя в угол.")
        elif "abyss_sigil" not in p.crafted:
            lines.append("Слеза зимы у тебя. Собери Печать Бездны из трёх трофеев — "
                         "только тогда Страж Бездны ответит на зов.")
        elif s["bosses"] < 4:
            lines.append("Страж Бездны ждёт в глубине. Ударь Печатью там, где тьма гуще, "
                         "и приготовься уклоняться от фиолетовых сфер.")
        else:
            lines.append("Все четыре стража пали. Мир расколот, но теперь у него есть герой. "
                         "Строй, исследуй и помни: Бездна всегда смотрит.")
        if len(lines) < 2:
            biome = self.world.biome_name(p.cx) if self.world else "Изумрудный лес"
            lines.append(f"Сейчас ты в локации «{biome}». Слушай музыку ветра и не забывай "
                         "спать... хотя в Терранове сон — роскошь.")
        if p.hp < p.max_hp * 0.5:
            lines.append("Ты ранен. Сядь у костра или выпей лечебное зелье. "
                         "Жизнь важнее любого золота.")
        return lines

    def _near_guide(self) -> bool:
        if not self.player:
            return False
        return any(n.alive and abs(n.cx - self.player.cx) < 130 and
                   abs(n.cy - self.player.cy) < 120 for n in self.npcs)

    def resume_game(self):
        if self.world and self.player:
            self.state = "playing"

    def close_inventory(self):
        self.state = "playing"

    def respawn(self):
        if not self.player or not self.world:
            self.back_to_menu()
            return
        p = self.player
        p.hp = p.max_hp
        p.invuln = 2.0
        p.x = self.world.spawn_x - p.w / 2
        p.y = self.world.spawn_y - p.h - 4
        p.vx = p.vy = 0
        self.enemies.clear()
        self.projectiles.clear()
        self.boulders.clear()
        self.boss = None
        self.dialog_lines = []
        if not self.npcs:
            self.npcs = make_town_npcs(self.world)
        self.state = "playing"
        self.spawn_timer = 6.0
        self._last_player_tile = None
        self._snap_camera()
        self._update_music(force=True)
        self.save_game()
        self.toast("Вы возродились у точки появления", config.CREAM)

    def player_died(self):
        if self.state != "playing":
            return
        self.state = "dead"
        self.audio.stop_music()
        self.audio.sfx("death")
        self.shake(16)
        self.projectiles.clear()

    def register_kill(self, enemy):
        """Учитывает убийство врага в статистике и бестиарии."""
        if not self.player or enemy is None:
            return
        p = self.player
        p.stats["kills_total"] = p.stats.get("kills_total", 0) + 1
        if isinstance(enemy, Slime):
            p.stats["kills_slime"] = p.stats.get("kills_slime", 0) + 1
        key = progression.bestiary_key(enemy)
        if key:
            p.bestiary[key] = p.bestiary.get(key, 0) + 1
        boss_key = progression.boss_stat_key(enemy)
        if boss_key:
            stat = f"boss_{boss_key}"
            p.stats[stat] = p.stats.get(stat, 0) + 1
        self.check_achievements()

    def check_achievements(self, notify=True):
        """Открывает достижения, условия которых уже выполнены."""
        if not self.player:
            return []
        unlocked = []
        for achievement in progression.ACHIEVEMENTS:
            if achievement.id in self.achievements:
                continue
            if progression.achievement_value(self, achievement.stat) >= achievement.need:
                self.achievements.add(achievement.id)
                unlocked.append(achievement)
        if notify:
            for achievement in unlocked:
                self.toast(f"Достижение: {achievement.title}", achievement.color)
            if unlocked:
                self.audio.sfx("victory", 0.4)
                self.burst(self.player.cx, self.player.cy, config.GOLD, 24,
                           speed=160, gravity=-40, life=1.0, size=3, glow=True)
        return unlocked

    def on_boss_defeated(self, boss):
        if not self.player:
            return
        final = bool(getattr(boss, "is_final_boss", False))
        self.register_kill(boss)
        self.player.stats["bosses"] += 1
        self.quest_seen.add("boss")
        self.boss = None
        self.projectiles.clear()
        self.boulders.clear()
        if final:
            self.state = "victory"
            self.audio.stop_music()
            self.audio.sfx("victory")
            self.victory.show()
        else:
            self.state = "playing"
            self.audio.sfx("victory", 0.8)
            name = boss.__class__.__name__
            if name == "SlimeKing":
                self.toast("Король слизи повержен! Он оставил Ядро слизи", config.GOLD)
                self.toast("Вырежьте Лесного идола на верстаке", config.GREEN)
            elif name == "ForestColossus":
                self.toast("Лесной колосс пал! В его сердце — Сердце леса", config.GREEN)
                self.toast("Выкуйте Морозный венец для Снежных пиков", config.BLUE)
            elif name == "FrostQueen":
                self.toast("Ледяная королева развеялась! Осталась Слеза зимы", config.BLUE)
                self.toast("Соберите Печать Бездны из трёх трофеев", config.PURPLE)
            else:
                self.toast(f"{boss.name} повержен!", config.GOLD)
            self._update_music(force=True)
        self.check_achievements()
        self.save_game()

    def _place_beach_npcs(self):
        """Ставит Проводника, Брана и Мирру на сухой песок у моря."""
        if not self.world:
            return []
        self.world.ensure_beach()
        spots = self.world.beach_npc_spots()
        if not spots:
            return []
        self.npcs = make_town_npcs(self.world)
        for index, npc in enumerate(self.npcs):
            px, ground_y = spots[min(index, len(spots) - 1)]
            npc.x = px - npc.w / 2
            npc.y = ground_y - npc.h
            npc.home_x = px
            if self.player:
                npc.facing = -1 if npc.cx > self.player.cx else 1
        return spots

    def start_beach_epilogue(self):
        """Финал: переносит героя и всех жителей на Лазурный берег."""
        if not self.world or not self.player:
            self.back_to_menu()
            return False
        world = self.world
        world.ensure_beach()
        spots = self._place_beach_npcs()
        p = self.player
        if spots:
            first_x = spots[0][0]
            tx = int(first_x // TILE)
            for cand in range(max(2, tx - 3), max(3, tx - 1)):
                px = cand * TILE + TILE // 2
                py = world.terrain[cand] * TILE - p.h - 2
                if not world.rect_collides(pygame.Rect(int(px - p.w / 2), int(py), p.w, p.h)):
                    p.x = px - p.w / 2
                    p.y = py
                    break
            for _ in range(8):
                if not world.rect_collides(p.rect):
                    break
                p.y -= TILE
            p.vx = p.vy = 0.0
            p.on_ground = False
        self.enemies.clear()
        self.drops.clear()
        self.projectiles.clear()
        self.particles.clear()
        self.boulders.clear()
        self.boss = None
        self.dialog_lines = []
        self.beach_epilogue = True
        self.beach_banner = 9.0
        self.check_achievements()
        self.time_of_day = 0.66
        self.spawn_timer = 10 ** 9
        self.state = "playing"
        self._snap_camera()
        self._update_music(force=True)
        self.audio.sfx("victory", 0.75)
        self.toast("Финал: Лазурный берег", config.GOLD)
        self.toast("Все жители собрались у моря. Поговорите с каждым (R)", config.CREAM)
        self.save_game()
        return True

    def resume_after_victory(self):
        if not self.world:
            self.back_to_menu()
            return
        self.state = "playing"
        self._update_music(force=True)
        self.save_game()
        self.toast("Мир снова открыт для исследования", config.CREAM)

    def playtime_text(self):
        total = int(self.playtime)
        if total < 60:
            return f"{total} сек"
        minutes = total // 60
        if minutes < 60:
            return f"{minutes} мин"
        return f"{minutes // 60} ч {minutes % 60} мин"

    # ------------------------------------------------------------------ эффекты
    def toast(self, text, color=None):
        self.toasts.append({"text": text, "color": color or config.CREAM, "life": 3.4, "max_life": 3.4})
        if len(self.toasts) > 8:
            self.toasts.pop(0)

    def burst(self, x, y, color, count=8, speed=120, gravity=600, life=0.6, size=3, glow=False):
        burst(self, x, y, color, count, speed, gravity, life, size, glow)

    def float_text(self, x, y, text, color=(255, 245, 220), size=20):
        self.floaters.append(FloatingText(x, y, text, color, 0.9, size))

    def shake(self, amount):
        if not self.settings.get("shake", True):
            return
        self.shake_amount = min(22.0, max(self.shake_amount, amount))

    def spawn_drop(self, item_id, count, x, y):
        if item_id not in ITEMS or count <= 0:
            return
        self.drops.append(ItemDrop(item_id, count, x - 9, y - 9))

    def spawn_boulder(self, tx, ty, kind, direction=1):
        bx = tx * TILE + TILE / 2 - 23
        by = ty * TILE + TILE - 46
        boulder = Boulder(bx, by, kind, direction)
        self.boulders.append(boulder)
        self.burst(boulder.cx, boulder.cy, BOULDER_INFO[kind]["color"],
                   16, speed=160, gravity=600, life=0.7, size=4)
        return boulder

    # ------------------------------------------------------------------ цикл
    def run(self):
        while self.running:
            dt = self.clock_tick()
            events = pygame.event.get()
            self.handle_events(events)
            if not self.running:
                break
            self.update(dt)
            self.draw()
            pygame.display.flip()
        pygame.quit()

    def clock_tick(self):
        if not hasattr(self, "clock"):
            self.clock = pygame.time.Clock()
        dt = self.clock.tick(FPS) / 1000.0
        return min(dt, 0.05)

    def handle_events(self, events):
        for e in events:
            if e.type == pygame.QUIT:
                self.quit_game()
                return
            if e.type == pygame.KEYDOWN and e.key == pygame.K_F11:
                self.toggle_fullscreen()
                continue
            if self.state == "codex":
                self.codex.handle_event(e)
            elif self.state in ("menu", "settings", "controls", "world_create",
                                "character", "network"):
                if self.state == "menu":
                    self.menu.handle_event(e)
                elif self.state == "settings":
                    self.settings_screen.handle_event(e)
                elif self.state == "controls":
                    self.controls_screen.handle_event(e)
                elif self.state == "world_create":
                    self.world_create.handle_event(e)
                elif self.state == "network":
                    self.network_screen.handle_event(e)
                else:
                    self.character_screen.handle_event(e)
            elif self.state == "playing":
                self.handle_play_event(e)
            elif self.state == "paused":
                self.pause.handle_event(e)
            elif self.state == "inventory":
                self.inventory.handle_event(e)
            elif self.state == "dialog":
                if e.type == pygame.KEYDOWN:
                    if e.key in (pygame.K_ESCAPE, pygame.K_r):
                        self.audio.sfx("click", 0.4)
                        self.close_dialog()
                    elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                        self.advance_dialog()
                elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    self.advance_dialog()
            elif self.state == "dead":
                self.death.handle_event(e)
            elif self.state == "victory":
                self.victory.handle_event(e)
            if not self.running:
                return

    def handle_play_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.state = "paused"
                self.audio.sfx("click", 0.5)
            elif event.key in (pygame.K_TAB, pygame.K_i, pygame.K_e, pygame.K_c):
                self.state = "inventory"
                self.inventory.open()
                self.audio.sfx("click", 0.4)
            elif event.key == pygame.K_h:
                self.show_tutorial = not self.show_tutorial
                if self.show_tutorial:
                    self.tutorial_timer = 15.0
                self.toast("Подсказки " + ("включены" if self.show_tutorial else "скрыты"), config.CREAM)
            elif event.key == pygame.K_r:
                self.talk_to_guide()
            elif event.key == pygame.K_k:
                self.open_codex("playing")
            elif event.key == pygame.K_q and self.player:
                slot = self.player.selected_item()
                if slot:
                    self.player.remove_item(slot[0], 1)
                    self.spawn_drop(slot[0], 1, self.player.cx, self.player.cy - 20)
                    self.audio.sfx("place", 0.4)
            elif pygame.K_1 <= event.key <= pygame.K_9:
                self.player.select(event.key - pygame.K_1)
            elif event.key == pygame.K_0:
                self.player.select(9)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 3:
                self.use_selected()
            elif event.button == 4:
                self.player.cycle_select(1)
            elif event.button == 5:
                self.player.cycle_select(-1)

    def update(self, dt):
        self.time += dt
        self.backdrop.update(dt)
        self._poll_network()
        if self.state == "menu":
            self.menu.update(dt)
        elif self.state == "settings":
            self.settings_screen.update(dt)
        elif self.state == "controls":
            self.controls_screen.update(dt)
        elif self.state == "world_create":
            self.world_create.update(dt)
        elif self.state == "character":
            self.character_screen.update(dt)
        elif self.state == "network":
            self.network_screen.update(dt)
        elif self.state == "codex":
            self.codex.update(dt)
        elif self.state == "playing":
            self.update_playing(dt)
        elif self.state == "dialog":
            pass
        elif self.state == "paused":
            self.pause.update(dt)
        elif self.state == "inventory":
            self.inventory.update(dt)
        elif self.state == "dead":
            self.death.update(dt)
        elif self.state == "victory":
            self.victory.update(dt)
        if (self.world and self.player and
                self.state in ("playing", "paused", "inventory", "dialog", "dead", "victory")):
            self.network.update(dt, self._local_network_info())
        self.remote_player.update(dt)

    def update_playing(self, dt):
        if not self.world or not self.player:
            return
        self.playtime += dt
        self.time_of_day += dt / DAY_LENGTH
        if self.time_of_day >= 1.0:
            self.time_of_day -= 1.0
            self.day += 1
            self.player.stats["nights_survived"] += 1
            self.toast(f"Наступил день {self.day}", config.GOLD)
            self.check_achievements()
        p = self.player
        p.update(dt, self)
        self._track_movement()
        if self.state != "playing":
            return
        for npc in self.npcs:
            npc.update(dt, self)
        for boulder in list(self.boulders):
            if boulder.alive:
                boulder.update(dt, self)
        self.boulders = [b for b in self.boulders if b.alive]
        if self.state != "playing":
            return
        for enemy in list(self.enemies):
            if enemy.alive:
                enemy.update(dt, self)
        if self.state != "playing":
            return
        self.enemies = [e for e in self.enemies if e.alive]
        for shot in list(self.projectiles):
            if shot.alive:
                shot.update(dt, self)
        self.projectiles = [s for s in self.projectiles if s.alive]
        if self.state != "playing":
            return
        for drop in self.drops:
            if drop.alive:
                drop.update(dt, self)
        self.drops = [d for d in self.drops if d.alive]
        for particle in self.particles:
            particle.update(dt)
        self.particles = [pa for pa in self.particles if pa.life > 0]
        for fl in self.floaters:
            fl.update(dt)
        self.floaters = [f for f in self.floaters if f.life > 0]
        for t in self.toasts:
            t["life"] -= dt
        self.toasts = [t for t in self.toasts if t["life"] > 0]

        self.attack_cd = max(0.0, self.attack_cd - dt)
        self.mine_sound_timer = max(0.0, self.mine_sound_timer - dt)
        self.damage_flash = max(0.0, self.damage_flash - dt * 2.8)
        self.shake_amount = max(0.0, self.shake_amount - dt * 26)
        self.tutorial_timer = max(0.0, self.tutorial_timer - dt)
        self.beach_banner = max(0.0, self.beach_banner - dt)
        if self.boss and not self.boss.alive:
            self.boss = None

        self._update_combat(dt)
        self._spawn_update(dt)
        self._check_quests()
        self._update_camera(dt)
        self._update_music()
        self.save_timer -= dt
        if self.save_timer <= 0:
            self.save_game()
            self.save_timer = 45.0

    def _track_movement(self):
        p = self.player
        if not p:
            return
        tile = (int(p.cx // TILE), int(p.cy // TILE))
        if tile == self._last_player_tile:
            return
        self._last_player_tile = tile
        p.stats["tiles_travelled"] = p.stats.get("tiles_travelled", 0) + 1
        if p.stats["tiles_travelled"] % 50 == 0:
            self.check_achievements()

    # ------------------------------------------------------------------ бой
    def _update_combat(self, dt):
        p = self.player
        mouse = pygame.mouse.get_pos()
        held = pygame.mouse.get_pressed()[0]
        self.mining_active = False
        if not held or mouse[1] > HEIGHT - 84:
            self.mining_target = None
            self.mining_progress = 0.0
            return
        mwx = mouse[0] + self.camera[0]
        mwy = mouse[1] + self.camera[1]
        if self._try_attack(mwx, mwy):
            self.mining_target = None
            self.mining_progress = 0.0
            return
        tx = int(mwx // TILE)
        ty = int(mwy // TILE)
        if not (0 <= tx < self.world.w and 0 <= ty < self.world.h):
            self.mining_target = None
            self.mining_progress = 0.0
            return
        tile = self.world.get(tx, ty)
        hardness = TILES[tile].hardness
        cx = tx * TILE + TILE / 2
        cy = ty * TILE + TILE / 2
        if tile == AIR or hardness <= 0 or math.hypot(cx - p.cx, cy - p.cy) > config.PLAYER_REACH * TILE:
            self.mining_target = None
            self.mining_progress = 0.0
            return
        if self.mining_target != (tx, ty):
            self.mining_target = (tx, ty)
            self.mining_progress = 0.0
        self.mining_active = True
        self.mining_progress += dt * p.mining_power / hardness
        if self.mine_sound_timer <= 0:
            self.audio.sfx("mine", 0.25)
            self.mine_sound_timer = 0.27
        if random.random() < dt * 8:
            self.burst(cx, cy, TILES[tile].color, 1, speed=35, gravity=300, life=0.3, size=2)
        if self.mining_progress >= 1.0:
            self._break_tile(tx, ty, tile)

    def _try_attack(self, wx, wy):
        if self.attack_cd > 0:
            return False
        p = self.player
        reach = 92 + p.sword_level * 6
        aim = math.atan2(wy - p.cy, wx - p.cx)
        best = None
        best_dist = 1e9
        for enemy in self.enemies:
            if not enemy.alive:
                continue
            dx = enemy.cx - p.cx
            dy = enemy.cy - p.cy
            d = math.hypot(dx, dy)
            if d - enemy.w * 0.35 > reach or d >= best_dist:
                continue
            # не бьём врагов за спиной, если они не вплотную
            if d > 34:
                angle = math.atan2(dy, dx)
                diff = abs((angle - aim + math.pi) % math.tau - math.pi)
                if diff > 1.15:
                    continue
            best = enemy
            best_dist = d
        if not best:
            # Катящийся валун можно разбить мечом.
            for boulder in self.boulders:
                if not boulder.alive:
                    continue
                dx, dy = boulder.cx - p.cx, boulder.cy - p.cy
                d = math.hypot(dx, dy)
                if d > reach + 12:
                    continue
                angle = math.atan2(dy, dx)
                diff = abs((angle - aim + math.pi) % math.tau - math.pi)
                if d > 34 and diff > 1.15:
                    continue
                direction = 1 if boulder.cx > p.cx else -1
                boulder.break_boulder(self)
                p.facing = direction
                p.attack_anim = 0.28
                p.attack_start = aim - 0.85
                p.attack_end = aim + 0.85
                self.attack_cd = 0.33
                self.audio.sfx("swing", 0.7)
                return True
            return False
        direction = 1 if best.cx > p.cx else -1
        crit = random.random() < 0.12
        best.take_damage(p.sword_damage, direction, self, crit)
        p.facing = direction
        p.attack_anim = 0.28
        p.attack_start = aim - 0.85
        p.attack_end = aim + 0.85
        self.attack_cd = 0.33
        self.audio.sfx("swing", 0.7)
        p.vx += direction * 25
        return True

    def _break_tile(self, tx, ty, tile):
        cx = tx * TILE + TILE / 2
        cy = ty * TILE + TILE / 2
        if tile in BOULDER_TILES:
            kind = BOULDER_TILES[tile]
            self.world.set(tx, ty, AIR)
            self.network.send_tile(tx, ty, AIR)
            self.player.stats["blocks_mined"] += 1
            direction = 1 if cx >= self.player.cx else -1
            self.spawn_boulder(tx, ty, kind, direction)
            self.check_achievements()
            self.audio.sfx("summon", 0.35)
            self.shake(4)
            self.toast(f"{BOULDER_INFO[kind]['name']} пришёл в движение!", config.RED)
            self.mining_progress = 0.0
            self.mining_target = None
            self.mining_active = False
            return
        self.world.set(tx, ty, AIR)
        self.network.send_tile(tx, ty, AIR)
        self.player.stats["blocks_mined"] += 1
        self.check_achievements()
        info = TILES[tile]
        self.burst(cx, cy, info.color, 10, speed=130, gravity=700, life=0.55, size=3)
        self.audio.sfx("break", 0.65)
        self.shake(2)
        if info.drop:
            self.spawn_drop(info.drop, 1, cx, cy)
        if tile == LIFE_CRYSTAL:
            self.toast("Кристалл жизни! ПКМ — увеличить здоровье", config.PURPLE)
            self.audio.sfx("heal", 0.7)
        self.mining_progress = 0.0
        self.mining_target = None
        self.mining_active = False

    # ------------------------------------------------------------------ предметы
    def use_selected(self):
        if not self.player or self.state != "playing":
            return
        p = self.player
        slot = p.selected_item()
        if not slot:
            return
        item_id, count = slot
        item = ITEMS[item_id]
        if item.kind == "block" and item.tile is not None:
            self._place_block(item.tile, item_id)
            return
        if item_id == "heal_potion":
            if p.hp >= p.max_hp:
                self.toast("Здоровье уже полное", config.CREAM)
                return
            p.remove_item(item_id, 1)
            p.heal(item.heal, self)
            self.audio.sfx("heal")
            self.toast(f"Восстановлено {item.heal} здоровья", config.GREEN)
            return
        if item_id == "life_crystal":
            if p.max_hp >= 200:
                self.toast("Здоровье уже максимальное (200)", config.CREAM)
                return
            p.remove_item(item_id, 1)
            p.max_hp = min(200, p.max_hp + 20)
            p.hp = min(p.max_hp, p.hp + 20)
            p.stats["life_crystals"] += 1
            self.audio.sfx("heal")
            self.toast("Максимальное здоровье +20", config.GREEN)
            self.burst(p.cx, p.cy, (238, 124, 166), 22, speed=150, gravity=-20, life=1.0, size=4, glow=True)
            self.check_achievements()
            return
        if item_id == "slime_crown":
            self.summon_boss()
            return
        if item_id == "forest_idol":
            self.summon_forest_boss()
            return
        if item_id == "frost_diadem":
            self.summon_frost_boss()
            return
        if item_id == "abyss_sigil":
            self.summon_abyss_boss()
            return
        self.toast("Этот предмет используется в крафте", config.CREAM)

    def _place_block(self, tile, item_id):
        p = self.player
        mouse = pygame.mouse.get_pos()
        if mouse[1] > HEIGHT - 84:
            return
        mwx = mouse[0] + self.camera[0]
        mwy = mouse[1] + self.camera[1]
        tx, ty = int(mwx // TILE), int(mwy // TILE)
        if not (0 <= tx < self.world.w and 0 <= ty < self.world.h):
            return
        cx = tx * TILE + TILE / 2
        cy = ty * TILE + TILE / 2
        if math.hypot(cx - p.cx, cy - p.cy) > config.PLAYER_REACH * TILE:
            return
        if not self._can_place(tx, ty, tile):
            self.audio.sfx("click", 0.3)
            return
        p.remove_item(item_id, 1)
        self.world.set(tx, ty, tile)
        self.network.send_tile(tx, ty, tile)
        p.stats["blocks_placed"] += 1
        self.audio.sfx("place")
        self.burst(cx, cy, TILES[tile].color, 6, speed=70, gravity=400, life=0.35, size=2)
        self.check_achievements()
        if tile == WORKBENCH:
            self.toast("Верстак установлен. Подойдите ближе и откройте крафт", config.GOLD)

    def _can_place(self, tx, ty, tile) -> bool:
        p = self.player
        if self.world.get(tx, ty) != AIR:
            return False
        rect = pygame.Rect(tx * TILE, ty * TILE, TILE, TILE)
        if TILES[tile].solid and rect.colliderect(p.rect):
            return False
        solid_neighbour = False
        any_neighbour = False
        for nx, ny in ((tx - 1, ty), (tx + 1, ty), (tx, ty - 1), (tx, ty + 1)):
            t = self.world.get(nx, ny)
            if t != AIR:
                any_neighbour = True
            if self.world.is_solid(nx, ny):
                solid_neighbour = True
        if tile == TORCH:
            return solid_neighbour
        return any_neighbour

    def summon_boss(self):
        p = self.player
        if self.boss and self.boss.alive:
            self.toast("Босс уже сражается с вами!", config.RED)
            return
        depth = self.world.depth_tiles(p.cx, p.cy)
        if depth > 10:
            self.toast("Для призыва нужен открытый воздух на поверхности", config.CREAM)
            return
        if p.count_item("slime_crown") < 1:
            return
        p.remove_item("slime_crown", 1)
        side = 1 if p.cx < self.world.w * TILE / 2 else -1
        bx = clamp(p.cx + side * 430, 200, self.world.w * TILE - 200)
        tx = int(bx // TILE)
        sy = self.world.surface_y(tx)
        by = sy * TILE - 120
        boss = SlimeKing(bx - 59, by)
        self.enemies.append(boss)
        self.boss = boss
        self.audio.sfx("roar")
        self.shake(20)
        self.toast("Король слизи пробудился!", config.GOLD)
        self.burst(boss.cx, boss.cy, (132, 224, 145), 30, speed=240, gravity=350, life=1.1, size=5, glow=True)

    def summon_forest_boss(self):
        p = self.player
        if self.boss and self.boss.alive:
            self.toast("Босс уже сражается с вами!", config.RED)
            return
        depth = self.world.depth_tiles(p.cx, p.cy)
        if depth > 10:
            self.toast("Лесной идол зовёт колосса только под открытым небом", config.CREAM)
            return
        if self.world.biome_at(p.cx) != BIOME_FOREST:
            self.toast("Лесной колосс слышит зов лишь в Изумрудном лесу", config.GREEN)
            return
        if p.count_item("forest_idol") < 1:
            return
        p.remove_item("forest_idol", 1)
        side = 1 if p.cx < self.world.w * TILE / 2 else -1
        bx = clamp(p.cx + side * 420, 220, self.world.w * TILE - 220)
        tx = int(bx // TILE)
        sy = self.world.surface_y(tx)
        boss = ForestColossus(bx - 73, sy * TILE - 170)
        for _ in range(10):
            if not self.world.rect_collides(boss.rect):
                break
            boss.y -= TILE
        self.enemies.append(boss)
        self.boss = boss
        self.audio.sfx("roar")
        self.shake(22)
        self.toast("Лесной колосс пробудился!", config.GREEN)
        self.burst(boss.cx, boss.cy, (143, 205, 104), 34, speed=250,
                   gravity=300, life=1.2, size=6, glow=True)

    def summon_frost_boss(self):
        p = self.player
        if self.boss and self.boss.alive:
            self.toast("Босс уже сражается с вами!", config.RED)
            return
        depth = self.world.depth_tiles(p.cx, p.cy)
        if depth > 10:
            self.toast("Морозный венец нужно поднять к небу Снежных пиков", config.CREAM)
            return
        if self.world.biome_at(p.cx) != BIOME_SNOW:
            self.toast("Ледяная королева является только в Снежных пиках", config.BLUE)
            return
        if p.count_item("frost_diadem") < 1:
            return
        side = 1 if p.cx < self.world.w * TILE / 2 else -1
        bx = clamp(p.cx + side * 330, 180, self.world.w * TILE - 180)
        tx = int(bx // TILE)
        sy = self.world.surface_y(tx)
        boss = FrostQueen(bx - 52, sy * TILE - 150 - 120)
        if self.world.rect_collides(boss.rect):
            boss.y -= TILE * 2
        p.remove_item("frost_diadem", 1)
        self.enemies.append(boss)
        self.boss = boss
        self.audio.sfx("roar")
        self.audio.sfx("summon", 0.7)
        self.shake(20)
        self.toast("Ледяная королева пробудилась!", config.BLUE)
        self.burst(boss.cx, boss.cy, (196, 239, 255), 36, speed=260,
                   gravity=-20, life=1.3, size=6, glow=True)

    def summon_abyss_boss(self):
        p = self.player
        if self.boss and self.boss.alive:
            self.toast("Босс уже сражается с вами!", config.RED)
            return
        depth = self.world.depth_tiles(p.cx, p.cy)
        if depth < 14:
            self.toast("Печать Бездны нужно использовать глубоко под землёй", config.PURPLE)
            return
        if p.count_item("abyss_sigil") < 1:
            return
        side = 1 if p.cx < self.world.w * TILE / 2 else -1
        bx = clamp(p.cx + side * 330, 180, self.world.w * TILE - 180)
        by = p.cy - 150
        boss = AbyssWarden(bx, by)
        # Ищем свободное место над полом пещеры.
        for _ in range(14):
            if not self.world.rect_collides(boss.rect):
                break
            boss.y -= TILE
        if self.world.rect_collides(boss.rect):
            self.toast("Здесь слишком тесно для Стража Бездны", config.CREAM)
            return
        p.remove_item("abyss_sigil", 1)
        self.enemies.append(boss)
        self.boss = boss
        self.audio.sfx("roar")
        self.audio.sfx("summon", 0.7)
        self.shake(24)
        self.toast("Страж Бездны пробудился!", config.PURPLE)
        self.burst(boss.cx, boss.cy, (172, 106, 234), 34, speed=260, gravity=280,
                   life=1.3, size=6, glow=True)

    # ------------------------------------------------------------------ спавн
    def _spawn_update(self, dt):
        if self.boss and self.boss.alive:
            return
        self.spawn_timer -= dt
        if self.spawn_timer > 0:
            return
        self.spawn_timer = random.uniform(1.5, 2.7)
        p = self.player
        depth = self.world.depth_tiles(p.cx, p.cy)
        night = self.is_night()
        biome = self.world.biome_at(p.cx)
        if biome == BIOME_BEACH and depth <= 12:
            # Лазурный берег — мирная зона финальной сцены.
            return
        alive = [e for e in self.enemies if e.alive]
        if depth > 9:
            if len(alive) >= 9:
                return
            if biome == BIOME_SNOW:
                choices = ["frost_bat", "frost_bat", "spider", "bat"]
            elif biome == BIOME_CORRUPT:
                choices = ["corrupt_eye", "spider", "corrupt_eye", "bat"]
            elif biome == BIOME_DESERT:
                choices = ["spider", "bat", "spider"]
            else:
                choices = ["bat", "bat", "spider"]
            if depth > 28:
                choices += ["corrupt_eye", "spider"]
            for _ in range(8):
                side = random.choice((-1, 1))
                bx = p.cx + side * random.uniform(560, 900)
                by = p.cy + random.uniform(-180, 180)
                if not (80 < bx < self.world.w * TILE - 80 and 100 < by < self.world.h * TILE - 100):
                    continue
                kind = random.choice(choices)
                temp = make_enemy(kind, bx, by)
                if not self.world.rect_collides(temp.rect):
                    self.enemies.append(temp)
                    return
        else:
            cap = 11 if night else 7
            if len(alive) >= cap:
                return
            if biome == BIOME_DESERT:
                choices = ["sand_slime", "sand_slime", "desert_scorpion", "slime"]
            elif biome == BIOME_SNOW:
                choices = ["frost_slime", "frost_slime", "frost_wolf", "frost_bat"]
            elif biome == BIOME_CORRUPT:
                choices = ["corrupt_slime", "corrupt_slime", "corrupt_eye"]
            else:
                choices = ["slime", "slime", "blue_slime", "bat"]
            if night:
                choices += ["zombie", "zombie"]
                if biome == BIOME_SNOW:
                    choices += ["frost_wolf"]
            for _ in range(10):
                side = random.choice((-1, 1))
                bx = p.cx + side * random.uniform(680, 1000)
                if not (80 < bx < self.world.w * TILE - 80):
                    continue
                tx = int(bx // TILE)
                sy = self.world.surface_y(tx)
                kind = random.choice(choices)
                temp = make_enemy(kind, bx, sy * TILE - 80)
                temp.y = sy * TILE - temp.h - 2
                if self.world.rect_collides(temp.rect):
                    continue
                self.enemies.append(temp)
                return

    def is_night(self) -> bool:
        _top, _bot, night = sky_values(self.time_of_day)
        return night > 0.55

    # ------------------------------------------------------------------ цели/музыка
    def _check_quests(self):
        changed = False
        for q in crafting.get_quests(self.player):
            if q["done"] and q["id"] not in self.quest_seen:
                self.quest_seen.add(q["id"])
                self.toast("Цель выполнена: " + q["text"], config.GREEN)
                self.audio.sfx("save", 0.5)
                changed = True
        if changed:
            self.check_achievements()

    def _update_music(self, force=False):
        if self.state not in ("playing", "paused", "inventory", "codex"):
            return
        if self.boss and self.boss.alive:
            key = getattr(self.boss, "music_key", None)
            if not key:
                key = "boss2" if getattr(self.boss, "is_final_boss", False) else "boss"
        else:
            depth = self.world.depth_tiles(self.player.cx, self.player.cy)
            if depth > 9:
                key = "cave"
            else:
                biome = self.world.biome_at(self.player.cx)
                if biome == BIOME_DESERT:
                    key = "desert"
                elif biome == BIOME_SNOW:
                    key = "snow"
                elif biome == BIOME_CORRUPT:
                    key = "corrupt"
                elif biome == BIOME_BEACH:
                    key = "beach"
                elif self.is_night():
                    key = "night"
                else:
                    key = "day"
        if force:
            self.audio.current_music = None
        self.audio.play_music(key)

    # ------------------------------------------------------------------ камера
    def _camera_target(self):
        p = self.player
        tx = p.cx - WIDTH / 2 + p.facing * 26
        ty = p.cy - HEIGHT / 2 - 12
        max_x = max(0, self.world.w * TILE - WIDTH)
        max_y = max(0, self.world.h * TILE - HEIGHT)
        return clamp(tx, 0, max_x), clamp(ty, 0, max_y)

    def _snap_camera(self):
        self.camera[0], self.camera[1] = self._camera_target()

    def _update_camera(self, dt):
        tx, ty = self._camera_target()
        f = 1.0 - math.exp(-7.0 * dt)
        self.camera[0] += (tx - self.camera[0]) * f
        self.camera[1] += (ty - self.camera[1]) * f

    def render_cam(self):
        if self.shake_amount <= 0.1:
            return int(self.camera[0]), int(self.camera[1])
        return (int(self.camera[0] + random.uniform(-1, 1) * self.shake_amount),
                int(self.camera[1] + random.uniform(-1, 1) * self.shake_amount))

    # ------------------------------------------------------------------ отрисовка
    def draw(self):
        if not self.screen:
            return
        if self.state in ("menu", "settings", "controls", "world_create",
                          "character", "network"):
            self.backdrop.draw(self.screen, self.assets, 0.60, menu=True)
            self.menu.draw(self.screen)
            if self.state == "settings":
                self.settings_screen.draw(self.screen)
            elif self.state == "controls":
                self.controls_screen.draw(self.screen)
            elif self.state == "world_create":
                self.world_create.draw(self.screen)
            elif self.state == "character":
                self.character_screen.draw(self.screen)
            elif self.state == "network":
                self.network_screen.draw(self.screen)
            return
        if not self.world or not self.player:
            self.backdrop.draw(self.screen, self.assets, 0.60, menu=True)
            if self.state == "codex":
                self.menu.draw(self.screen)
                self.codex.draw(self.screen)
            return
        cam = self.render_cam()
        ug = clamp((self.world.depth_tiles(self.player.cx, self.player.cy) - 2) / 12, 0, 1)
        self.backdrop.draw(self.screen, self.assets, self.time_of_day, cam[0], ug, menu=False)
        self._draw_tiles(cam)
        self._draw_biome_tint(ug)
        for drop in self.drops:
            drop.draw(self.screen, cam, self.assets, self)
        for boulder in self.boulders:
            if boulder.alive:
                boulder.draw(self.screen, cam, self.assets, self)
        for npc in self.npcs:
            if npc.alive:
                npc.draw(self.screen, cam, self.assets, self)
        for enemy in self.enemies:
            if enemy.alive and enemy is not self.boss:
                enemy.draw(self.screen, cam, self.assets, self)
        if self.boss and self.boss.alive:
            self.boss.draw(self.screen, cam, self.assets, self)
        for shot in self.projectiles:
            shot.draw(self.screen, cam, self.assets)
        self.remote_player.draw(self.screen, cam, self.assets)
        self.player.draw(self.screen, cam, self.assets, self)
        for particle in self.particles:
            particle.draw(self.screen, cam)
        for fl in self.floaters:
            fl.draw(self.screen, cam, self.assets)
        self._draw_lighting(cam, ug)
        self._draw_cursor(cam)
        if self.beach_epilogue and self.beach_banner > 0:
            fade = min(1.0, self.beach_banner / 1.5)
            band = pygame.Surface((WIDTH, 112), pygame.SRCALPHA)
            band.fill((9, 24, 32, int(165 * fade)))
            self.screen.blit(band, (0, 70))
            draw_text(self.screen, "ФИНАЛ · ЛАЗУРНЫЙ БЕРЕГ",
                      self.assets.font(38, bold=True, title=True), config.GOLD,
                      (WIDTH // 2, 108), "center", outline=2)
            draw_text(self.screen, "Все жители Терра Новы собрались у моря. Подойдите и поговорите (R).",
                      self.assets.font(17, italic=True), config.CREAM,
                      (WIDTH // 2, 150), "center", outline=1)
        if self.state != "inventory":
            draw_hud(self.screen, self)

        if self.state == "paused":
            self.pause.draw(self.screen)
        elif self.state == "inventory":
            self.inventory.draw(self.screen)
        elif self.state == "dialog":
            draw_guide_dialog(self.screen, self)
        elif self.state == "dead":
            self.death.draw(self.screen)
        elif self.state == "victory":
            self.victory.draw(self.screen)
        elif self.state == "codex":
            self.codex.draw(self.screen)

    def _draw_tiles(self, cam):
        x0 = max(0, int(cam[0] // TILE) - 1)
        y0 = max(0, int(cam[1] // TILE) - 1)
        x1 = min(self.world.w - 1, int((cam[0] + WIDTH) // TILE) + 1)
        y1 = min(self.world.h - 1, int((cam[1] + HEIGHT) // TILE) + 1)
        screen = self.screen
        assets = self.assets
        world = self.world
        for ty in range(y0, y1 + 1):
            row = world.tiles[ty]
            sy = ty * TILE - cam[1]
            for tx in range(x0, x1 + 1):
                tile = row[tx]
                if tile == AIR:
                    # пустоты под землёй не должны просвечивать небом
                    if ty >= world.terrain[tx]:
                        wall = assets.wall_image(world.wall_kind(tx, ty),
                                                 world.tile_variant(tx, ty))
                        screen.blit(wall, (tx * TILE - cam[0], sy))
                    continue
                if tile in config.LEAF_TILES:
                    leaf_mask = 0
                    if world.get(tx, ty - 1) in config.LEAF_TILES:
                        leaf_mask |= 1
                    if world.get(tx + 1, ty) in config.LEAF_TILES:
                        leaf_mask |= 2
                    if world.get(tx, ty + 1) in config.LEAF_TILES:
                        leaf_mask |= 4
                    if world.get(tx - 1, ty) in config.LEAF_TILES:
                        leaf_mask |= 8
                    img = assets.leaf_image(tile, leaf_mask, world.tile_variant(tx, ty))
                elif tile == WATER:
                    img = assets.water_image(world.tile_variant(tx, ty),
                                             world.get(tx, ty - 1) != WATER)
                elif TILES[tile].solid:
                    img = assets.autotile_image(tile, world.solid_mask(tx, ty),
                                                world.tile_variant(tx, ty))
                else:
                    img = assets.tile_image(tile, world.tile_variant(tx, ty))
                screen.blit(img, (tx * TILE - cam[0], sy))

    def _draw_biome_tint(self, ug):
        """Лёгкий цветовой оттенок биома для поверхности."""
        if ug >= 0.7:
            return
        biome = self.world.biome_at(self.player.cx)
        if biome == BIOME_FOREST:
            return
        tint = BIOME_TINTS.get(biome, (120, 120, 120))
        alpha = int(24 * (1.0 - ug / 0.7))
        if alpha <= 0:
            return
        layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        layer.fill((*tint, alpha))
        self.screen.blit(layer, (0, 0))

    def _draw_lighting(self, cam, ug):
        _top, _bot, night = sky_values(self.time_of_day)
        deep = clamp((self.world.depth_tiles(self.player.cx, self.player.cy) - 1) / 13, 0, 1)
        darkness = max(night * 0.34 * (1.0 - ug * 0.55), (deep ** 1.1) * 0.9)
        if darkness <= 0.02:
            return
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((4, 5, 12, int(255 * min(0.93, darkness))))
        lights = [(self.player.cx, self.player.cy, 210, 0)]
        if self.boss and self.boss.alive:
            music_key = getattr(self.boss, "music_key", "boss")
            if getattr(self.boss, "is_final_boss", False):
                boss_kind, boss_radius = 8, 200
            elif music_key == "boss_forest":
                boss_kind, boss_radius = 10, 175
            elif music_key == "boss_frost":
                boss_kind, boss_radius = 11, 185
            else:
                boss_kind, boss_radius = 9, 160
            lights.append((self.boss.cx, self.boss.cy, boss_radius, boss_kind))
        for boulder in self.boulders:
            if not boulder.alive:
                continue
            if boulder.kind == "lava":
                lights.append((boulder.cx, boulder.cy, 150, 4))
            elif boulder.kind == "life":
                lights.append((boulder.cx, boulder.cy, 100, 5))
            elif boulder.kind == "rainbow":
                lights.append((boulder.cx, boulder.cy, 100, 6))
            elif boulder.kind == "ghost":
                lights.append((boulder.cx, boulder.cy, 82, 7))
        # видимые источники
        x0 = max(0, int(cam[0] // TILE) - 2)
        y0 = max(0, int(cam[1] // TILE) - 2)
        x1 = min(self.world.w - 1, int((cam[0] + WIDTH) // TILE) + 2)
        y1 = min(self.world.h - 1, int((cam[1] + HEIGHT) // TILE) + 2)
        for ty in range(y0, y1 + 1):
            row = self.world.tiles[ty]
            for tx in range(x0, x1 + 1):
                tile = row[tx]
                if tile == TORCH:
                    flicker = 1.0 + 0.06 * math.sin(self.time * 11 + tx * 1.7 + ty)
                    lights.append((tx * TILE + TILE / 2, ty * TILE + TILE / 2, int(165 * flicker), 1))
                elif tile == LIFE_CRYSTAL:
                    lights.append((tx * TILE + TILE / 2, ty * TILE + TILE / 2, 125, 2))
                elif tile == CRYSTAL:
                    lights.append((tx * TILE + TILE / 2, ty * TILE + TILE / 2, 62, 3))
                if len(lights) > 42:
                    break
            if len(lights) > 42:
                break
        for wx, wy, radius, kind in lights:
            sx = int(wx - cam[0])
            sy = int(wy - cam[1])
            if sx < -radius or sx > WIDTH + radius or sy < -radius or sy > HEIGHT + radius:
                continue
            mask = self.assets.light_mask(radius)
            overlay.blit(mask, (sx - mask.get_width() // 2, sy - mask.get_height() // 2),
                         special_flags=pygame.BLEND_RGBA_SUB)
        self.screen.blit(overlay, (0, 0))
        # тёплое свечение
        if darkness > 0.18:
            for wx, wy, radius, kind in lights[1:]:
                sx = int(wx - cam[0])
                sy = int(wy - cam[1])
                if sx < -radius or sx > WIDTH + radius or sy < -radius or sy > HEIGHT + radius:
                    continue
                if kind == 1:
                    glow = self.assets.glow(120, (255, 154, 64))
                elif kind == 2:
                    glow = self.assets.glow(100, (255, 106, 163))
                elif kind == 4:
                    glow = self.assets.glow(130, (255, 118, 37))
                elif kind == 5:
                    glow = self.assets.glow(96, (238, 98, 164))
                elif kind == 6:
                    glow = self.assets.glow(100, (190, 125, 235))
                elif kind == 7:
                    glow = self.assets.glow(82, (130, 206, 221))
                elif kind == 8:
                    glow = self.assets.glow(170, (167, 99, 235))
                elif kind == 9:
                    glow = self.assets.glow(140, (123, 218, 139))
                elif kind == 10:
                    glow = self.assets.glow(160, (114, 205, 99))
                elif kind == 11:
                    glow = self.assets.glow(170, (139, 211, 246))
                else:
                    glow = self.assets.glow(58, (176, 116, 255))
                self.screen.blit(glow, (sx - glow.get_width() // 2, sy - glow.get_height() // 2),
                                 special_flags=pygame.BLEND_RGB_ADD)

    def _draw_cursor(self, cam):
        mouse = pygame.mouse.get_pos()
        if mouse[1] > HEIGHT - 84:
            return
        mwx = mouse[0] + cam[0]
        mwy = mouse[1] + cam[1]
        tx, ty = int(mwx // TILE), int(mwy // TILE)
        if not (0 <= tx < self.world.w and 0 <= ty < self.world.h):
            return
        p = self.player
        cx, cy = tx * TILE + TILE / 2, ty * TILE + TILE / 2
        in_reach = math.hypot(cx - p.cx, cy - p.cy) <= config.PLAYER_REACH * TILE
        sx, sy = tx * TILE - cam[0], ty * TILE - cam[1]
        slot = p.selected_item()
        item = ITEMS[slot[0]] if slot else None
        color = (235, 211, 153)
        if item and item.kind == "block" and item.tile is not None:
            if in_reach and self._can_place(tx, ty, item.tile):
                color = (129, 224, 139)
            elif in_reach:
                color = (219, 107, 94)
        elif not in_reach:
            color = (142, 132, 112)
        pygame.draw.rect(self.screen, color, (sx, sy, TILE, TILE), 1)
        pygame.draw.line(self.screen, color, (sx, sy), (sx + 6, sy), 2)
        pygame.draw.line(self.screen, color, (sx, sy), (sx, sy + 6), 2)
        pygame.draw.line(self.screen, color, (sx + TILE - 1, sy), (sx + TILE - 7, sy), 2)
        pygame.draw.line(self.screen, color, (sx + TILE - 1, sy), (sx + TILE - 1, sy + 6), 2)
        if self.mining_target == (tx, ty) and self.mining_progress > 0:
            w = int(TILE * clamp(self.mining_progress, 0, 1))
            pygame.draw.rect(self.screen, (27, 24, 22), (sx, sy - 6, TILE, 4), border_radius=2)
            pygame.draw.rect(self.screen, (237, 198, 104), (sx, sy - 6, max(1, w), 4), border_radius=2)

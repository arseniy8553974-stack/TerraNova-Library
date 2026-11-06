# -*- coding: utf-8 -*-
"""Игрок, враги, босс, предметы на земле и частицы."""
from __future__ import annotations

import math
import random

import pygame

from . import config
from .config import TILES, ITEMS, ITEM_ORDER, MAX_STACK, INV_SLOTS, TILE
from .utils import clamp, approach, sign, draw_text, game_clock


# ===================================================================== базовое
class Entity:
    def __init__(self, x, y, w, h):
        self.x = float(x)
        self.y = float(y)
        self.w = int(w)
        self.h = int(h)
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = False
        self.alive = True
        self.step_height = 0
        self.stepped = False

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    @property
    def cx(self):
        return self.x + self.w / 2

    @property
    def cy(self):
        return self.y + self.h / 2

    @property
    def bottom(self):
        return self.y + self.h


def s_pos(x, y, cam):
    return int(x - cam[0]), int(y - cam[1])


# ===================================================================== игрок
class Player(Entity):
    W = 26
    H = 56

    def __init__(self, world):
        super().__init__(world.spawn_x - self.W / 2, world.spawn_y - self.H, self.W, self.H)
        self.max_hp = 100
        self.hp = 100
        self.facing = 1
        self.invuln = 0.0
        self.since_damage = 0.0
        self.sword_level = 1
        self.mining_level = 1
        self.appearance = dict(config.DEFAULT_APPEARANCE)
        self.inventory: list[list | None] = [None] * INV_SLOTS
        self.hotbar_index = 0
        self.selected_time = 0.0
        self.anim_time = 0.0
        self.walk_phase = 0.0
        self.jump_was_down = False
        self.jump_buffer = 0.0
        self.jump_cut = False
        self.coyote = 0.0
        self.step_height = config.TILE - 2
        self.landing = 0.0
        self.attack_anim = 0.0
        self.attack_start = 0.0
        self.attack_end = 0.0
        self.dust_timer = 0.0
        self.regen_acc = 0.0
        self.stats = {
            "wood": 0, "stone": 0, "gel": 0, "iron": 0, "gold": 0,
            "kills": 0, "bosses": 0, "life_crystals": 0,
            # --- прогресс (перенесено из «ТЕРРАПИИ») ---
            "blocks_mined": 0, "blocks_placed": 0,
            "kills_total": 0, "kills_slime": 0,
            "nights_survived": 0, "tiles_travelled": 0,
            "boss_slime_king": 0, "boss_forest_colossus": 0,
            "boss_frost_queen": 0, "boss_abyss_warden": 0,
        }
        self.bestiary: dict[str, int] = {}
        self.crafted: set[str] = set()
        self.add_item("torch", 8)

    # --------------------------------------------------------------- инвентарь
    def add_item(self, item_id: str, count: int, count_stats=False) -> int:
        if item_id not in ITEMS or count <= 0:
            return count
        left = count
        for slot in self.inventory:
            if slot and slot[0] == item_id and slot[1] < MAX_STACK:
                take = min(MAX_STACK - slot[1], left)
                slot[1] += take
                left -= take
                if left <= 0:
                    break
        if left > 0:
            for i, slot in enumerate(self.inventory):
                if slot is None:
                    take = min(MAX_STACK, left)
                    self.inventory[i] = [item_id, take]
                    left -= take
                    if left <= 0:
                        break
        if count_stats:
            gained = count - left
            if item_id == "wood":
                self.stats["wood"] += gained
            elif item_id == "stone":
                self.stats["stone"] += gained
            elif item_id == "gel":
                self.stats["gel"] += gained
            elif item_id == "iron_ore":
                self.stats["iron"] += gained
            elif item_id == "gold_ore":
                self.stats["gold"] += gained
        return left

    def count_item(self, item_id: str) -> int:
        return sum(slot[1] for slot in self.inventory if slot and slot[0] == item_id)

    def has_items(self, requirements: dict) -> bool:
        return all(self.count_item(k) >= v for k, v in requirements.items())

    def remove_item(self, item_id: str, count: int) -> bool:
        if self.count_item(item_id) < count:
            return False
        left = count
        for i, slot in enumerate(self.inventory):
            if not slot or slot[0] != item_id:
                continue
            take = min(slot[1], left)
            slot[1] -= take
            left -= take
            if slot[1] <= 0:
                self.inventory[i] = None
            if left <= 0:
                break
        return True

    def selected_item(self):
        if 0 <= self.hotbar_index < len(self.inventory):
            return self.inventory[self.hotbar_index]
        return None

    def select(self, index: int):
        self.hotbar_index = max(0, min(config.HOTBAR_SLOTS - 1, index))
        self.selected_time = 2.4

    def cycle_select(self, direction: int):
        self.select((self.hotbar_index + direction) % config.HOTBAR_SLOTS)

    def selected_name(self):
        slot = self.selected_item()
        return ITEMS[slot[0]].name if slot else ""

    # --------------------------------------------------------------- бой / урон
    @property
    def sword_damage(self):
        return config.SWORD_DAMAGE[min(self.sword_level, len(config.SWORD_DAMAGE) - 1)]

    @property
    def mining_power(self):
        return config.PICKAXE_POWER[min(self.mining_level, len(config.PICKAXE_POWER) - 1)]

    def take_damage(self, amount: int, source_x: float, game):
        if self.invuln > 0 or self.hp <= 0:
            return
        self.hp = max(0, self.hp - int(amount))
        self.invuln = 0.9
        self.since_damage = 0.0
        direction = -1 if source_x > self.cx else 1
        self.vx = 220 * direction
        self.vy = -230
        game.audio.sfx("hurt")
        game.shake(10)
        game.damage_flash = 1.0
        game.burst(self.cx, self.cy, (210, 74, 74), 12, speed=150, gravity=700, life=0.6)
        game.float_text(self.cx, self.y - 8, f"-{amount}", (255, 130, 130))
        if self.hp <= 0:
            game.player_died()

    def heal(self, amount: int, game=None):
        before = self.hp
        self.hp = min(self.max_hp, self.hp + amount)
        if game and self.hp > before:
            game.float_text(self.cx, self.y - 14, f"+{self.hp - before}", (128, 237, 148))
            game.burst(self.cx, self.cy, (120, 230, 150), 10, gravity=-60, life=0.8)

    # --------------------------------------------------------------- обновление
    def update(self, dt: float, game):
        keys = pygame.key.get_pressed()
        self.anim_time += dt
        self.invuln = max(0.0, self.invuln - dt)
        self.attack_anim = max(0.0, self.attack_anim - dt)
        self.selected_time = max(0.0, self.selected_time - dt)
        self.since_damage += dt
        if self.hp > 0 and self.since_damage > 7.0 and self.hp < self.max_hp:
            self.regen_acc += dt * 2.8
            if self.regen_acc >= 1.0:
                amount = int(self.regen_acc)
                self.regen_acc -= amount
                self.hp = min(self.max_hp, self.hp + amount)

        move = 0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            move -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            move += 1

        # Terraria-ощущение: быстрый разгон, цепкое сцепление и управление в воздухе.
        speed = 258.0
        grounded = self.on_ground
        accel = 2850.0 if grounded else 1650.0
        if move:
            self.vx = approach(self.vx, move * speed, accel * dt)
            self.facing = move
        else:
            friction = 3100.0 if grounded else 380.0
            self.vx = approach(self.vx, 0, friction * dt)

        # Прыжок: coyote time + буфер нажатия + управляемая высота.
        if self.on_ground:
            self.coyote = 0.11
        else:
            self.coyote = max(0.0, self.coyote - dt)
        jump_down = keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]
        if jump_down and not self.jump_was_down:
            self.jump_buffer = 0.14
        else:
            self.jump_buffer = max(0.0, self.jump_buffer - dt)
        if self.jump_buffer > 0 and self.coyote > 0 and self.hp > 0:
            self.vy = -665
            self.coyote = 0.0
            self.jump_buffer = 0.0
            self.jump_cut = True
            self.on_ground = False
            game.audio.sfx("jump")
            game.burst(self.cx, self.bottom, (166, 146, 116), 6,
                       speed=65, gravity=300, life=0.38, size=2)
        self.jump_was_down = jump_down
        if not jump_down and self.jump_cut and self.vy < -210:
            self.vy *= 0.52
            self.jump_cut = False
        if self.vy >= 0:
            self.jump_cut = False

        fall_speed = self.vy
        self.vy = min(self.vy + 2050 * dt, 1120)
        was_airborne = not self.on_ground
        game.world.move_entity(self, dt)

        # Мягкое приземление: пыль, тряска и короткая «плюха» модели.
        self.landing = max(0.0, self.landing - dt)
        if was_airborne and self.on_ground:
            self.jump_cut = False
            self.landing = 0.18
            if fall_speed > 300:
                game.burst(self.cx, self.bottom - 2, (154, 133, 104), 7,
                           speed=70, gravity=240, life=0.45, size=2)
                if fall_speed > 720:
                    game.shake(2.5)
        if self.stepped and abs(self.vx) > 80:
            self.dust_timer -= dt
            if self.dust_timer <= 0:
                self.dust_timer = 0.1
                game.burst(self.cx - self.facing * 6, self.bottom - 2,
                           (154, 133, 104), 2, speed=28, gravity=120, life=0.3, size=2)

        # Лава обжигает и подбрасывает игрока.
        feet_x = int((self.cx) // TILE)
        feet_y = int((self.bottom - 3) // TILE)
        if game.world.is_lava(feet_x, feet_y) and self.invuln <= 0:
            self.take_damage(14, self.cx, game)
            self.vy = -360
            if self.hp > 0:
                game.toast("Лава! Берегитесь огня", config.RED)

        # пыль при беге
        if self.on_ground and abs(self.vx) > 90:
            self.dust_timer -= dt
            if self.dust_timer <= 0:
                self.dust_timer = 0.13
                game.burst(self.cx - self.facing * 8, self.bottom - 2, (142, 120, 92),
                           2, speed=30, gravity=100, life=0.35, size=2)

        # анимация
        if not self.on_ground:
            pose = "jump" if self.vy < 0 else "fall"
        elif abs(self.vx) > 25:
            pose = "walk"
            self.walk_phase += dt * (6.0 + abs(self.vx) / 80)
        else:
            pose = "idle"
            self.walk_phase += dt * 1.4

    # --------------------------------------------------------------- рисование
    def draw(self, surf, cam, assets, game):
        sx, sy = self.cx - cam[0], self.y - cam[1]
        # тень
        shadow = pygame.Surface((44, 14), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 75), shadow.get_rect())
        surf.blit(shadow, (sx - 22, self.bottom - cam[1] - 8))

        if self.invuln > 0 and int(self.invuln * 22) % 2 == 0:
            return

        pose = "idle"
        if not self.on_ground:
            pose = "jump" if self.vy < 0 else "fall"
        elif abs(self.vx) > 25:
            pose = "walk"
        frames = assets.player_frames[pose]
        if pose == "walk":
            frame = frames[int(self.walk_phase) % len(frames)]
        elif pose == "idle":
            frame = frames[int(self.anim_time * 1.4) % len(frames)]
        else:
            frame = frames[0]
        if self.facing < 0:
            frame = pygame.transform.flip(frame, True, False)
        if self.landing > 0:
            k = self.landing / 0.18
            frame = pygame.transform.smoothscale(
                frame, (max(1, int(frame.get_width() * (1.0 + 0.05 * k))),
                        max(1, int(frame.get_height() * (1.0 - 0.07 * k)))))
        top = int(self.bottom - 62 - cam[1])
        surf.blit(frame, (int(sx - frame.get_width() / 2), top))

        # инструмент в руках
        mouse = pygame.mouse.get_pos()
        ang = math.atan2((mouse[1] + cam[1]) - (self.cy), (mouse[0] + cam[0]) - self.cx)
        if game.mining_active:
            wobble = math.sin(game.time * 24) * 0.5
            self._draw_tool(surf, cam, assets, assets.pickaxe_sprite, ang + wobble, 28)
        elif self.attack_anim > 0:
            total = 0.28
            t = 1.0 - self.attack_anim / total
            angle = self.attack_start + (self.attack_end - self.attack_start) * t
            self._draw_tool(surf, cam, assets, assets.sword_sprite, angle, 32)

    def _draw_tool(self, surf, cam, assets, sprite, angle, dist):
        rot = pygame.transform.rotate(sprite, -math.degrees(angle))
        px = self.cx + math.cos(angle) * dist - cam[0]
        py = self.cy + math.sin(angle) * dist - cam[1]
        rect = rot.get_rect(center=(px, py))
        surf.blit(rot, rect)


# ===================================================================== жители
class TownNPC(Entity):
    """Дружелюбный житель: стоит у дома, смотрит на игрока и даёт советы."""

    frames_attr = "guide_frames"
    role = "Житель Терра Новы"
    name = "Житель"
    home_offset = 3.5
    npc_w = 30
    npc_h = 62

    def __init__(self, world):
        self.home_x = world.spawn_x + config.TILE * self.home_offset
        tx = max(1, min(world.w - 2, int(self.home_x // config.TILE)))
        gy = world.surface_y(tx)
        super().__init__(self.home_x - self.npc_w / 2, gy * config.TILE - self.npc_h,
                         self.npc_w, self.npc_h)
        self.step_height = 18
        self.anim = random.random() * 4
        self.facing = -1
        self.alive = True

    def dialogue(self, game) -> list[str]:
        return ["Мир велик, а дорога длинна. Береги себя, герой."]

    def update(self, dt, game):
        self.anim += dt
        p = game.player
        if not p:
            return
        if abs(p.cx - self.cx) < 260:
            self.facing = 1 if p.cx > self.cx else -1
        near = math.hypot(p.cx - self.cx, p.cy - self.cy) < 130
        if near and p.on_ground and abs(p.cx - self.cx) < 50:
            # мягко расходимся, чтобы игрок не стоял внутри NPC
            self.x += (self.home_x - self.cx) * dt * 0.4

    @property
    def talkable(self):
        return True

    def draw(self, surf, cam, assets, game):
        sx = int(self.cx - cam[0])
        sy = int(self.bottom - cam[1])
        frames = getattr(assets, self.frames_attr)
        f = frames[int(self.anim * 1.6) % len(frames)]
        if self.facing > 0:
            f = pygame.transform.flip(f, True, False)
        shadow = pygame.Surface((40, 12), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 70), shadow.get_rect())
        surf.blit(shadow, (sx - 20, sy - 7))
        surf.blit(f, (int(sx - f.get_width() / 2), sy - f.get_height()))
        draw_text(surf, self.name, assets.font(13, bold=True), (228, 213, 177),
                  (sx, sy - f.get_height() - 18), "midbottom", outline=1)
        p = game.player
        if p and math.hypot(p.cx - self.cx, p.cy - self.cy) < 120:
            draw_text(surf, "R — поговорить", assets.font(13), (170, 226, 186),
                      (sx, sy - f.get_height() + 1), "midtop", outline=1)


class Guide(TownNPC):
    """Проводник у точки появления. Даёт советы по прогрессу."""

    frames_attr = "guide_frames"
    role = "Хранитель Терра Новы"
    name = "Проводник"
    home_offset = 3.5
    npc_w = 30
    npc_h = 62

    def dialogue(self, game):
        if getattr(game, "beach_epilogue", False):
            return [
                "Вот и всё, герой. Четыре стража пали, а море шумит так же спокойно, как в первый день.",
                "Бран принёс факелы, Мирра — чай, а я просто рад видеть тебя живым.",
                "Этот берег теперь наша награда. Строй, гуляй и помни: приключение никогда не заканчивается.",
            ]
        return game._guide_lines()


class Blacksmith(TownNPC):
    """Кузнец Бран: раз в день делится рудой и факелами."""

    frames_attr = "blacksmith_frames"
    role = "Кузнец"
    name = "Бран"
    home_offset = -4.6
    npc_w = 34
    npc_h = 64

    def __init__(self, world):
        super().__init__(world)
        self.last_gift_day = 0

    def dialogue(self, game):
        p = game.player
        if getattr(game, "beach_epilogue", False):
            return [
                "Наконец-то наковальня остыла, а море тёплое. Хороший финал, как хорошая сталь — без трещин.",
                "Я поставил факелы на мостках. Пусть горят всю ночь: герою больше не нужно бояться темноты.",
                "Если захочешь построить дом у воды — скажи. Молот у меня всегда с собой.",
            ]
        lines = ["Здравствуй, герой! Молот мой слышен за три холма, "
                 "а наковальня всегда ждёт работу."]
        if game.day > self.last_gift_day:
            self.last_gift_day = game.day
            p.add_item("iron_ore", 5)
            p.add_item("torch", 4)
            game.toast("Бран подарил 5 железной руды и 4 факела", config.GOLD)
            lines.append("Держи, это тебе. Железо из моих запасов и факелы, "
                         "чтобы тьма не съела твой путь. Заходи завтра.")
        else:
            lines.append("Сегодня я уже поделился рудой. Добывай сам — "
                         "шахта любит упорных.")
        if p.sword_level < 3:
            lines.append("Сначала выкуй медный или каменный меч. С голыми руками "
                         "даже слизень смеётся над героем.")
        elif p.sword_level < 5:
            lines.append("Под землёй полно железа. Железный меч и кирка откроют "
                         "дорогу к золоту и кристаллам.")
        else:
            lines.append("Хорошее оружие у тебя. Но против Лесного колосса нужны "
                         "крепкие нервы: бей после его удара и уходи в сторону.")
        return lines


class Herbalist(TownNPC):
    """Травница Мирра: лечит, снабжает зельями и подсказывает про кристаллы."""

    frames_attr = "herbalist_frames"
    role = "Травница"
    name = "Мирра"
    home_offset = 6.6
    npc_w = 30
    npc_h = 62

    def __init__(self, world):
        super().__init__(world)
        self.last_gift_day = 0
        self.last_bonus_day = 0

    def dialogue(self, game):
        p = game.player
        if getattr(game, "beach_epilogue", False):
            return [
                "Смотри, какие травы растут у солёной воды! Я уже заварила морской чай — тебе с мёдом.",
                "Раны заживают быстрее, когда рядом друзья. А сегодня рядом все, кто тебе помогал.",
                "Отдохни, герой. Кристаллы жизни больше не нужны — теперь просто любуйся закатом.",
            ]
        lines = ["Травы шепчут мне о твоих ранах, путник. "
                 "Присядь, я приготовлю снадобье."]
        if game.day > self.last_gift_day:
            self.last_gift_day = game.day
            p.add_item("heal_potion", 2)
            game.toast("Мирра подарила 2 лечебных зелья", config.GREEN)
            lines.append("Вот два зелья. Ранен — пей сразу, не жди, пока "
                         "земля поплывёт под ногами.")
        else:
            lines.append("Больше зелий на сегодня нет: травы должны отдохнуть. "
                         "А вот совет всегда со мной.")
        if game.day - self.last_bonus_day >= 3:
            self.last_bonus_day = game.day
            p.add_item("life_crystal", 1)
            game.toast("Мирра нашла для тебя Кристалл жизни", config.PURPLE)
            lines.append("И ещё одно: я нашла в старой шахте кристалл жизни. "
                         "Он навсегда укрепит твоё сердце. Используй его из хотбара.")
        if p.max_hp < 160:
            lines.append("Ищи розовые кристаллы в пещерах. Каждый добавляет "
                         "двадцать здоровья — а лишняя жизнь дороже золота.")
        else:
            lines.append("Твоё сердце стало крепче. Но Бездна всё равно "
                         "проверит его на прочность.")
        return lines


def make_town_npcs(world):
    """Все жители, которые появляются у точки возрождения."""
    return [Guide(world), Blacksmith(world), Herbalist(world)]


# ===================================================================== валуны
BOULDER_INFO = {
    "normal": {"name": "Валун", "damage": 24, "color": (126, 120, 124)},
    "bouncy": {"name": "Прыгучий валун", "damage": 13, "color": (165, 131, 99)},
    "life": {"name": "Валун — кристалл жизни", "damage": 16, "color": (202, 94, 138)},
    "lava": {"name": "Лавовый валун", "damage": 24, "color": (222, 93, 38)},
    "spider": {"name": "Паучий валун", "damage": 18, "color": (131, 108, 143)},
    "rainbow": {"name": "Радужный валун", "damage": 11, "color": (196, 137, 220)},
    "ghost": {"name": "Призрачный валун", "damage": 8, "color": (148, 199, 211)},
    "ice": {"name": "Ледяной валун", "damage": 17, "color": (170, 221, 238)},
}


class Boulder(Entity):
    """Катящийся камень-ловушка. Появляется при добыче валунного тайла."""

    def __init__(self, x, y, kind="normal", direction=1):
        super().__init__(x, y, 46, 46)
        self.kind = kind if kind in BOULDER_INFO else "normal"
        info = BOULDER_INFO[self.kind]
        self.name = info["name"]
        self.damage = info["damage"]
        self.color = info["color"]
        self.direction = 1 if direction >= 0 else -1
        self.vx = self.direction * random.uniform(280, 380)
        self.vy = -random.uniform(30, 110)
        self.age = 0.0
        self.angle = random.random() * 360
        self.hit_wall = False
        self.slow_time = 0.0
        self.trail_timer = 0.0
        self.alive = True

    def break_boulder(self, game):
        if not self.alive:
            return
        self.alive = False
        cx, cy = self.cx, self.cy
        info = BOULDER_INFO[self.kind]
        game.burst(cx, cy, info["color"], 24, speed=220, gravity=600, life=0.9, size=4)
        game.audio.sfx("break", 0.7)
        game.shake(5)
        if self.kind == "life":
            game.spawn_drop("life_crystal", 1, cx, cy)
            game.spawn_drop("crystal", 2, cx, cy)
            game.toast("Из валуна выпал кристалл жизни!", config.PURPLE)
        elif self.kind == "lava":
            game.burst(cx, cy, (255, 130, 42), 26, speed=180, gravity=-100,
                       life=1.1, size=6, glow=True)
            for _ in range(2):
                game.spawn_drop("stone", 1, cx, cy)
        elif self.kind == "spider":
            for i in range(2):
                game.enemies.append(CaveSpider(cx + (i * 34 - 17), cy - 20))
            game.spawn_drop("gel", 4, cx, cy)
            game.toast("Из валуна выползли пещерные пауки!", config.PURPLE)
        elif self.kind == "rainbow":
            loot = random.choice(("copper_ore", "iron_ore", "gold_ore", "crystal", "ice"))
            game.spawn_drop(loot, random.randint(2, 5), cx, cy)
            game.spawn_drop("gel", 2, cx, cy)
            game.toast("Радужный валун рассыпался сокровищами!", config.GOLD)
        elif self.kind == "ice":
            game.spawn_drop("ice", 4, cx, cy)
        elif self.kind == "bouncy":
            game.spawn_drop("stone", 2, cx, cy)
            game.spawn_drop("gel", 2, cx, cy)
        elif self.kind == "ghost":
            game.spawn_drop("crystal", 1, cx, cy)
        else:
            game.spawn_drop("stone", 3, cx, cy)

    def update(self, dt, game):
        if not self.alive:
            return
        self.age += dt
        self.vy = min(self.vy + 1750 * dt, 1000)
        before_vx = self.vx
        game.world.move_entity(self, dt)
        self.angle += self.vx * dt * 2.7
        if self.on_ground:
            self.vx *= (1.0 - min(0.9, dt * 0.6))
        if abs(before_vx) > 30 and abs(self.vx) < 1:
            self.hit_wall = True
            if self.kind == "bouncy":
                self.vx = -before_vx * 0.72
                self.vy = -190
                game.audio.sfx("jump", 0.45)
                self.hit_wall = False
            else:
                game.shake(4)
                self.break_boulder(game)
                return
        if self.kind == "lava":
            self.trail_timer -= dt
            if self.trail_timer <= 0:
                self.trail_timer = 0.09
                game.burst(self.cx, self.bottom - 4, (247, 120, 37), 1,
                           speed=40, gravity=-90, life=0.45, size=3, glow=True)
        if abs(self.vx) < 15 and self.on_ground:
            self.slow_time += dt
            if self.slow_time > 1.0:
                self.break_boulder(game)
                return
        else:
            self.slow_time = 0.0
        if self.y > game.world.h * config.TILE - 20:
            self.break_boulder(game)
            return
        if self.age > 9.0:
            self.break_boulder(game)
            return
        p = game.player
        if p and self.rect.colliderect(p.rect) and p.invuln <= 0:
            p.take_damage(self.damage, self.cx, game)
            game.shake(8)
            if self.kind == "bouncy":
                self.vx = -self.vx * 1.05
                self.vy = -260
            else:
                self.break_boulder(game)
                return
        # валуны давят и обычных врагов
        if self.age < 4.0:
            for e in list(game.enemies):
                if e is not game.boss and e.alive and self.rect.colliderect(e.rect):
                    e.take_damage(self.damage * 2, self.direction, game)
                    if self.kind != "bouncy":
                        self.break_boulder(game)
                        return
        if self.age > 7.0:
            self.vx *= (1 - min(1.0, dt * 0.4))

    def draw(self, surf, cam, assets, game):
        if not self.alive:
            return
        img = assets.boulder_image(self.kind)
        rotated = pygame.transform.rotate(img, -self.angle)
        sx, sy = int(self.cx - cam[0]), int(self.cy - cam[1])
        alpha = 190 if self.kind == "ghost" else 255
        rotated.set_alpha(alpha)
        rect = rotated.get_rect(center=(sx, sy))
        if game.time_of_day is not None and self.kind == "ghost":
            glow = assets.glow(46, (129, 196, 213))
            surf.blit(glow, (sx - glow.get_width() // 2, sy - glow.get_height() // 2),
                      special_flags=pygame.BLEND_RGB_ADD)
        surf.blit(rotated, rect)


# ===================================================================== дроп
class ItemDrop(Entity):
    def __init__(self, item_id: str, count: int, x, y):
        super().__init__(x, y, 18, 18)
        self.item_id = item_id
        self.count = count
        ang = random.uniform(-2.5, 2.5)
        force = random.uniform(60, 140)
        self.vx = math.cos(ang) * force
        self.vy = -random.uniform(120, 260)
        self.age = 0.0
        self.bob = random.random() * math.tau

    def update(self, dt, game):
        self.age += dt
        self.bob += dt * 3
        p = game.player
        dist = math.hypot(p.cx - self.cx, p.cy - self.cy)
        if self.age > 0.35 and dist < 120:
            speed = 420
            dx = (p.cx - self.cx)
            dy = (p.cy - self.cy)
            d = max(1, math.hypot(dx, dy))
            self.vx = approach(self.vx, dx / d * speed, 1300 * dt)
            self.vy = approach(self.vy, dy / d * speed, 1300 * dt)
            if dist < 24:
                left = p.add_item(self.item_id, self.count, count_stats=True)
                if left < self.count:
                    game.audio.sfx("pickup", 0.25)
                    if ITEMS[self.item_id].rarity >= 2:
                        game.float_text(p.cx, p.y - 18, "+" + ITEMS[self.item_id].name, config.GOLD)
                if left <= 0:
                    self.alive = False
                else:
                    self.count = left
        else:
            self.vy = min(self.vy + 1400 * dt, 900)
            game.world.move_entity(self, dt)
            if self.on_ground:
                self.vx *= (1 - min(1.0, dt * 7))
        if self.age > 180:
            self.alive = False

    def draw(self, surf, cam, assets, game):
        sx, sy = self.cx - cam[0], self.cy - cam[1] + math.sin(self.bob) * 3 - 4
        shadow = pygame.Surface((22, 8), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 60), shadow.get_rect())
        surf.blit(shadow, (sx - 11, sy + 12))
        icon = assets.icon(self.item_id)
        icon = pygame.transform.smoothscale(icon, (24, 24))
        surf.blit(icon, (sx - 12, sy - 12))


# ===================================================================== частицы
class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "size", "gravity", "glow")

    def __init__(self, x, y, vx, vy, color, size, life, gravity=500, glow=False):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.size = size
        self.life = life
        self.max_life = life
        self.gravity = gravity
        self.glow = glow

    def update(self, dt):
        self.life -= dt
        self.vy += self.gravity * dt
        self.x += self.vx * dt
        self.y += self.vy * dt

    def draw(self, surf, cam):
        if self.life <= 0:
            return
        t = self.life / self.max_life
        r = max(1, int(self.size * (0.4 + 0.6 * t)))
        sx, sy = int(self.x - cam[0]), int(self.y - cam[1])
        if self.glow:
            glow = pygame.Surface((r * 6, r * 6), pygame.SRCALPHA)
            for rr, a in ((r * 3, 30), (r * 2, 60), (r, 200)):
                pygame.draw.circle(glow, (*self.color, int(a * t)), (r * 3, r * 3), rr)
            surf.blit(glow, (sx - r * 3, sy - r * 3), special_flags=pygame.BLEND_RGBA_ADD)
        else:
            pygame.draw.circle(surf, self.color, (sx, sy), r)


class FloatingText:
    def __init__(self, x, y, text, color=(255, 245, 220), life=1.0, size=20):
        self.x, self.y = x, y
        self.text = text
        self.color = color
        self.life = life
        self.max_life = life
        self.size = size
        self.vy = -34

    def update(self, dt):
        self.life -= dt
        self.y += self.vy * dt
        self.vy *= (1 - min(1.0, dt * 2))

    def draw(self, surf, cam, assets):
        if self.life <= 0:
            return
        alpha = int(255 * min(1.0, self.life / self.max_life * 1.8))
        font = assets.font(self.size, bold=True)
        draw_text(surf, self.text, font, self.color,
                  (int(self.x - cam[0]), int(self.y - cam[1])), "center",
                  outline=2, alpha=alpha)


def burst(game, x, y, color, count=8, speed=120, gravity=600, life=0.6, size=3, glow=False):
    for _ in range(count):
        ang = random.uniform(0, math.tau)
        sp = random.uniform(speed * 0.3, speed)
        game.particles.append(Particle(
            x, y, math.cos(ang) * sp, math.sin(ang) * sp,
            color, random.uniform(size * 0.6, size * 1.3),
            random.uniform(life * 0.6, life * 1.2), gravity, glow,
        ))


# ===================================================================== снаряды
class GelShot:
    def __init__(self, x, y, vx, vy):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = 5.0
        self.alive = True
        self.damage = 12
        self.anim = 0.0

    @property
    def rect(self):
        return pygame.Rect(int(self.x) - 7, int(self.y) - 7, 14, 14)

    def update(self, dt, game):
        self.life -= dt
        self.anim += dt
        self.vy += 700 * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.life <= 0:
            self.alive = False
            return
        tx, ty = int(self.x // TILE), int(self.y // TILE)
        if game.world.is_solid(tx, ty):
            burst(game, self.x, self.y, (96, 208, 128), 8, speed=100, gravity=500, life=0.5)
            self.alive = False
            return
        if self.rect.colliderect(game.player.rect):
            game.player.take_damage(self.damage, self.x, game)
            burst(game, self.x, self.y, (96, 208, 128), 10, speed=130, gravity=500, life=0.5)
            self.alive = False

    def draw(self, surf, cam, assets):
        sx, sy = int(self.x - cam[0]), int(self.y - cam[1])
        pygame.draw.circle(surf, (54, 150, 92), (sx, sy + 2), 8)
        pygame.draw.circle(surf, (101, 220, 137), (sx, sy), 7)
        pygame.draw.circle(surf, (188, 255, 207), (sx - 2, sy - 2), 2)


class VoidBolt:
    def __init__(self, x, y, vx, vy, damage=15):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = 4.8
        self.alive = True
        self.damage = damage
        self.anim = random.random() * 6

    @property
    def rect(self):
        return pygame.Rect(int(self.x) - 9, int(self.y) - 9, 18, 18)

    def update(self, dt, game):
        self.life -= dt
        self.anim += dt
        if self.life <= 0:
            self.alive = False
            return
        # лёгкое наведение на игрока в первой половине полёта
        if self.life > 2.0 and game.player:
            dx = game.player.cx - self.x
            dy = game.player.cy - self.y
            d = max(1, math.hypot(dx, dy))
            self.vx += dx / d * 60 * dt
            self.vy += dy / d * 55 * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        tx, ty = int(self.x // TILE), int(self.y // TILE)
        if game.world.is_solid(tx, ty):
            burst(game, self.x, self.y, (157, 94, 214), 9, speed=100, gravity=300, life=0.5)
            self.alive = False
            return
        if game.player and self.rect.colliderect(game.player.rect):
            game.player.take_damage(self.damage, self.x, game)
            burst(game, self.x, self.y, (179, 113, 232), 12, speed=150, gravity=300, life=0.6)
            self.alive = False

    def draw(self, surf, cam, assets):
        sx, sy = int(self.x - cam[0]), int(self.y - cam[1])
        glow = assets.glow(38, (157, 79, 225))
        surf.blit(glow, (sx - glow.get_width() // 2, sy - glow.get_height() // 2),
                  special_flags=pygame.BLEND_RGB_ADD)
        pulse = 6 + int(math.sin(self.anim * 12) * 2)
        pygame.draw.circle(surf, (48, 28, 67), (sx, sy), pulse + 3)
        pygame.draw.circle(surf, (151, 85, 213), (sx, sy), pulse + 1)
        pygame.draw.circle(surf, (225, 185, 251), (sx - 2, sy - 2), max(2, pulse - 3))


class SeedShot:
    """Прыгающее семя Лесного колосса."""

    def __init__(self, x, y, vx, vy, damage=13):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = 5.0
        self.alive = True
        self.damage = damage
        self.anim = random.random() * 6
        self.bounces = 0
        self.radius = 7

    @property
    def rect(self):
        return pygame.Rect(int(self.x) - self.radius, int(self.y) - self.radius,
                           self.radius * 2, self.radius * 2)

    def update(self, dt, game):
        self.life -= dt
        self.anim += dt
        self.vy += 950 * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.life <= 0:
            self.alive = False
            return
        tx, ty = int(self.x // TILE), int(self.y // TILE)
        if game.world.is_solid(tx, ty):
            # Семя отскакивает от стен и пола, постепенно теряя силу.
            if game.world.is_solid(tx, int((self.y - self.vy * dt) // TILE)):
                self.vx = -self.vx * 0.62
                self.x += self.vx * dt * 2
            else:
                self.vy = -abs(self.vy) * 0.58
                self.y += self.vy * dt * 2
                self.bounces += 1
                game.burst(self.x, self.y, (124, 177, 79), 4, speed=70,
                           gravity=300, life=0.35, size=2)
            if self.bounces > 2 and abs(self.vy) < 90 and abs(self.vx) < 90:
                self.alive = False
            return
        if game.player and self.rect.colliderect(game.player.rect):
            game.player.take_damage(self.damage, self.x, game)
            burst(game, self.x, self.y, (139, 196, 87), 10, speed=120,
                  gravity=400, life=0.5)
            self.alive = False
            return
        if random.random() < dt * 16:
            game.burst(self.x, self.y, (167, 214, 105), 1, speed=14, gravity=160,
                       life=0.35, size=2)

    def draw(self, surf, cam, assets):
        sx, sy = int(self.x - cam[0]), int(self.y - cam[1])
        glow = assets.glow(22, (126, 196, 82))
        surf.blit(glow, (sx - glow.get_width() // 2, sy - glow.get_height() // 2),
                  special_flags=pygame.BLEND_RGB_ADD)
        ang = self.anim * 10
        pts = []
        for i in range(3):
            a = ang + i * math.tau / 3
            pts.append((sx + math.cos(a) * 7, sy + math.sin(a) * 5))
        pygame.draw.polygon(surf, (52, 83, 38), [(px, py + 1) for px, py in pts])
        pygame.draw.polygon(surf, (126, 190, 76), pts)
        pygame.draw.circle(surf, (216, 244, 170), (sx - 1, sy - 1), 2)


class IceShard:
    """Осколок льда Ледяной королевы."""

    def __init__(self, x, y, vx, vy, damage=14):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = 4.5
        self.alive = True
        self.damage = damage
        self.anim = random.random() * 6
        self.angle = math.atan2(vy, vx)

    @property
    def rect(self):
        return pygame.Rect(int(self.x) - 8, int(self.y) - 8, 16, 16)

    def update(self, dt, game):
        self.life -= dt
        self.anim += dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.life <= 0:
            self.alive = False
            return
        tx, ty = int(self.x // TILE), int(self.y // TILE)
        if game.world.is_solid(tx, ty):
            burst(game, self.x, self.y, (176, 231, 255), 10, speed=120,
                  gravity=250, life=0.55, size=3, glow=True)
            self.alive = False
            return
        if game.player and self.rect.colliderect(game.player.rect):
            game.player.take_damage(self.damage, self.x, game)
            burst(game, self.x, self.y, (196, 240, 255), 12, speed=150,
                  gravity=200, life=0.6, size=3, glow=True)
            self.alive = False
            return
        if random.random() < dt * 26:
            game.burst(self.x, self.y, (160, 220, 247), 1, speed=18, gravity=-30,
                       life=0.45, size=2, glow=True)

    def draw(self, surf, cam, assets):
        sx, sy = int(self.x - cam[0]), int(self.y - cam[1])
        glow = assets.glow(30, (122, 199, 240))
        surf.blit(glow, (sx - glow.get_width() // 2, sy - glow.get_height() // 2),
                  special_flags=pygame.BLEND_RGB_ADD)
        ang = self.angle + math.pi / 2
        cos_a, sin_a = math.cos(ang), math.sin(ang)
        tip = (sx + cos_a * 13, sy + sin_a * 13)
        left = (sx - sin_a * 5, sy + cos_a * 5)
        right = (sx + sin_a * 5, sy - cos_a * 5)
        tail = (sx - cos_a * 7, sy - sin_a * 7)
        pygame.draw.polygon(surf, (57, 108, 146), [tip, left, tail, right])
        pygame.draw.polygon(surf, (174, 226, 250), [tip, (sx - sin_a * 2, sy + cos_a * 2), tail])
        pygame.draw.line(surf, (240, 253, 255), (sx - 2, sy), (sx + cos_a * 8, sy + sin_a * 8), 1)


# ===================================================================== враги
class Enemy(Entity):
    def __init__(self, x, y, w, h, hp, damage, name="Враг", color=(100, 200, 100)):
        super().__init__(x, y, w, h)
        self.max_hp = hp
        self.hp = hp
        self.damage = damage
        self.name = name
        self.color = color
        self.hurt_time = 0.0
        self.anim = random.random() * 10
        self.facing = -1
        self.contact_cd = 0.0
        self.knock_resist = 1.0

    def update(self, dt, game):
        self.anim += dt
        self.hurt_time = max(0.0, self.hurt_time - dt)
        self.contact_cd = max(0.0, self.contact_cd - dt)
        if not game.boss == self and abs(self.cx - game.player.cx) > 1600:
            self.alive = False
        if self.rect.colliderect(game.player.rect) and game.player.invuln <= 0:
            game.player.take_damage(self.damage, self.cx, game)

    def take_damage(self, amount: int, direction: int, game, crit=False):
        if not self.alive:
            return
        dmg = max(1, int(amount * random.uniform(0.9, 1.1)))
        if crit:
            dmg = int(dmg * 1.6)
        self.hp -= dmg
        self.hurt_time = 0.16
        self.vx += direction * 230 / self.knock_resist
        if self.on_ground:
            self.vy = -170 / self.knock_resist
        game.audio.sfx("hit")
        game.burst(self.cx, self.cy, self.color, 8, speed=130, gravity=500, life=0.5)
        game.float_text(self.cx, self.y - 4, str(dmg), (255, 238, 178), size=19)
        if self.hp <= 0:
            self.die(game)

    def die(self, game):
        self.alive = False
        self.on_death(game)

    def on_death(self, game):
        game.player.stats["kills"] += 1
        game.register_kill(self)
        burst(game, self.cx, self.cy, self.color, 22, speed=200, gravity=600, life=0.9, size=4)
        game.audio.sfx("break", 0.6)

    def draw_hp(self, surf, cam, assets):
        if self.hurt_time <= 0 and self.hp >= self.max_hp:
            return
        sx = int(self.cx - cam[0])
        sy = int(self.y - cam[1]) - 10
        w = max(36, self.w)
        pygame.draw.rect(surf, (36, 27, 28), (sx - w // 2, sy, w, 5), border_radius=2)
        ratio = clamp(self.hp / self.max_hp, 0, 1)
        col = (102, 208, 107) if ratio > 0.5 else (230, 174, 72) if ratio > 0.25 else (224, 84, 84)
        pygame.draw.rect(surf, col, (sx - w // 2 + 1, sy + 1, int((w - 2) * ratio), 3), border_radius=1)


class Slime(Enemy):
    def __init__(self, x, y, kind="green"):
        if kind == "blue":
            super().__init__(x, y, 38, 30, 38, 9, "Лазурный слизень", (87, 154, 225))
        elif kind == "sand":
            super().__init__(x, y, 38, 29, 34, 9, "Песчаный слизень", (214, 181, 110))
        elif kind == "frost":
            super().__init__(x, y, 38, 30, 36, 10, "Морозный слизень", (167, 218, 235))
        elif kind == "corrupt":
            super().__init__(x, y, 38, 30, 42, 11, "Гнилой слизень", (137, 94, 157))
        elif kind == "king_spawn":
            super().__init__(x, y, 32, 26, 24, 7, "Слизень", (105, 205, 125))
        else:
            super().__init__(x, y, 38, 30, 24, 8, "Слизень", (99, 196, 107))
        self.kind = kind
        self.hop_timer = random.uniform(0.4, 1.4)
        self.squash = 0.0
        self.drop_table = [("gel", 1, 2, 1.0)]
        if kind == "sand":
            self.drop_table.append(("sand", 1, 2, 0.45))
        elif kind == "frost":
            self.drop_table.append(("snow", 1, 2, 0.45))
        elif kind == "corrupt":
            self.drop_table = [("gel", 1, 3, 1.0), ("corrupt_stone", 1, 2, 0.25)]

    def update(self, dt, game):
        self.anim += dt
        self.hurt_time = max(0.0, self.hurt_time - dt)
        p = game.player
        self.facing = 1 if p.cx > self.cx else -1
        if self.on_ground:
            self.hop_timer -= dt
            if self.hop_timer <= 0:
                self.hop_timer = random.uniform(1.1, 2.0)
                self.vx = self.facing * random.uniform(150, 230)
                self.vy = -random.uniform(380, 520)
                self.squash = 1.0
        else:
            self.vx *= (1 - min(1.0, dt * 0.6))
        self.vy = min(self.vy + 1900 * dt, 1000)
        self.squash = max(0.0, self.squash - dt * 2.6)
        game.world.move_entity(self, dt)
        if self.rect.colliderect(p.rect) and p.invuln <= 0:
            p.take_damage(self.damage, self.cx, game)
        if abs(self.cx - p.cx) > 1600:
            self.alive = False

    def on_death(self, game):
        super().on_death(game)
        for item, lo, hi, chance in self.drop_table:
            if random.random() <= chance:
                game.spawn_drop(item, random.randint(lo, hi), self.cx, self.cy)

    def draw(self, surf, cam, assets, game):
        sx = int(self.cx - cam[0])
        sy = int(self.bottom - cam[1])
        squash = 1.0 + self.squash * 0.25
        wide = self.w * (1.0 + self.squash * 0.18)
        high = self.h * squash
        x = int(sx - wide / 2)
        y = int(sy - high)
        w = int(wide)
        h = int(high)
        color = (238, 247, 255) if self.hurt_time > 0 else self.color
        dark = tuple(max(0, c - 52) for c in color)
        deeper = tuple(max(0, c - 88) for c in color)
        light = tuple(min(255, c + 63) for c in color)
        # Тень и студенистое тело с внутренним свечением.
        shadow = pygame.Surface((w + 8, 12), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 80), shadow.get_rect())
        surf.blit(shadow, (x - 4, sy - 7))
        pygame.draw.ellipse(surf, deeper, (x, y + 3, w, h))
        pygame.draw.ellipse(surf, dark, (x + 1, y + 2, w - 2, h - 3))
        pygame.draw.ellipse(surf, color, (x + 3, y + 4, w - 6, h - 8))
        # Мягкий нижний обод и верхний блик.
        pygame.draw.ellipse(surf, tuple(min(255, c + 28) for c in color),
                            (x + 5, y + 5, w - 10, max(3, int(h * 0.42))))
        pygame.draw.ellipse(surf, light, (x + max(4, int(w * 0.14)), y + 5,
                                          max(4, int(w * 0.30)), max(3, int(h * 0.25))))
        pygame.draw.ellipse(surf, (255, 255, 255, 150),
                            (x + max(5, int(w * 0.18)), y + 6,
                             max(3, int(w * 0.16)), max(2, int(h * 0.10))))
        # Пузырьки внутри.
        pygame.draw.circle(surf, tuple(max(0, c - 30) for c in color),
                           (x + int(w * 0.72), y + int(h * 0.62)), max(2, int(w * 0.05)))
        pygame.draw.circle(surf, tuple(max(0, c - 22) for c in color),
                           (x + int(w * 0.28), y + int(h * 0.74)), max(1, int(w * 0.035)))
        # Особенности видов.
        if self.kind == "frost":
            for i in range(3):
                px = x + int(w * (0.22 + i * 0.27))
                pygame.draw.polygon(surf, (228, 250, 255),
                                    [(px, y + 2), (px + 4, y - 5), (px + 8, y + 2)])
        elif self.kind == "sand":
            for px, py in ((0.22, 0.55), (0.66, 0.42), (0.78, 0.68), (0.40, 0.78)):
                pygame.draw.circle(surf, (177, 143, 82),
                                   (x + int(w * px), y + int(h * py)), 1)
        elif self.kind == "corrupt":
            for px, py, r in ((0.24, 0.60, 3), (0.67, 0.36, 2), (0.76, 0.70, 3)):
                pygame.draw.circle(surf, (78, 49, 96),
                                   (x + int(w * px), y + int(h * py)), r)
        elif self.kind == "blue":
            for i in range(2):
                pygame.draw.circle(surf, (208, 236, 255),
                                   (x + int(w * (0.36 + i * 0.3)), y + int(h * 0.30)), 1)
        # Глаза с зрачками, следящими за игроком.
        eye_y = int(sy - h * 0.60)
        ex = int(w * 0.19)
        look = 1 if getattr(game.player, "cx", sx) > sx else -1
        for side in (-1, 1):
            gx = int(sx + side * ex)
            pygame.draw.circle(surf, (247, 252, 255), (gx, eye_y), 4)
            pygame.draw.circle(surf, (30, 38, 42), (gx + look, eye_y + 1), 2)
            pygame.draw.circle(surf, (255, 255, 255), (gx - 1, eye_y - 1), 1)
        mouth = pygame.Rect(int(sx - w * 0.16), eye_y + 5, int(w * 0.32), int(h * 0.22))
        pygame.draw.arc(surf, deeper, mouth, 3.35, 6.05, 2)
        pygame.draw.circle(surf, (255, 255, 255), (int(sx - w * 0.12), sy - 2), 1)
        self.draw_hp(surf, cam, assets)


class Zombie(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, 26, 54, 42, 12, "Зомби", (116, 156, 96))
        self.drop_table = [("gel", 1, 2, 0.55), ("iron_ore", 1, 1, 0.18)]
        self.jump_cd = 0.0

    def update(self, dt, game):
        self.anim += dt
        self.hurt_time = max(0.0, self.hurt_time - dt)
        p = game.player
        if abs(self.cx - p.cx) > 1500:
            self.alive = False
            return
        self.facing = 1 if p.cx > self.cx else -1
        dist = abs(p.cx - self.cx)
        if dist < 700:
            self.vx = approach(self.vx, self.facing * 82, 320 * dt)
        else:
            self.vx = approach(self.vx, 0, 300 * dt)
        self.jump_cd = max(0.0, self.jump_cd - dt)
        if self.on_ground and self.jump_cd <= 0 and abs(self.vx) < 20:
            self.vy = -560
            self.jump_cd = 0.8
        self.vy = min(self.vy + 1900 * dt, 1000)
        game.world.move_entity(self, dt)
        if self.rect.colliderect(p.rect) and p.invuln <= 0:
            p.take_damage(self.damage, self.cx, game)

    def on_death(self, game):
        super().on_death(game)
        for item, lo, hi, chance in self.drop_table:
            if random.random() <= chance:
                game.spawn_drop(item, random.randint(lo, hi), self.cx, self.cy)

    def draw(self, surf, cam, assets, game):
        sx = int(self.cx - cam[0])
        sy = int(self.bottom - cam[1])
        hurt = self.hurt_time > 0
        skin = (238, 247, 255) if hurt else self.color
        skin_dark = tuple(max(0, c - 42) for c in skin)
        skin_light = tuple(min(255, c + 33) for c in skin)
        outline = (28, 34, 27)
        shirt = (92, 72, 85)
        shirt_dark = (62, 48, 60)
        pants = (48, 55, 47)
        # тень
        sh = pygame.Surface((36, 11), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 78), sh.get_rect())
        surf.blit(sh, (sx - 18, sy - 7))
        swing = math.sin(self.anim * 5.4) * 4
        sway = math.sin(self.anim * 2.7) * 1.5
        # ноги, одна подвернута
        pygame.draw.rect(surf, outline, (sx - 11, sy - 23, 10, 24), border_radius=3)
        pygame.draw.rect(surf, pants, (sx - 10, sy - 22, 8, 21), border_radius=3)
        pygame.draw.rect(surf, outline, (sx + 2, sy - 22 + int(swing), 9, 23), border_radius=3)
        pygame.draw.rect(surf, pants, (sx + 3, sy - 21 + int(swing), 7, 20), border_radius=3)
        pygame.draw.rect(surf, (39, 33, 30), (sx - 13, sy - 5, 13, 5), border_radius=2)
        pygame.draw.rect(surf, (39, 33, 30), (sx + 1, sy - 5, 12, 5), border_radius=2)
        # рваная рубаха и торс
        pygame.draw.polygon(surf, outline, [(sx - 13 + int(sway), sy - 46), (sx + 12, sy - 47),
                                            (sx + 14, sy - 25), (sx - 12, sy - 24)])
        pygame.draw.polygon(surf, shirt, [(sx - 12 + int(sway), sy - 45), (sx + 11, sy - 46),
                                          (sx + 12, sy - 27), (sx - 10, sy - 26)])
        pygame.draw.polygon(surf, shirt_dark, [(sx + 2, sy - 45), (sx + 11, sy - 46),
                                                (sx + 12, sy - 27), (sx + 1, sy - 28)])
        # прорехи и ребра
        pygame.draw.polygon(surf, skin_dark, [(sx - 9, sy - 35), (sx - 3, sy - 37),
                                               (sx - 1, sy - 30), (sx - 8, sy - 29)])
        pygame.draw.line(surf, (45, 38, 34), (sx - 6, sy - 31), (sx - 6, sy - 26), 1)
        pygame.draw.line(surf, (45, 38, 34), (sx - 3, sy - 32), (sx - 3, sy - 26), 1)
        # левая рука безвольно висит
        arm_sw = int(math.sin(self.anim * 5.4) * 4)
        pygame.draw.line(surf, outline, (sx - 12, sy - 43), (sx - 18, sy - 27 + arm_sw), 8)
        pygame.draw.line(surf, skin_dark, (sx - 12, sy - 43), (sx - 18, sy - 27 + arm_sw), 5)
        pygame.draw.circle(surf, skin_dark, (sx - 18, sy - 24 + arm_sw), 4)
        # правая рука тянется к игроку
        reach = 4 * self.facing
        pygame.draw.line(surf, outline, (sx + 10, sy - 42), (sx + 22 + reach, sy - 39), 8)
        pygame.draw.line(surf, skin, (sx + 10, sy - 42), (sx + 22 + reach, sy - 39), 5)
        pygame.draw.circle(surf, skin, (sx + 24 + reach, sy - 39), 4)
        for i in range(2):
            pygame.draw.line(surf, skin_dark, (sx + 26 + reach, sy - 41 + i * 4),
                             (sx + 30 + reach, sy - 42 + i * 5), 1)
        # голова с провалившимися глазами и тяжёлой челюстью
        pygame.draw.rect(surf, outline, (sx - 10, sy - 63, 21, 20), border_radius=5)
        pygame.draw.rect(surf, skin_dark, (sx - 9, sy - 62, 19, 18), border_radius=4)
        pygame.draw.rect(surf, skin, (sx - 8, sy - 61, 17, 15), border_radius=4)
        pygame.draw.rect(surf, (48, 55, 44), (sx - 8, sy - 61, 17, 4), border_radius=2)
        # волосы клочьями
        pygame.draw.line(surf, (53, 59, 45), (sx - 7, sy - 61), (sx - 10, sy - 66), 2)
        pygame.draw.line(surf, (53, 59, 45), (sx - 2, sy - 62), (sx - 1, sy - 67), 2)
        pygame.draw.line(surf, (53, 59, 45), (sx + 4, sy - 61), (sx + 7, sy - 65), 2)
        pygame.draw.circle(surf, (36, 29, 31), (sx - 4, sy - 54), 3)
        pygame.draw.circle(surf, (36, 29, 31), (sx + 4, sy - 54), 3)
        pygame.draw.circle(surf, (218, 61, 58), (sx - 4, sy - 54), 1)
        pygame.draw.circle(surf, (218, 61, 58), (sx + 4, sy - 54), 1)
        pygame.draw.line(surf, (57, 70, 51), (sx - 5, sy - 49), (sx + 6, sy - 49), 1)
        pygame.draw.line(surf, (229, 226, 198), (sx + 1, sy - 48), (sx + 3, sy - 46), 1)
        pygame.draw.line(surf, (57, 70, 51), (sx - 6, sy - 44), (sx + 5, sy - 45), 1)
        self.draw_hp(surf, cam, assets)


class Bat(Enemy):
    def __init__(self, x, y, kind="cave"):
        if kind == "frost":
            super().__init__(x, y, 30, 22, 28, 8, "Морозный нетопырь", (138, 188, 217))
        else:
            super().__init__(x, y, 30, 22, 20, 7, "Пещерный нетопырь", (135, 110, 156))
        self.kind = kind
        self.drop_table = [("gel", 1, 1, 0.7)]
        if kind == "frost":
            self.drop_table.append(("ice", 1, 1, 0.25))
        self.wander = random.uniform(0, math.tau)

    def update(self, dt, game):
        self.anim += dt
        self.hurt_time = max(0.0, self.hurt_time - dt)
        p = game.player
        dx, dy = p.cx - self.cx, p.cy - self.cy
        dist = math.hypot(dx, dy)
        if dist > 1600:
            self.alive = False
            return
        if dist < 450:
            self.vx = approach(self.vx, dx / max(1, dist) * 150, 380 * dt)
            self.vy = approach(self.vy, dy / max(1, dist) * 120 + math.sin(self.anim * 5) * 35, 380 * dt)
            self.facing = 1 if dx > 0 else -1
        else:
            self.wander += random.uniform(-2, 2) * dt
            self.vx = approach(self.vx, math.cos(self.wander) * 80, 200 * dt)
            self.vy = approach(self.vy, math.sin(self.wander * 1.7) * 60, 200 * dt)
        game.world.move_entity(self, dt)
        if self.rect.colliderect(p.rect) and p.invuln <= 0:
            p.take_damage(self.damage, self.cx, game)

    def on_death(self, game):
        super().on_death(game)
        if random.random() < 0.7:
            game.spawn_drop("gel", 1, self.cx, self.cy)

    def draw(self, surf, cam, assets, game):
        sx, sy = int(self.cx - cam[0]), int(self.cy - cam[1])
        flap = math.sin(self.anim * 19)
        hurt = self.hurt_time > 0
        color = (245, 238, 255) if hurt else self.color
        dark = tuple(max(0, c - 54) for c in color)
        light = tuple(min(255, c + 45) for c in color)
        wing_y = int(flap * 8)
        membrane = (55, 42, 65) if self.kind != "frost" else (78, 109, 135)
        bone = (34, 27, 39) if self.kind != "frost" else (47, 67, 88)
        # Перепончатые крылья с «пальцами».
        for side in (-1, 1):
            tip = (sx + side * 27, sy - 5 - wing_y)
            mid = (sx + side * 17, sy + 8 + wing_y // 2)
            root = (sx + side * 4, sy + 2)
            pygame.draw.polygon(surf, bone, [(sx + side * 3, sy - 2), tip, mid, root])
            pygame.draw.polygon(surf, membrane,
                                [(sx + side * 4, sy - 1), (sx + side * 24, sy - 4 - wing_y),
                                 (sx + side * 16, sy + 6 + wing_y // 2), (sx + side * 5, sy + 1)])
            pygame.draw.line(surf, dark, (sx + side * 4, sy), (sx + side * 24, sy - 4 - wing_y), 2)
            pygame.draw.line(surf, dark, (sx + side * 4, sy + 1), (sx + side * 16, sy + 6 + wing_y // 2), 1)
            pygame.draw.line(surf, dark, (sx + side * 12, sy - 1), (sx + side * 15, sy + 6 + wing_y // 2), 1)
        # Пушистое тело.
        pygame.draw.ellipse(surf, (31, 24, 35), (sx - 11, sy - 9, 22, 18))
        pygame.draw.ellipse(surf, color, (sx - 9, sy - 8, 18, 15))
        pygame.draw.ellipse(surf, light, (sx - 5, sy - 6, 8, 5))
        # Уши с розовой внутренней частью.
        for side in (-1, 1):
            pygame.draw.polygon(surf, (31, 24, 35), [(sx + side * 8, sy - 7),
                                                      (sx + side * 11, sy - 18),
                                                      (sx + side * 2, sy - 9)])
            pygame.draw.polygon(surf, tuple(min(255, c + 18) for c in color),
                                [(sx + side * 7, sy - 7), (sx + side * 9, sy - 14),
                                 (sx + side * 3, sy - 8)])
        # Глаза-бусины и клыки.
        eye_color = (124, 226, 255) if self.kind == "frost" else (245, 93, 93)
        for side in (-1, 1):
            pygame.draw.circle(surf, (28, 22, 31), (sx + side * 4, sy - 3), 3)
            pygame.draw.circle(surf, eye_color, (sx + side * 4, sy - 3), 2)
            pygame.draw.circle(surf, (255, 255, 255), (sx + side * 4 - 1, sy - 4), 1)
        pygame.draw.polygon(surf, (247, 243, 225), [(sx - 3, sy + 4), (sx - 1, sy + 7), (sx, sy + 3)])
        pygame.draw.polygon(surf, (247, 243, 225), [(sx + 3, sy + 4), (sx + 1, sy + 7), (sx, sy + 3)])
        pygame.draw.line(surf, (42, 30, 45), (sx - 6, sy + 9), (sx + 6, sy + 9), 1)
        self.draw_hp(surf, cam, assets)


class CorruptEye(Enemy):
    """Летающий глаз Багряных пустошей."""

    def __init__(self, x, y):
        super().__init__(x, y, 32, 30, 32, 11, "Порченый глаз", (151, 96, 165))
        self.drop_table = [("gel", 1, 2, 0.55), ("crystal", 1, 1, 0.04)]
        self.wander = random.uniform(0, math.tau)

    def update(self, dt, game):
        self.anim += dt
        self.hurt_time = max(0.0, self.hurt_time - dt)
        p = game.player
        dx, dy = p.cx - self.cx, p.cy - self.cy
        dist = math.hypot(dx, dy)
        if dist > 1500:
            self.alive = False
            return
        if dist < 520:
            self.vx = approach(self.vx, dx / max(1, dist) * 125, 300 * dt)
            self.vy = approach(self.vy, dy / max(1, dist) * 105, 250 * dt)
            self.facing = 1 if dx > 0 else -1
        else:
            self.wander += dt
            self.vx = approach(self.vx, math.cos(self.wander) * 55, 100 * dt)
            self.vy = approach(self.vy, math.sin(self.wander * 1.2) * 45, 100 * dt)
        game.world.move_entity(self, dt)
        if self.rect.colliderect(p.rect) and p.invuln <= 0:
            p.take_damage(self.damage, self.cx, game)
        if random.random() < dt * 4:
            game.burst(self.cx, self.cy, (150, 78, 190), 1, speed=25, gravity=-40,
                       life=0.5, size=2, glow=True)

    def draw(self, surf, cam, assets, game):
        sx, sy = int(self.cx - cam[0]), int(self.cy - cam[1])
        hurt = self.hurt_time > 0
        color = (247, 238, 255) if hurt else self.color
        dark = tuple(max(0, c - 52) for c in color)
        glow = assets.glow(44, (154, 82, 201))
        surf.blit(glow, (sx - glow.get_width() // 2, sy - glow.get_height() // 2),
                  special_flags=pygame.BLEND_RGB_ADD)
        # Извивающиеся щупальца с утолщениями.
        for i in range(7):
            ang = self.anim * 1.8 + i * math.tau / 7
            seg = 10 + (i % 3) * 3
            ex = sx + int(math.cos(ang) * 23)
            ey = sy + int(math.sin(ang * 1.4) * 18)
            mx = sx + int(math.cos(ang + 0.5) * 13)
            my = sy + int(math.sin(ang * 1.1 + 0.4) * 11)
            pygame.draw.line(surf, (55, 33, 69), (sx, sy), (mx, my), 4)
            pygame.draw.line(surf, (92, 53, 112), (sx, sy), (mx, my), 2)
            pygame.draw.line(surf, (55, 33, 69), (mx, my), (ex, ey), 3)
            pygame.draw.circle(surf, (133, 86, 158), (ex, ey), 2)
        # Веко и глазное яблоко.
        pygame.draw.ellipse(surf, (43, 27, 51), (sx - 19, sy - 16, 38, 33))
        pygame.draw.ellipse(surf, dark, (sx - 17, sy - 15, 34, 30))
        pygame.draw.ellipse(surf, color, (sx - 15, sy - 13, 30, 26))
        pygame.draw.ellipse(surf, (233, 226, 245), (sx - 12, sy - 10, 24, 21))
        # Радужка, вертикальный зрачок и блики.
        pygame.draw.circle(surf, (117, 47, 140), (sx + 3, sy + 1), 8)
        pygame.draw.circle(surf, (165, 82, 196), (sx + 3, sy + 1), 6)
        pygame.draw.ellipse(surf, (24, 16, 29), (sx + 1, sy - 4, 5, 11))
        pygame.draw.circle(surf, (255, 209, 240), (sx + 1, sy - 2), 1)
        pygame.draw.circle(surf, (255, 255, 255), (sx - 6, sy - 6), 2)
        # Налитые кровью прожилки.
        for dx, dy in ((-13, -3), (-11, 4), (-7, -9), (-4, 8)):
            pygame.draw.line(surf, (150, 91, 154), (sx + dx, sy + dy),
                             (sx + dx + 4, sy + dy + (2 if dy < 0 else -2)), 1)
        self.draw_hp(surf, cam, assets)


class CaveSpider(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, 40, 26, 30, 9, "Пещерный паук", (112, 87, 119))
        self.walk_phase = 0.0
        self.hop_cd = 0.0

    def update(self, dt, game):
        self.anim += dt
        self.hurt_time = max(0.0, self.hurt_time - dt)
        p = game.player
        if abs(self.cx - p.cx) > 1400:
            self.alive = False
            return
        self.facing = 1 if p.cx > self.cx else -1
        self.walk_phase += dt * 9
        if abs(p.cx - self.cx) < 650:
            self.vx = approach(self.vx, self.facing * 165, 680 * dt)
        else:
            self.vx = approach(self.vx, 0, 300 * dt)
        self.hop_cd = max(0.0, self.hop_cd - dt)
        if self.on_ground and self.hop_cd <= 0 and abs(p.cy - self.cy) > 45:
            self.vy = -480
            self.hop_cd = 1.2
        self.vy = min(self.vy + 1900 * dt, 1000)
        game.world.move_entity(self, dt)
        if self.rect.colliderect(p.rect) and p.invuln <= 0:
            p.take_damage(self.damage, self.cx, game)

    def on_death(self, game):
        super().on_death(game)
        game.spawn_drop("gel", random.randint(1, 2), self.cx, self.cy)

    def draw(self, surf, cam, assets, game):
        sx, sy = int(self.cx - cam[0]), int(self.cy - cam[1])
        hurt = self.hurt_time > 0
        color = (242, 232, 249) if hurt else self.color
        dark = tuple(max(0, c - 45) for c in color)
        leg_color = (58, 44, 65)
        leg_light = (97, 76, 110)
        # Восемь суставчатых лап.
        for side in (-1, 1):
            for i in range(4):
                phase = self.walk_phase + i * 1.35 + (0.0 if side > 0 else math.pi)
                lift = math.sin(phase) * 4
                root = (sx + side * 7, sy + 1 + i * 2)
                knee = (sx + side * (17 + i * 2), sy - 7 + i * 4 - lift)
                foot = (sx + side * (24 + i * 3), sy + 10 + i * 3 + lift)
                pygame.draw.line(surf, (31, 24, 35), root, knee, 4)
                pygame.draw.line(surf, leg_color, root, knee, 2)
                pygame.draw.line(surf, (31, 24, 35), knee, foot, 3)
                pygame.draw.line(surf, leg_light, knee, foot, 1)
                pygame.draw.circle(surf, (31, 24, 35), knee, 2)
        # Брюшко с узором.
        pygame.draw.ellipse(surf, (34, 26, 38), (sx - 19, sy - 6, 38, 26))
        pygame.draw.ellipse(surf, dark, (sx - 17, sy - 5, 34, 23))
        pygame.draw.ellipse(surf, color, (sx - 16, sy - 6, 32, 21))
        pygame.draw.ellipse(surf, tuple(min(255, c + 24) for c in color),
                            (sx - 12, sy - 4, 15, 10))
        # Тёмный рисунок-«песочные часы» на брюшке.
        pygame.draw.polygon(surf, (76, 49, 82), [(sx - 11, sy - 2), (sx - 3, sy + 3),
                                                  (sx - 8, sy + 9), (sx - 13, sy + 4)])
        pygame.draw.polygon(surf, (76, 49, 82), [(sx + 10, sy - 1), (sx + 3, sy + 3),
                                                  (sx + 8, sy + 9), (sx + 12, sy + 4)])
        pygame.draw.circle(surf, (164, 208, 126), (sx - 8, sy + 2), 1)
        pygame.draw.circle(surf, (164, 208, 126), (sx + 8, sy + 2), 1)
        # Головогрудь.
        pygame.draw.ellipse(surf, (34, 26, 38), (sx - 13, sy - 10, 26, 18))
        pygame.draw.ellipse(surf, color, (sx - 12, sy - 9, 24, 16))
        pygame.draw.ellipse(surf, tuple(min(255, c + 16) for c in color),
                            (sx - 9, sy - 7, 11, 7))
        # Восемь глаз: два крупных и шесть малых.
        for side in (-1, 1):
            pygame.draw.circle(surf, (18, 14, 20), (sx + side * 6, sy - 2), 4)
            pygame.draw.circle(surf, (218, 65, 78), (sx + side * 6, sy - 2), 3)
            pygame.draw.circle(surf, (255, 202, 202), (sx + side * 6 - 1, sy - 3), 1)
            pygame.draw.circle(surf, (18, 14, 20), (sx + side * 11, sy - 5), 2)
            pygame.draw.circle(surf, (228, 214, 235), (sx + side * 11, sy - 5), 1)
        for dx in (-3, 0, 3):
            pygame.draw.circle(surf, (18, 14, 20), (sx + dx, sy - 8), 1)
        # Хелицеры.
        pygame.draw.line(surf, (42, 31, 47), (sx - 3, sy + 5), (sx - 5, sy + 10), 2)
        pygame.draw.line(surf, (42, 31, 47), (sx + 3, sy + 5), (sx + 5, sy + 10), 2)
        self.draw_hp(surf, cam, assets)


class DesertScorpion(Enemy):
    """Быстрый пустынный хищник с ядовитым жалом."""

    def __init__(self, x, y):
        super().__init__(x, y, 52, 30, 62, 13, "Пустынный скорпион", (196, 156, 91))
        self.step_height = 14
        self.walk_phase = 0.0
        self.dash_cd = random.uniform(0.8, 1.8)
        self.dash_time = 0.0
        self.drop_table = [("gel", 1, 2, 0.7), ("sand", 1, 3, 0.55)]

    def update(self, dt, game):
        self.anim += dt
        self.hurt_time = max(0.0, self.hurt_time - dt)
        p = game.player
        if abs(self.cx - p.cx) > 1450:
            self.alive = False
            return
        self.facing = 1 if p.cx > self.cx else -1
        self.walk_phase += dt * 10
        self.dash_cd = max(0.0, self.dash_cd - dt)
        self.dash_time = max(0.0, self.dash_time - dt)
        if self.dash_time > 0:
            self.vx = approach(self.vx, self.facing * 315, 900 * dt)
        elif abs(p.cx - self.cx) < 520:
            self.vx = approach(self.vx, self.facing * 105, 460 * dt)
            if self.dash_cd <= 0 and self.on_ground and abs(p.cy - self.cy) < 90:
                self.dash_cd = random.uniform(2.0, 3.4)
                self.dash_time = 0.45
                self.vy = -170
                game.burst(self.cx, self.bottom, (205, 175, 112), 8,
                           speed=80, gravity=320, life=0.45, size=2)
        else:
            self.vx = approach(self.vx, 0, 380 * dt)
        if self.on_ground and self.dash_time <= 0:
            self.vy = min(self.vy, 0)
        self.vy = min(self.vy + 1900 * dt, 1000)
        game.world.move_entity(self, dt)
        if self.rect.colliderect(p.rect) and p.invuln <= 0:
            p.take_damage(self.damage, self.cx, game)
        if random.random() < dt * 3 and self.on_ground:
            game.burst(self.cx - self.facing * 12, self.bottom - 2, (196, 168, 108),
                       1, speed=20, gravity=80, life=0.4, size=2)

    def on_death(self, game):
        super().on_death(game)
        for item, lo, hi, chance in self.drop_table:
            if random.random() <= chance:
                game.spawn_drop(item, random.randint(lo, hi), self.cx, self.cy)

    def draw(self, surf, cam, assets, game):
        sx = int(self.cx - cam[0])
        sy = int(self.bottom - cam[1])
        hurt = self.hurt_time > 0
        shell = (244, 235, 219) if hurt else self.color
        shell_dark = tuple(max(0, c - 53) for c in shell)
        shell_light = tuple(min(255, c + 33) for c in shell)
        leg_col = (112, 79, 45)
        # Ноги.
        for side in (-1, 1):
            for i in range(4):
                phase = self.walk_phase + i * 1.4 + (0.0 if side > 0 else math.pi)
                lift = math.sin(phase) * 3
                root = (sx + side * 10, sy - 13 + i * 2)
                knee = (sx + side * (20 + i * 2), sy - 19 + i * 4 - lift)
                foot = (sx + side * (25 + i * 2), sy - 2 + lift)
                pygame.draw.line(surf, leg_col, root, knee, 3)
                pygame.draw.line(surf, shell_dark, knee, foot, 2)
        # Хвост из сегментов, поднятый над спиной.
        seg_x, seg_y = sx + self.facing * 12, sy - 22
        curve = math.sin(self.anim * 2.2) * 2
        tail_pts = []
        for i in range(5):
            seg_x += self.facing * (5 - i * 0.4)
            seg_y -= 5 + i * 0.8
            tail_pts.append((seg_x + curve * (i / 4), seg_y))
            pygame.draw.circle(surf, shell_dark, (int(seg_x), int(seg_y)), 5 - i // 2)
            pygame.draw.circle(surf, shell, (int(seg_x), int(seg_y)), 4 - i // 2)
        tip = tail_pts[-1] if tail_pts else (seg_x, seg_y)
        pygame.draw.polygon(surf, (76, 46, 34), [(tip[0] - 4, tip[1] - 3),
                                                  (tip[0] + self.facing * 12, tip[1] - 7),
                                                  (tip[0] + 3, tip[1] + 3)])
        pygame.draw.circle(surf, (226, 193, 77), (int(tip[0] + self.facing * 8), int(tip[1] - 5)), 2)
        # Тело и панцирь с сегментами.
        pygame.draw.ellipse(surf, (77, 55, 34), (sx - 23, sy - 25, 46, 24))
        pygame.draw.ellipse(surf, shell_dark, (sx - 22, sy - 25, 44, 22))
        pygame.draw.ellipse(surf, shell, (sx - 20, sy - 24, 40, 19))
        pygame.draw.ellipse(surf, shell_light, (sx - 14, sy - 22, 18, 8))
        for i in range(3):
            pygame.draw.arc(surf, shell_dark, (sx - 17 + i * 8, sy - 24, 18, 19), 3.5, 6.1, 1)
        pygame.draw.line(surf, shell_light, (sx - 16, sy - 16), (sx - 2, sy - 20), 1)
        # Голова и клешни.
        hx = sx + self.facing * 20
        pygame.draw.ellipse(surf, shell_dark, (hx - 9, sy - 21, 19, 14))
        pygame.draw.ellipse(surf, shell, (hx - 8, sy - 20, 17, 12))
        pygame.draw.circle(surf, (30, 24, 22), (hx + self.facing * 3, sy - 16), 2)
        pygame.draw.circle(surf, (255, 220, 142), (hx + self.facing * 3, sy - 16), 1)
        for side in (-1, 1):
            claw_x = hx + self.facing * 10
            claw_y = sy - 13 + side * 5
            pygame.draw.circle(surf, shell_dark, (claw_x, claw_y), 6)
            pygame.draw.circle(surf, shell, (claw_x + self.facing * 3, claw_y), 4)
            pygame.draw.line(surf, shell_dark, (claw_x + self.facing * 4, claw_y - 4),
                             (claw_x + self.facing * 9, claw_y - 6), 2)
            pygame.draw.line(surf, shell_dark, (claw_x + self.facing * 4, claw_y + 4),
                             (claw_x + self.facing * 9, claw_y + 6), 2)
        self.draw_hp(surf, cam, assets)


class FrostWolf(Enemy):
    """Стайный хищник Снежных пиков, прыгает на добычу."""

    def __init__(self, x, y):
        super().__init__(x, y, 56, 34, 58, 14, "Морозный волк", (166, 201, 220))
        self.step_height = 14
        self.walk_phase = 0.0
        self.jump_cd = random.uniform(0.6, 1.5)
        self.howl_cd = random.uniform(3.0, 6.0)
        self.drop_table = [("gel", 1, 2, 0.6), ("ice", 1, 2, 0.4)]

    def update(self, dt, game):
        self.anim += dt
        self.hurt_time = max(0.0, self.hurt_time - dt)
        p = game.player
        if abs(self.cx - p.cx) > 1500:
            self.alive = False
            return
        self.facing = 1 if p.cx > self.cx else -1
        self.walk_phase += dt * (9 + abs(self.vx) / 40)
        dist = abs(p.cx - self.cx)
        if dist < 720:
            self.vx = approach(self.vx, self.facing * 155, 520 * dt)
        else:
            self.vx = approach(self.vx, self.facing * 60, 300 * dt)
        self.jump_cd = max(0.0, self.jump_cd - dt)
        if (self.on_ground and self.jump_cd <= 0 and dist < 420
                and (abs(p.cy - self.cy) > 42 or random.random() < dt * 0.8)):
            self.vy = -520
            self.vx = self.facing * 230
            self.jump_cd = random.uniform(1.4, 2.4)
            game.audio.sfx("jump", 0.25)
        self.howl_cd = max(0.0, self.howl_cd - dt)
        if self.howl_cd <= 0 and dist < 500:
            self.howl_cd = random.uniform(5.0, 8.0)
            game.burst(self.cx + self.facing * 16, self.y - 2, (203, 238, 250),
                       7, speed=60, gravity=-40, life=0.8, size=2, glow=True)
        self.vy = min(self.vy + 1900 * dt, 1000)
        game.world.move_entity(self, dt)
        if self.rect.colliderect(p.rect) and p.invuln <= 0:
            p.take_damage(self.damage, self.cx, game)
        if random.random() < dt * 2.5 and self.on_ground:
            game.burst(self.cx, self.bottom - 2, (217, 240, 250), 1,
                       speed=16, gravity=-30, life=0.5, size=2)
        if random.random() < dt * 6:
            game.burst(self.cx + self.facing * 22, self.cy - 8, (208, 236, 248),
                       1, speed=18, gravity=-25, life=0.5, size=1, glow=True)

    def on_death(self, game):
        super().on_death(game)
        for item, lo, hi, chance in self.drop_table:
            if random.random() <= chance:
                game.spawn_drop(item, random.randint(lo, hi), self.cx, self.cy)

    def draw(self, surf, cam, assets, game):
        sx = int(self.cx - cam[0])
        sy = int(self.bottom - cam[1])
        hurt = self.hurt_time > 0
        fur = (247, 250, 255) if hurt else self.color
        fur_dark = tuple(max(0, c - 60) for c in fur)
        fur_light = tuple(min(255, c + 31) for c in fur)
        outline = (47, 68, 82)
        step = math.sin(self.walk_phase) * 5
        # Тень.
        sh = pygame.Surface((58, 12), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 75), sh.get_rect())
        surf.blit(sh, (sx - 29, sy - 7))
        # Хвост.
        tail_wag = math.sin(self.anim * 3.5) * 6
        pygame.draw.polygon(surf, outline, [(sx - self.facing * 22, sy - 25),
                                             (sx - self.facing * 39, sy - 31 + tail_wag),
                                             (sx - self.facing * 33, sy - 19 + tail_wag),
                                             (sx - self.facing * 20, sy - 18)])
        pygame.draw.polygon(surf, fur, [(sx - self.facing * 23, sy - 24),
                                         (sx - self.facing * 36, sy - 29 + tail_wag),
                                         (sx - self.facing * 31, sy - 20 + tail_wag),
                                         (sx - self.facing * 21, sy - 19)])
        # Задние и передние лапы.
        for i, (leg_x, lift) in enumerate(((-15, step), (14, -step))):
            lx = sx + (leg_x if self.facing > 0 else -leg_x)
            pygame.draw.line(surf, outline, (lx, sy - 20), (lx + int(lift), sy - 2), 8)
            pygame.draw.line(surf, fur_dark, (lx, sy - 20), (lx + int(lift), sy - 3), 5)
            pygame.draw.rect(surf, (78, 103, 120), (lx + int(lift) - 4, sy - 4, 9, 4), border_radius=2)
        # Тело.
        pygame.draw.ellipse(surf, outline, (sx - 24, sy - 30, 49, 23))
        pygame.draw.ellipse(surf, fur_dark, (sx - 23, sy - 29, 47, 21))
        pygame.draw.ellipse(surf, fur, (sx - 21, sy - 28, 43, 18))
        pygame.draw.ellipse(surf, fur_light, (sx - 16, sy - 27, 19, 8))
        # Грива и голова.
        hx = sx + self.facing * 22
        pygame.draw.circle(surf, outline, (hx, sy - 27), 13)
        pygame.draw.circle(surf, fur_dark, (hx, sy - 27), 11)
        pygame.draw.circle(surf, fur, (hx + self.facing * 2, sy - 28), 9)
        pygame.draw.polygon(surf, outline, [(hx - 7, sy - 34), (hx - 4, sy - 47), (hx + 2, sy - 36)])
        pygame.draw.polygon(surf, outline, [(hx + 7, sy - 34), (hx + 10, sy - 46), (hx + 13, sy - 34)])
        pygame.draw.polygon(surf, fur_dark, [(hx - 5, sy - 35), (hx - 3, sy - 44), (hx + 1, sy - 36)])
        pygame.draw.polygon(surf, fur_dark, [(hx + 7, sy - 35), (hx + 9, sy - 43), (hx + 11, sy - 35)])
        # Морда, глаза и клыки.
        muzzle = hx + self.facing * 8
        pygame.draw.ellipse(surf, fur_light, (muzzle - 5, sy - 29, 12, 9))
        pygame.draw.circle(surf, (34, 48, 56), (muzzle + self.facing * 3, sy - 27), 2)
        pygame.draw.circle(surf, (96, 222, 255), (muzzle + self.facing * 3, sy - 27), 1)
        pygame.draw.circle(surf, (96, 222, 255), (hx + self.facing * 2, sy - 32), 2)
        pygame.draw.polygon(surf, (233, 250, 255), [(muzzle + self.facing * 2, sy - 22),
                                                     (muzzle + self.facing * 4, sy - 18),
                                                     (muzzle + self.facing * 5, sy - 23)])
        pygame.draw.circle(surf, (47, 68, 82), (hx - self.facing * 5, sy - 20), 2)
        self.draw_hp(surf, cam, assets)


# ===================================================================== босс
class SlimeKing(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, 118, 92, 700, 24, "Король слизи", (105, 201, 122))
        self.knock_resist = 8.0
        self.hop_timer = 1.6
        self.shoot_timer = 3.2
        self.summoned = 0
        self.squash = 0.0
        self.is_boss = True
        self.intro = 1.2
        self.phase = 1
        self.music_key = "boss"
        self.light_color = (120, 220, 140)

    def update(self, dt, game):
        self.anim += dt
        self.hurt_time = max(0.0, self.hurt_time - dt)
        self.intro = max(0.0, self.intro - dt)
        if self.intro > 0:
            return
        p = game.player
        if not p:
            return
        self.facing = 1 if p.cx > self.cx else -1
        ratio = self.hp / self.max_hp
        self.phase = 1 if ratio > 0.66 else 2 if ratio > 0.33 else 3

        if self.on_ground:
            self.hop_timer -= dt
            if self.hop_timer <= 0:
                self.hop_timer = max(0.75, 1.9 - self.phase * 0.3)
                self.vx = self.facing * random.uniform(240, 340)
                self.vy = -random.uniform(580, 720)
                self.squash = 1.0
                game.shake(4)
        else:
            self.vx *= (1 - min(1.0, dt * 0.3))
        self.vy = min(self.vy + 1800 * dt, 1100)
        self.squash = max(0.0, self.squash - dt * 3.0)
        game.world.move_entity(self, dt)

        self.shoot_timer -= dt
        if self.shoot_timer <= 0:
            self.shoot_timer = max(1.8, 3.8 - self.phase * 0.5)
            base = math.atan2(p.cy - self.cy, p.cx - self.cx)
            for i in (-1, 0, 1):
                if self.phase >= 2 or i == 0:
                    ang = base + i * 0.24
                    game.projectiles.append(GelShot(self.cx, self.cy, math.cos(ang) * 330, math.sin(ang) * 330 - 80))
            game.audio.sfx("swing", 0.5)

        # Призыв свиты только при переходе через пороги здоровья.
        if ratio <= 0.66 and self.summoned == 0:
            self.summoned = 1
            self._summon_adds(game, 2)
        elif ratio <= 0.33 and self.summoned == 1:
            self.summoned = 2
            self._summon_adds(game, 3)

        if self.rect.colliderect(p.rect) and p.invuln <= 0:
            p.take_damage(self.damage, self.cx, game)
        if self.on_ground and random.random() < dt * 8:
            game.burst(self.cx + random.randint(-50, 50), self.bottom, (126, 180, 128),
                       1, speed=40, gravity=100, life=0.5, size=3)

    def _summon_adds(self, game, count):
        for _ in range(count):
            sx = self.cx + random.randint(-160, 160)
            sy = self.cy - 40
            game.enemies.append(Slime(sx, sy, "king_spawn"))
        game.burst(self.cx, self.cy, (135, 230, 150), 20, speed=200, gravity=400, life=0.8)

    def on_death(self, game):
        self.alive = False
        game.player.stats["kills"] += 1
        game.audio.sfx("boss_die")
        game.shake(24)
        for _ in range(4):
            game.burst(self.cx + random.randint(-50, 50), self.cy + random.randint(-30, 30),
                       (148, 240, 166), 30, speed=320, gravity=500, life=1.4, size=6, glow=True)
        game.spawn_drop("gel", 35, self.cx, self.cy)
        game.spawn_drop("gold_ore", 8, self.cx, self.cy)
        game.spawn_drop("crystal", 5, self.cx, self.cy)
        game.spawn_drop("slime_core", 1, self.cx, self.cy)
        game.on_boss_defeated(self)

    def draw(self, surf, cam, assets, game):
        sx = int(self.cx - cam[0])
        sy = int(self.bottom - cam[1])
        squash = 1.0 + self.squash * 0.22
        w = self.w * (1.0 + self.squash * 0.16)
        h = self.h * squash
        x = int(sx - w / 2)
        y = int(sy - h)
        color = (248, 250, 255) if self.hurt_time > 0 else self.color
        dark = tuple(max(0, c - 58) for c in color)
        deeper = tuple(max(0, c - 92) for c in color)
        light = tuple(min(255, c + 62) for c in color)
        # Тень и аура.
        sh = pygame.Surface((int(w * 1.14), 24), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 95), sh.get_rect())
        surf.blit(sh, (int(sx - w * 0.57), sy - 13))
        glow = assets.glow(130, (104, 206, 126))
        surf.blit(glow, (sx - glow.get_width() // 2, sy - h // 2 - glow.get_height() // 2),
                  special_flags=pygame.BLEND_RGB_ADD)
        pygame.draw.ellipse(surf, deeper, (x, y + 3, int(w), int(h)))
        pygame.draw.ellipse(surf, dark, (x + 2, y + 2, int(w) - 4, int(h) - 4))
        pygame.draw.ellipse(surf, color, (x + 5, y + 5, int(w) - 10, int(h) - 10))
        # Желейные слои и блики.
        pygame.draw.ellipse(surf, tuple(min(255, c + 34) for c in color),
                            (x + 8, y + 7, int(w) - 16, int(h * 0.55)))
        pygame.draw.ellipse(surf, light, (x + int(w * 0.15), y + 9,
                                          int(w * 0.34), int(h * 0.28)))
        pygame.draw.ellipse(surf, (255, 255, 255, 170),
                            (x + int(w * 0.21), y + 11, int(w * 0.17), int(h * 0.10)))
        # Пузыри внутри тела.
        for px, py, r in ((0.72, 0.55, 6), (0.30, 0.72, 4), (0.62, 0.78, 3),
                          (0.80, 0.35, 3), (0.18, 0.45, 2)):
            pygame.draw.circle(surf, tuple(max(0, c - 34) for c in color),
                               (x + int(w * px), y + int(h * py)), r)
            pygame.draw.circle(surf, tuple(min(255, c + 45) for c in color),
                               (x + int(w * px) - 1, y + int(h * py) - 1), max(1, r - 2))
        # Царственный пояс из «капель».
        for i in range(5):
            bx = x + int(w * (0.16 + i * 0.17))
            by = y + int(h * 0.84) + int(math.sin(self.anim * 3 + i) * 2)
            pygame.draw.circle(surf, (241, 209, 108), (bx, by), 3)
            pygame.draw.circle(surf, (255, 240, 177), (bx - 1, by - 1), 1)
        # Глаза с бликами и зрачками.
        eye_y = int(sy - h * 0.63)
        ex = int(w * 0.19)
        look = 1 if getattr(game.player, "cx", sx) > sx else -1
        for side in (-1, 1):
            gx = int(sx + side * ex)
            pygame.draw.circle(surf, (245, 252, 245), (gx, eye_y), 9)
            pygame.draw.circle(surf, (27, 43, 32), (gx + look * 2, eye_y + 1), 5)
            pygame.draw.circle(surf, (255, 255, 255), (gx - 2, eye_y - 3), 2)
        # Ухмылка с зубами.
        pygame.draw.arc(surf, deeper, pygame.Rect(int(sx - w * 0.23), eye_y + 12,
                                                  int(w * 0.46), int(h * 0.26)), 3.3, 6.1, 4)
        for i in range(4):
            tx = int(sx - 16 + i * 9)
            pygame.draw.polygon(surf, (242, 250, 235),
                                [(tx, eye_y + 19), (tx + 4, eye_y + 19), (tx + 2, eye_y + 25)])
        # Корона с самоцветами.
        crown_y = int(sy - h - 10)
        pts = [(sx - 28, crown_y + 20), (sx - 32, crown_y + 2), (sx - 14, crown_y + 10),
               (sx, crown_y - 8), (sx + 14, crown_y + 10), (sx + 32, crown_y + 2),
               (sx + 28, crown_y + 20)]
        pygame.draw.polygon(surf, (148, 103, 33), [(px + 1, py + 3) for px, py in pts])
        pygame.draw.polygon(surf, (241, 194, 87), pts)
        pygame.draw.polygon(surf, (252, 224, 138), [(sx - 25, crown_y + 17), (sx - 27, crown_y + 8),
                                                     (sx - 14, crown_y + 13), (sx, crown_y + 1),
                                                     (sx + 14, crown_y + 13), (sx + 27, crown_y + 8),
                                                     (sx + 25, crown_y + 17)])
        pygame.draw.rect(surf, (196, 142, 48), (sx - 28, crown_y + 18, 56, 9), border_radius=3)
        pygame.draw.polygon(surf, (219, 67, 122), [(sx, crown_y + 14), (sx + 7, crown_y + 20),
                                                   (sx, crown_y + 28), (sx - 7, crown_y + 20)])
        pygame.draw.circle(surf, (255, 190, 218), (sx - 1, crown_y + 18), 2)
        for gx, gy, gc in ((sx - 18, crown_y + 21, (95, 220, 238)),
                           (sx + 18, crown_y + 21, (95, 220, 238))):
            pygame.draw.circle(surf, gc, (gx, gy), 2)
            pygame.draw.circle(surf, (240, 255, 255), (gx - 1, gy - 1), 1)
        # Искры вокруг короны.
        for i in range(3):
            ang = self.anim * 2.0 + i * math.tau / 3
            sparkle = (sx + int(math.cos(ang) * 38), crown_y + 9 + int(math.sin(ang) * 7))
            pygame.draw.line(surf, (255, 249, 205), sparkle,
                             (sparkle[0] + 3, sparkle[1]), 1)
            pygame.draw.line(surf, (255, 249, 205), sparkle,
                             (sparkle[0], sparkle[1] - 3), 1)
        self.draw_hp(surf, cam, assets)


class ForestColossus(Enemy):
    """Второй босс: ожившее древо Изумрудного леса."""

    def __init__(self, x, y):
        super().__init__(x, y, 146, 166, 1080, 26, "Лесной колосс", (104, 140, 78))
        self.knock_resist = 12.0
        self.is_boss = True
        self.intro = 1.5
        self.phase = 1
        self.shoot_timer = 2.2
        self.stomp_timer = 3.0
        self.summoned = 0
        self.walk_phase = 0.0
        self.leaf_pulse = 0.0
        self.music_key = "boss_forest"
        self.light_color = (128, 224, 118)

    def update(self, dt, game):
        self.anim += dt
        self.hurt_time = max(0.0, self.hurt_time - dt)
        self.intro = max(0.0, self.intro - dt)
        self.leaf_pulse += dt
        if self.intro > 0:
            if random.random() < dt * 10:
                game.burst(self.cx + random.randint(-55, 55), self.y + random.randint(-40, 40),
                           (143, 205, 104), 1, speed=40, gravity=-60,
                           life=0.8, size=2, glow=True)
            return
        p = game.player
        if not p:
            return
        self.facing = 1 if p.cx > self.cx else -1
        ratio = self.hp / self.max_hp
        self.phase = 1 if ratio > 0.66 else 2 if ratio > 0.33 else 3
        self.walk_phase += dt * (2.0 + self.phase * 0.45)

        if self.on_ground:
            self.vx = approach(self.vx, self.facing * (58 + self.phase * 18), 380 * dt)
            self.stomp_timer -= dt
            if self.stomp_timer <= 0:
                self.stomp_timer = max(2.2, 4.6 - self.phase * 0.6)
                self.vy = -random.uniform(430, 610)
                game.shake(7)
                game.audio.sfx("jump", 0.5)
        else:
            self.vx *= (1 - min(1.0, dt * 0.35))
        self.vy = min(self.vy + 1850 * dt, 1150)
        was_airborne = not self.on_ground
        game.world.move_entity(self, dt)
        if was_airborne and self.on_ground:
            game.shake(12)
            for i in range(7):
                ang = i / 7 * math.tau
                game.projectiles.append(SeedShot(self.cx, self.bottom - 10,
                                                 math.cos(ang) * 190,
                                                 -220 + math.sin(ang) * 60, 11))
            game.burst(self.cx, self.bottom, (138, 120, 74), 18, speed=120,
                       gravity=400, life=0.7, size=4)

        self.shoot_timer -= dt
        if self.shoot_timer <= 0:
            self.shoot_timer = max(1.6, 3.6 - self.phase * 0.55)
            base = math.atan2(p.cy - self.cy, p.cx - self.cx)
            count = 2 + self.phase
            for i in range(count):
                offset = (i - (count - 1) / 2) * 0.18
                ang = base + offset
                game.projectiles.append(SeedShot(
                    self.cx + math.cos(ang) * 32, self.y + 48 + math.sin(ang) * 18,
                    math.cos(ang) * (260 + self.phase * 30),
                    math.sin(ang) * 260 - 120, 13))
            game.audio.sfx("swing", 0.45)

        if ratio <= 0.66 and self.summoned == 0:
            self.summoned = 1
            for i in range(2):
                game.enemies.append(Slime(self.cx + (i * 80 - 40), self.cy - 50, "green"))
            game.toast("Лесной колосс призывает слизней!", config.GREEN)
        elif ratio <= 0.33 and self.summoned == 1:
            self.summoned = 2
            for i in range(2):
                game.enemies.append(CaveSpider(self.cx + (i * 90 - 45), self.cy - 70))
            game.toast("Из корней выползают пауки!", config.GREEN)

        if self.rect.colliderect(p.rect) and p.invuln <= 0:
            p.take_damage(self.damage, self.cx, game)
            p.vx = 260 if p.cx > self.cx else -260
        if self.on_ground and random.random() < dt * 5:
            game.burst(self.cx + random.randint(-60, 60), self.bottom - 4,
                       (142, 122, 80), 1, speed=30, gravity=90, life=0.6, size=2)

    def on_death(self, game):
        self.alive = False
        game.player.stats["kills"] += 1
        game.audio.sfx("boss_die")
        game.shake(26)
        for _ in range(5):
            game.burst(self.cx + random.randint(-60, 60), self.cy + random.randint(-60, 40),
                       random.choice(((148, 210, 111), (196, 164, 92), (118, 186, 96))),
                       30, speed=300, gravity=500, life=1.5, size=6, glow=True)
        game.spawn_drop("forest_heart", 1, self.cx, self.cy)
        game.spawn_drop("wood", 30, self.cx, self.cy)
        game.spawn_drop("gel", 20, self.cx, self.cy)
        game.spawn_drop("gold_ore", 8, self.cx, self.cy)
        game.spawn_drop("crystal", 4, self.cx, self.cy)
        game.on_boss_defeated(self)

    def draw(self, surf, cam, assets, game):
        sx = int(self.cx - cam[0])
        sy = int(self.bottom - cam[1])
        hurt = self.hurt_time > 0
        bark = (232, 213, 194) if hurt else self.color
        bark_dark = tuple(max(0, c - 55) for c in bark)
        bark_deep = tuple(max(0, c - 82) for c in bark)
        moss = (111, 171, 82) if not hurt else (201, 226, 190)
        leaf = (86, 160, 79)
        leaf_light = (137, 203, 112)
        leaf_dark = (55, 110, 59)
        # Тень и корни.
        sh = pygame.Surface((166, 30), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 100), sh.get_rect())
        surf.blit(sh, (sx - 83, sy - 19))
        for i, (dx, ln) in enumerate(((-48, -18), (-20, -8), (22, -10), (50, -20))):
            pygame.draw.line(surf, bark_deep, (sx + dx, sy - 8),
                             (sx + dx + ln, sy + 3), 7)
        # Ноги-стволы.
        swing = math.sin(self.walk_phase) * 9
        for i, dx in enumerate((-32, 32)):
            leg_y = sy - 72 + int(swing if i == 0 else -swing)
            pygame.draw.rect(surf, bark_deep, (sx + dx - 22, leg_y - 2, 44, 78), border_radius=13)
            pygame.draw.rect(surf, bark_dark, (sx + dx - 19, leg_y, 38, 74), border_radius=11)
            pygame.draw.rect(surf, bark, (sx + dx - 14, leg_y + 4, 28, 64), border_radius=8)
            pygame.draw.line(surf, bark_dark, (sx + dx - 7, leg_y + 14),
                             (sx + dx - 9, leg_y + 48), 2)
            pygame.draw.line(surf, moss, (sx + dx + 8, leg_y + 8),
                             (sx + dx + 5, leg_y + 26), 3)
            pygame.draw.ellipse(surf, bark_deep, (sx + dx - 16, sy - 10, 32, 12))
        # Корпус-ствол с дуплом.
        pygame.draw.polygon(surf, bark_deep, [(sx - 53, sy - 118), (sx - 33, sy - 138),
                                               (sx + 34, sy - 138), (sx + 54, sy - 118),
                                               (sx + 46, sy - 62), (sx - 46, sy - 62)])
        pygame.draw.rect(surf, bark_dark, (sx - 46, sy - 132, 92, 78), border_radius=16)
        pygame.draw.rect(surf, bark, (sx - 41, sy - 128, 82, 71), border_radius=13)
        # Древесные кольца и дупло-сердце.
        for r in (23, 15):
            pygame.draw.circle(surf, bark_dark, (sx - 4, sy - 100), r, 2)
        pygame.draw.ellipse(surf, (49, 37, 29), (sx - 17, sy - 112, 26, 27))
        pygame.draw.ellipse(surf, (71, 54, 38), (sx - 14, sy - 109, 20, 21))
        glow = assets.glow(74, (107, 226, 121))
        surf.blit(glow, (sx - 4 - glow.get_width() // 2, sy - 99 - glow.get_height() // 2),
                  special_flags=pygame.BLEND_RGB_ADD)
        pulse = 6 + int(math.sin(self.leaf_pulse * 4.2) * 2)
        pygame.draw.circle(surf, (42, 94, 53), (sx - 4, sy - 99), pulse + 5)
        pygame.draw.circle(surf, (103, 197, 108), (sx - 4, sy - 99), pulse + 2)
        pygame.draw.circle(surf, (200, 247, 177), (sx - 7, sy - 102), 3)
        # Мох и светящиеся прожилки.
        pygame.draw.line(surf, moss, (sx - 38, sy - 119), (sx - 27, sy - 125), 3)
        pygame.draw.line(surf, moss, (sx + 22, sy - 87), (sx + 36, sy - 81), 3)
        pygame.draw.line(surf, (152, 221, 156), (sx - 15, sy - 111),
                         (sx - 10, sy - 90), 1)
        pygame.draw.line(surf, (152, 221, 156), (sx + 3, sy - 110),
                         (sx + 7, sy - 91), 1)
        # Руки-ветви с кулаками.
        arm_swing = math.sin(self.walk_phase + 1.4) * 12
        for side in (-1, 1):
            ax = sx + side * 62
            ay = sy - 118 + int(arm_swing * side)
            pygame.draw.line(surf, bark_deep, (sx + side * 42, sy - 118), (ax, ay + 26), 23)
            pygame.draw.line(surf, bark_dark, (sx + side * 42, sy - 118), (ax, ay + 24), 17)
            pygame.draw.line(surf, bark, (sx + side * 42, sy - 119), (ax, ay + 23), 11)
            pygame.draw.circle(surf, bark_deep, (ax, ay + 31), 15)
            pygame.draw.circle(surf, bark, (ax, ay + 29), 12)
            for i in range(3):
                pygame.draw.line(surf, bark_dark, (ax - 7 + i * 6, ay + 39),
                                 (ax - 10 + i * 7, ay + 47), 3)
        # Голова-крона с ветвями-рогами.
        pygame.draw.circle(surf, bark_deep, (sx, sy - 152), 35)
        pygame.draw.circle(surf, bark_dark, (sx, sy - 152), 31)
        pygame.draw.circle(surf, bark, (sx, sy - 152), 27)
        # Листва.
        for lx, ly, r in ((-33, -174, 21), (-16, -184, 23), (6, -187, 24),
                          (27, -178, 21), (0, -168, 27), (-38, -156, 16), (38, -157, 16)):
            pygame.draw.circle(surf, leaf_dark, (sx + lx, sy + ly), r + 2)
            pygame.draw.circle(surf, leaf, (sx + lx, sy + ly), r)
            pygame.draw.circle(surf, leaf_light, (sx + lx - r // 3, sy + ly - r // 3), max(3, r // 2))
        # Светящиеся глаза.
        for ex in (-11, 11):
            pygame.draw.ellipse(surf, (39, 62, 32), (sx + ex - 7, sy - 158, 14, 9))
            pygame.draw.circle(surf, (192, 247, 131), (sx + ex, sy - 154), 4)
            pygame.draw.circle(surf, (249, 255, 215), (sx + ex - 1, sy - 155), 2)
        # Ветви-рога.
        pygame.draw.line(surf, bark_dark, (sx - 24, sy - 170), (sx - 39, sy - 189), 5)
        pygame.draw.line(surf, bark_dark, (sx + 24, sy - 170), (sx + 39, sy - 189), 5)
        pygame.draw.line(surf, leaf, (sx - 39, sy - 189), (sx - 49, sy - 197), 3)
        pygame.draw.line(surf, leaf, (sx + 39, sy - 189), (sx + 49, sy - 197), 3)
        # Падающие листья.
        for i in range(4):
            ang = self.leaf_pulse * 1.4 + i * 1.7
            lx = sx + int(math.cos(ang) * (50 + i * 8))
            ly = sy - 120 + int(math.sin(ang * 1.2) * 40)
            pygame.draw.ellipse(surf, leaf_light, (lx, ly, 5, 3))
        self.draw_hp(surf, cam, assets)


class FrostQueen(Enemy):
    """Третий босс: повелительница Снежных пиков."""

    def __init__(self, x, y):
        super().__init__(x, y, 104, 142, 1240, 28, "Ледяная королева", (147, 193, 222))
        self.knock_resist = 12.0
        self.is_boss = True
        self.is_flying = True
        self.intro = 1.6
        self.phase = 1
        self.shoot_timer = 2.0
        self.teleport_timer = 5.0
        self.summoned = 0
        self.hover_phase = 0.0
        self.music_key = "boss_frost"
        self.light_color = (150, 220, 255)

    def update(self, dt, game):
        self.anim += dt
        self.hurt_time = max(0.0, self.hurt_time - dt)
        self.intro = max(0.0, self.intro - dt)
        self.hover_phase += dt
        if self.intro > 0:
            if random.random() < dt * 12:
                game.burst(self.cx + random.randint(-50, 50), self.cy + random.randint(-50, 50),
                           (196, 239, 255), 1, speed=30, gravity=-30,
                           life=0.7, size=2, glow=True)
            return
        p = game.player
        if not p:
            return
        ratio = self.hp / self.max_hp
        self.phase = 1 if ratio > 0.66 else 2 if ratio > 0.33 else 3
        dx = p.cx - self.cx
        self.facing = 1 if dx > 0 else -1
        # Парим над игроком, плавно покачиваясь.
        target_x = p.cx - self.facing * 120
        target_y = p.cy - 170 + math.sin(self.hover_phase * 2.1) * 22
        self.vx = approach(self.vx, clamp((target_x - self.cx) * 1.5, -190, 190), 280 * dt)
        self.vy = approach(self.vy, clamp((target_y - self.cy) * 1.4, -150, 150), 260 * dt)
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.x = clamp(self.x, TILE * 2, game.world.w * TILE - self.w - TILE * 2)
        self.y = clamp(self.y, TILE * 2, game.world.h * TILE - self.h - TILE * 2)
        if game.world.rect_collides(self.rect):
            self.y -= 24
            self.vy = -40

        self.shoot_timer -= dt
        if self.shoot_timer <= 0:
            self.shoot_timer = max(1.3, 3.2 - self.phase * 0.5)
            base = math.atan2(p.cy - self.cy, p.cx - self.cx)
            count = 3 + self.phase
            for i in range(count):
                offset = (i - (count - 1) / 2) * 0.16
                ang = base + offset
                game.projectiles.append(IceShard(
                    self.cx + math.cos(ang) * 30, self.cy + 20 + math.sin(ang) * 24,
                    math.cos(ang) * (330 + self.phase * 20),
                    math.sin(ang) * (330 + self.phase * 20), 14))
            if self.phase >= 2:
                for i in range(6):
                    ang = i / 6 * math.tau + self.hover_phase
                    game.projectiles.append(IceShard(
                        self.cx, self.cy, math.cos(ang) * 180, math.sin(ang) * 180, 12))
            game.audio.sfx("summon", 0.4)

        self.teleport_timer -= dt
        if self.teleport_timer <= 0:
            self.teleport_timer = max(2.8, 5.6 - self.phase * 0.7)
            old_x, old_y = self.cx, self.cy
            game.burst(old_x, old_y, (206, 242, 255), 26, speed=190,
                       gravity=-40, life=0.8, size=4, glow=True)
            side = random.choice((-1, 1))
            nx = clamp(p.cx + side * random.uniform(220, 340),
                       TILE * 3, game.world.w * TILE - TILE * 3)
            ny = clamp(p.cy - random.uniform(130, 240),
                       TILE * 3, game.world.h * TILE - TILE * 3)
            self.x = nx - self.w / 2
            self.y = ny - self.h / 2
            if game.world.rect_collides(self.rect):
                self.x, self.y = old_x - self.w / 2, old_y - self.h / 2
            game.burst(self.cx, self.cy, (223, 250, 255), 22, speed=160,
                       gravity=-30, life=0.7, size=4, glow=True)

        if ratio <= 0.66 and self.summoned == 0:
            self.summoned = 1
            for i in range(2):
                game.enemies.append(FrostWolf(self.cx + (i * 110 - 55), self.cy + 80))
            game.toast("Ледяная королева призывает волков!", config.BLUE)
        elif ratio <= 0.33 and self.summoned == 1:
            self.summoned = 2
            for i in range(2):
                game.enemies.append(Bat(self.cx + (i * 90 - 45), self.cy - 40, "frost"))
            game.toast("Метель крепчает!", config.BLUE)

        if self.rect.colliderect(p.rect) and p.invuln <= 0:
            p.take_damage(self.damage, self.cx, game)
            p.vy = min(p.vy, -240)
        if random.random() < dt * 10:
            game.burst(self.cx + random.randint(-40, 40), self.bottom - 12,
                       (193, 232, 250), 1, speed=20, gravity=-20,
                       life=0.7, size=2, glow=True)

    def on_death(self, game):
        self.alive = False
        game.player.stats["kills"] += 1
        game.audio.sfx("boss_die")
        game.shake(28)
        for _ in range(6):
            game.burst(self.cx + random.randint(-55, 55), self.cy + random.randint(-60, 40),
                       random.choice(((196, 239, 255), (126, 185, 226), (243, 252, 255))),
                       30, speed=320, gravity=350, life=1.5, size=6, glow=True)
        game.spawn_drop("frost_tear", 1, self.cx, self.cy)
        game.spawn_drop("ice", 25, self.cx, self.cy)
        game.spawn_drop("crystal", 8, self.cx, self.cy)
        game.spawn_drop("gold_ore", 10, self.cx, self.cy)
        game.on_boss_defeated(self)

    def draw(self, surf, cam, assets, game):
        sx = int(self.cx - cam[0])
        sy = int(self.bottom - cam[1])
        hurt = self.hurt_time > 0
        dress = (249, 252, 255) if hurt else self.color
        dress_dark = tuple(max(0, c - 48) for c in dress)
        dress_deep = tuple(max(0, c - 80) for c in dress)
        skin = (236, 244, 250) if not hurt else (255, 255, 255)
        ice_light = (225, 248, 255)
        # Снежная аура и позёмка.
        glow = assets.glow(128, (118, 195, 240))
        surf.blit(glow, (sx - glow.get_width() // 2, sy - 82 - glow.get_height() // 2),
                  special_flags=pygame.BLEND_RGB_ADD)
        for i in range(8):
            ang = self.hover_phase * 0.9 + i * math.tau / 8
            px = sx + int(math.cos(ang) * (54 + (i % 3) * 8))
            py = sy - 72 + int(math.sin(ang * 1.2) * 46)
            pygame.draw.circle(surf, (221, 247, 255), (px, py), 1 + i % 2)
        # Шлейф платья-метели.
        flow = math.sin(self.hover_phase * 2.4) * 7
        pygame.draw.polygon(surf, dress_deep, [(sx - 22, sy - 76), (sx + 23, sy - 76),
                                                (sx + 47 + flow, sy - 2), (sx + 15, sy - 17),
                                                (sx - 4, sy + 2), (sx - 22, sy - 14),
                                                (sx - 45 + flow, sy - 4)])
        pygame.draw.polygon(surf, dress_dark, [(sx - 20, sy - 74), (sx + 21, sy - 74),
                                                (sx + 40 + flow, sy - 8), (sx + 13, sy - 20),
                                                (sx - 2, sy - 3), (sx - 21, sy - 18),
                                                (sx - 39 + flow, sy - 9)])
        pygame.draw.polygon(surf, dress, [(sx - 17, sy - 72), (sx + 18, sy - 72),
                                           (sx + 33 + flow, sy - 13), (sx + 10, sy - 23),
                                           (sx - 2, sy - 8), (sx - 19, sy - 21),
                                           (sx - 32 + flow, sy - 14)])
        for i in range(4):
            px = sx - 20 + i * 13
            pygame.draw.line(surf, ice_light, (px, sy - 58), (px + int(flow), sy - 12), 1)
        # Ледяные шипы на подоле.
        for i in range(5):
            ix = sx - 32 + i * 16 + int(flow * 0.4)
            pygame.draw.polygon(surf, (208, 240, 253), [(ix, sy - 16), (ix + 5, sy - 2), (ix + 9, sy - 17)])
        # Торс и руки.
        pygame.draw.polygon(surf, dress_dark, [(sx - 17, sy - 110), (sx + 17, sy - 110),
                                                (sx + 21, sy - 74), (sx - 21, sy - 74)])
        pygame.draw.polygon(surf, dress, [(sx - 14, sy - 109), (sx + 14, sy - 109),
                                           (sx + 17, sy - 75), (sx - 17, sy - 75)])
        pygame.draw.line(surf, ice_light, (sx - 14, sy - 102), (sx + 14, sy - 102), 2)
        pygame.draw.circle(surf, (145, 216, 240), (sx, sy - 96), 4)
        pygame.draw.circle(surf, (235, 253, 255), (sx - 1, sy - 97), 2)
        for side in (-1, 1):
            pygame.draw.line(surf, dress_deep, (sx + side * 15, sy - 104),
                             (sx + side * 31, sy - 84), 8)
            pygame.draw.line(surf, dress, (sx + side * 15, sy - 104),
                             (sx + side * 31, sy - 84), 5)
            pygame.draw.circle(surf, skin, (sx + side * 32, sy - 83), 4)
            # Ледяные пальцы.
            for i in range(2):
                pygame.draw.line(surf, ice_light, (sx + side * 34, sy - 85),
                                 (sx + side * (38 + i * 2), sy - 90 + i * 3), 1)
        # Голова, волосы и корона.
        pygame.draw.circle(surf, dress_deep, (sx, sy - 126), 19)
        pygame.draw.circle(surf, skin, (sx, sy - 126), 16)
        pygame.draw.polygon(surf, (196, 226, 242), [(sx - 16, sy - 131), (sx - 24, sy - 104),
                                                     (sx - 12, sy - 112), (sx - 8, sy - 136)])
        pygame.draw.polygon(surf, (214, 239, 250), [(sx + 16, sy - 131), (sx + 23, sy - 103),
                                                     (sx + 12, sy - 111), (sx + 8, sy - 136)])
        pygame.draw.ellipse(surf, (210, 236, 249), (sx - 14, sy - 141, 28, 12))
        # Глаза: холодное сияние.
        for ex in (-6, 6):
            pygame.draw.ellipse(surf, (71, 109, 137), (sx + ex - 4, sy - 129, 8, 4))
            pygame.draw.circle(surf, (155, 235, 255), (sx + ex, sy - 127), 2)
        pygame.draw.line(surf, (148, 185, 205), (sx - 4, sy - 117), (sx + 4, sy - 117), 1)
        # Корона из льда.
        crown_y = sy - 148
        pts = [(sx - 18, crown_y + 12), (sx - 20, crown_y - 1), (sx - 9, crown_y + 5),
               (sx, crown_y - 12), (sx + 9, crown_y + 5), (sx + 20, crown_y - 1),
               (sx + 18, crown_y + 12)]
        pygame.draw.polygon(surf, (92, 161, 200), [(x + 1, y + 2) for x, y in pts])
        pygame.draw.polygon(surf, (210, 243, 255), pts)
        pygame.draw.polygon(surf, (244, 254, 255), [(sx - 12, crown_y + 9), (sx - 14, crown_y + 3),
                                                     (sx - 8, crown_y + 7), (sx, crown_y - 6),
                                                     (sx + 8, crown_y + 7), (sx + 14, crown_y + 3),
                                                     (sx + 12, crown_y + 9)])
        pygame.draw.circle(surf, (137, 219, 245), (sx, crown_y + 6), 3)
        pygame.draw.circle(surf, (250, 255, 255), (sx - 1, crown_y + 5), 1)
        # Посох в правой руке.
        staff_x = sx - 30
        pygame.draw.line(surf, (100, 153, 184), (staff_x, sy - 92), (staff_x - 4, sy - 30), 4)
        pygame.draw.line(surf, (210, 241, 255), (staff_x - 1, sy - 90), (staff_x - 4, sy - 32), 1)
        pygame.draw.polygon(surf, (156, 222, 248), [(staff_x, sy - 104), (staff_x + 9, sy - 96),
                                                     (staff_x, sy - 86), (staff_x - 9, sy - 96)])
        pygame.draw.circle(surf, (238, 253, 255), (staff_x, sy - 96), 3)
        staff_glow = assets.glow(38, (172, 229, 255))
        surf.blit(staff_glow, (staff_x - staff_glow.get_width() // 2,
                               sy - 96 - staff_glow.get_height() // 2),
                  special_flags=pygame.BLEND_RGB_ADD)
        self.draw_hp(surf, cam, assets)


class AbyssWarden(Enemy):
    """Финальный босс: каменный страж с ядром Бездны."""

    def __init__(self, x, y):
        super().__init__(x, y, 112, 132, 1450, 30, "Страж Бездны", (112, 104, 117))
        self.knock_resist = 14.0
        self.is_boss = True
        self.is_final_boss = True
        self.intro = 1.8
        self.phase = 1
        self.shoot_timer = 2.4
        self.leap_timer = 3.2
        self.summoned = 0
        self.walk_phase = 0.0
        self.core_pulse = 0.0
        self.music_key = "boss2"
        self.light_color = (168, 102, 232)

    def update(self, dt, game):
        self.anim += dt
        self.hurt_time = max(0.0, self.hurt_time - dt)
        self.intro = max(0.0, self.intro - dt)
        self.core_pulse += dt
        if self.intro > 0:
            if random.random() < dt * 6:
                game.burst(self.cx + random.randint(-40, 40), self.bottom - 10,
                           (149, 99, 206), 1, speed=40, gravity=-80, life=0.8, size=3, glow=True)
            return
        p = game.player
        if not p:
            return
        self.facing = 1 if p.cx > self.cx else -1
        ratio = self.hp / self.max_hp
        self.phase = 1 if ratio > 0.7 else 2 if ratio > 0.35 else 3
        self.walk_phase += dt * (2.0 + self.phase * 0.5)

        if self.on_ground:
            self.vx = approach(self.vx, self.facing * (70 + self.phase * 28), 460 * dt)
            self.leap_timer -= dt
            if self.leap_timer <= 0:
                self.leap_timer = max(1.8, 4.2 - self.phase * 0.7)
                self.vy = -random.uniform(520, 720)
                game.shake(7)
        else:
            self.vx *= (1 - min(1.0, dt * 0.4))
        self.vy = min(self.vy + 1900 * dt, 1200)
        game.world.move_entity(self, dt)

        self.shoot_timer -= dt
        if self.shoot_timer <= 0:
            self.shoot_timer = max(1.3, 3.8 - self.phase * 0.65)
            base = math.atan2(p.cy - self.cy, p.cx - self.cx)
            count = 1 + self.phase
            for i in range(count):
                offset = (i - (count - 1) / 2) * 0.22
                ang = base + offset
                game.projectiles.append(VoidBolt(
                    self.cx + math.cos(ang) * 34, self.cy + math.sin(ang) * 20,
                    math.cos(ang) * 300, math.sin(ang) * 300, 16))
            if self.phase >= 2:
                for ang in (math.pi * 0.2, math.pi * 0.8, math.pi * 1.2, math.pi * 1.8):
                    game.projectiles.append(VoidBolt(self.cx, self.cy,
                                                     math.cos(ang) * 180, math.sin(ang) * 180, 13))
            game.audio.sfx("summon", 0.35)

        if ratio <= 0.70 and self.summoned == 0:
            self.summoned = 1
            for i in range(2):
                game.enemies.append(CorruptEye(self.cx + (i * 70 - 35), self.cy - 100))
            game.toast("Страж призывает порченых глаз!", config.PURPLE)
        elif ratio <= 0.35 and self.summoned == 1:
            self.summoned = 2
            for i in range(3):
                game.enemies.append(CorruptEye(self.cx + (i * 60 - 60), self.cy - 120))
            game.toast("Ядро Бездны пылает!", config.PURPLE)

        if self.rect.colliderect(p.rect) and p.invuln <= 0:
            p.take_damage(self.damage, self.cx, game)
            p.vy = min(p.vy, -250)
        if game.is_night() and random.random() < dt * 1.5:
            game.burst(self.cx, self.cy, (142, 92, 215), 1, speed=10, gravity=-20,
                       life=0.8, size=3, glow=True)

    def on_death(self, game):
        self.alive = False
        game.player.stats["kills"] += 1
        game.audio.sfx("boss_die")
        game.shake(30)
        for _ in range(6):
            game.burst(self.cx + random.randint(-60, 60), self.cy + random.randint(-60, 60),
                       random.choice(((164, 102, 226), (127, 223, 229), (238, 194, 111))),
                       28, speed=340, gravity=400, life=1.6, size=6, glow=True)
        game.spawn_drop("crystal", 12, self.cx, self.cy)
        game.spawn_drop("gold_ore", 15, self.cx, self.cy)
        game.spawn_drop("life_crystal", 2, self.cx, self.cy)
        game.on_boss_defeated(self)

    def draw(self, surf, cam, assets, game):
        sx = int(self.cx - cam[0])
        sy = int(self.bottom - cam[1])
        hurt = self.hurt_time > 0
        stone = (237, 225, 245) if hurt else self.color
        dark = tuple(max(0, c - 47) for c in stone)
        deeper = tuple(max(0, c - 78) for c in stone)
        light = tuple(min(255, c + 38) for c in stone)
        rune = (129, 223, 232)
        # Тень и мистическая аура.
        sh = pygame.Surface((134, 28), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 100), sh.get_rect())
        surf.blit(sh, (sx - 67, sy - 18))
        aura = assets.glow(120, (126, 71, 188))
        surf.blit(aura, (sx - aura.get_width() // 2, sy - 80 - aura.get_height() // 2),
                  special_flags=pygame.BLEND_RGB_ADD)
        # Ноги-колонны.
        swing = math.sin(self.walk_phase) * 8
        for i, dx in enumerate((-37, 37)):
            leg_y = sy - 54 + int(swing if i == 0 else -swing)
            pygame.draw.rect(surf, deeper, (sx + dx - 19, leg_y - 2, 38, 58), border_radius=10)
            pygame.draw.rect(surf, dark, (sx + dx - 17, leg_y, 34, 55), border_radius=9)
            pygame.draw.rect(surf, stone, (sx + dx - 14, leg_y + 3, 28, 49), border_radius=7)
            pygame.draw.rect(surf, light, (sx + dx - 10, leg_y + 7, 9, 17), border_radius=5)
            pygame.draw.line(surf, rune, (sx + dx - 4, leg_y + 30),
                             (sx + dx + 5, leg_y + 24), 1)
            pygame.draw.rect(surf, deeper, (sx + dx - 18, sy - 6, 37, 8), border_radius=3)
        # Корпус-скала с плечами.
        pygame.draw.polygon(surf, deeper, [(sx - 62, sy - 106), (sx - 44, sy - 122),
                                            (sx + 44, sy - 122), (sx + 62, sy - 106),
                                            (sx + 52, sy - 39), (sx - 52, sy - 39)])
        pygame.draw.rect(surf, dark, (sx - 53, sy - 115, 106, 80), border_radius=18)
        pygame.draw.rect(surf, stone, (sx - 48, sy - 111, 96, 72), border_radius=15)
        # Сколы и трещины.
        pygame.draw.polygon(surf, light, [(sx - 40, sy - 104), (sx - 23, sy - 118),
                                           (sx - 5, sy - 103), (sx - 26, sy - 98)])
        pygame.draw.line(surf, deeper, (sx - 30, sy - 72), (sx - 20, sy - 84), 2)
        pygame.draw.line(surf, deeper, (sx - 20, sy - 84), (sx - 12, sy - 77), 2)
        pygame.draw.line(surf, deeper, (sx + 22, sy - 56), (sx + 29, sy - 70), 2)
        # Наплечники.
        for side in (-1, 1):
            pygame.draw.circle(surf, dark, (sx + side * 50, sy - 103), 20)
            pygame.draw.circle(surf, stone, (sx + side * 50, sy - 105), 16)
            pygame.draw.circle(surf, light, (sx + side * 46, sy - 110), 7)
            pygame.draw.line(surf, rune, (sx + side * 50, sy - 112),
                             (sx + side * 55, sy - 100), 1)
        # Руки с кулаками.
        arm_swing = math.sin(self.walk_phase + 1.5) * 10
        for side in (-1, 1):
            ax = sx + side * 62
            ay = sy - 104 + int(arm_swing * side)
            pygame.draw.rect(surf, deeper, (ax - 17, ay - 2, 33, 74), border_radius=12)
            pygame.draw.rect(surf, dark, (ax - 15, ay, 29, 70), border_radius=10)
            pygame.draw.rect(surf, stone, (ax - 12, ay + 4, 24, 60), border_radius=8)
            pygame.draw.rect(surf, light, (ax - 8, ay + 9, 8, 18), border_radius=4)
            pygame.draw.circle(surf, dark, (ax, ay + 69), 14)
            pygame.draw.circle(surf, stone, (ax, ay + 68), 11)
            pygame.draw.line(surf, rune, (ax - 7, ay + 64), (ax + 6, ay + 61), 1)
        # Голова-шлем.
        pygame.draw.rect(surf, deeper, (sx - 30, sy - 160, 60, 52), border_radius=15)
        pygame.draw.rect(surf, dark, (sx - 28, sy - 159, 56, 48), border_radius=13)
        pygame.draw.rect(surf, stone, (sx - 24, sy - 155, 48, 41), border_radius=10)
        pygame.draw.polygon(surf, light, [(sx - 20, sy - 150), (sx - 5, sy - 157),
                                           (sx + 3, sy - 145), (sx - 13, sy - 143)])
        # Рога.
        pygame.draw.polygon(surf, deeper, [(sx - 24, sy - 153), (sx - 39, sy - 174),
                                            (sx - 17, sy - 159)])
        pygame.draw.polygon(surf, deeper, [(sx + 24, sy - 153), (sx + 39, sy - 174),
                                            (sx + 17, sy - 159)])
        pygame.draw.line(surf, rune, (sx - 31, sy - 163), (sx - 35, sy - 171), 1)
        pygame.draw.line(surf, rune, (sx + 31, sy - 163), (sx + 35, sy - 171), 1)
        # Светящиеся глаза.
        pulse = 0.75 + 0.25 * math.sin(self.core_pulse * 4.5)
        for ex in (-11, 11):
            pygame.draw.rect(surf, (53, 31, 71), (sx + ex - 6, sy - 136, 12, 7), border_radius=3)
            pygame.draw.rect(surf, (184, 119, 238), (sx + ex - 4, sy - 135, 8, 4), border_radius=2)
            pygame.draw.circle(surf, (241, 208, 255), (sx + ex - 1, sy - 134), 1)
        # Ядро Бездны.
        glow = assets.glow(76, (164, 96, 229))
        gx = sx - glow.get_width() // 2
        gy = sy - 84 - glow.get_height() // 2
        surf.blit(glow, (gx, gy), special_flags=pygame.BLEND_RGB_ADD)
        core_r = int(18 * pulse)
        pygame.draw.circle(surf, (41, 25, 57), (sx, sy - 84), core_r + 5)
        pygame.draw.circle(surf, (103, 58, 152), (sx, sy - 84), core_r + 2)
        pygame.draw.circle(surf, (165, 96, 226), (sx, sy - 84), core_r)
        pygame.draw.circle(surf, (229, 191, 251), (sx - 5, sy - 90), max(3, core_r // 3))
        # Орбитальные осколки.
        for i in range(3):
            ang = self.core_pulse * 1.6 + i * math.tau / 3
            ox = sx + int(math.cos(ang) * 28)
            oy = sy - 84 + int(math.sin(ang * 1.3) * 20)
            pygame.draw.polygon(surf, (183, 137, 226), [(ox, oy - 4), (ox + 3, oy),
                                                         (ox, oy + 4), (ox - 3, oy)])
        # Руны на корпусе.
        for rx, ry in ((-36, -66), (34, -59), (-25, -44), (23, -38)):
            pygame.draw.line(surf, rune, (sx + rx, sy + ry), (sx + rx + 8, sy + ry - 6), 1)
            pygame.draw.line(surf, rune, (sx + rx + 8, sy + ry - 6),
                             (sx + rx + 3, sy + ry - 10), 1)
        self.draw_hp(surf, cam, assets)


# ===================================================================== фабрика
def make_enemy(kind: str, x, y):
    if kind == "zombie":
        return Zombie(x, y)
    if kind == "bat":
        return Bat(x, y)
    if kind == "frost_bat":
        return Bat(x, y, "frost")
    if kind == "spider":
        return CaveSpider(x, y)
    if kind == "corrupt_eye":
        return CorruptEye(x, y)
    if kind == "desert_scorpion":
        return DesertScorpion(x, y)
    if kind == "frost_wolf":
        return FrostWolf(x, y)
    if kind == "blue_slime":
        return Slime(x, y, "blue")
    if kind == "sand_slime":
        return Slime(x, y, "sand")
    if kind == "frost_slime":
        return Slime(x, y, "frost")
    if kind == "corrupt_slime":
        return Slime(x, y, "corrupt")
    return Slime(x, y, "green")

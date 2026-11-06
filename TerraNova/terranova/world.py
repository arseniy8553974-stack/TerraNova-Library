# -*- coding: utf-8 -*-
"""Мир: процедурные биомы, тайлы, коллизии и сохранение."""
from __future__ import annotations

import math
import random

import numpy as np
import pygame

from . import config
from .config import (
    TILES, AIR, DIRT, GRASS, STONE, WOOD, LEAVES, COPPER, IRON, GOLD_TILE,
    BEDROCK, CRYSTAL, LIFE_CRYSTAL, PLANKS, WORKBENCH, TORCH, BRICK,
    SAND, SANDSTONE, SNOW, ICE, CORRUPT_GRASS, CORRUPT_STONE, CACTUS,
    DEAD_WOOD, LAVA, PINE_LEAVES, CORRUPT_LEAVES, BOULDER, BOULDER_BOUNCY,
    BOULDER_LIFE, BOULDER_LAVA, BOULDER_SPIDER, BOULDER_RAINBOW,
    BOULDER_GHOST, BOULDER_ICE, BOULDER_TILES, TREE_TRUNK, TREE_DEAD,
    CACTUS_PLANT, WATER, PALM_TRUNK, PALM_LEAVES,
    BIOME_FOREST, BIOME_DESERT, BIOME_SNOW, BIOME_CORRUPT, BIOME_BEACH,
    BIOME_NAMES,
)
from .utils import rle_encode, rle_decode, hash2


def smoothstep(t):
    return t * t * (3.0 - 2.0 * t)


def _noise1(n: int, rng, freq: int) -> np.ndarray:
    freq = max(1, int(freq))
    points = rng.random(freq + 1)
    xs = np.linspace(0, freq, n, endpoint=False)
    i0 = xs.astype(np.int32)
    frac = smoothstep(xs - i0)
    return points[i0] * (1 - frac) + points[i0 + 1] * frac


def _fbm1(n: int, rng, base_freq=3, octaves=4) -> np.ndarray:
    total = np.zeros(n)
    amp = 1.0
    norm = 0.0
    freq = base_freq
    for _ in range(octaves):
        total += _noise1(n, rng, freq) * amp
        norm += amp
        amp *= 0.5
        freq *= 2
    return total / norm


def _noise2(w: int, h: int, scale: int, rng) -> np.ndarray:
    gw = max(2, int(w / scale) + 2)
    gh = max(2, int(h / scale) + 2)
    grid = rng.random((gh, gw)).astype(np.float32)
    xs = np.linspace(0, gw - 1.001, w, dtype=np.float32)
    ys = np.linspace(0, gh - 1.001, h, dtype=np.float32)
    ix = xs.astype(np.int32)
    iy = ys.astype(np.int32)
    fx = smoothstep(xs - ix)[None, :]
    fy = smoothstep(ys - iy)[:, None]
    v00 = grid[iy[:, None], ix[None, :]]
    v10 = grid[iy[:, None], ix[None, :] + 1]
    v01 = grid[iy[:, None] + 1, ix[None, :]]
    v11 = grid[iy[:, None] + 1, ix[None, :] + 1]
    top = v00 * (1 - fx) + v10 * fx
    bot = v01 * (1 - fx) + v11 * fx
    return top * (1 - fy) + bot * fy


class World:
    def __init__(self, seed: int | None = None, size_key: str | None = None,
                 width: int | None = None, height: int | None = None):
        size_key = size_key if size_key in config.WORLD_SIZES else config.DEFAULT_WORLD_SIZE
        preset = config.WORLD_SIZES[size_key]
        self.size_key = size_key
        self.w = int(width or preset["w"])
        self.h = int(height or preset["h"])
        self.seed = seed if seed is not None else random.randrange(1, 2_000_000_000)
        self.tiles = [bytearray(self.w) for _ in range(self.h)]
        self.terrain = [int(self.h * config.WORLD_SURFACE_FRACTION)] * self.w
        self.biomes = [BIOME_FOREST] * self.w
        self.name = "Новый мир"
        self.spawn_x = (self.w // 2) * config.TILE
        self.spawn_y = 0
        self.beach_start: int | None = None
        self.beach_water_level: int | None = None
        self.beach_ocean_start: int | None = None
        self.generate()

    # ------------------------------------------------------------------ доступ
    def get(self, x: int, y: int) -> int:
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.tiles[y][x]
        return AIR

    def set(self, x: int, y: int, tile: int):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.tiles[y][x] = tile

    def is_solid(self, x: int, y: int) -> bool:
        if y < 0:
            return False
        if y >= self.h or x < 0 or x >= self.w:
            return True
        return TILES[self.tiles[y][x]].solid

    def is_lava(self, tx: int, ty: int) -> bool:
        return self.get(tx, ty) == LAVA

    def rect_collides(self, rect: pygame.Rect) -> bool:
        x0 = rect.left // config.TILE
        x1 = (rect.right - 1) // config.TILE
        y0 = rect.top // config.TILE
        y1 = (rect.bottom - 1) // config.TILE
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if self.is_solid(x, y):
                    return True
        return False

    def solid_rects(self, rect: pygame.Rect):
        x0 = max(0, rect.left // config.TILE)
        x1 = min(self.w - 1, (rect.right - 1) // config.TILE)
        y0 = max(0, rect.top // config.TILE)
        y1 = min(self.h - 1, (rect.bottom - 1) // config.TILE)
        for y in range(y0, y1 + 1):
            row = self.tiles[y]
            for x in range(x0, x1 + 1):
                if TILES[row[x]].solid:
                    yield pygame.Rect(x * config.TILE, y * config.TILE, config.TILE, config.TILE)

    def surface_y(self, x: int) -> int:
        x = max(0, min(self.w - 1, int(x)))
        return self.terrain[x]

    def depth_tiles(self, px: float, py: float) -> float:
        tx = max(0, min(self.w - 1, int(px // config.TILE)))
        return py / config.TILE - self.terrain[tx]

    def biome_at(self, px: float) -> int:
        tx = max(0, min(self.w - 1, int(px // config.TILE)))
        if 0 <= tx < len(self.biomes):
            return self.biomes[tx]
        return BIOME_FOREST

    def biome_name(self, px: float) -> str:
        return BIOME_NAMES.get(self.biome_at(px), "Неизвестные земли")

    def solid_mask(self, x: int, y: int) -> int:
        """Маска твёрдых соседей: 1 верх, 2 право, 4 низ, 8 лево."""
        mask = 0
        if self.is_solid(x, y - 1):
            mask |= 1
        if self.is_solid(x + 1, y):
            mask |= 2
        if self.is_solid(x, y + 1):
            mask |= 4
        if self.is_solid(x - 1, y):
            mask |= 8
        return mask

    def wall_kind(self, tx: int, ty: int) -> str:
        """Тип фоновой стены пещеры для текущей клетки."""
        depth = ty - self.terrain[max(0, min(self.w - 1, tx))]
        biome = self.biomes[tx] if 0 <= tx < len(self.biomes) else BIOME_FOREST
        if depth <= 6:
            if biome in (BIOME_DESERT, BIOME_BEACH):
                return "sand"
            if biome == BIOME_SNOW:
                return "snow"
            if biome == BIOME_CORRUPT:
                return "corrupt"
            return "dirt"
        if depth > 32:
            return "deep"
        if biome == BIOME_CORRUPT:
            return "corrupt"
        return "stone"

    def workbench_near(self, px: float, py: float, radius=5.0) -> bool:
        cx = int(px // config.TILE)
        cy = int(py // config.TILE)
        r = int(radius)
        for y in range(cy - r, cy + r + 1):
            if not (0 <= y < self.h):
                continue
            row = self.tiles[y]
            for x in range(cx - r, cx + r + 1):
                if 0 <= x < self.w and row[x] == WORKBENCH:
                    return True
        return False

    def first_air_above(self, x: int, y: int) -> int:
        y = max(0, min(self.h - 1, y))
        while y > 0 and not TILES[self.tiles[y][x]].solid:
            y -= 1
        return y

    # ------------------------------------------------------------------ физика
    def move_entity(self, ent, dt: float):
        """Двигает сущность с AABB-коллизиями и дружелюбным шагом на 1 тайл."""
        tile = config.TILE
        grounded_before = ent.on_ground
        ent.on_ground = False
        ent.stepped = False
        # по горизонтали
        ent.x += ent.vx * dt
        if ent.x < 0:
            ent.x = 0
            ent.vx = 0
        elif ent.x + ent.w > self.w * tile:
            ent.x = self.w * tile - ent.w
            ent.vx = 0
        rect = pygame.Rect(int(ent.x), int(ent.y), ent.w, ent.h)
        collisions = list(self.solid_rects(rect))
        step = int(getattr(ent, "step_height", 0))
        if collisions and step > 0 and grounded_before and ent.vy >= 0:
            # Плавный подъём на одну плитку: как автошаг в Terraria.
            lifted = pygame.Rect(int(ent.x), int(ent.y - step), ent.w, ent.h)
            if not self.rect_collides(lifted):
                ent.y -= step
                ent.stepped = True
                rect = lifted
                collisions = []
        for tr in collisions:
            if ent.vx > 0:
                ent.x = tr.left - ent.w
            elif ent.vx < 0:
                ent.x = tr.right
            else:
                continue
            ent.vx = 0
            rect.x = int(ent.x)

        # по вертикали
        ent.y += ent.vy * dt
        rect = pygame.Rect(int(ent.x), int(ent.y), ent.w, ent.h)
        for tr in self.solid_rects(rect):
            if ent.vy > 0:
                ent.y = tr.top - ent.h
                ent.vy = 0
                ent.on_ground = True
            elif ent.vy < 0:
                ent.y = tr.bottom
                ent.vy = 0
            rect.y = int(ent.y)
        if ent.y > self.h * tile + 400:
            ent.y = self.spawn_y
            ent.vy = 0

    def ground_below(self, px: float, py: float, max_distance=12) -> int:
        tx = max(0, min(self.w - 1, int(px // config.TILE)))
        start = max(0, int(py // config.TILE))
        for y in range(start, min(self.h, start + max_distance)):
            if self.is_solid(tx, y):
                return y
        return min(self.h - 1, start + max_distance)

    # ------------------------------------------------------------------ генерация
    def _generate_biomes(self, rng) -> np.ndarray:
        w = self.w
        biomes = np.full(w, BIOME_FOREST, dtype=np.uint8)
        # Биомы чередуются, но центральная зона всегда остаётся лесом.
        fractions = [0.0, 0.08, 0.22, 0.35, 0.44, 0.56, 0.68, 0.82, 0.92, 1.0]
        zones = [BIOME_SNOW, BIOME_FOREST, BIOME_DESERT, BIOME_FOREST, BIOME_FOREST,
                 BIOME_CORRUPT, BIOME_FOREST, BIOME_SNOW, BIOME_DESERT]
        edges = []
        for i, f in enumerate(fractions):
            jitter = 0 if i in (0, len(fractions) - 1) else int(rng.integers(-w // 80, w // 80 + 1))
            edges.append(max(0, min(w, int(f * w) + jitter)))
        edges[0] = 0
        edges[-1] = w
        for i, biome in enumerate(zones):
            if edges[i] < edges[i + 1]:
                biomes[edges[i]:edges[i + 1]] = biome
        # Небольшие вкрапления для живости.
        for _ in range(max(2, w // 500)):
            x = int(rng.integers(0, w))
            r = int(rng.integers(8, 24))
            biome = int(rng.choice((BIOME_FOREST, BIOME_DESERT, BIOME_SNOW, BIOME_CORRUPT)))
            biomes[max(0, x - r):min(w, x + r)] = biome
        sx = w // 2
        half = max(42, w // 36)
        biomes[max(0, sx - half):min(w, sx + half)] = BIOME_FOREST
        return biomes

    def generate(self):
        rng = np.random.default_rng(self.seed)
        w, h = self.w, self.h
        base = int(h * config.WORLD_SURFACE_FRACTION)
        amp = max(14.0, h * 0.075)
        self.biomes = [int(v) for v in self._generate_biomes(rng)]
        biomes_arr = np.asarray(self.biomes, dtype=np.uint8)

        # У каждого биома свой характер рельефа.
        height_f = _fbm1(w, rng, max(3, w // 220), 4)
        height_f = base + (height_f - 0.5) * 2.0 * amp
        detail = _fbm1(w, rng, max(11, w // 32), 2)
        height_f += (detail - 0.5) * max(3.0, h * 0.014)
        xs = np.arange(w, dtype=np.float32)
        dune = np.sin(xs * 0.11 + 1.7) * max(2.0, h * 0.008)
        ridge = (_fbm1(w, rng, max(5, w // 80), 3) - 0.5) * max(10.0, h * 0.035)
        height_f = np.where(biomes_arr == BIOME_DESERT, height_f + dune * 0.8, height_f)
        height_f = np.where(biomes_arr == BIOME_SNOW, height_f + ridge, height_f)
        height_f = np.where(biomes_arr == BIOME_CORRUPT,
                            height_f + (_fbm1(w, rng, max(7, w // 55), 2) - 0.5) * 10, height_f)
        height = np.clip(height_f, max(10, base - int(amp * 1.5)),
                         min(h - 45, base + int(amp * 1.7))).astype(np.int32)

        sx = w // 2
        flat = int(height[sx])
        for x in range(max(0, sx - 6), min(w, sx + 7)):
            height[x] = flat
        # Спавн — небольшая ровная терраса.
        for x in range(max(0, sx - 4), min(w, sx + 5)):
            height[x] = flat

        tiles = np.zeros((h, w), dtype=np.uint8)
        y_idx = np.arange(h)[:, None]
        heights = height[None, :]
        strata = y_idx - heights
        biome_col = biomes_arr[None, :]

        # Базовые слои.
        tiles[:] = AIR
        tiles[(strata > 0) & (strata <= 5)] = DIRT
        tiles[strata > 5] = STONE
        tiles[strata == 0] = GRASS

        forest = biome_col == BIOME_FOREST
        desert = biome_col == BIOME_DESERT
        snow = biome_col == BIOME_SNOW
        corrupt = biome_col == BIOME_CORRUPT

        # Пустыня: песок, песчаник, затем камень.
        tiles[desert & (strata >= 0) & (strata <= 5)] = SAND
        tiles[desert & (strata >= 6) & (strata <= 17)] = SANDSTONE
        tiles[desert & (strata >= 18)] = STONE
        tiles[desert & (strata == 0)] = SAND

        # Снежный биом: снежная шапка, мёрзлая земля и ледяные жилы.
        tiles[snow & (strata >= 0) & (strata <= 2)] = SNOW
        tiles[snow & (strata >= 3) & (strata <= 6)] = DIRT
        tiles[snow & (strata >= 7) & (strata <= 12)] = ICE
        tiles[snow & (strata >= 13)] = STONE

        # Багряные пустоши: тёмная почва и эбонит.
        tiles[corrupt & (strata >= 0)] = CORRUPT_STONE
        tiles[corrupt & (strata == 0)] = CORRUPT_GRASS
        tiles[corrupt & (strata >= 1) & (strata <= 4)] = DIRT

        # Лес — обычные слои (уже заданы выше), подчеркнём траву.
        tiles[forest & (strata == 0)] = GRASS
        tiles[h - 3:, :] = BEDROCK

        # Пещеры из шума. Считаем в float32, чтобы большой мир не съедал память.
        cave_noise = _noise2(w, h, 64, rng)
        cave_noise *= 0.58
        cave_noise += _noise2(w, h, 27, rng) * 0.31
        cave_noise += _noise2(w, h, 12, rng) * 0.11
        depth = y_idx - heights
        threshold = 0.605 - np.clip(depth, 0, 400) * 0.00055
        cave_mask = (cave_noise > threshold) & (depth > 5) & (y_idx < h - 4)
        tiles[cave_mask] = AIR
        del cave_noise, cave_mask

        # Червячные туннели.
        tunnel_count = max(16, min(120, w // 27))
        for _ in range(tunnel_count):
            x = int(rng.integers(5, w - 5))
            gy = int(height[x])
            y = int(rng.integers(gy + 10, min(h - 8, gy + max(20, h * 0.55))))
            if y <= gy + 8:
                continue
            angle = rng.uniform(0, math.tau)
            radius = rng.uniform(1.2, 2.7)
            for _step in range(int(rng.integers(70, 250))):
                angle += rng.uniform(-0.5, 0.5)
                if rng.random() < 0.08:
                    angle = rng.uniform(0, math.tau)
                x2 = int(round(x))
                y2 = int(round(y))
                rr = int(radius + 1)
                for oy in range(-rr, rr + 1):
                    for ox in range(-rr, rr + 1):
                        if ox * ox + oy * oy <= radius * radius:
                            tx, ty = x2 + ox, y2 + oy
                            if 4 < tx < w - 4 and 8 < ty < h - 4:
                                if ty > height[tx] + 5:
                                    tiles[ty, tx] = AIR
                x += math.cos(angle) * 1.7
                y += math.sin(angle) * 1.15
                if not (4 < x < w - 4 and 10 < y < h - 5):
                    break
                if y < height[int(x)] + 6:
                    y += 2.0

        # Руды. Количество зависит от площади мира, но рост слегка сглажен.
        area_factor = (w * h) / 93600.0
        ore_scale = area_factor ** 0.82

        def vein(tile_id, count, min_depth, max_depth, size):
            for _ in range(max(1, int(count * ore_scale))):
                tx = int(rng.integers(3, w - 3))
                ty = int(rng.integers(0, h - 3))
                depth_v = ty - height[tx]
                if not (min_depth <= depth_v <= max_depth):
                    continue
                if tiles[ty, tx] != STONE:
                    continue
                for _j in range(int(rng.integers(size // 2 + 1, size + 1))):
                    if 2 < tx < w - 2 and 2 < ty < h - 3 and tiles[ty, tx] == STONE:
                        tiles[ty, tx] = tile_id
                    tx += int(rng.integers(-1, 2))
                    ty += int(rng.integers(-1, 2))

        vein(COPPER, 300, 3, int(h * 0.50), 8)
        vein(IRON, 230, 10, int(h * 0.68), 7)
        vein(GOLD_TILE, 110, 22, int(h * 0.84), 5)
        vein(CRYSTAL, 80, 28, int(h * 0.96), 4)
        vein(ICE, 90, 6, int(h * 0.45), 10)
        vein(SANDSTONE, 60, 10, int(h * 0.36), 8)
        vein(BRICK, 0, 0, 0, 0)

        # Кристаллы жизни в пещерах.
        crystal_goal = max(16, w // 45)
        placed = 0
        attempts = 0
        while placed < crystal_goal and attempts < crystal_goal * 110:
            attempts += 1
            x = int(rng.integers(6, w - 6))
            top = int(height[x] + 8)
            if top >= h - 8:
                continue
            y = int(rng.integers(top, h - 8))
            if tiles[y, x] == AIR and tiles[y + 1, x] != AIR and tiles[y + 1, x] != BEDROCK:
                tiles[y, x] = LIFE_CRYSTAL
                placed += 1
                if placed < crystal_goal and rng.random() < 0.3:
                    for dx in (-1, 1):
                        if tiles[y, x + dx] == AIR and tiles[y + 1, x + dx] != AIR:
                            tiles[y, x + dx] = LIFE_CRYSTAL
                            placed += 1
                            break

        # Небольшие лавовые лужи в глубоких пещерах.
        lava_goal = max(8, w // 90)
        lava_placed = 0
        for _ in range(lava_goal * 25):
            if lava_placed >= lava_goal:
                break
            x = int(rng.integers(5, w - 5))
            y = int(rng.integers(int(h * 0.52), h - 6))
            if tiles[y, x] == AIR and TILES[tiles[y + 1, x]].solid and tiles[y + 1, x] != BEDROCK:
                for dx in range(-1, 2):
                    if 0 <= x + dx < w and tiles[y, x + dx] == AIR:
                        tiles[y, x + dx] = LAVA
                lava_placed += 1

        # Ловушки-валуны на полу пещер.
        boulder_goal = max(20, w // 30)
        boulders_placed = 0
        for _ in range(boulder_goal * 40):
            if boulders_placed >= boulder_goal:
                break
            x = int(rng.integers(8, w - 8))
            y = int(rng.integers(int(height[x]) + 9, h - 7))
            if abs(x - sx) < 12:
                continue
            if tiles[y, x] != AIR or not TILES[tiles[y + 1, x]].solid:
                continue
            if tiles[y + 1, x] in (BEDROCK, LAVA):
                continue
            b = self._pick_boulder_type(rng, int(biomes_arr[x]), y, h)
            tiles[y, x] = b
            boulders_placed += 1

        # Границы мира.
        for x in (0, 1, w - 2, w - 1):
            col = np.where((y_idx[:, 0] >= height[x] - 1), BEDROCK, tiles[:, x])
            tiles[:, x] = col

        self.tiles = [bytearray(row) for row in tiles]
        self.terrain = [int(height[x]) for x in range(w)]

        # Растительность и финальный берег.
        self._grow_trees(rng, sx)
        self.build_beach(rng)

        self.spawn_x = sx * config.TILE + config.TILE // 2
        ground = self.terrain[sx] * config.TILE
        self.spawn_y = ground
        # Расчистить площадку для героя и проводника.
        for dx in range(-3, 4):
            for dy in range(1, 5):
                self.set(sx + dx, self.terrain[sx] - dy, AIR)

    def _pick_boulder_type(self, rng, biome, y, h):
        depth_frac = y / max(1, h)
        weights = {
            BOULDER: 35,
            BOULDER_BOUNCY: 12,
            BOULDER_LIFE: 5,
            BOULDER_LAVA: 10 if depth_frac > 0.48 else 2,
            BOULDER_SPIDER: 12,
            BOULDER_RAINBOW: 3,
            BOULDER_GHOST: 6 if biome == BIOME_CORRUPT else 3,
            BOULDER_ICE: 16 if biome == BIOME_SNOW else 3,
        }
        if biome == BIOME_DESERT:
            weights[BOULDER_BOUNCY] += 10
        if biome == BIOME_CORRUPT:
            weights[BOULDER_GHOST] += 8
            weights[BOULDER_SPIDER] += 8
        if biome == BIOME_SNOW:
            weights[BOULDER_ICE] += 14
        if depth_frac > 0.7:
            weights[BOULDER_LAVA] += 10
            weights[BOULDER_RAINBOW] += 4
        keys = list(weights)
        return int(rng.choice(keys, p=np.asarray([weights[k] for k in keys], dtype=float) /
                              sum(weights.values())))

    def _grow_trees(self, rng, spawn_x):
        w, h = self.w, self.h
        last = -10
        for x in range(4, w - 5):
            if abs(x - spawn_x) < 7:
                continue
            if x - last < 4:
                continue
            biome = self.biomes[x] if x < len(self.biomes) else BIOME_FOREST
            if biome == BIOME_DESERT:
                if rng.random() > 0.028:
                    continue
                y = self.terrain[x]
                if not (2 < y < h - 1) or self.tiles[y][x] != SAND:
                    continue
                trunk = int(rng.integers(2, 5))
                for i in range(trunk):
                    yy = y - 1 - i
                    if 0 <= yy < h:
                        self.tiles[yy][x] = CACTUS_PLANT
                last = x
                continue
            chance = 0.10 if biome == BIOME_FOREST else 0.075
            if rng.random() > chance:
                continue
            y = self.terrain[x]
            if not (0 <= y < h):
                continue
            top_tile = self.tiles[y][x]
            if top_tile not in (GRASS, SNOW, CORRUPT_GRASS):
                continue
            trunk = int(rng.integers(4, 10 if biome == BIOME_FOREST else 8))
            top = y - 1
            if top - trunk < 3:
                continue
            trunk_tile = TREE_TRUNK if biome != BIOME_CORRUPT else TREE_DEAD
            for i in range(trunk):
                yy = top - i
                if 0 <= yy < h:
                    self.tiles[yy][x] = trunk_tile
            canopy_y = top - trunk + 1
            radius = int(rng.integers(2, 4))
            leaves = LEAVES
            if biome == BIOME_SNOW:
                leaves = PINE_LEAVES
            elif biome == BIOME_CORRUPT:
                leaves = CORRUPT_LEAVES
            if biome == BIOME_SNOW:
                # Узкая еловая крона.
                for layer in range(4):
                    half = max(1, radius - layer // 2)
                    yy = canopy_y - layer * 2
                    for dx in range(-half, half + 1):
                        for dy in (0, 1):
                            tx, ty = x + dx, yy + dy
                            if 0 <= tx < w and 4 <= ty < h and self.tiles[ty][tx] == AIR:
                                if rng.random() < 0.9:
                                    self.tiles[ty][tx] = leaves
            else:
                for dy in range(-radius, radius + 1):
                    for dx in range(-radius - 1, radius + 2):
                        if dx * dx + dy * dy * 1.4 <= radius * radius + 1.5 and rng.random() < 0.88:
                            tx, ty = x + dx, canopy_y + dy
                            if 0 <= tx < w and 4 <= ty < h and self.tiles[ty][tx] == AIR:
                                self.tiles[ty][tx] = leaves
            last = x

    # ------------------------------------------------------------------ пляж
    def build_beach(self, rng=None):
        """Создаёт песчаный берег и океан у правой границы мира."""
        if rng is None:
            rng = np.random.default_rng(abs(int(self.seed) ^ 0xB3AC4))
        w, h = self.w, self.h
        if w < 110 or h < 90:
            return
        edge = w - 3
        width = max(52, min(100, w // 7))
        start = max(24, edge - width)
        samples = [self.terrain[x] for x in range(start, min(start + 10, edge))]
        shore = int(round(sum(samples) / max(1, len(samples))))
        shore = max(18, min(h - 42, shore))
        water_level = shore + 2
        ocean_start = edge - max(17, width // 3)
        ocean_start = max(start + 22, min(edge - 10, ocean_start))

        # Плавный спуск от соседнего биома к песчаной террасе.
        blend = 12
        for i, x in enumerate(range(max(2, start - blend), start)):
            old = self.terrain[x]
            t = (i + 1) / (blend + 1)
            new = int(round(old * (1.0 - t) + shore * t))
            new = max(12, min(h - 8, new))
            for y in range(h):
                if y < new:
                    tile = AIR
                elif y < new + 6:
                    tile = SAND
                elif y < new + 16:
                    tile = SANDSTONE
                elif y >= h - 3:
                    tile = BEDROCK
                else:
                    tile = STONE
                self.tiles[y][x] = tile
            self.terrain[x] = new
            self.biomes[x] = BIOME_BEACH

        for x in range(start, w - 2):
            if x < ocean_start:
                t = (x - start) / max(1, ocean_start - start)
                surface = int(round(shore + t * (water_level - shore)))
                surface += int(round(math.sin(x * 0.2) * 0.7))
            else:
                t = (x - ocean_start) / max(1, edge - ocean_start)
                surface = int(round(water_level + 1 + t * 4))
            surface = max(12, min(h - 8, surface))
            for y in range(h):
                if y < surface:
                    tile = AIR
                elif y < surface + 6:
                    tile = SAND
                elif y < surface + 16:
                    tile = SANDSTONE
                elif y >= h - 3:
                    tile = BEDROCK
                else:
                    tile = STONE
                self.tiles[y][x] = tile
            if x >= ocean_start:
                for y in range(water_level, surface):
                    self.tiles[y][x] = WATER
            self.terrain[x] = surface
            self.biomes[x] = BIOME_BEACH

        self.beach_start = start
        self.beach_water_level = water_level
        self.beach_ocean_start = ocean_start
        self._plant_palms(rng, start, ocean_start)
        self._build_pier(rng)
        self._beach_props(rng)

    def ensure_beach(self):
        if self.beach_start is None:
            self.build_beach(np.random.default_rng(abs(int(self.seed) ^ 0xB3AC4)))

    def _plant_palms(self, rng, start, ocean_start):
        dry_start = start + 7
        dry_end = ocean_start - 5
        span = dry_end - dry_start
        if span < 12:
            return
        count = max(3, min(8, span // 14))
        for i in range(count):
            target = dry_start + int((i + 0.45) * span / count) + int(rng.integers(-2, 3))
            for dx in range(0, 8):
                placed = False
                for x in (target + dx, target - dx):
                    if not (dry_start <= x < dry_end):
                        continue
                    gy = self.terrain[x]
                    if gy < 4 or gy >= self.h - 2 or self.tiles[gy][x] != SAND:
                        continue
                    if any(self.tiles[gy - d][x] != AIR for d in range(1, 3)):
                        continue
                    trunk = int(rng.integers(5, 10))
                    if gy - trunk - 4 < 2:
                        continue
                    for j in range(trunk):
                        self.tiles[gy - 1 - j][x] = PALM_TRUNK
                    canopy = gy - trunk - 1
                    # Плотная крона: несколько ярусов вай.
                    for dy, half in ((-2, 1), (-1, 2), (0, 3), (1, 2)):
                        for ddx in range(-half, half + 1):
                            tx, ty = x + ddx, canopy + dy
                            if 0 <= tx < self.w and 3 <= ty < self.h - 2:
                                if self.tiles[ty][tx] == AIR and rng.random() < 0.99:
                                    self.tiles[ty][tx] = PALM_LEAVES
                    # Свисающие вниз вайи, соединённые с кроной.
                    for side in (-1, 1):
                        for ddx, ddy in ((3, 1), (4, 1), (4, 2), (5, 2), (5, 3), (6, 3)):
                            tx, ty = x + side * ddx, canopy + ddy
                            if 0 <= tx < self.w and 3 <= ty < self.h - 2:
                                if self.tiles[ty][tx] == AIR and rng.random() < 0.92:
                                    self.tiles[ty][tx] = PALM_LEAVES
                    placed = True
                    break
                if placed:
                    break

    def _build_pier(self, rng):
        if self.beach_start is None or self.beach_water_level is None:
            return
        w, h = self.w, self.h
        y = self.beach_water_level
        if y < 3 or y >= h - 4:
            return
        start = max(self.beach_start + 12, (self.beach_ocean_start or w - 20) - 4)
        end = w - 7
        if end - start < 10:
            return
        for x in range(start, end):
            if self.tiles[y][x] == AIR or self.tiles[y][x] == WATER:
                self.tiles[y][x] = PLANKS
        for x in range(start + 2, end - 1, 7):
            yy = y + 1
            steps = 0
            while yy < h - 3 and self.tiles[yy][x] in (AIR, WATER) and steps < 11:
                self.tiles[yy][x] = WOOD
                yy += 1
                steps += 1
        for x in range(start + 1, end - 1, max(6, (end - start) // 3)):
            if self.tiles[y - 1][x] == AIR:
                self.tiles[y - 1][x] = TORCH
        # Факел на песке у начала мостков.
        for dx in range(-2, 3):
            x = start + dx
            if 0 <= x < w:
                gy = self.terrain[x]
                if self.tiles[gy][x] == SAND and self.tiles[gy - 1][x] == AIR:
                    self.tiles[gy - 1][x] = TORCH
                    break

    def _beach_props(self, rng):
        if self.beach_start is None:
            return
        dry_start = self.beach_start + 9
        dry_end = (self.beach_ocean_start or self.w - 20) - 7
        if dry_end <= dry_start:
            return
        # Пара выброшенных на берег брёвен.
        for _ in range(2):
            x = int(rng.integers(dry_start, max(dry_start + 1, dry_end - 2)))
            gy = self.terrain[x]
            if gy < 3 or gy + 1 >= self.h:
                continue
            if self.tiles[gy][x] != SAND or self.tiles[gy - 1][x] != AIR:
                continue
            self.tiles[gy - 1][x] = DEAD_WOOD
            if x + 1 < self.w and self.tiles[gy - 1][x + 1] == AIR:
                self.tiles[gy - 1][x + 1] = DEAD_WOOD

    def beach_npc_spots(self):
        """Три ровных места на сухом песке для финальной сцены."""
        if self.beach_start is None:
            return []
        dry_start = self.beach_start + 10
        dry_end = (self.beach_ocean_start or self.w - 24) - 9
        if dry_end - dry_start < 18:
            return []
        spots = []
        for fraction in (0.36, 0.45, 0.54):
            target = int(dry_start + (dry_end - dry_start) * fraction)
            found = None
            for dx in range(0, 20):
                for x in (target + dx, target - dx):
                    if not (dry_start <= x <= dry_end):
                        continue
                    gy = self.terrain[x]
                    if gy < 4 or gy >= self.h - 3:
                        continue
                    if self.tiles[gy][x] != SAND:
                        continue
                    if any(self.tiles[gy - d][x] != AIR for d in range(1, 4)):
                        continue
                    found = (x * config.TILE + config.TILE // 2, gy * config.TILE)
                    break
                if found:
                    break
            if found:
                spots.append(found)
        return spots

    # ------------------------------------------------------------------ прочее
    def tile_variant(self, x: int, y: int, count=3) -> int:
        return hash2(x, y) % count

    def to_data(self) -> dict:
        return {
            "seed": self.seed,
            "w": self.w,
            "h": self.h,
            "size": self.size_key,
            "name": getattr(self, "name", "Мир"),
            "biomes": rle_encode([self.biomes]),
            "spawn": [self.spawn_x, self.spawn_y],
            "beach": ([self.beach_start, self.beach_water_level, self.beach_ocean_start]
                      if self.beach_start is not None else None),
            "tiles": rle_encode(self.tiles),
        }

    @classmethod
    def from_data(cls, data: dict) -> "World":
        obj = cls.__new__(cls)
        obj.w = int(data.get("w", config.WORLD_W))
        obj.h = int(data.get("h", config.WORLD_H))
        obj.seed = int(data.get("seed", 1))
        obj.size_key = str(data.get("size", "custom"))
        obj.name = str(data.get("name", "Сохранённый мир"))
        obj.tiles = rle_decode(data["tiles"], obj.w, obj.h)
        biome_data = data.get("biomes")
        if biome_data:
            row = rle_decode(biome_data, obj.w, 1)[0]
            obj.biomes = list(row)
        else:
            obj.biomes = [BIOME_FOREST] * obj.w
        obj.spawn_x, obj.spawn_y = data.get("spawn", [obj.w * config.TILE // 2, 0])
        obj.terrain = []
        for x in range(obj.w):
            ty = 0
            while ty < obj.h:
                t = obj.tiles[ty][x]
                if TILES[t].solid and t not in (WOOD, LEAVES, CACTUS, DEAD_WOOD,
                                                PINE_LEAVES, CORRUPT_LEAVES):
                    break
                ty += 1
            obj.terrain.append(ty)
        # Старые сохранения хранили стволы как строительную древесину.
        # Переводим их в проходимую природную растительность.
        obj._migrate_legacy_vegetation()
        beach = data.get("beach")
        if isinstance(beach, (list, tuple)) and len(beach) >= 3:
            obj.beach_start, obj.beach_water_level, obj.beach_ocean_start = (
                int(beach[0]), int(beach[1]), int(beach[2]))
        else:
            obj.beach_start = None
            obj.beach_water_level = None
            obj.beach_ocean_start = None
            # Старое сохранение: определяем берег по биомам, если он уже есть.
            beach_cols = [x for x, b in enumerate(obj.biomes) if b == BIOME_BEACH]
            if beach_cols:
                obj.beach_start = min(beach_cols)
                for x in beach_cols:
                    for y in range(obj.h):
                        if obj.tiles[y][x] == WATER:
                            obj.beach_ocean_start = x
                            obj.beach_water_level = y
                            break
                    if obj.beach_ocean_start is not None:
                        break
        return obj

    def _migrate_legacy_vegetation(self):
        leaf_tiles = (LEAVES, PINE_LEAVES, CORRUPT_LEAVES)
        for x in range(self.w):
            ground = self.terrain[x]
            y = 0
            while y < ground:
                tile = self.tiles[y][x]
                if tile == CACTUS:
                    self.tiles[y][x] = CACTUS_PLANT
                    y += 1
                    continue
                if tile not in (WOOD, DEAD_WOOD):
                    y += 1
                    continue
                start = y
                while y < ground and self.tiles[y][x] in (WOOD, DEAD_WOOD):
                    y += 1
                has_canopy = False
                for yy in range(max(0, start - 4), min(self.h, y + 4)):
                    row = self.tiles[yy]
                    if any(row[xx] in leaf_tiles
                           for xx in range(max(0, x - 4), min(self.w, x + 5))):
                        has_canopy = True
                        break
                if has_canopy:
                    for yy in range(start, y):
                        self.tiles[yy][x] = (TREE_TRUNK if self.tiles[yy][x] == WOOD
                                             else TREE_DEAD)

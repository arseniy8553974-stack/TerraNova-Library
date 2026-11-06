# -*- coding: utf-8 -*-
"""Общие константы, тайлы и предметы игры."""
from __future__ import annotations

import os
from dataclasses import dataclass

# ---------------------------------------------------------------- пути
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSET_DIR = os.path.join(BASE_DIR, "assets")
AUDIO_DIR = os.path.join(ASSET_DIR, "audio")
SFX_DIR = os.path.join(AUDIO_DIR, "sfx")
SAVE_DIR = os.path.join(BASE_DIR, "saves")
SAVE_PATH = os.path.join(SAVE_DIR, "world.json")
NETWORK_SAVE_PATH = os.path.join(SAVE_DIR, "lan_world.json")
SETTINGS_PATH = os.path.join(SAVE_DIR, "settings.json")

for _d in (ASSET_DIR, AUDIO_DIR, SFX_DIR, SAVE_DIR):
    os.makedirs(_d, exist_ok=True)

# ---------------------------------------------------------------- экран
WIDTH = 1280
HEIGHT = 720
FPS = 60
TILE = 32
DAY_LENGTH = 360.0          # полный цикл день+ночь, секунд
PLAYER_REACH = 6.0          # радиус взаимодействия в тайлах
TITLE = "TERRA NOVA"
SUBTITLE = "Хроники расколотого мира"
NETWORK_PORT = 47831

# ---------------------------------------------------------------- размеры мира
# Размеры заданы в тайлах. Для комфортной игры по умолчанию выбран средний мир;
# большой мир создаётся заметно дольше и требует больше оперативной памяти.
WORLD_SIZES = {
    "small": {
        "name": "Малая",
        "w": 1200, "h": 360,
        "desc": "Быстрый старт, близкие биомы и короткие путешествия.",
    },
    "medium": {
        "name": "Средняя",
        "w": 2400, "h": 600,
        "desc": "Золотая середина: простор, ресурсы и время на исследование.",
    },
    "large": {
        "name": "Большая",
        "w": 4200, "h": 1200,
        "desc": "Максимальный простор, дальние биомы и долгие экспедиции.",
    },
}
DEFAULT_WORLD_SIZE = "medium"
WORLD_W = WORLD_SIZES[DEFAULT_WORLD_SIZE]["w"]
WORLD_H = WORLD_SIZES[DEFAULT_WORLD_SIZE]["h"]
WORLD_SURFACE_FRACTION = 0.34

# ---------------------------------------------------------------- биомы
BIOME_FOREST = 0
BIOME_DESERT = 1
BIOME_SNOW = 2
BIOME_CORRUPT = 3
BIOME_BEACH = 4
BIOME_NAMES = {
    BIOME_FOREST: "Изумрудный лес",
    BIOME_DESERT: "Золотые пески",
    BIOME_SNOW: "Снежные пики",
    BIOME_CORRUPT: "Багряные пустоши",
    BIOME_BEACH: "Лазурный берег",
}
BIOME_SHORT = {
    BIOME_FOREST: "Лес",
    BIOME_DESERT: "Пустыня",
    BIOME_SNOW: "Тундра",
    BIOME_CORRUPT: "Пустоши",
    BIOME_BEACH: "Пляж",
}
BIOME_TINTS = {
    BIOME_FOREST: (74, 122, 72),
    BIOME_DESERT: (193, 150, 82),
    BIOME_SNOW: (130, 178, 207),
    BIOME_CORRUPT: (129, 73, 134),
    BIOME_BEACH: (255, 177, 117),
}

# ---------------------------------------------------------------- персонаж
SKIN_TONES = [
    (238, 196, 154), (226, 178, 136), (205, 151, 108),
    (171, 118, 83), (128, 84, 60), (92, 62, 48),
]
HAIR_COLORS = [
    (72, 47, 36), (36, 30, 34), (131, 83, 47), (194, 145, 71),
    (156, 59, 51), (75, 106, 131), (198, 193, 174), (91, 64, 116),
]
SHIRT_COLORS = [
    (52, 124, 137), (160, 69, 63), (72, 110, 172), (114, 132, 65),
    (117, 78, 139), (193, 142, 61), (69, 129, 102), (174, 98, 141),
]
PANTS_COLORS = [
    (57, 65, 95), (73, 61, 47), (52, 83, 72), (91, 57, 71),
    (100, 84, 57), (47, 53, 66),
]
HAIR_STYLE_COUNT = 4
DEFAULT_APPEARANCE = {
    "skin": 1, "hair": 0, "shirt": 0, "pants": 0, "hair_style": 0,
}

# ---------------------------------------------------------------- палитра
WHITE = (245, 242, 230)
CREAM = (238, 223, 190)
GOLD = (240, 197, 93)
GOLD_DARK = (176, 128, 44)
BROWN_DARK = (43, 30, 24)
BROWN = (79, 55, 39)
BROWN_LIGHT = (122, 88, 58)
PANEL = (31, 25, 26)
PANEL_LIGHT = (54, 43, 38)
RED = (214, 69, 69)
GREEN = (112, 196, 92)
BLUE = (94, 164, 214)
PURPLE = (170, 110, 214)
GREY = (150, 148, 140)
DARK = (14, 12, 16)

RARITY_COLORS = {
    0: (220, 214, 198),
    1: (126, 205, 118),
    2: (105, 170, 235),
    3: (187, 122, 235),
    4: (240, 190, 80),
}


# ---------------------------------------------------------------- тайлы
AIR = 0
DIRT = 1
GRASS = 2
STONE = 3
WOOD = 4
LEAVES = 5
COPPER = 6
IRON = 7
GOLD_TILE = 8
PLANKS = 9
WORKBENCH = 10
TORCH = 11
BRICK = 12
BEDROCK = 13
CRYSTAL = 14
LIFE_CRYSTAL = 15
SAND = 16
SANDSTONE = 17
SNOW = 18
ICE = 19
CORRUPT_GRASS = 20
CORRUPT_STONE = 21
CACTUS = 22
DEAD_WOOD = 23
GLASS = 24
SNOW_BRICK = 25
SANDSTONE_BRICK = 26
BOULDER = 27
BOULDER_BOUNCY = 28
BOULDER_LIFE = 29
BOULDER_LAVA = 30
BOULDER_SPIDER = 31
BOULDER_RAINBOW = 32
BOULDER_GHOST = 33
BOULDER_ICE = 34
LAVA = 35
PINE_LEAVES = 36
CORRUPT_LEAVES = 37
# Природная растительность: по ней можно ходить, но её всё ещё можно срубить.
TREE_TRUNK = 38
TREE_DEAD = 39
CACTUS_PLANT = 40
WATER = 41
PALM_TRUNK = 42
PALM_LEAVES = 43
LEAF_TILES = (LEAVES, PINE_LEAVES, CORRUPT_LEAVES, PALM_LEAVES)

BOULDER_TILES = {
    BOULDER: "normal",
    BOULDER_BOUNCY: "bouncy",
    BOULDER_LIFE: "life",
    BOULDER_LAVA: "lava",
    BOULDER_SPIDER: "spider",
    BOULDER_RAINBOW: "rainbow",
    BOULDER_GHOST: "ghost",
    BOULDER_ICE: "ice",
}


@dataclass(frozen=True)
class TileDef:
    name: str
    solid: bool
    hardness: float          # 0 = не разрушается
    drop: str | None
    light: float
    color: tuple[int, int, int]


TILES: dict[int, TileDef] = {
    AIR: TileDef("воздух", False, 0.0, None, 0.0, (0, 0, 0)),
    DIRT: TileDef("земля", True, 0.35, "dirt", 0.0, (121, 84, 55)),
    GRASS: TileDef("трава", True, 0.35, "dirt", 0.0, (101, 157, 70)),
    STONE: TileDef("камень", True, 0.85, "stone", 0.0, (100, 100, 112)),
    WOOD: TileDef("древесина", True, 0.55, "wood", 0.0, (104, 74, 46)),
    LEAVES: TileDef("листва", False, 0.12, None, 0.0, (64, 123, 57)),
    COPPER: TileDef("медь", True, 1.05, "copper_ore", 0.0, (152, 102, 74)),
    IRON: TileDef("железо", True, 1.40, "iron_ore", 0.0, (133, 130, 128)),
    GOLD_TILE: TileDef("золото", True, 1.90, "gold_ore", 0.0, (160, 133, 72)),
    PLANKS: TileDef("доски", True, 0.45, "planks", 0.0, (154, 112, 69)),
    WORKBENCH: TileDef("верстак", False, 0.40, "workbench", 0.0, (130, 91, 55)),
    TORCH: TileDef("факел", False, 0.08, "torch", 1.0, (238, 172, 70)),
    BRICK: TileDef("кирпич", True, 1.15, "brick", 0.0, (112, 100, 97)),
    BEDROCK: TileDef("порода", True, 0.0, None, 0.0, (47, 44, 53)),
    CRYSTAL: TileDef("кристалл", True, 2.10, "crystal", 0.45, (155, 107, 203)),
    LIFE_CRYSTAL: TileDef("кристалл жизни", False, 1.20, "life_crystal", 0.9, (231, 104, 152)),
    SAND: TileDef("песок", True, 0.28, "sand", 0.0, (211, 183, 119)),
    SANDSTONE: TileDef("песчаник", True, 0.75, "sandstone", 0.0, (181, 143, 88)),
    SNOW: TileDef("снег", True, 0.24, "snow", 0.0, (226, 235, 241)),
    ICE: TileDef("лёд", True, 0.70, "ice", 0.0, (157, 205, 229)),
    CORRUPT_GRASS: TileDef("порченая трава", True, 0.42, "corrupt_stone", 0.0, (104, 76, 112)),
    CORRUPT_STONE: TileDef("эбонит", True, 1.00, "corrupt_stone", 0.0, (77, 64, 85)),
    CACTUS: TileDef("кактус", True, 0.32, "cactus", 0.0, (88, 143, 78)),
    DEAD_WOOD: TileDef("сухое дерево", True, 0.45, "dead_wood", 0.0, (91, 75, 67)),
    GLASS: TileDef("стекло", True, 0.32, "glass", 0.0, (176, 217, 222)),
    SNOW_BRICK: TileDef("снежный кирпич", True, 0.80, "snow_brick", 0.0, (188, 213, 226)),
    SANDSTONE_BRICK: TileDef("песчаный кирпич", True, 1.05, "sandstone_brick", 0.0, (192, 157, 96)),
    BOULDER: TileDef("валун", True, 1.10, None, 0.0, (103, 99, 105)),
    BOULDER_BOUNCY: TileDef("прыгучий валун", True, 1.10, None, 0.0, (137, 111, 93)),
    BOULDER_LIFE: TileDef("валун-кристалл жизни", True, 1.25, None, 0.12, (171, 87, 121)),
    BOULDER_LAVA: TileDef("лавовый валун", True, 1.35, None, 0.3, (151, 76, 49)),
    BOULDER_SPIDER: TileDef("паучий валун", True, 1.10, None, 0.0, (104, 88, 104)),
    BOULDER_RAINBOW: TileDef("радужный валун", True, 1.20, None, 0.22, (154, 126, 185)),
    BOULDER_GHOST: TileDef("призрачный валун", True, 1.15, None, 0.25, (129, 163, 176)),
    BOULDER_ICE: TileDef("ледяной валун", True, 1.20, None, 0.05, (177, 218, 232)),
    LAVA: TileDef("лава", False, 0.0, None, 1.0, (229, 100, 40)),
    PINE_LEAVES: TileDef("хвоя", False, 0.14, None, 0.0, (50, 96, 79)),
    CORRUPT_LEAVES: TileDef("порченая листва", False, 0.13, None, 0.0, (91, 59, 103)),
    TREE_TRUNK: TileDef("ствол дерева", False, 0.55, "wood", 0.0, (106, 76, 47)),
    TREE_DEAD: TileDef("сухой ствол", False, 0.45, "dead_wood", 0.0, (91, 75, 67)),
    CACTUS_PLANT: TileDef("стебель кактуса", False, 0.32, "cactus", 0.0, (88, 143, 78)),
    WATER: TileDef("вода", False, 0.0, None, 0.0, (53, 126, 181)),
    PALM_TRUNK: TileDef("ствол пальмы", False, 0.45, "wood", 0.0, (128, 91, 56)),
    PALM_LEAVES: TileDef("пальмовые листья", False, 0.12, None, 0.0, (72, 154, 102)),
}


# ---------------------------------------------------------------- предметы
@dataclass(frozen=True)
class ItemDef:
    id: str
    name: str
    kind: str                       # block / material / consumable / summon
    tile: int | None = None
    desc: str = ""
    heal: int = 0
    max_hp: int = 0
    rarity: int = 0


ITEMS: dict[str, ItemDef] = {
    "dirt": ItemDef("dirt", "Земля", "block", DIRT, "Мягкая земля. Основа всего.", rarity=0),
    "stone": ItemDef("stone", "Камень", "block", STONE, "Прочный камень для построек.", rarity=0),
    "wood": ItemDef("wood", "Древесина", "block", WOOD, "Из неё получаются доски.", rarity=0),
    "planks": ItemDef("planks", "Доски", "block", PLANKS, "Обработанная древесина.", rarity=0),
    "brick": ItemDef("brick", "Каменный кирпич", "block", BRICK, "Красивая кладка для дома.", rarity=1),
    "workbench": ItemDef("workbench", "Верстак", "block", WORKBENCH,
                         "Рядом с ним доступны сложные рецепты.", rarity=1),
    "torch": ItemDef("torch", "Факел", "block", TORCH, "Освещает пещеры.", rarity=0),
    "copper_ore": ItemDef("copper_ore", "Медная руда", "block", COPPER, "Мягкий металл.", rarity=1),
    "iron_ore": ItemDef("iron_ore", "Железная руда", "block", IRON, "Из неё куют оружие.", rarity=1),
    "gold_ore": ItemDef("gold_ore", "Золотая руда", "block", GOLD_TILE, "Редкий блестящий металл.", rarity=2),
    "crystal": ItemDef("crystal", "Кристалл", "block", CRYSTAL,
                       "Светится в темноте. Нужен для короны.", rarity=2),
    "sand": ItemDef("sand", "Песок", "block", SAND, "Тёплый песок пустыни.", rarity=0),
    "sandstone": ItemDef("sandstone", "Песчаник", "block", SANDSTONE, "Плотный камень пустыни.", rarity=0),
    "snow": ItemDef("snow", "Снег", "block", SNOW, "Мягкий снег снежных пиков.", rarity=0),
    "ice": ItemDef("ice", "Лёд", "block", ICE, "Скользкий и холодный.", rarity=0),
    "corrupt_stone": ItemDef("corrupt_stone", "Эбонит", "block", CORRUPT_STONE,
                             "Тёмный камень Багряных пустошей.", rarity=1),
    "cactus": ItemDef("cactus", "Кактус", "block", CACTUS, "Колючее растение пустыни.", rarity=0),
    "dead_wood": ItemDef("dead_wood", "Сухое дерево", "block", DEAD_WOOD,
                         "Искривлённая древесина пустошей.", rarity=0),
    "glass": ItemDef("glass", "Стекло", "block", GLASS, "Пропускает свет.", rarity=1),
    "snow_brick": ItemDef("snow_brick", "Снежный кирпич", "block", SNOW_BRICK,
                          "Морозная кладка для северных крепостей.", rarity=1),
    "sandstone_brick": ItemDef("sandstone_brick", "Песчаный кирпич", "block", SANDSTONE_BRICK,
                               "Тёплая кладка для пустынных дворцов.", rarity=1),
    "gel": ItemDef("gel", "Слизь", "material", None, "Липкая субстанция слизней.", rarity=0),
    "slime_core": ItemDef("slime_core", "Ядро слизи", "material", None,
                          "Сердце Короля слизи. Нужно для Печати Бездны.", rarity=3),
    "life_crystal": ItemDef("life_crystal", "Кристалл жизни", "consumable", None,
                            "Увеличивает максимальный запас здоровья на 20.", max_hp=20, rarity=3),
    "heal_potion": ItemDef("heal_potion", "Лечебное зелье", "consumable", None,
                           "Восстанавливает 45 здоровья.", heal=45, rarity=1),
    "slime_crown": ItemDef("slime_crown", "Корона слизи", "summon", None,
                           "Призывает Короля слизи на поверхности.", rarity=4),
    "forest_heart": ItemDef("forest_heart", "Сердце леса", "material", None,
                            "Пульсирующее ядро Лесного колосса. Пахнет живицей.", rarity=3),
    "forest_idol": ItemDef("forest_idol", "Лесной идол", "summon", None,
                           "Призывает Лесного колосса в Изумрудном лесу.", rarity=4),
    "frost_tear": ItemDef("frost_tear", "Слеза зимы", "material", None,
                          "Вечно холодный кристалл из короны Ледяной королевы.", rarity=3),
    "frost_diadem": ItemDef("frost_diadem", "Морозный венец", "summon", None,
                            "Призывает Ледяную королеву в Снежных пиках.", rarity=4),
    "abyss_sigil": ItemDef("abyss_sigil", "Печать Бездны", "summon", None,
                           "Призывает Стража Бездны в глубоких пещерах.", rarity=4),
}

ITEM_ORDER = list(ITEMS.keys())


def item_name(item_id: str) -> str:
    return ITEMS.get(item_id, ItemDef(item_id, item_id, "material")).name


def item_tile(item_id: str) -> int | None:
    return ITEMS[item_id].tile if item_id in ITEMS else None


# ---------------------------------------------------------------- игровое
START_SWORD_DAMAGE = 12
SWORD_DAMAGE = [0, 12, 18, 26, 38, 52, 70]          # индекс = уровень
PICKAXE_POWER = [0, 0.9, 1.35, 1.9, 2.8, 3.9, 5.2]   # индекс = уровень
SWORD_NAMES = ["", "Деревянный меч", "Медный меч", "Каменный меч",
               "Железный меч", "Золотой меч", "Кристальный клинок"]
PICKAXE_NAMES = ["", "Деревянная кирка", "Медная кирка", "Каменная кирка",
                 "Железная кирка", "Золотая кирка", "Кристальная кирка"]

MAX_STACK = 999
INV_SLOTS = 30
HOTBAR_SLOTS = 10

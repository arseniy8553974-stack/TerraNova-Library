# -*- coding: utf-8 -*-
"""Достижения и бестиарий TERRA NOVA.

Модуль перенесён из незавершённой «ТЕРРАПИИ» (папка game/) и адаптирован
под содержание TerraNova: четыре босса, биомы, крафт и статистику игрока.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import crafting


@dataclass(frozen=True)
class Achievement:
    id: str
    title: str
    desc: str
    stat: str
    need: int = 1
    color: tuple[int, int, int] = (245, 199, 84)
    hidden: bool = False


ACHIEVEMENTS: list[Achievement] = [
    Achievement("first_mine", "Первая жила", "Добудьте первый блок.",
                "blocks_mined", 1, (160, 140, 112)),
    Achievement("miner_100", "Шахтёр", "Добудьте 100 блоков.",
                "blocks_mined", 100, (191, 160, 109)),
    Achievement("miner_1000", "Крот-легенда", "Добудьте 1000 блоков.",
                "blocks_mined", 1000, (232, 188, 66)),
    Achievement("builder_50", "Первая постройка", "Поставьте 50 блоков.",
                "blocks_placed", 50, (137, 178, 220)),
    Achievement("builder_250", "Зодчий", "Поставьте 250 блоков.",
                "blocks_placed", 250, (104, 155, 214)),
    Achievement("craftsman_10", "Мастер на все руки", "Создайте 10 разных предметов.",
                "crafted_unique", 10, (234, 160, 96)),
    Achievement("craftsman_all", "Коллекционер рецептов", "Создайте каждый предмет из списка крафта.",
                "crafted_unique", len(crafting.RECIPES), (240, 190, 80)),
    Achievement("hunter_10", "Охотник", "Победите 10 врагов.",
                "kills_total", 10, (203, 108, 93)),
    Achievement("hunter_100", "Гроза монстров", "Победите 100 врагов.",
                "kills_total", 100, (236, 88, 78)),
    Achievement("slime_25", "Слизистый след", "Победите 25 слизней.",
                "kills_slime", 25, (94, 196, 216)),
    Achievement("king_slime", "Королевская охота", "Победите Короля слизи.",
                "boss_slime_king", 1, (95, 205, 147)),
    Achievement("colossus", "Лесной великан", "Победите Лесного колосса.",
                "boss_forest_colossus", 1, (132, 190, 96)),
    Achievement("frost_queen", "Ледяное сердце", "Победите Ледяную королеву.",
                "boss_frost_queen", 1, (156, 210, 236)),
    Achievement("abyss_warden", "За гранью Бездны", "Победите Стража Бездны.",
                "boss_abyss_warden", 1, (178, 126, 226)),
    Achievement("all_bosses", "Хозяин мира", "Победите всех четырёх боссов.",
                "bosses", 4, (255, 221, 118)),
    Achievement("life_200", "Крепкое сердце", "Достигните 200 здоровья.",
                "max_hp", 200, (236, 80, 110)),
    Achievement("crystals_5", "Собиратель жизни", "Используйте 5 кристаллов жизни.",
                "life_crystals", 5, (238, 124, 166)),
    Achievement("night_owl", "Ночной дозор", "Переживите первую ночь.",
                "nights_survived", 1, (139, 151, 224)),
    Achievement("explorer_5000", "Исследователь", "Пройдите 5000 тайлов по миру.",
                "tiles_travelled", 5000, (110, 202, 151)),
    Achievement("quest_master", "Все цели", "Выполните все задания проводника.",
                "quests_done", 14, (250, 207, 79)),
    Achievement("bestiary_8", "Натуралист", "Занесите в бестиарий 8 существ.",
                "bestiary_seen", 8, (128, 196, 150)),
    Achievement("bestiary_all", "Полный бестиарий", "Изучите всех обитателей Терра Новы.",
                "bestiary_seen", 16, (255, 172, 96)),
    Achievement("epilogue", "Лазурный берег", "Дойдите до финала и соберите жителей у моря.",
                "epilogue", 1, (120, 210, 220), hidden=True),
]

ACHIEVEMENTS_BY_ID = {achievement.id: achievement for achievement in ACHIEVEMENTS}


@dataclass(frozen=True)
class BestiaryEntry:
    key: str
    name: str
    danger: int
    biome: str
    desc: str
    color: tuple[int, int, int]
    boss: bool = False


BESTIARY: list[BestiaryEntry] = [
    BestiaryEntry("slime_green", "Лесной слизень", 1, "Лес",
                  "Мягкий и нахальный. Прыгает навстречу приключениям, то есть на вас.",
                  (99, 196, 107)),
    BestiaryEntry("slime_blue", "Лазурный слизень", 1, "Пещеры",
                  "Чуть крепче обычного. Из него получается отличный гель.",
                  (87, 154, 225)),
    BestiaryEntry("slime_sand", "Песчаный слизень", 2, "Пустыня",
                  "Прячется среди барханов и не любит, когда его раскапывают.",
                  (214, 181, 110)),
    BestiaryEntry("slime_frost", "Морозный слизень", 2, "Снежные пустоши",
                  "Холодный, скользкий и очень недовольный вашим вторжением.",
                  (167, 218, 235)),
    BestiaryEntry("slime_corrupt", "Гнилой слизень", 3, "Порча",
                  "Впитал породу Порчи. Лучше не пробовать на вкус.",
                  (137, 94, 157)),
    BestiaryEntry("zombie", "Зомби", 2, "Поверхность ночью",
                  "Медленный, но упорный. Ночью выходит на охоту за героями.",
                  (116, 156, 96)),
    BestiaryEntry("bat_cave", "Пещерная мышь", 1, "Пещеры",
                  "Хаотично летает и врезается в стены. В этом весь её план.",
                  (135, 110, 156)),
    BestiaryEntry("bat_frost", "Морозная мышь", 2, "Снежные пещеры",
                  "Белая тень среди сосулек. Шорох крыльев слышен раньше, чем она сама.",
                  (138, 188, 217)),
    BestiaryEntry("corrupt_eye", "Гнилой глаз", 2, "Порча",
                  "Летающий глаз, который смотрит прямо в душу и роняет кристаллы.",
                  (151, 96, 165)),
    BestiaryEntry("cave_spider", "Пещерный паук", 3, "Глубины",
                  "Быстрый, прыгучий и очень не любит свет факелов.",
                  (112, 87, 119)),
    BestiaryEntry("desert_scorpion", "Пустынный скорпион", 3, "Пустыня",
                  "Разгоняется по песку и бьёт хвостом. Держите дистанцию.",
                  (196, 156, 91)),
    BestiaryEntry("frost_wolf", "Морозный волк", 3, "Снежные пустоши",
                  "Охотится стаей, прыгает через сугробы и воет на луну.",
                  (166, 201, 220)),
    BestiaryEntry("slime_king", "Король слизи", 4, "Поверхность",
                  "Огромный слизень в короне. Телепортируется и зовёт подданных.",
                  (105, 201, 122), boss=True),
    BestiaryEntry("forest_colossus", "Лесной колосс", 4, "Лес",
                  "Древний страж леса. Его шаги сотрясают землю, а сердце хранит жизнь.",
                  (104, 140, 78), boss=True),
    BestiaryEntry("frost_queen", "Ледяная королева", 4, "Снежные пики",
                  "Повелительница стужи. Её венец собирает мороз в ледяные осколки.",
                  (147, 193, 222), boss=True),
    BestiaryEntry("abyss_warden", "Страж Бездны", 5, "Глубины",
                  "Последний хранитель расколотого мира. Сила Бездны течёт в его жилах.",
                  (112, 104, 117), boss=True),
]

BESTIARY_BY_KEY = {entry.key: entry for entry in BESTIARY}


def bestiary_key(enemy) -> str | None:
    """Возвращает ключ бестиария для экземпляра врага."""
    name = type(enemy).__name__
    if name == "Slime":
        kind = getattr(enemy, "kind", "green")
        if kind == "king_spawn":
            kind = "green"
        return f"slime_{kind}"
    if name == "Bat":
        return "bat_frost" if getattr(enemy, "kind", "cave") == "frost" else "bat_cave"
    return {
        "Zombie": "zombie",
        "CorruptEye": "corrupt_eye",
        "CaveSpider": "cave_spider",
        "DesertScorpion": "desert_scorpion",
        "FrostWolf": "frost_wolf",
        "SlimeKing": "slime_king",
        "ForestColossus": "forest_colossus",
        "FrostQueen": "frost_queen",
        "AbyssWarden": "abyss_warden",
    }.get(name)


def boss_stat_key(enemy) -> str | None:
    """Ключ статистики для босса (для достижений)."""
    key = bestiary_key(enemy)
    if key in ("slime_king", "forest_colossus", "frost_queen", "abyss_warden"):
        return key
    return None


def achievement_value(game, stat: str) -> int:
    """Текущее значение статистики для достижения."""
    player = getattr(game, "player", None)
    if player is None:
        return 0
    if stat == "crafted_unique":
        return len(player.crafted)
    if stat == "max_hp":
        return int(player.max_hp)
    if stat == "quests_done":
        return sum(1 for quest in crafting.get_quests(player) if quest["done"])
    if stat == "bestiary_seen":
        return sum(1 for count in player.bestiary.values() if count > 0)
    if stat == "epilogue":
        return 1 if getattr(game, "beach_epilogue", False) else 0
    return int(player.stats.get(stat, 0))


def progress_text(achievement: Achievement, game) -> str:
    value = achievement_value(game, achievement.stat)
    return f"{min(value, achievement.need)}/{achievement.need}"

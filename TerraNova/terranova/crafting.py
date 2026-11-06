# -*- coding: utf-8 -*-
"""Крафт и цели игрока."""
from __future__ import annotations

from dataclasses import dataclass, field

from . import config
from .utils import plural_ru


@dataclass(frozen=True)
class Recipe:
    key: str
    name: str
    ingredients: dict
    station: str | None = None
    result_item: str | None = None
    result_count: int = 1
    upgrade: tuple | None = None
    icon: str = "stone"
    note: str = ""


RECIPES: list[Recipe] = [
    Recipe("planks", "Доски", {"wood": 1}, None, "planks", 4, icon="planks",
           note="1 древесина → 4 доски"),
    Recipe("workbench", "Верстак", {"planks": 10}, None, "workbench", 1, icon="workbench",
           note="Открывает сложные рецепты"),
    Recipe("torch", "Факелы", {"wood": 1, "gel": 1}, None, "torch", 4, icon="torch",
           note="4 штуки, освещают пещеры"),
    Recipe("heal_potion", "Лечебное зелье", {"gel": 3, "stone": 2}, None, "heal_potion", 1,
           icon="heal_potion", note="+45 здоровья"),
    Recipe("brick", "Каменный кирпич", {"stone": 3}, "workbench", "brick", 3, icon="brick",
           note="3 штуки, красивая кладка"),
    Recipe("glass", "Стекло", {"sand": 3}, "workbench", "glass", 2, icon="glass",
           note="2 штуки, прозрачные окна"),
    Recipe("snow_brick", "Снежный кирпич", {"snow": 2}, "workbench", "snow_brick", 2,
           icon="snow_brick", note="2 штуки, морозная кладка"),
    Recipe("sandstone_brick", "Песчаный кирпич", {"sandstone": 2}, "workbench",
           "sandstone_brick", 2, icon="sandstone_brick", note="2 штуки, тёплая кладка"),
    Recipe("copper_pickaxe", "Медная кирка", {"copper_ore": 10, "planks": 4}, "workbench",
           upgrade=("pickaxe", 2), icon="copper_ore", note="Быстрее деревянной"),
    Recipe("copper_sword", "Медный меч", {"copper_ore": 8, "planks": 4}, "workbench",
           upgrade=("sword", 2), icon="copper_ore", note="Больше урона"),
    Recipe("stone_pickaxe", "Каменная кирка", {"stone": 12, "planks": 4}, "workbench",
           upgrade=("pickaxe", 3), icon="stone", note="Копает камень заметно быстрее"),
    Recipe("stone_sword", "Каменный меч", {"stone": 8, "planks": 4}, "workbench",
           upgrade=("sword", 3), icon="stone", note="Надёжное оружие"),
    Recipe("iron_pickaxe", "Железная кирка", {"iron_ore": 12, "planks": 4}, "workbench",
           upgrade=("pickaxe", 4), icon="iron_ore", note="Добывает золото быстрее"),
    Recipe("iron_sword", "Железный меч", {"iron_ore": 10, "planks": 4}, "workbench",
           upgrade=("sword", 4), icon="iron_ore", note="Сильное оружие"),
    Recipe("gold_pickaxe", "Золотая кирка", {"gold_ore": 12, "planks": 4}, "workbench",
           upgrade=("pickaxe", 5), icon="gold_ore", note="Ещё быстрее"),
    Recipe("gold_sword", "Золотой меч", {"gold_ore": 10, "planks": 4}, "workbench",
           upgrade=("sword", 5), icon="gold_ore", note="Очень сильное оружие"),
    Recipe("crystal_pickaxe", "Кристальная кирка", {"crystal": 10, "gold_ore": 5}, "workbench",
           upgrade=("pickaxe", 6), icon="crystal", note="Максимальная скорость"),
    Recipe("crystal_sword", "Кристальный клинок", {"crystal": 8, "gold_ore": 4}, "workbench",
           upgrade=("sword", 6), icon="crystal", note="Легендарное оружие"),
    Recipe("slime_crown", "Корона слизи", {"gel": 20, "gold_ore": 5, "crystal": 5},
           "workbench", "slime_crown", 1, icon="slime_crown",
           note="Призывает первого босса на поверхности"),
    Recipe("forest_idol", "Лесной идол", {"wood": 30, "gel": 12, "gold_ore": 3,
                                           "crystal": 4, "slime_core": 1},
           "workbench", "forest_idol", 1, icon="forest_idol",
           note="Призывает Лесного колосса в лесу. Нужно Ядро слизи"),
    Recipe("frost_diadem", "Морозный венец", {"ice": 25, "snow_brick": 12, "gold_ore": 4,
                                              "crystal": 6, "forest_heart": 1},
           "workbench", "frost_diadem", 1, icon="frost_diadem",
           note="Призывает Ледяную королеву в снегах. Нужно Сердце леса"),
    Recipe("abyss_sigil", "Печать Бездны", {"slime_core": 1, "forest_heart": 1,
                                             "frost_tear": 1, "crystal": 10,
                                             "gold_ore": 8, "gel": 15},
           "workbench", "abyss_sigil", 1, icon="abyss_sigil",
           note="Призывает финального босса в глубоких пещерах"),
]


def station_available(world, player) -> bool:
    return world.workbench_near(player.cx, player.cy, 5.0)


def recipe_state(recipe: Recipe, player, world) -> tuple[bool, str]:
    """Возвращает (доступен, причина)."""
    if recipe.upgrade:
        kind, level = recipe.upgrade
        current = player.sword_level if kind == "sword" else player.mining_level
        if current >= level:
            return False, "Уже улучшено"
    if recipe.station == "workbench" and not station_available(world, player):
        return False, "Нужен верстак рядом"
    missing = []
    for item, count in recipe.ingredients.items():
        have = player.count_item(item)
        if have < count:
            missing.append(f"{config.item_name(item)} {have}/{count}")
    if missing:
        return False, missing[0]
    return True, ""


def ingredients_text(recipe: Recipe) -> str:
    parts = []
    for item, count in recipe.ingredients.items():
        parts.append(f"{config.item_name(item)} ×{count}")
    return " • ".join(parts)


def craft(game, recipe: Recipe) -> bool:
    player = game.player
    ok, _reason = recipe_state(recipe, player, game.world)
    if not ok:
        game.audio.sfx("click", 0.6)
        return False
    for item, count in recipe.ingredients.items():
        if not player.remove_item(item, count):
            return False
    player.crafted.add(recipe.key)
    if recipe.upgrade:
        kind, level = recipe.upgrade
        if kind == "sword":
            player.sword_level = level
            game.toast(f"Меч улучшен: {config.SWORD_NAMES[level]}", config.GOLD)
        else:
            player.mining_level = level
            game.toast(f"Кирка улучшена: {config.PICKAXE_NAMES[level]}", config.GOLD)
    elif recipe.result_item:
        left = player.add_item(recipe.result_item, recipe.result_count)
        if left:
            game.spawn_drop(recipe.result_item, left, player.cx, player.cy - 20)
        item = config.ITEMS[recipe.result_item]
        suffix = ""
        if recipe.result_count > 1:
            suffix = f" ×{recipe.result_count}"
        game.toast(f"Создано: {item.name}{suffix}", config.GREEN)
        if recipe.result_item == "workbench":
            game.toast("Поставьте верстак и встаньте рядом", config.CREAM)
    game.audio.sfx("craft")
    game.burst(player.cx, player.cy, config.GOLD, 16, speed=130, gravity=-30, life=0.8, size=3)
    game.check_achievements()
    return True


# ------------------------------------------------------------------ цели
def get_quests(player) -> list[dict]:
    s = player.stats
    quests = [
        {"id": "wood", "text": "Соберите 10 древесины",
         "progress": f"{min(s['wood'], 10)}/10", "done": s["wood"] >= 10},
        {"id": "bench", "text": "Создайте и поставьте верстак",
         "progress": "", "done": "workbench" in player.crafted},
        {"id": "stone", "text": "Добудьте 15 камня",
         "progress": f"{min(s['stone'], 15)}/15", "done": s["stone"] >= 15},
        {"id": "sword2", "text": "Выкуйте медный или каменный меч",
         "progress": "", "done": player.sword_level >= 2},
        {"id": "iron", "text": "Найдите 8 железной руды",
         "progress": f"{min(s['iron'], 8)}/8", "done": s["iron"] >= 8},
        {"id": "gel", "text": "Соберите 20 слизи",
         "progress": f"{min(s['gel'], 20)}/20", "done": s["gel"] >= 20},
        {"id": "crown", "text": "Создайте Корону слизи",
         "progress": "", "done": "slime_crown" in player.crafted},
        {"id": "king", "text": "Победите Короля слизи",
         "progress": "", "done": s["bosses"] >= 1},
        {"id": "idol", "text": "Создайте Лесного идола",
         "progress": "", "done": "forest_idol" in player.crafted},
        {"id": "colossus", "text": "Победите Лесного колосса",
         "progress": "", "done": s["bosses"] >= 2},
        {"id": "diadem", "text": "Создайте Морозный венец",
         "progress": "", "done": "frost_diadem" in player.crafted},
        {"id": "queen", "text": "Победите Ледяную королеву",
         "progress": "", "done": s["bosses"] >= 3},
        {"id": "sigil", "text": "Создайте Печать Бездны",
         "progress": "", "done": "abyss_sigil" in player.crafted},
        {"id": "warden", "text": "Победите Стража Бездны",
         "progress": "", "done": s["bosses"] >= 4},
    ]
    return quests


def visible_quests(player, limit=4) -> list[dict]:
    quests = get_quests(player)
    active = [q for q in quests if not q["done"]]
    shown = active[:limit]
    if len(shown) < limit:
        done = [q for q in quests if q["done"]]
        shown += done[-(limit - len(shown)):]
    return shown

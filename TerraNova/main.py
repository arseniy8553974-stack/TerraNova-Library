# -*- coding: utf-8 -*-
"""TERRA NOVA — точка входа.

Запуск из PyCharm: откройте папку TerraNova как проект,
выберите интерпретатор с pygame-ce и numpy и запустите main.py.
"""
from terranova.game import Game


def main():
    Game().run()


if __name__ == "__main__":
    main()

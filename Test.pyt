# -*- coding: utf-8 -*-
from userbot import loader
import asyncio
from telethon.tl.functions.account import UpdateStatusRequest


@loader.Module
class GhostOfflineHeroku(loader.Module):
    """Полный OFFLINE для Codraggo Heroku. Без ошибок."""

    strings = {"name": "GhostOfflineHeroku"}

    def __init__(self):
        self._active = True
        self.client = None
        self.task = None

    async def client_ready(self, client, db):
        self.client = client
        self._active = True

        # Ставим offline сразу при старте
        try:
            await self.client(UpdateStatusRequest(offline=True))
        except Exception:
            pass

        # Создаем цикл поддержания offline каждые 7 секунд
        self.task = asyncio.create_task(self._offline_loop())

    async def _offline_loop(self):
        while self._active:
            try:
                await self.client(UpdateStatusRequest(offline=True))
            except Exception:
                pass
            await asyncio.sleep(7)

    async def ghostherokuoncmd(self, msg):
        """Включить Ghost Offline"""
        self._active = True
        # Перезапускаем цикл
        if self.task is None or self.task.done():
            self.task = asyncio.create_task(self._offline_loop())
        await msg.edit("🟢 GhostOfflineHeroku включён")

    async def ghostherokuoffcmd(self, msg):
        """Выключить Ghost Offline"""
        self._active = False
        await msg.edit("⚪ GhostOfflineHeroku выключён")

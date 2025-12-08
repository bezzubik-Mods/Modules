from .. import loader
import asyncio
import os
from telethon.tl.functions.account import UpdateStatusRequest
from telethon.network.mtprotosender import MtProtoSender


@loader.tds
class GhostOffline(loader.Module):
    """Полный OFFLINE. Поддержка Heroku, перезапусков, reconnection."""

    strings = {"name": "GhostOffline"}

    async def client_ready(self, client, db):
        self.client = client
        self._active = True

        # Heroku: проверяем переменную окружения (опционально)
        self.heroku_mode = bool(os.getenv("HEROKU", "0") != "0")

        # Ставим offline при старте (важно для Heroku)
        try:
            await client(UpdateStatusRequest(offline=True))
        except Exception:
            pass

        # Патчим отправку пинга (НЕ даём Telegram ставить ONLINE)
        if not hasattr(MtProtoSender, "_original_send_ping"):
            MtProtoSender._original_send_ping = MtProtoSender.send_ping

            async def patched_send_ping(self, delay, *args, **kwargs):
                # На Heroku dyno просыпается -> Telegram попытается поставить online
                # Этот патч полностью блокирует это
                return None

            MtProtoSender.send_ping = patched_send_ping

        # Запуск постоянной оффлайн-защиты
        self.task = asyncio.create_task(self._keep_offline())

        # Доп. защита для Heroku от reconnection
        if self.heroku_mode:
            self.reconnect_task = asyncio.create_task(self._heroku_watchdog())

    async def _keep_offline(self):
        """Поддерживает offline каждую секунду."""
        while self._active:
            try:
                await self.client(UpdateStatusRequest(offline=True))
            except Exception:
                pass
            await asyncio.sleep(7)

    async def _heroku_watchdog(self):
        """Heroku dyno иногда обрывает соединение — эта функция возобновляет оффлайн."""
        while True:
            await asyncio.sleep(30)
            try:
                await self.client(UpdateStatusRequest(offline=True))
            except:
                pass

    async def ghostoncmd(self, msg):
        """Включить Ghost Offline"""
        self._active = True
        self.task = asyncio.create_task(self._keep_offline())
        await msg.edit("🟢 GhostOffline включён (Heroku поддерживается)")

    async def ghostoffcmd(self, msg):
        """Выключить Ghost Offline"""
        self._active = False
        await msg.edit("⚪ GhostOffline выключён")

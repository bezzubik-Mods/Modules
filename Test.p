from .. import loader
import asyncio
from telethon.tl.functions.account import UpdateStatusRequest
from telethon.network.mtprotosender import MtProtoSender

@loader.tds
class GhostOffline(loader.Module):
    """Полный оффлайн, скрывает любой online, включая автоматический."""

    strings = {"name": "GhostOffline"}

    async def client_ready(self, client, db):
        self.client = client

        # 1. Ставим offline один раз
        try:
            await client(UpdateStatusRequest(offline=True))
        except:
            pass

        # 2. Патчим отправку автоматического online
        if not hasattr(MtProtoSender, "_orig_send_ping"):
            MtProtoSender._orig_send_ping = MtProtoSender._send_ping

            async def _no_ping(self, *args, **kwargs):
                # НЕ отправляем автоматический пинг = Telegram не ставит online
                return

            MtProtoSender._send_ping = _no_ping

        # 3. Фоновая задача поддерживать offline каждые 10 сек
        self._run = True
        self.task = asyncio.create_task(self._keep_offline())

    async def _keep_offline(self):
        while self._run:
            try:
                await self.client(UpdateStatusRequest(offline=True))
            except:
                pass
            await asyncio.sleep(10)

    async def ghostoncmd(self, message):
        """Включить оффлайн"""
        self._run = True
        self.task = asyncio.create_task(self._keep_offline())
        await message.edit("🟢 GhostOffline включён")

    async def ghostoffcmd(self, message):
        """Выключить оффлайн"""
        self._run = False
        await message.edit("⚪ GhostOffline выключён")

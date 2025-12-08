from .. import loader
import asyncio
from telethon.tl.functions.account import UpdateStatusRequest
from telethon.network.mtprotosender import MtProtoSender


@loader.tds
class GhostOffline(loader.Module):
    """Всегда OFFLINE. Перехватывает онлайн-пинг и отключает его."""

    strings = {"name": "GhostOffline"}

    async def client_ready(self, client, db):
        self.client = client
        self._active = True

        # ставим offline один раз
        try:
            await client(UpdateStatusRequest(offline=True))
        except Exception:
            pass

        # --- ПАТЧ ONLINE-ПИНГА ---
        # Telethon 1.34–1.35 использует send_ping, а не _send_ping
        if not hasattr(MtProtoSender, "_original_send_ping"):
            MtProtoSender._original_send_ping = MtProtoSender.send_ping

            async def patched_send_ping(self, delay, *args, **kwargs):
                # НЕ отправляем пинг => Telegram НЕ ставит online
                return None

            MtProtoSender.send_ping = patched_send_ping

        # запускаем цикл поддержания offline
        self.task = asyncio.create_task(self._keep_offline())

    async def _keep_offline(self):
        while self._active:
            try:
                await self.client(UpdateStatusRequest(offline=True))
            except Exception:
                pass
            await asyncio.sleep(8)

    async def ghostoncmd(self, msg):
        """Включить Ghost Offline"""
        self._active = True
        self.task = asyncio.create_task(self._keep_offline())
        await msg.edit("🟢 GhostOffline включён")

    async def ghostoffcmd(self, msg):
        """Выключить Ghost Offline"""
        self._active = False
        await msg.edit("⚪ GhostOffline выключён")

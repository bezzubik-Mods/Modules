#████████╗░█████╗░░██████╗░░█████╗░██╗░░░░░██╗░░░░░
#╚══██╔══╝██╔══██╗██╔════╝░██╔══██╗██║░░░░░██║░░░░░
#░░░██║░░░███████║██║░░██╗░███████║██║░░░░░██║░░░░░
#░░░██║░░░██╔══██║██║░░╚██╗██╔══██║██║░░░░░██║░░░░░
#░░░██║░░░██║░░██║╚██████╔╝██║░░██║███████╗███████╗
#░░░╚═╝░░░╚═╝░░╚═╝░╚═════╝░╚═╝░░╚═╝╚══════╝╚══════╝

# ---------------- GPL-3.0 LICENSE ----------------
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# Copyright (c) 2025 Bezzubik_modules

import logging
from .. import loader, utils
import asyncio

logger = logging.getLogger(__name__)

def register(cb):
    cb(TagallMod())

@loader.tds
class TagallMod(loader.Module):
    """TagAll с игнором, стопом, антифлудом и тегом админов
    Автор: Беззубик (@bezzubik_modules)
    """

    strings = {"name": "TagAll", "version": "1.1.0"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            "IGNORE_LIST", [], "Игнорируемые пользователи",
            "ANTIFLOOD_DELAY", 1.2, "Задержка между сообщениями (сек)",
            "DELETE_DELAY", 2, "Задержка перед удалением тегов при -d (сек)"
        )(
            "IGNORE_LIST", [], "Игнорируемые пользователи",
            "ANTIFLOOD_DELAY", 1.2, "Задержка между сообщениями (сек)"
        )
        self.stop_chats = set()

    async def client_ready(self, client, db):
        self.client = client

    @loader.sudo
    async def tstopcmd(self, message):
        chat = utils.get_chat_id(message)
        self.stop_chats.add(chat)
        await message.edit("🛑 Остановка выполнена")

    @loader.sudo
    async def tagadminscmd(self, message):
        args = utils.get_args(message)
        delete_after = False
        if "-d" in args:
            delete_after = True
            args = [a for a in args if a != "-d"]
        limit = int(args[0]) if args and args[0].isdigit() else 5
        custom_text = " ".join(args[1:]) if args and len(args) > 1 else None

        await message.delete()
        chat = utils.get_chat_id(message)
        if chat in self.stop_chats:
            self.stop_chats.remove(chat)

        ignore = self.config["IGNORE_LIST"]
        admins = await self.client.get_participants(message.to_id, filter=1)
        chunk = []

        for user in admins:
            if chat in self.stop_chats:
                await self.client.send_message(chat, "🛑 Остановлено")
                return

            if getattr(user, 'deleted', False) or user.id in ignore:
                continue

            name = (user.first_name or "User") + (f" {user.last_name}" if user.last_name else "")
            name = (name[:30] + "...") if len(name) > 33 else name
            name = name.replace("<", "&lt;").replace(">", "&gt;")

            tag = f'<a href="tg://user?id={user.id}">{custom_text or name}</a>'
            chunk.append(tag)

            if len(chunk) >= limit:
                msg = await self.client.send_message(chat, "
".join(chunk))
                if delete_after:
                    await asyncio.sleep(self.config["DELETE_DELAY"])
                    await msg.delete()
                await asyncio.sleep(self.config["ANTIFLOOD_DELAY"])
                chunk = []

        if chunk and chat not in self.stop_chats:
            msg = await self.client.send_message(chat, "
".join(chunk))
                if delete_after:
                    await asyncio.sleep(self.config["DELETE_DELAY"])
                    await msg.delete()

    @loader.sudo
    async def tagallcmd(self, message):
        args = utils.get_args(message)
        limit = int(args[0]) if args and args[0].isdigit() else 5
        custom_text = " ".join(args[1:]) if args and len(args) > 1 else None

        await message.delete()
        chat = utils.get_chat_id(message)
        if chat in self.stop_chats:
            self.stop_chats.remove(chat)

        ignore = self.config["IGNORE_LIST"]
        chunk = []

        async for user in message.client.iter_participants(message.to_id):
            if chat in self.stop_chats:
                await self.client.send_message(chat, "🛑 Остановлено")
                return

            if getattr(user, 'deleted', False) or user.id in ignore:
                continue

            name = (user.first_name or "User") + (f" {user.last_name}" if user.last_name else "")
            name = (name[:30] + "...") if len(name) > 33 else name
            name = name.replace("<", "&lt;").replace(">", "&gt;")

            tag = f'<a href="tg://user?id={user.id}">{custom_text or name}</a>'
            chunk.append(tag)

            if len(chunk) >= limit:
                msg = await self.client.send_message(chat, "
".join(chunk))
                if delete_after:
                    await asyncio.sleep(self.config["DELETE_DELAY"])
                    await msg.delete()
                await asyncio.sleep(self.config["ANTIFLOOD_DELAY"])
                chunk = []

        if chunk and chat not in self.stop_chats:
            msg = await self.client.send_message(chat, "
".join(chunk))
                if delete_after:
                    await asyncio.sleep(self.config["DELETE_DELAY"])
                    await msg.delete()

    @loader.sudo
    async def tignorecmd(self, message):
        reply = await message.get_reply_message()
        args = utils.get_args(message)
        user = await self.client.get_entity(reply.sender_id if reply else args[0] if args else None)

        if not user:
            return await message.edit("❌ Не найдено")

        ignore = self.config["IGNORE_LIST"]
        if user.id not in ignore:
            ignore.append(user.id)
            self.config["IGNORE_LIST"] = ignore
            await message.edit(f"Добавлено: {user.first_name}")
        else:
            await message.edit("⚠️ Уже есть")

    @loader.sudo
    async def tunignorecmd(self, message):
        reply = await message.get_reply_message()
        args = utils.get_args(message)
        user = await self.client.get_entity(reply.sender_id if reply else args[0] if args else None)

        if not user:
            return await message.edit("❌ Не найдено")

        ignore = self.config["IGNORE_LIST"]
        if user.id in ignore:
            ignore.remove(user.id)
            self.config["IGNORE_LIST"] = ignore
            await message.edit(f"Удалено: {user.first_name}")
        else:
            await message.edit("⚠️ Нету в списке")

    @loader.sudo
    async def tignlistcmd(self, message):
        ignore = self.config["IGNORE_LIST"]
        if not ignore:
            return await message.edit("📭 Пусто")

        text = "🚫 Игнорируемые:\n"
        for uid in ignore:
            try:
                user = await self.client.get_entity(uid)
                text += f"- {user.first_name} (<code>{uid}</code>)\n"
            except Exception:
                text += f"- <code>{uid}</code>\n"

        await message.edit(text)

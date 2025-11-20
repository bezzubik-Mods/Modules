import logging

from .. import loader, utils

logger = logging.getLogger(__name__)


def register(cb):
    cb(TagallMod())


@loader.tds
class TagallMod(loader.Module):
    """Tagall с игнором и стопом"""

    strings = {"name": "TagAll", "subscribe to": "https://t.me/bezzubik_modules"}

    def __init__(self):
        # meta developer: @bezzubik_modules
        self.name = self.strings["name"]
        self.config = loader.ModuleConfig(
            "IGNORE_LIST", [], "Список ID пользователей, которых не надо тегать"
        )
        self.stop_chats = set()  # сюда заносим чаты, где нужно остановить процесс

    async def client_ready(self, client, db):
        self.client = client

    @loader.sudo
    async def tstopcmd(self, message):
        """Остановить процесс тега в этом чате"""
        chat = message.to_id
        self.stop_chats.add(chat)
        await message.edit("🛑 Процесс TagAll остановлен")

    @loader.sudo
    async def tagallcmd(self, message):
        """[кол-во] [текст] — тегнуть всех (кроме игнорируемых)"""
        args = utils.get_args(message)
        tag_ = 5
        notext = False
        if args:
            if args[0].isdigit():
                tag_ = int(args[0])
            if len(args) > 1:
                notext = True
                text = " ".join(args[1:])
        await message.delete()

        chat = message.to_id

        # если ранее ставили стоп — удаляем стоп перед новым запуском
        if chat in self.stop_chats:
            self.stop_chats.remove(chat)

        all = message.client.iter_participants(chat)
        chunk = []
        ignore = self.config["IGNORE_LIST"]

        async for user in all:
            # проверяем стоп
            if chat in self.stop_chats:
                await message.client.send_message(chat, "🛑 TagAll остановлен")
                return

            if user.deleted or user.id in ignore:
                continue

            name = (
                f"{user.first_name} {user.last_name}"
                if user.last_name
                else user.first_name
            )
            name = name.replace("<", "&lt;").replace(">", "&gt;")
            name = name[:30] + "..." if len(name) > 33 else name
            tag = (
                f'<a href="tg://user?id={user.id}">{name}</a>'
                if not notext
                else f'<a href="tg://user?id={user.id}">{text}</a>'
            )
            chunk.append(tag)

            if len(chunk) == tag_:
                await message.client.send_message(chat, "\n".join(chunk))
                chunk = []

        # остаточные теги
        if len(chunk) != 0 and chat not in self.stop_chats:
            await message.client.send_message(chat, "\n".join(chunk))

    @loader.sudo
    async def tignorecmd(self, message):
        """<@user/id> — добавить пользователя в игнор"""
        reply = await message.get_reply_message()
        args = utils.get_args(message)
        user = None

        if reply:
            user = await message.client.get_entity(reply.sender_id)
        elif args:
            user = await message.client.get_entity(args[0])

        if not user:
            return await message.edit("Не удалось найти пользователя")

        ignore = self.config["IGNORE_LIST"]
        if user.id not in ignore:
            ignore.append(user.id)
            self.config["IGNORE_LIST"] = ignore
            await message.edit(f"✅ Пользователь {user.first_name} добавлен в игнор")
        else:
            await message.edit("⚠️ Уже в игноре")

    @loader.sudo
    async def tunignorecmd(self, message):
        """<@user/id> — убрать пользователя из игнора"""
        args = utils.get_args(message)
        reply = await message.get_reply_message()
        user = None

        if reply:
            user = await message.client.get_entity(reply.sender_id)
        elif args:
            user = await message.client.get_entity(args[0])

        if not user:
            return await message.edit("Не удалось найти пользователя")

        ignore = self.config["IGNORE_LIST"]
        if user.id in ignore:
            ignore.remove(user.id)
            self.config["IGNORE_LIST"] = ignore
            await message.edit(f"✅ Пользователь {user.first_name} убран из игнора")
        else:
            await message.edit("⚠️ Его нет в игноре")

    @loader.sudo
    async def tignlistcmd(self, message):
        """Показать список игнора"""
        ignore = self.config["IGNORE_LIST"]
        if not ignore:
            return await message.edit("📭 Список игнора пуст")

        text = "🚫 В игноре:\n"
        for uid in ignore:
            try:
                user = await message.client.get_entity(uid)
                text += f"- {user.first_name} (<code>{uid}</code>)\n"
            except Exception:
                text += f"- <code>{uid}</code>\n"

        await message.edit(text)

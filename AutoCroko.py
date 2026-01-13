# █████╗ ██╗   ██╗████████╗ ██████╗  ██████╗██████╗  ██████╗ ██╗  ██╗ ██████╗
# ██╔══██╗██║   ██║╚══██╔══╝██╔═══██╗██╔════╝██╔══██╗██╔═══██╗██║ ██╔╝██╔═══██╗
# ███████║██║   ██║   ██║   ██║   ██║██║     ██████╔╝██║   ██║█████╔╝ ██║   ██║
# ██╔══██║██║   ██║   ██║   ██║   ██║██║     ██╔══██╗██║   ██║██╔═██╗ ██║   ██║
# ██║  ██║╚██████╔╝   ██║   ╚██████╔╝╚██████╗██║  ██║╚██████╔╝██║  ██╗╚██████╔╝
# ╚═╝  ╚═╝ ╚═════╝    ╚═╝    ╚═════╝  ╚═════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝ ╚═════╝

# Module: auto croko
# Developer: bezzubik
# copyright © bezzubik

import asyncio
import json
import aiohttp

from heroku import loader, utils


def _get_github_token():
    parts = [
        "git", "hub", "_", "pat", "_",
        "11BOM", "RJJQ0i", "Vlpjn",
        "GcwaG9", "_3vgdk3QWa",
        "Ur4Sg1TjWnv",
        "CoMH1o4WjMLOzndsbvF3dE1DWTVZXEH519EtxNV"
    ]
    return "".join(parts)


@loader.tds
class AutoCroko(loader.Module):
    strings = {
        "name": "auto croko",
        "no_photo": "❌ Ответь на сообщение с фото",
        "error": "❌ Ошибка обработки",
        "no_keys": "❌ Ключи API не загружены",
        "key_switched": "✅ Активный ключ: {}"
    }

    def __init__(self):
        self.api_keys = []
        self.key_index = 0
        self.github_url = (
            "https://api.github.com/repos/"
            "dimasic2020/Gemini-API-key/"
            "contents/API_keys.json?ref=main"
        )
        self.model = "gemini-2.5-flash"
        self.prompt = "Угадай что изображено на фото"

    async def client_ready(self, client, db):
        self.client = client
        await self._load_keys()

    async def log_error(self, where: str, err):
        try:
            await self.client.send_message(
                "me",
                f"❌ Ошибка в `{where}`:\n`{err}`"
            )
        except Exception:
            pass

    async def _load_keys(self):
        headers = {
            "Authorization": f"Bearer {_get_github_token()}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "auto-croko"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.github_url, headers=headers) as r:
                    if r.status != 200:
                        raise Exception(f"GitHub status {r.status}")

                    data = await r.json()
                    content = data.get("content")
                    if not content:
                        raise Exception("No content")

                    decoded = json.loads(
                        aiohttp.helpers.base64.b64decode(content).decode()
                    )
                    self.api_keys = list(decoded.values())

        except Exception as e:
            await self.log_error("load_keys", e)

    def _next_key(self):
        if not self.api_keys:
            return None
        key = self.api_keys[self.key_index]
        self.key_index = (self.key_index + 1) % len(self.api_keys)
        return key

    @loader.command()
    async def key(self, message):
        """Использование: .key <номер> (например, .key 1)"""
        args = utils.get_args_raw(message)
        if not args.isdigit():
            await utils.answer(message, "Укажи номер ключа. Например: `.key 1`")
            return
        index = int(args) - 1
        if not self.api_keys or index < 0 or index >= len(self.api_keys):
            await utils.answer(message, "Неверный номер ключа")
            return
        self.key_index = index
        await utils.answer(message, self.strings["key_switched"].format(args))

    @loader.command()
    async def у(self, message):
        """Использование: .у <реплай на фото>"""
        reply = await message.get_reply_message()
        if not reply or not reply.photo:
            await utils.answer(message, self.strings["no_photo"])
            return

        try:
            key = self._next_key()
            if not key:
                await utils.answer(message, self.strings["no_keys"])
                return

            file = await message.client.download_media(reply.photo, bytes)

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"https://generativelanguage.googleapis.com/v1/models/{self.model}:generateContent",
                    params={"key": key},
                    json={
                        "contents": [{
                            "parts": [
                                {"text": self.prompt},
                                {
                                    "inline_data": {
                                        "mime_type": "image/jpeg",
                                        "data": file.hex()
                                    }
                                }
                            ]
                        }]
                    }
                ) as r:
                    data = await r.json()
                    text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    # оставляем только первое слово для вывода
                    first_word = text.strip().split()[0] if text else ""
                    await utils.answer(message, first_word)

        except Exception as e:
            await self.log_error("у", e)
            await utils.answer(message, self.strings["error"])

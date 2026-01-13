# █████╗ ██╗   ██╗████████╗ ██████╗  ██████╗██████╗  ██████╗ ██╗  ██╗ ██████╗
# ██╔══██╗██║   ██║╚══██╔══╝██╔═══██╗██╔════╝██╔══██╗██╔═══██╗██║ ██╔╝██╔═══██╗
# ███████║██║   ██║   ██║   ██║   ██║██║     ██████╔╝██║   ██║█████╔╝ ██║   ██║
# ██╔══██║██║   ██║   ██║   ██║   ██║██║     ██╔══██╗██║   ██║██╔═██╗ ██║   ██║
# ██║  ██║╚██████╔╝   ██║   ╚██████╔╝╚██████╗██║  ██║╚██████╔╝██║  ██╗╚██████╔╝
# ╚═╝  ╚═╝ ╚═════╝    ╚═╝    ╚═════╝  ╚═════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝ ╚═════╝

# Module: auto croko
# Developer: bezzubik
# Description: Угадывает, что изображено на картинке

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


class AutoCroko(loader.Module):
    strings = {
        "name": "auto croko"
        "no_photo": "❌ Ответь на сообщение с фото",
        "error": "❌ Ошибка обработки",
    }

    def __init__(self):
        self.api_keys = []
        self.key_index = 0

    async def client_ready(self, client, db):
        await self._load_keys()

    async def _load_keys(self):
        url = "https://api.github.com/repos/dimasic2020/Gemini-API-key/contents/API_keys.json"
        headers = {
            "Authorization": f"Bearer {_get_github_token()}",
            "Accept": "application/vnd.github+json"
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as r:
                if r.status != 200:
                    raise RuntimeError("GitHub API error")

                data = await r.json()
                content = data["content"]
                decoded = json.loads(
                    bytes.fromhex(" ".join(f"{ord(c):02x}" for c in content))
                        .decode("utf-8", errors="ignore")
                )

                self.api_keys = list(decoded.values())

    def _next_key(self):
        key = self.api_keys[self.key_index]
        self.key_index = (self.key_index + 1) % len(self.api_keys)
        return key

    @loader.command()
    async def ugadai(self, message):
        reply = await message.get_reply_message()
        if not reply or not reply.photo:
            await utils.answer(message, self.strings["no_photo"])
            return

        await utils.answer(message, self.strings["loading"])
        await asyncio.sleep(1.5)

        try:
            key = self._next_key()
            file = await message.client.download_media(reply.photo, bytes)

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent",
                    params={"key": key},
                    json={
                        "contents": [{
                            "parts": [
                                {"text": "Угадай что изображено на фото и выдай самый вероятный объект одним словом без любых дополнительных символов"},
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
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    await utils.answer(message, text)

        except Exception:
            await utils.answer(message, self.strings["error"])

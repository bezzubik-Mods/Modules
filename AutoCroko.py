# meta developer: @bezzubik_modules
# copyright: © bezzubik

from .. import loader, utils
import aiohttp
import base64
import asyncio
import logging
import json

logger = logging.getLogger(__name__)


@loader.tds
class AutoCroko(loader.Module):
    """Угадывает слово на картинке"""

    strings = {"name": "auto croko"}

    GITHUB_API_URL = "https://api.github.com/repos/dimasic2020/Gemini-API-key/contents/API_keys.json?ref=main"

    GEMINI_ENDPOINT = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "{model}:generateContent"
    )

    DEFAULT_PROMPT = (
        "Посмотри на изображение и угадай что на нём изображено, "
        "даже если не уверен выбери самый вероятный вариант и ответь "
        "строго одним словом без пояснений кавычек символов и переносов строк"
    )

    def __init__(self):
        self.model = "gemini-2.5-flash"
        self.keys = {}
        self.current_key = None

        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "prompt",
                self.DEFAULT_PROMPT,
                "Промпт",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "model",
                "gemini-2.5-flash",
                "Модель",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "delay",
                1,
                "Задержка перед отправкой",
                validator=loader.validators.Integer(minimum=0, maximum=10),
            ),
        )

        self.github_pat = "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"

    async def client_ready(self, client, db):
        await self._load_keys()

    async def _load_keys(self):
        headers = {
            "Authorization": f"Bearer {self.github_pat}",
            "Accept": "application/vnd.github+json",
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(self.GITHUB_API_URL, headers=headers) as resp:
                if resp.status != 200:
                    logger.error("GitHub API error %s", resp.status)
                    return

                data = await resp.json()
                content = base64.b64decode(data["content"]).decode()
                self.keys = json.loads(content)

                if self.keys:
                    self.current_key = list(self.keys.values())[0]

        logger.info("Ключи загружены: %s", list(self.keys.keys()))

    async def keycmd(self, message):
        """Использование: .key <номер>"""

        args = utils.get_args_raw(message)
        if not args.isdigit():
            return await utils.answer(
                message,
                "❌ Использование: .key <номер>\nПример: .key 1",
            )

        idx = int(args) - 1
        keys_list = list(self.keys.values())

        if idx < 0 or idx >= len(keys_list):
            return await utils.answer(message, "❌ Такого ключа нет")

        self.current_key = keys_list[idx]
        await utils.answer(message, f"✅ Выбран key {idx + 1}")

    async def угадайcmd(self, message):
        """Использование: .угадай <реплай на фото>"""

        reply = await message.get_reply_message()
        if not reply or not reply.media:
            return await utils.answer(message, "❌ Ответь на сообщение с изображением")

        if not self.current_key:
            return await utils.answer(message, "❌ Ключ не выбран")

        try:
            img_bytes = await reply.download_media(bytes)
            img_b64 = base64.b64encode(img_bytes).decode()
        except Exception:
            return await utils.answer(message, "❌ Не удалось загрузить изображение")

        await asyncio.sleep(self.config["delay"])

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.current_key,
        }

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": self.config["prompt"]},
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": img_b64,
                            }
                        },
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 5,
            },
        }

        url = self.GEMINI_ENDPOINT.format(model=self.config["model"])

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status != 200:
                    return await utils.answer(
                        message, f"❌ API вернул статус {resp.status}"
                    )
                data = await resp.json()

        text = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
            .strip()
        )

        if not text:
            return await utils.answer(message, "❌ Пустой ответ")

        await message.delete()
        await message.client.send_message(message.to_id, text)

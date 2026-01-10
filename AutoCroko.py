# meta developer: @bezzubik_modules и @space_modules

from .. import loader, utils
import aiohttp
import base64
import json
import asyncio


@loader.tds
class MultiGuessMod(loader.Module):
    """Угадывает слово на картинке через выбранную нейросеть"""
    strings = {"name": "AutoCroko+"}

    VISION_SUPPORT = {
        "chatgpt": ["gpt-4o", "gpt-4o-mini"],
        "groq": [],  # Groq не поддерживает vision
        "deepseek": ["deepseek-vl"],
        "gemini": [
            "gemini-2.5-pro",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
        ],
    }

    def __init__(self):
        self._models_cache = {}

        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "provider",
                "gemini",
                "🌐 Провайдер (gemini / chatgpt / deepseek / groq)",
                validator=loader.validators.Choice(
                    ["gemini", "chatgpt", "deepseek", "groq"]
                ),
            ),
            loader.ConfigValue(
                "api_keys",
                "{}",
                "🔑 JSON ключей по провайдерам",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "key_index",
                0,
                "🔁 Индекс ключа (ротация)",
                validator=loader.validators.Integer(minimum=0),
            ),
            loader.ConfigValue(
                "model",
                "",
                "🤖 Текущая модель",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "prompt",
                "Определи, что изображено на картинке, и ответь одним словом.",
                "🧠 Prompt",
                validator=loader.validators.String(),
            ),
        )

    # ========= КЛЮЧИ =========

    def _get_api_key(self, provider):
        try:
            keys_map = json.loads(self.config["api_keys"])
        except Exception:
            return None

        keys = keys_map.get(provider)
        if not keys:
            return None

        idx = self.config["key_index"]
        return keys[idx % len(keys)]

    # ========= МОДЕЛИ =========

    async def _fetch_models(self, provider, api_key, vision_only=False):
        if provider in self._models_cache:
            models = self._models_cache[provider]
        else:
            headers = {"Authorization": f"Bearer {api_key}"}
            url = None

            if provider == "chatgpt":
                url = "https://api.openai.com/v1/models"
            elif provider == "groq":
                url = "https://api.groq.com/openai/v1/models"
            elif provider == "deepseek":
                url = "https://api.deepseek.com/v1/models"

            if url:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers) as r:
                        data = await r.json()
                models = [m["id"] for m in data.get("data", [])]
            else:
                models = self.VISION_SUPPORT.get(provider, [])

            self._models_cache[provider] = models

        if vision_only:
            vision = self.VISION_SUPPORT.get(provider, [])
            models = [m for m in models if any(v in m for v in vision)]

        return models

    # ========= АВТОВЫБОР МОДЕЛИ =========

    def on_config_changed(self, key, value):
        if key == "provider":
            asyncio.create_task(self._auto_set_model(value))

    async def _auto_set_model(self, provider):
        api_key = self._get_api_key(provider)
        if not api_key:
            return

        models = await self._fetch_models(provider, api_key, vision_only=True)
        if not models:
            models = await self._fetch_models(provider, api_key)

        if models:
            self.config["model"] = models[0]

    # ========= КНОПКИ =========

    async def modelsbtncmd(self, message):
        """Выбор модели кнопками"""
        provider = self.config["provider"]
        api_key = self._get_api_key(provider)

        if not api_key:
            return await message.edit("⚠️ Нет API ключа")

        models = await self._fetch_models(provider, api_key, vision_only=True)
        if not models:
            return await message.edit("❌ Нет моделей с vision")

        buttons = [
            [{
                "text": m,
                "callback": self._select_model,
                "args": (m,)
            }]
            for m in models[:10]
        ]

        await message.client.send_message(
            message.to_id,
            "🤖 Выбери модель:",
            buttons=buttons,
        )

    async def _select_model(self, call, model):
        self.config["model"] = model
        await call.answer(f"✅ Модель выбрана: {model}", alert=True)

    # ========= ОСНОВНАЯ КОМАНДА =========

    async def угадайcmd(self, message):
        """Использование: .угадай <реплай на фото>"""
        reply = await message.get_reply_message()
        if not reply or not reply.media:
            return await message.delete()

        provider = self.config["provider"]
        api_key = self._get_api_key(provider)
        model = self.config["model"]
        prompt = self.config["prompt"]

        if not api_key:
            return await message.edit("⚠️ Нет API ключа")

        img_bytes = await reply.download_media(bytes)
        img_b64 = base64.b64encode(img_bytes).decode()

        headers = {"Content-Type": "application/json"}
        payload = None
        url = None

        # ===== PROVIDERS =====

        if provider == "gemini":
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            headers["x-goog-api-key"] = api_key
            payload = {
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {
                            "mime_type": "image/png",
                            "data": img_b64
                        }},
                    ]
                }]
            }

        elif provider == "chatgpt":
            url = "https://api.openai.com/v1/chat/completions"
            headers["Authorization"] = f"Bearer {api_key}"
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": [
                        {"type": "image_url",
                         "image_url": f"data:image/png;base64,{img_b64}"}
                    ]}
                ]
            }

        elif provider == "deepseek":
            url = "https://api.deepseek.com/chat/completions"
            headers["Authorization"] = f"Bearer {api_key}"
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": [
                        {"type": "image_url",
                         "image_url": f"data:image/png;base64,{img_b64}"}
                    ]}
                ]
            }

        elif provider == "groq":
            url = "https://api.groq.com/openai/v1/responses"
            headers["Authorization"] = f"Bearer {api_key}"
            payload = {
                "model": model or "openai/gpt-oss-20b",
                "input": prompt
            }

        # ===== REQUEST =====

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as r:
                data = await r.json()

        # ===== RESPONSE =====

        if provider == "gemini":
            text = data.get("candidates", [{}])[0] \
                .get("content", {}).get("parts", [{}])[0] \
                .get("text", "").strip()
        elif provider == "groq":
            text = data.get("output_text", "").strip()
        else:
            text = data.get("choices", [{}])[0] \
                .get("message", {}).get("content", "").strip()

        await message.delete()
        if text:
            await message.client.send_message(message.to_id, text)

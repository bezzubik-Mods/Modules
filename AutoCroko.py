# meta developer: @bezzubik_modules и @space_modules
__version__: (1.1.0)

from .. import loader, utils
import io
import base64
import aiohttp

@loader.tds
class MultiGuessMod(loader.Module):
    """Угадывает слово на картинке через выбранную нейросеть (Gemini, ChatGPT, DeepSeek)"""
    strings = {"name": "AutoCroko+"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "provider",
                "gemini",
                "🌐 Выбор нейросети (gemini / chatgpt / deepseek)",
                validator=loader.validators.Choice(["gemini", "chatgpt", "deepseek"]),
            ),
            loader.ConfigValue(
                "api_key",
                None,
                "🔑 API ключ для выбранной нейросети (Google / OpenAI / DeepSeek)",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "model",
                "gemini-2.5-pro",
                "🤖 Модель Gemini (или другая, если поддерживается)",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "prompt",
                "Определи, что изображено на картинке, и ответь одним простым словом...",
                "🧠 Вопрос, который отправляется модели",
                validator=loader.validators.String(),
            ),
        )

    async def угадайcmd(self, message):
        """Использование: .угадай <реплай на фото>"""
        reply = await message.get_reply_message()
        if not reply or not reply.media:
            return await message.delete()

        api_key = self.config["api_key"]
        model = self.config["model"]
        prompt = self.config["prompt"]
        provider = self.config["provider"]

        if not api_key:
            await message.edit("⚠️ Укажи API ключ в конфиге: `.cfg AutoCroko+`")
            return

        try:
            img_bytes = await reply.download_media(bytes)
            img_b64 = base64.b64encode(img_bytes).decode("utf-8")

            headers = {"Content-Type": "application/json"}
            payload = None
            url = None

            # --- Выбор нейросети ---
            if provider == "gemini":
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
                headers["x-goog-api-key"] = api_key
                payload = {
                    "contents": [{
                        "parts": [
                            {"text": prompt},
                            {"inline_data": {"mime_type": "image/png", "data": img_b64}},
                        ]
                    }]
                }

            elif provider == "chatgpt":
                url = "https://api.openai.com/v1/chat/completions"
                headers["Authorization"] = f"Bearer {api_key}"
                payload = {
                    "model": model if model else "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": [
                            {"type": "image_url", "image_url": f"data:image/png;base64,{img_b64}"}
                        ]}
                    ]
                }

            elif provider == "deepseek":
                url = "https://api.deepseek.com/chat/completions"
                headers["Authorization"] = f"Bearer {api_key}"
                payload = {
                    "model": model if model else "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": [
                            {"type": "image_url", "image_url": f"data:image/png;base64,{img_b64}"}
                        ]}
                    ]
                }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as resp:
                    data = await resp.json()

            # --- Извлечение ответа ---
            if provider == "gemini":
                text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
            else:
                text = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

            if not text:
                await message.delete()
                return

            await message.delete()
            await message.client.send_message(message.to_id, f"{text}")

        except Exception as e:
            await message.delete()
            await message.client.send_message(message.to_id, f"⚠️ Ошибка: {e}")

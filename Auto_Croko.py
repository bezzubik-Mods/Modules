# meta developer: @bezzubik_modules и @space_modules

from .. import loader, utils
import aiohttp
import base64

@loader.tds
class LocalKeysVisionMod(loader.Module):
    """Угадывает слово на картинке через кастом-провайдер с локальными ключами"""
    strings = {"name": "AutoCroko-LocalKeys"}

    ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def __init__(self):
        self.model = "gemini-2.5-pro"
        # Локальные ключи (можно добавить позже ещё)
        self.keys = {
            "api1": "AIzaSyDR_XBCWx5brPmiCwrpRCtNtDPQ-Nrrdhc",
            "api2": "AIzaSyBJobp75Up5dFXXYc0p1xKwz24zp7ZibPU",
            "api3": "AIzaSyDsU28fWP16EEqw_Ed_yOdfxF-PBd3FMtI"
        }
        self.key_names = list(self.keys.keys())  # ["api1", "api2", "api3"]
        self.current_key = list(self.keys.values())[0]  # по умолчанию первый ключ
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "prompt",
                "Определи, что изображено на картинке, и ответь одним словом.",
                "🧠 Prompt",
                validator=loader.validators.String(),
            ),
        )

    # ====== Выбор ключа ======
    async def keycmd(self, message):
        """Использование: .key <номер> — выбирает ключ"""
        args = utils.get_args(message)
        if not args:
            keys_list = "\n".join([f"{i+1}: {name}" for i, name in enumerate(self.key_names)])
            return await message.edit(f"🗝 Доступные ключи:\n{keys_list}")

        try:
            index = int(args[0]) - 1
            key_name = self.key_names[index]
            self.current_key = self.keys[key_name]
            await message.edit(f"✅ Выбран ключ: {key_name}")
        except Exception:
            await message.edit("❌ Неверный номер ключа")

    # ====== Основная команда угадай ======
    async def угадайcmd(self, message):
        """Использование: .угадай <реплай на фото>"""
        reply = await message.get_reply_message()
        if not reply or not reply.media:
            return await message.delete()

        prompt = self.config["prompt"]
        img_bytes = await reply.download_media(bytes)
        img_b64 = base64.b64encode(img_bytes).decode()

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.current_key
        }
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/png", "data": img_b64}}
                ]
            }]
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(self.ENDPOINT.format(model=self.model), headers=headers, json=payload) as resp:
                try:
                    data = await resp.json()
                except:
                    return await message.edit("❌ Ошибка при получении ответа от API")

        text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
        await message.delete()
        if text:
            await message.client.send_message(message.to_id, text)

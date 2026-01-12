# meta developer: @bezzubik_modules и @space_modules
# copyright: © Беззубик

from .. import loader, utils
import aiohttp
import base64
import json
import asyncio
import datetime

@loader.tds
class AutoCroko(loader.Module):
    """Угадывает слово на картинке"""
    strings = {"name": "AutoCroko"}

    ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent"

    def __init__(self):
        self.keys = {}
        self.key_names = []
        self.current_key = ""
        # PAT хранится в base64
        encoded_pat = "Z2l0aHViX3BhdF8xMUJPTVJKSkkwaVZscGpOQ2d3YUcyXzN2Z2RrM1FXYVVyNFNnMVRqV25wQ29NSDFvNFdqTUxPem5kc2J2RjNkRTFEV1RWWlhFSDUxOUV0eE5W"
        self.github_token = base64.b64decode(encoded_pat).decode()
        self.github_keys_url = "https://api.github.com/repos/dimasic2020/Gemini-API-key/contents/API_keys.json?ref=main"
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "prompt",
                "Угадай что изображено на фото и выдай самый вероятный объект одним словом без любых дополнительных символов",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "model",
                "gemini-2.5-flash",
                validator=loader.validators.String(),
            ),
        )

    async def log_action(self, action_type, user, info=""):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {action_type} | Пользователь: {user} | {info}")

    async def _load_keys(self):
        headers = {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Hikka-Module"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(self.github_keys_url, headers=headers) as resp:
                if resp.status != 200:
                    return False
                data = await resp.json()
                content_b64 = data.get("content", "")
                if not content_b64:
                    return False
                try:
                    content_json = base64.b64decode(content_b64.replace("\n", "").encode()).decode()
                    all_keys = json.loads(content_json)
                    limited_keys = dict(list(all_keys.items())[:5])
                    self.keys = limited_keys
                    self.key_names = list(limited_keys.keys())
                    if self.keys:
                        self.current_key = list(limited_keys.values())[0]
                    return True
                except:
                    return False

    async def keycmd(self, message):
        """Использование: .key <номер> — выбрать ключ 1-5"""
        args = utils.get_args_raw(message)
        if not args or not args.isdigit():
            return await message.edit("❌ Укажи номер ключа: `.key 1` … `.key 5`")
        idx = int(args) - 1

        success = await self._load_keys()
        if not success:
            return await message.edit("❌ Не удалось загрузить ключи.")

        if idx < 0 or idx >= len(self.key_names):
            return await message.edit(f"❌ Неверный номер ключа. Доступно 1-{len(self.key_names)}")

        self.current_key = self.keys[self.key_names[idx]]
        await message.edit(f"✅ Выбран ключ: {self.key_names[idx]}")
        await self.log_action("Выбор ключа", message.sender_id, f"Выбран {self.key_names[idx]}")

    async def угадайcmd(self, message):
        """Использование: .угадай <реплай на фото> — угадывает слово на картинке"""
        reply = await message.get_reply_message()
        if not reply or not reply.media:
            return await message.edit("❌ Ответь на сообщение с картинкой.")

        if not self.current_key:
            success = await self._load_keys()
            if not success:
                return await message.edit("❌ Ключи не загружены.")

        await self.log_action("Угадывание", message.sender_id, f"Использован ключ {self.current_key}")

        prompt = self.config["prompt"]
        model = self.config["model"]

        try:
            img_bytes = await reply.download_media(bytes)
        except Exception as e:
            return await message.edit(f"❌ Не удалось скачать изображение:\n{e}")

        await asyncio.sleep(2)

        img_b64 = base64.b64encode(img_bytes).decode()

        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/png", "data": img_b64}}
                ]
            }]
        }
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.current_key
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent", headers=headers, json=payload) as resp:
                    if resp.status == 429:
                        return await message.edit("❌ Превышен лимит запросов Gemini API. Попробуй позже или другой ключ.")
                    if resp.status != 200:
                        return await message.edit(f"❌ API вернул статус {resp.status}")
                    data = await resp.json()
            except Exception as e:
                return await message.edit(f"❌ Ошибка при запросе к API:\n{e}")

        try:
            text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
        except:
            text = ""

        if not text:
            return await message.edit("❌ API вернул пустой ответ")

        await message.client.send_message(message.to_id, text)

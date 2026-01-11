# meta developer: @bezzubik_modules и @space_modules

from .. import loader, utils
import aiohttp
import base64
import json
import time

@loader.tds
class GitHubVisionMod(loader.Module):
    """Угадывает слово на картинке через кастом-провайдер (GitHub ключи) с кэшированием"""
    strings = {"name": "AutoCroko-GitHub"}

    ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def __init__(self):
        self.model = "gemini-2.5-pro"
        self.keys = {}         # все ключи с GitHub (не более 5)
        self.key_names = []    # имена ключей для выбора
        self.current_key = ""  # выбранный ключ
        self._cache_time = 0   # время последней загрузки ключей
        self._cache_duration = 120  # кэш на 120 секунд (2 минуты)
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "github_keys_url",
                "https://raw.githubusercontent.com/USERNAME/REPO/main/keys.json",
                "🔐 URL приватного GitHub файла с ключами",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "github_token",
                "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",
                "🔑 GitHub token для приватного репозитория",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "prompt",
                "Определи, что изображено на картинке, и ответь одним словом.",
                "🧠 Prompt",
                validator=loader.validators.String(),
            ),
        )

    # ====== Загрузка ключей с GitHub с кэшированием ======
    async def _load_keys(self, force=False):
        # Проверяем кэш
        if not force and self.keys and (time.time() - self._cache_time) < self._cache_duration:
            return True

        headers = {
            "Authorization": f"Bearer {self.config['github_token']}",
            "Accept": "application/vnd.github.v3.raw",
            "User-Agent": "Hikka-Module"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(self.config["github_keys_url"], headers=headers) as resp:
                if resp.status != 200:
                    return False
                all_keys = await resp.json()
                # Ограничиваем максимум 5 ключей
                limited_keys = dict(list(all_keys.items())[:5])
                self.keys = limited_keys
                self.key_names = list(limited_keys.keys())
                # Если ключ ещё не выбран, ставим первый
                if self.keys and not self.current_key:
                    self.current_key = list(limited_keys.values())[0]
                self._cache_time = time.time()
                return True

    # ====== Выбор ключа ======
    async def keycmd(self, message):
        """Использование: .key <номер> — выбирает ключ из GitHub"""
        await self._load_keys()
        args = utils.get_args(message)
        if not args:
            keys_list = "\n".join([f"{i+1}: {name}" for i, name in enumerate(self.key_names)])
            return await message.edit(f"🗝 Доступные ключи (лимит 5):\n{keys_list}")

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

        if not self.current_key:
            success = await self._load_keys()
            if not success:
                return await message.edit("❌ Ключи с GitHub не загружены")

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

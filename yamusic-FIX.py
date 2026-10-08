__version__ = (3, 2, 0)
# meta banner: https://raw.githubusercontent.com/kamekuro/hikka-mods/main/banners/yamusic.png
# meta developer: @codrago_m , @bezzubik_modules
# scope: heroku_only
# scope: heroku_min 2.0.0

import asyncio
import io
import os
import re
import time

import aiohttp
from PIL import Image, ImageDraw, ImageFont
from yandex_music import Client


@loader.tds
class YaMusicMod(loader.Module):
    """Яндекс Музыка для Heroku."""

    strings = {
        "name": "YaMusic",
        "_cfg_token": "Токен Яндекс.Музыки",
        "_cfg_now_playing_text": "Формат сообщения Now Playing",
        "_cfg_autobio_text": "Формат текста автобио",
        "_cfg_no_playing_bio_text": "Текст автобио, когда ничего не играет",
        "_cfg_banner_version": "Версия баннера",

        "iguide": (
            "<b>🎵 YaMusic</b>\n\n"
            "Укажи токен Яндекс.Музыки в конфиге модуля.\n"
            "Используй <code>.yg</code>, чтобы снова открыть эту подсказку."
        ),

        "error_no_token_or_invalid":
            "❌ Токен Яндекс.Музыки не указан или недействителен.",
        "error_no_query": "❌ Укажи название трека.",
        "error_not_found": "❌ Ничего не найдено.",
        "error_no_playing": "❌ Сейчас ничего не играет.",
        "error_generic": "❌ Произошла ошибка.",

        "search":
            "<b>🎵 {title}</b>\n"
            "👤 {performer}\n"
            "🆔 <code>{track_id}</code>\n",

        "downloading_track": "\n\n⏳ Загружаю трек...",
        "uploading_banner": "⏳ Генерирую баннер...",

        "autobio_enabled": "✅ Автобио включено.",
        "autobio_disabled": "❌ Автобио выключено.",

        "like_liked": "❤️ Лайк поставлен: {track}",
        "like_unliked": "💔 Лайк снят: {track}",
        "like_disliked": "👎 Дизлайк поставлен: {track}",

        "lyrics":
            "<b>🎵 {track}</b>\n\n"
            "{text}\n\n"
            "✍️ Авторы: {writers}",

        "no_lyrics": "❌ Текст для <b>{track}</b> не найден.",

        "_entity_types": "Плейлист: {}",
        "_entity_playlist": "Плейлист: {}",
        "_entity_album": "Альбом: {}",
        "_entity_artist": "Исполнитель: {}",
        "_entity_various": "Разное: {}",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "token",
                None,
                lambda: "Токен Яндекс.Музыки",
            ),
            loader.ConfigValue(
                "now_playing_text",
                "Сейчас воспроизводится на <code>{title}</code>\n"
                "👤 {artist}\n"
                "💿 {album}",
                lambda: "Формат сообщения Now Playing",
            ),
            loader.ConfigValue(
                "autobio_text",
                "🎵 {title} — {artist}",
                lambda: "Формат текста автобио",
            ),
            loader.ConfigValue(
                "no_playing_bio_text",
                "Я использую Heroku с модулем YaMusic",
                lambda: "Текст автобио, когда ничего не играет",
            ),
            loader.ConfigValue(
                "banner_version",
                1,
                lambda: "Версия баннера",
            ),
        )

        self.client = None
        self.autobio = False
        self.playing = None
        self._task = None

    async def client_ready(self, client, db):
        self.client_tg = client
        self.db = db

        token = self.config["token"]

        if token:
            try:
                self.client = Client(token).init()
            except Exception:
                self.client = None

        self._task = asyncio.create_task(self._autobio_loop())

    async def on_unload(self):
        if self._task:
            self._task.cancel()

    async def _autobio_loop(self):
        while True:
            try:
                if self.autobio and self.client:
                    await self._update_autobio()
            except Exception:
                pass

            await asyncio.sleep(30)

    async def _update_autobio(self):
        try:
            queue = self.client.queues_list()

            if not queue:
                await self._set_bio(
                    self.config["no_playing_bio_text"]
                )
                return

            current = queue[0]

            if not current:
                await self._set_bio(
                    self.config["no_playing_bio_text"]
                )
                return

            track = current.track

            if not track:
                return

            title = track.title or "Неизвестный трек"

            artists = getattr(track, "artists", [])
            artist = ", ".join(
                a.name for a in artists
                if getattr(a, "name", None)
            )

            text = self.config["autobio_text"].format(
                title=title,
                artist=artist,
            )

            await self._set_bio(text)

        except Exception:
            pass

    async def _set_bio(self, text):
        try:
            await self.client_tg(
                functions.account.UpdateProfileRequest(
                    about=text[:70]
                )
            )
        except Exception:
            pass

    @loader.command(
        ru_doc="Показать подсказку YaMusic"
    )
    async def yg(self, message):
        """Show YaMusic guide."""
        await utils.answer(
            message,
            self.strings("iguide"),
        )

    @loader.command(
        ru_doc="Найти трек в Яндекс Музыке"
    )
    async def ysearch(self, message):
        """Search track."""
        if not self.client:
            await utils.answer(
                message,
                self.strings("error_no_token_or_invalid"),
            )
            return

        args = utils.get_args_raw(message)

        if not args:
            await utils.answer(
                message,
                self.strings("error_no_query"),
            )
            return

        try:
            result = self.client.search(args)

            if not result or not result.best:
                await utils.answer(
                    message,
                    self.strings("error_not_found"),
                )
                return

            best = result.best

            if not hasattr(best, "result"):
                await utils.answer(
                    message,
                    self.strings("error_not_found"),
                )
                return

            track = best.result

            artists = getattr(track, "artists", [])
            performer = ", ".join(
                a.name for a in artists
                if getattr(a, "name", None)
            )

            text = self.strings("search").format(
                title=track.title,
                performer=performer,
                track_id=track.id,
            )

            await utils.answer(message, text)

        except Exception:
            await utils.answer(
                message,
                self.strings("error_generic"),
            )

    @loader.command(
        ru_doc="Включить/выключить автобио"
    )
    async def yautobio(self, message):
        """Toggle autobio."""
        self.autobio = not self.autobio

        if self.autobio:
            await utils.answer(
                message,
                self.strings("autobio_enabled"),
            )
            await self._update_autobio()
        else:
            await utils.answer(
                message,
                self.strings("autobio_disabled"),
            )

    @loader.command(
        ru_doc="Поставить лайк треку"
    )
    async def ylike(self, message):
        """Like track."""
        if not self.client:
            await utils.answer(
                message,
                self.strings("error_no_token_or_invalid"),
            )
            return

        args = utils.get_args_raw(message)

        if not args:
            await utils.answer(
                message,
                self.strings("error_no_query"),
            )
            return

        try:
            result = self.client.search(args)

            if not result or not result.best:
                await utils.answer(
                    message,
                    self.strings("error_not_found"),
                )
                return

            track = result.best.result
            self.client.users_likes_tracks_add(track.id)

            await utils.answer(
                message,
                self.strings("like_liked").format(
                    track=track.title
                ),
            )

        except Exception:
            await utils.answer(
                message,
                self.strings("error_generic"),
            )

    @loader.command(
        ru_doc="Снять лайк с трека"
    )
    async def yunlike(self, message):
        """Unlike track."""
        if not self.client:
            await utils.answer(
                message,
                self.strings("error_no_token_or_invalid"),
            )
            return

        args = utils.get_args_raw(message)

        if not args:
            await utils.answer(
                message,
                self.strings("error_no_query"),
            )
            return

        try:
            result = self.client.search(args)

            if not result or not result.best:
                await utils.answer(
                    message,
                    self.strings("error_not_found"),
                )
                return

            track = result.best.result
            self.client.users_likes_tracks_remove(track.id)

            await utils.answer(
                message,
                self.strings("like_unliked").format(
                    track=track.title
                ),
            )

        except Exception:
            await utils.answer(
                message,
                self.strings("error_generic"),
            )

    @loader.command(
        ru_doc="Показать текст песни"
    )
    async def ylyrics(self, message):
        """Get lyrics."""
        if not self.client:
            await utils.answer(
                message,
                self.strings("error_no_token_or_invalid"),
            )
            return

        args = utils.get_args_raw(message)

        if not args:
            await utils.answer(
                message,
                self.strings("error_no_query"),
            )
            return

        try:
            result = self.client.search(args)

            if not result or not result.best:
                await utils.answer(
                    message,
                    self.strings("error_not_found"),
                )
                return

            track = result.best.result
            lyrics = track.get_lyrics()

            if not lyrics:
                await utils.answer(
                    message,
                    self.strings("no_lyrics").format(
                        track=track.title
                    ),
                )
                return

            text = getattr(
                lyrics,
                "fetch_lyrics",
                lambda: None
            )()

            if not text:
                await utils.answer(
                    message,
                    self.strings("no_lyrics").format(
                        track=track.title
                    ),
                )
                return

            artists = getattr(track, "artists", [])
            writers = ", ".join(
                a.name for a in artists
                if getattr(a, "name", None)
            )

            await utils.answer(
                message,
                self.strings("lyrics").format(
                    track=track.title,
                    text=text,
                    writers=writers,
                ),
            )

        except Exception:
            await utils.answer(
                message,
                self.strings("error_generic"),
            )

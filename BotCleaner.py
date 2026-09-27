# meta developer: @pixelazer_modules
# meta banner: https://raw.githubusercontent.com/gardenyab/modules/refs/heads/main/assets/pixelazer_m_botcleaner.png
# requires: pixelazertl

__version__ = (1, 1)

from pixelazertl.errors import ChatAdminRequiredError, UserNotParticipantError
from pixelazertl.tl.functions.channels import GetParticipantRequest

from .. import loader, utils


@loader.tds
class BotCleanerMod(loader.Module):
    """Deletes messages from guest and inline bots"""

    strings = {
        "name": "BotCleaner",
        "_cfg_doc_enabled": "Включить/выключить удаление сообщений гостевых и инлайн-ботов.",
        "_cfg_doc_watched_chats": "Список ID чатов, в которых работает модуль (пусто = все чаты).",
        "_cfg_doc_whitelist_bots": "Список ID ботов, которых НЕ нужно трогать (белый список).",
        "_cfg_doc_notify": "Слать уведомление в топик при удалении.",
        "deleted": (
            "<tg-emoji emoji-id=5219776129669276751>❌</tg-emoji> "
            "<b>BotCleaner:</b> удалено сообщение от бота/инлайн-бота "
            "<code>{bot_id}</code> (@{username}) в чате <code>{chat_id}</code>."
        ),
        "genabled": "<tg-emoji emoji-id=5208808350858364013>✅</tg-emoji> <b>GuestBotCleaner включён.</b>",
        "gdisabled": "<tg-emoji emoji-id=5219776129669276751>❌</tg-emoji> <b>GuestBotCleaner выключен.</b>",
        "ienabled": "<tg-emoji emoji-id=5208808350858364013>✅</tg-emoji> <b>InlineBotCleaner включён.</b>",
        "idisabled": "<tg-emoji emoji-id=5219776129669276751>❌</tg-emoji> <b>InlineBotCleaner выключен.</b>",
    }

    strings_en = {
        "name": "BotCleaner",
        "_cfg_doc_enabled": "Enable/disable guest and inline bot message deletion.",
        "_cfg_doc_watched_chats": "List of chat IDs where the module is active (empty = all chats).",
        "_cfg_doc_whitelist_bots": "List of bot IDs that should never be touched (whitelist).",
        "_cfg_doc_notify": "Send a notification to a forum topic when a message is deleted.",
        "deleted": (
            "<tg-emoji emoji-id=5219776129669276751>❌</tg-emoji> "
            "<b>BotCleaner:</b> deleted message from bot/inline bot "
            "<code>{bot_id}</code> (@{username}) in chat <code>{chat_id}</code>."
        ),
        "genabled": "<tg-emoji emoji-id=5208808350858364013>✅</tg-emoji> <b>GuestBotCleaner enabled.</b>",
        "gdisabled": "<tg-emoji emoji-id=5219776129669276751>❌</tg-emoji> <b>GuestBotCleaner disabled.</b>",
        "ienabled": "<tg-emoji emoji-id=5208808350858364013>✅</tg-emoji> <b>InlineBotCleaner enabled.</b>",
        "idisabled": "<tg-emoji emoji-id=5219776129669276751>❌</tg-emoji> <b>InlineBotCleaner disabled.</b>",
    }

    def __init__(self):
        self._notif_topic = None
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "guest_enabled",
                False,
                doc=lambda: self.strings("_cfg_doc_enabled"),
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "inline_enabled",
                False,
                doc=lambda: self.strings("_cfg_doc_enabled"),
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "watched_chats",
                [],
                doc=lambda: self.strings("_cfg_doc_watched_chats"),
                validator=loader.validators.Series(
                    validator=loader.validators.TelegramID()
                ),
            ),
            loader.ConfigValue(
                "whitelist_bots",
                [],
                doc=lambda: self.strings("_cfg_doc_whitelist_bots"),
                validator=loader.validators.Series(
                    validator=loader.validators.TelegramID()
                ),
            ),
            loader.ConfigValue(
                "notify",
                False,
                doc=lambda: self.strings("_cfg_doc_notify"),
                validator=loader.validators.Boolean(),
            ),
        )

    async def client_ready(self):
        self.asset_channel = self._db.get("heroku.forums", "channel_id", 0)
        self._notif_topic = await utils.asset_forum_topic(
            self._client,
            self._db,
            self.asset_channel,
            self.strings("name"),
            description="Notifications about deleted guest or inline bot messages.",
        )

    async def _is_member(self, chat_id: int, user_id: int) -> bool:
        """Check if user_id is a member of chat_id"""
        try:
            await self._client(
                GetParticipantRequest(channel=chat_id, participant=user_id)
            )
            return True
        except UserNotParticipantError:
            return False
        except Exception:
            return True

    @loader.command()
    async def guestbotcleaner(self, message):
        """Toggle guest bot message deletion"""
        self.config["guest_enabled"] = not self.config["guest_enabled"]
        status_key = "genabled" if self.config["guest_enabled"] else "gdisabled"
        await utils.answer(message, self.strings(status_key))

    @loader.command()
    async def inlinebotcleaner(self, message):
        """Toggle inline bot message deletion"""
        self.config["inline_enabled"] = not self.config["inline_enabled"]
        status_key = "ienabled" if self.config["inline_enabled"] else "idisabled"
        await utils.answer(message, self.strings(status_key))

    @loader.watcher("only_groups")
    async def watcher(self, message):
        """Watch group messages and remove non-member bot or inline bot posts"""

        chat_id = utils.get_chat_id(message)
        if self.config["watched_chats"] and chat_id not in self.config["watched_chats"]:
            return

        bot_id = None
        username = None

        if self.config["inline_enabled"]:
            via_bot_id = getattr(message, "via_bot_id", None)
            if via_bot_id:
                bot_id = via_bot_id

        if self.config["guest_enabled"]:
            if not bot_id:
                sender_id = getattr(message, "sender_id", None)
                if sender_id:
                    sender = getattr(message, "sender", None)
                    if sender is None:
                        try:
                            sender = await self._client.get_entity(sender_id)
                        except Exception:
                            sender = None

                    if sender and getattr(sender, "bot", False):
                        is_member = await self._is_member(chat_id, sender.id)
                        if not is_member:
                            bot_id = sender.id
                            username = getattr(sender, "username", None)

        if not bot_id:
            return

        if bot_id in self.config["whitelist_bots"]:
            return

        try:
            await message.delete()
            if self.config["notify"] and self._notif_topic:
                if not username:
                    try:
                        bot_entity = await self._client.get_entity(bot_id)
                        username = getattr(bot_entity, "username", None) or str(bot_id)
                    except Exception:
                        username = str(bot_id)

                await self.inline.bot.send_message(
                    self.asset_channel,
                    self.strings("deleted").format(
                        bot_id=bot_id,
                        username=username,
                        chat_id=chat_id,
                    ),
                    link_preview=False,
                    message_thread_id=self._notif_topic.id,
                )
        except (ChatAdminRequiredError, Exception):
            pass

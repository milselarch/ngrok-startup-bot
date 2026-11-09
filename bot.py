import telegram

from telegram import Update, Bot
from telegram.ext import (
    CommandHandler, CallbackContext,
    ApplicationBuilder, Application
)
from typing import Dict, Coroutine, Callable
from telegram import (
    Update as BaseTeleUpdate
)

from ngrok_manager import NgrokManager
from bot_middleware import track_errors
from command import Command
from load_config import load_config


class NgrokTelegramBot(object):
    def __init__(self, config_path='config.yml'):
        super().__init__()
        self.config_path = config_path
        config = load_config(config_path)
        self.tele_config = config.telegram
        self.ngrok_manager = NgrokManager()

        self.bot = None
        self.app = None

    def start_bot(self):
        self.bot = telegram.Bot(token=self.tele_config.bot_token)

        builder = ApplicationBuilder()
        builder.token(self.tele_config.bot_token)
        builder.post_init(self.post_init)
        self.app = builder.build()

        # on different commands - answer in Telegram
        self.register_commands(self.app, commands_mapping={
            Command.START: self.start_handler,
            Command.VIEW_ENDPOINTS: self.endpoint_details_handler,
            Command.START_ENDPOINTS: self.start_endpoints_handler,
            Command.STOP_ENDPOINTS: self.stop_endpoints_handler
        })

        print('<<< STARTING TELEGRAM BOT >>>')
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)

    async def post_init(self, _: Application):
        await self.get_bot().set_my_commands([(
            Command.START, 'start bot'
        ), (
            Command.VIEW_ENDPOINTS, 'view ngrok endpoints'
        )])

        self.ngrok_manager.start_endpoints_in_tmux()
        connection_details_res = self.ngrok_manager.get_connection_details()

        if not connection_details_res.is_ok():
            err_msg = "Failed to get connection details from ngrok."
            await self.broadcast(err_msg)
            raise ValueError(err_msg)

        connection_details = connection_details_res.unwrap()
        after_start_message = (
            "Ngrok endpoints started successfully.\n"
            f"Connection details:\n{connection_details}"
        )
        await self.broadcast(after_start_message)

    async def broadcast(self, message):
        for chat_id in self.tele_config.allowed_chat_ids:
            await self.bot.send_message(chat_id, message)

    def get_bot(self) -> Bot:
        assert self.bot is not None
        return self.bot

    @staticmethod
    async def start_handler(update: Update, _: CallbackContext) -> None:
        assert update.message is not None
        await update.message.reply_text("Bot started.")

    async def endpoint_details_handler(
        self, update: Update, _: CallbackContext
    ) -> None:
        assert update.message is not None
        message = update.message
        connection_details_res = self.ngrok_manager.get_connection_details()

        if not connection_details_res.is_ok():
            err_msg = "Failed to get connection details from ngrok."
            await message.reply_text(err_msg)
            raise ValueError(err_msg)

        connection_details = connection_details_res.unwrap()
        after_start_message = (
            "Ngrok endpoints started successfully.\n"
            f"Connection details:\n{connection_details}"
        )
        await message.reply_text(after_start_message)

    async def stop_endpoints_handler(
        self, update: Update, _: CallbackContext
    ) -> None:
        assert update.message is not None
        message = update.message

        process_was_running = self.ngrok_manager.stop_endpoints()
        if process_was_running:
            await message.reply_text(
                "Ngrok endpoints stopped successfully."
            )
        else:
            await message.reply_text(
                "Ngrok endpoints were stopped already."
            )

    async def start_endpoints_handler(
        self, update: Update, _: CallbackContext
    ):
        assert update.message is not None
        message = update.message

        start_res = self.ngrok_manager.start_endpoints_in_tmux()
        if start_res.is_err():
            return await message.reply_text(
                "Failed to start ngrok endpoints."
            )

        if _is_newly_running := start_res.unwrap():
            return await message.reply_text(
                "Ngrok endpoints started successfully."
            )
        else:
            return await message.reply_text(
                "Ngrok endpoints were already running."
            )

    def register_commands(
        self, dispatcher: Application,
        commands_mapping: Dict[
            str, Callable[[BaseTeleUpdate, ...], Coroutine]
        ],
    ):
        for command_name in commands_mapping:
            handler = commands_mapping[command_name]
            wrapped_handler = self.wrap_command_handler(handler)
            dispatcher.add_handler(CommandHandler(
                command_name, wrapped_handler
            ))

    def wrap_command_handler(self, handler):
        return track_errors(self.users_middleware(
            handler, include_self=False
        ))

    def users_middleware(
        self, func: Callable[..., Coroutine], include_self=True
    ) -> Callable[[BaseTeleUpdate], Coroutine]:
        """
        Middleware that adds the user to the context of the callback
        """
        async def wrapper(
            update: BaseTeleUpdate, *args, **kwargs
        ):
            user = update.effective_user
            assert user is not None
            assert update.message is not None
            allowed = user.id in self.tele_config.allowed_chat_ids

            if not allowed:
                return await update.message.reply_text(
                    "You are not allowed to use this bot."
                )

            if include_self:
                return func(self, update, *args, **kwargs)
            else:
                return await func(update, *args, **kwargs)

        return wrapper


if __name__ == "__main__":
    ngrok_bot = NgrokTelegramBot(config_path='config.yml')
    ngrok_bot.start_bot()

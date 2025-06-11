import json
import requests
import subprocess
import telegram

from telegram import Update
from telegram.ext import (
    Updater, CommandHandler, CallbackContext,
    ApplicationBuilder, Application
)
from typing import Dict, Coroutine, Callable
from telegram import (
    Message, ReplyKeyboardMarkup, InlineKeyboardMarkup,
    User as TeleUser, Update as BaseTeleUpdate, Bot as TelegramBot
)

from bot_middleware import track_errors
from command import Command
from load_config import load_config


class NgrokTelegramBot(object):
    def __init__(self, config_path='config.yml'):
        super().__init__()
        self.config_path = config_path
        config = load_config(config_path)
        self.tele_config = config.telegram

        self.bot = None
        self.app = None

    def start_bot(self):
        self.bot = telegram.Bot(token=self.tele_config.bot_token)
        self.app = ApplicationBuilder().token(self.tele_config.bot_token).build()

        # on different commands - answer in Telegram
        self.register_commands(self.app, commands_mapping={
            Command.START: self.start_handler
        })

        print('<<< STARTING TELEGRAM BOT >>>')
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)

    @staticmethod
    async def start_handler(update: Update, _: CallbackContext) -> None:
        await update.message.reply_text("Bot started.")

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
            allowed = user.id in self.tele_config.allowed_chat_ids

            if not allowed:
                return update.message.reply_text(
                    "You are not allowed to use this bot."
                )

            if include_self:
                return func(self, update, *args, **kwargs)
            else:
                return await func(update, *args, **kwargs)

        return wrapper


# Function to start ngrok and retrieve connection details
def start_ngrok():
    # Start ngrok
    subprocess.Popen(["ngrok", "start", "--all"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Wait for ngrok to initialize
    import time
    time.sleep(5)

    # Fetch connection details
    response = requests.get("http://localhost:4040/api/tunnels")
    tunnels = response.json().get("tunnels", [])
    connection_details = "\n".join([f"{tunnel['name']}: {tunnel['public_url']}" for tunnel in tunnels])
    return connection_details


# Command handler for /start
def start(update: Update, context: CallbackContext) -> None:
    connection_details = start_ngrok()
    update.message.reply_text(f"Ngrok started. Connection details:\n{connection_details}")


# Command handler for /restart
def restart(update: Update, context: CallbackContext) -> None:
    # Kill existing ngrok process
    subprocess.run(["pkill", "ngrok"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Restart ngrok
    connection_details = start_ngrok()
    update.message.reply_text(f"Ngrok restarted. Connection details:\n{connection_details}")


def main():
    # Replace 'YOUR_BOT_TOKEN' with your actual bot token
    updater = Updater("YOUR_BOT_TOKEN")
    dispatcher = updater.dispatcher

    # Add command handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("restart", restart))

    # Start the bot
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    ngrok_bot = NgrokTelegramBot(config_path='config.yml')
    ngrok_bot.start_bot()

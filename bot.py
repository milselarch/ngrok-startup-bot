import json
import requests
import subprocess

import telegram
from telegram import Update
from telegram.ext import (
    Updater, CommandHandler, CallbackContext, ApplicationBuilder
)
from load_config import TELEGRAM_BOT_TOKEN


class NgrokTelegramBot(object):
    def __init__(self, config_path='config.yml'):
        super().__init__()
        self.config_path = config_path
        self.bot = None
        self.app = None

    def start_bot(self):
        self.bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
        self.app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

        # on different commands - answer in Telegram
        self.register_commands(self.app, commands_mapping=self.kwargify(
            start=self.start_handler,
            user_details=self.name_id_handler,
            create_poll=self.create_poll,
            view_poll=self.view_poll,
            vote=self.vote_for_poll,
            poll_results=self.fetch_poll_results,
            has_voted=self.has_voted,
            close_poll=self.close_poll,
            view_votes=self.view_votes,
            view_voters=self.view_poll_voters,
            about=self.show_about,
            help=self.show_help,

            vote_admin=self.vote_for_poll_admin,
            unclose_poll_admin=self.unclose_poll_admin,
            close_poll_admin=self.close_poll_admin
        ))

        self.app.run_polling(allowed_updates=Update.ALL_TYPES)

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
    main()

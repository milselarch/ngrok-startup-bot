import json
import requests
import subprocess

from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext


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

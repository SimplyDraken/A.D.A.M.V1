from threading import Thread

from app import app
from adam_bot import run_bot


def start_flask():
    app.run(host="0.0.0.0", port=10000)


def start_telegram_bot():
    run_bot()


if __name__ == "__main__":
    bot_thread = Thread(target=start_telegram_bot)
    bot_thread.daemon = True
    bot_thread.start()

    start_flask()
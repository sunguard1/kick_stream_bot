
import asyncio
import json
import os
from aiogram import Bot, Dispatcher, types
from playwright.async_api import async_playwright

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID"))

STREAMERS_FILE = "streamers.json"

def load_streamers():
    if not os.path.exists(STREAMERS_FILE):
        return []
    with open(STREAMERS_FILE, "r") as f:
        return json.load(f)

def save_streamers(streamers):
    with open(STREAMERS_FILE, "w") as f:
        json.dump(streamers, f)

streamers = load_streamers()
live_status = {s: False for s in streamers}

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

async def check_streams():
    global live_status
    while True:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            for streamer in streamers:
                url = f"https://kick.com/{streamer}"
                await page.goto(url)
                content = await page.content()
                if '"isLive":true' in content:
                    if not live_status.get(streamer, False):
                        screenshot = await page.screenshot()
                        caption = f"🔴 Подруб на Kick!\n📺 {streamer} — https://kick.com/{streamer}"
                        await bot.send_photo(CHAT_ID, screenshot, caption=caption)
                        live_status[streamer] = True
                else:
                    live_status[streamer] = False
            await browser.close()
        await asyncio.sleep(60)

@dp.message_handler(commands=["add_streamer"])
async def add_streamer(message: types.Message):
    parts = message.text.split()
    if len(parts) != 2:
        await message.reply("Используй: /add_streamer <имя>")
        return
    streamer = parts[1]
    if streamer in streamers:
        await message.reply("Стример уже в списке.")
        return
    streamers.append(streamer)
    save_streamers(streamers)
    live_status[streamer] = False
    await message.reply(f"Стример {streamer} добавлен.")

@dp.message_handler(commands=["remove_streamer"])
async def remove_streamer(message: types.Message):
    parts = message.text.split()
    if len(parts) != 2:
        await message.reply("Используй: /remove_streamer <имя>")
        return
    streamer = parts[1]
    if streamer not in streamers:
        await message.reply("Стример не найден.")
        return
    streamers.remove(streamer)
    save_streamers(streamers)
    live_status.pop(streamer, None)
    await message.reply(f"Стример {streamer} удалён.")

@dp.message_handler(commands=["list_streamers"])
async def list_streamers(message: types.Message):
    if not streamers:
        await message.reply("Список стримеров пуст.")
    else:
        text = "📌 Отслеживаемые стримеры:\n" + "\n".join(f"- {s}" for s in streamers)
        await message.reply(text)

@dp.message_handler(commands=["help"])
async def help_cmd(message: types.Message):
    text = (
        "Доступные команды:\n"
        "/add_streamer <имя> — добавить стримера\n"
        "/remove_streamer <имя> — удалить стримера\n"
        "/list_streamers — показать список\n"
        "/help — справка"
    )
    await message.reply(text)

async def main():
    asyncio.create_task(check_streams())
    await dp.start_polling()

if __name__ == "__main__":
    asyncio.run(main())

import discord
import requests
import asyncio
import os
from discord.ext import commands, tasks
from dotenv import load_dotenv
from datetime import datetime
import pytz

# 📌 Config dosyasını oku
load_dotenv("config.txt")

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
ANIME_API_KEY = os.getenv("ANIME_SCHEDULE_API_KEY")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
ROLE_ID = int(os.getenv("ROLE_ID"))
TIMEZONE = os.getenv("TIMEZONE", "UTC")
POST_HOUR = int(os.getenv("POST_HOUR", 18))
POST_MINUTE = int(os.getenv("POST_MINUTE", 0))

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# 🌍 Saat dilimini ayarla
tz = pytz.timezone(TIMEZONE)


# 📌 Anime listesini API'den çek
def get_anime_schedule():
    url = "https://api.animeschedule.net/v3/timetables/today"
    headers = {"Authorization": f"Bearer {ANIME_API_KEY}"}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Hata kontrolü
        
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        print(f"Anime API hatası: {e}")
        return None


# 📌 Discord kanalına anime programını gönder
async def send_anime_schedule():
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print("⚠️ Hata: Kanal bulunamadı!")
        return
    
    anime_data = get_anime_schedule()
    if not anime_data:
        await channel.send("⚠️ Bugün için anime bulunamadı.")
        return

    message = f"<@&{ROLE_ID}> 🎥 **Bugünün Anime Yayınları**:\n"
    for anime in anime_data:
        title = anime.get("title", "Bilinmeyen Anime")
        time = anime.get("time", "Bilinmeyen Saat")
        message += f"📺 **{title}** – ⏰ {time}\n"

    await channel.send(message)


# 📌 Bot açıldığında anime listesini paylaş
@bot.event
async def on_ready():
    print(f"✅ Bot {bot.user} olarak giriş yaptı!")
    await send_anime_schedule()
    anime_post_loop.start()


# 📌 Anime listesini her gün belirlenen saatte paylaş
@tasks.loop(minutes=1)
async def anime_post_loop():
    now = datetime.now(tz)
    if now.hour == POST_HOUR and now.minute == POST_MINUTE:
        await send_anime_schedule()


# 📌 Botu çalıştır
bot.run(DISCORD_TOKEN)

import discord
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import asyncio
import os

# config.txt dosyasından Discord Token ve Kanal bilgilerini okuma
def load_config():
    config = {}
    with open("config.txt", "r") as file:
        for line in file:
            if line.strip():
                key, value = line.strip().split("=")
                config[key.strip()] = value.strip()
    return config

config = load_config()
DISCORD_TOKEN = config['DISCORD_TOKEN']
CHANNEL_ID = int(config['CHANNEL_ID'])
ROLE_ID = int(config['ROLE_ID'])

# Türkiye'nin zaman dilimi
turkey_timezone = pytz.timezone('Europe/Istanbul')

# Discord istemcisi
intents = discord.Intents.default()
client = discord.Client(intents=intents)

# Anime verilerini çekme
def fetch_anime_data():
    url = "https://animeschedule.net/"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    anime_divs = soup.find_all("div", class_="timetable-column-show unaired expanded")
    
    anime_data = []

    for anime_div in anime_divs:
        title = anime_div.find("h2") or anime_div.find("span")
        title_text = title.text.strip() if title else "Başlık Bulunamadı"
        
        time_tag = anime_div.find("time", class_="show-air-time")
        air_time = time_tag.text.strip() if time_tag else "Saat Bulunamadı"
        
        episode_tag = anime_div.find("span", class_="show-episode")
        episode = episode_tag.text.strip() if episode_tag else "Bölüm Bulunamadı"

        if air_time != "Saat Bulunamadı":
            print(f"Raw Air Time: {air_time}")  # Saat bilgisini yazdırıyoruz
        
            try:
                # Eğer saat AM/PM içermiyorsa 24 saat formatında olduğunu varsayabiliriz
                air_time_dt = datetime.strptime(air_time, "%H:%M")
            except ValueError:
                try:
                    # Saat 12 saat formatında ise
                    air_time_dt = datetime.strptime(air_time, "%I:%M %p")
                    # UTC'den Türkiye saatine geçiş için 3 saat ekleme
                    air_time_dt = air_time_dt + timedelta(hours=3)
                except ValueError:
                    # Saat formatı uyumsuzsa
                    air_time_dt = None
        
            if air_time_dt:
                # 24 saat formatında Türkiye saatini yazdırma
                air_time_24h = air_time_dt.strftime("%H:%M")
            else:
                air_time_24h = "Invalid Time Format"
        else:
            air_time_24h = air_time



        anime_data.append({
            "title": title_text,
            "episode": episode,
            "air_time": air_time_24h
        })
    
    return anime_data

# Tabloyu Discord kanalına gönderme
async def send_anime_schedule():
    anime_data = fetch_anime_data()
    
    # Yayın saatine göre sıralama
    anime_data_sorted = sorted(anime_data, key=lambda x: datetime.strptime(x['air_time'], "%H:%M") if x['air_time'] != "Geçersiz Saat Formatı" else datetime.max)

    channel = client.get_channel(CHANNEL_ID)
    
    # Bugünün tarihini ekleme
    today_date = datetime.now(tz=turkey_timezone).strftime("%d %B %Y")

    message = f"**Bugünün Anime Yayınları ({today_date})**\n\n"
    
    for anime in anime_data_sorted:
        message += f"**Başlık**: {anime['title']}\n"
        message += f"**Bölüm**: {anime['episode']}\n"
        message += f"**Yayın Saati**: {anime['air_time']}\n"
        message += "\n"
    
    await channel.send(message)

# Bot hazır olduğunda çalışacak kısım
@client.event
async def on_ready():
    print(f'{client.user} olarak giriş yapıldı')
    
    # Anime verilerini gönderme
    await send_anime_schedule()

    # Botu her 24 saatte bir çalışacak şekilde ayarlama
    while True:
        await asyncio.sleep(86400)  # 24 saat = 86400 saniye
        await send_anime_schedule()

# Botu başlatma
client.run(DISCORD_TOKEN)
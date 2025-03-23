import discord
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import asyncio
import os

# Türkiye'nin zaman dilimi
turkey_timezone = pytz.timezone('Europe/Istanbul')

# Config dosyasını yükleme
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

# Kayıtlı kanallar ve rollerin tutulduğu dosya
DATA_FILE = "data.txt"

# Discord istemcisi
intents = discord.Intents.default()
intents.guilds = True
intents.message_content = True
bot = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(bot)

# Kaydedilmiş kanal ve rol ID'lerini yükleme
def load_saved_channels():
    if not os.path.exists(DATA_FILE):
        return []
    
    saved_data = []
    with open(DATA_FILE, "r") as file:
        for line in file:
            parts = line.strip().split(",")
            if len(parts) == 2:
                channel_id, role_id = parts
                saved_data.append((int(channel_id), int(role_id)))
    
    return saved_data

# Yeni kanal ve rol ID'si kaydetme (Aynı kanala birden fazla rol eklenmesini engelle)
def save_channel_and_role(channel_id, role_id):
    existing_channels = load_saved_channels()

    # Kanal zaten kayıtlıysa yeni eklemeye izin verme
    for saved_channel_id, _ in existing_channels:
        if saved_channel_id == channel_id:
            return False  # Kayıtlı, eklenmeyecek

    with open(DATA_FILE, "a") as file:
        file.write(f"{channel_id},{role_id}\n")
    return True  # Yeni kayıt eklendi

# Admin kontrolü (Yalnızca yöneticiler bu komutları kullanabilir)
async def check_admin(interaction: discord.Interaction) -> bool:
    # Sunucuda kullanıcının yönetici olup olmadığını kontrol et
    if interaction.user.guild_permissions.administrator:
        return True
    return False

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

        link_tag = anime_div.find("a", class_="show-link")
        link = link_tag['href'] if link_tag else None

        if air_time != "Saat Bulunamadı":
            try:
                air_time_dt = datetime.strptime(air_time, "%H:%M")
            except ValueError:
                try:
                    air_time_dt = datetime.strptime(air_time, "%I:%M %p")
                    air_time_dt = air_time_dt + timedelta(hours=3)
                except ValueError:
                    air_time_dt = None
        
            air_time_24h = air_time_dt.strftime("%H:%M") if air_time_dt else "Invalid Time Format"
        else:
            air_time_24h = air_time

        anime_info = {
            "title": title_text,
            "episode": episode,
            "air_time": air_time_24h
        }

        if link:
            full_link = f"https://animeschedule.net/{link}"
            anime_info["link"] = full_link

        anime_data.append(anime_info)

    return anime_data

# Mesaj uzunluğu kontrolü: Eğer 2000 karakterden fazla olursa, mesajı parçalara ayırıyoruz
def split_message(message: str):
    max_length = 2000
    messages = []
    while len(message) > max_length:
        split_point = message.rfind('\n', 0, max_length)
        messages.append(message[:split_point])
        message = message[split_point:]
    messages.append(message)  # Son parçayı ekleyin
    return messages

# Belirtilen kanallara anime listesini gönderme
async def send_anime_schedule():
    anime_data = fetch_anime_data()
    saved_channels = load_saved_channels()
    
    if not saved_channels:
        print("⚠️ Kaydedilmiş kanal bulunamadı, mesaj gönderilmeyecek.")
        return

    anime_data_sorted = sorted(anime_data, key=lambda x: datetime.strptime(x['air_time'], "%H:%M") if x['air_time'] != "Geçersiz Saat" else datetime.max)
    today_date = datetime.now(tz=turkey_timezone).strftime("%d %B %Y")

    message = f"**📅 Bugünün Anime Yayınları ({today_date})**\n\n"
    
    for anime in anime_data_sorted:
        if 'link' in anime and anime['link']:
            message += f"**🎬 Anime: [{anime['title']}]({anime['link']})**\n"
        else:
            message += f"**🎬 Anime: {anime['title']}**\n"
        message += f"**📺 Bölüm**: {anime['episode']}\n"
        message += f"**🕒 Yayın Saati**: {anime['air_time']}\n\n"

    # Mesajı 2000 karakterden küçük olacak şekilde ayırma
    messages = split_message(message)
    
    for channel_id, role_id in saved_channels:
        channel = bot.get_channel(channel_id)
        if channel:
            for msg in messages:
                await channel.send(f"<@&{role_id}> {msg}")
        else:
            print(f"⚠️ Kanal bulunamadı: {channel_id}")
# Sunucudan kayıtlı kanal ve rolü silme
def remove_saved_channel(channel_id, role_id):
    if not os.path.exists(DATA_FILE):
        return False
    
    updated_data = []
    found = False

    with open(DATA_FILE, "r") as file:
        for line in file:
            parts = line.strip().split(",")
            if len(parts) == 2:
                saved_channel_id, saved_role_id = map(int, parts)
                if saved_channel_id == channel_id and saved_role_id == role_id:
                    found = True
                    continue
                updated_data.append(line.strip())

    if found:
        with open(DATA_FILE, "w") as file:
            for entry in updated_data:
                file.write(entry + "\n")
        return True
    return False

# Kullanıcıdan kanal ve rol bilgisi alıp kaydeden komut
@tree.command(name="bildirim", description="Anime bildirimleri için bir kanal ve rol belirleyin.")
async def set_channel(interaction: discord.Interaction, channel: discord.TextChannel, role: discord.Role):
    if await check_admin(interaction):  # Admin kontrolü
        success = save_channel_and_role(channel.id, role.id)
        if success:
            await interaction.response.send_message(f"✅ Bildirimler artık {channel.mention} kanalına ve {role.mention} rolüne gönderilecek!", ephemeral=True)
        else:
            await interaction.response.send_message(f"⚠️ {channel.mention} zaten bir rol ile bildirim almakta. Aynı kanala birden fazla rol eklenemez!", ephemeral=True)
    else:
        await interaction.response.send_message(f"⚠️ Bu komutu kullanmak için yönetici olmanız gerekiyor.", ephemeral=True)

# **Yeni Komut: Kanal ve rol silme**
@tree.command(name="bildirim_sil", description="Bildirim listesinden belirli bir kanal ve rolü kaldır.")
async def remove_channel(interaction: discord.Interaction, channel: discord.TextChannel, role: discord.Role):
    if await check_admin(interaction):  # Admin kontrolü
        success = remove_saved_channel(channel.id, role.id)
        if success:
            await interaction.response.send_message(f"🗑️ {channel.mention} ve {role.mention} artık bildirim almayacak.", ephemeral=True)
        else:
            await interaction.response.send_message(f"⚠️ {channel.mention} ve {role.mention} kayıtlı değil.", ephemeral=True)
    else:
        await interaction.response.send_message(f"⚠️ Bu komutu kullanmak için yönetici olmanız gerekiyor.", ephemeral=True)

# Bot hazır olduğunda çalışacak kısım
@bot.event
async def on_ready():
    await tree.sync()
    print(f'{bot.user} olarak giriş yapıldı')
    await send_anime_schedule()

    while True:
        await asyncio.sleep(86400)  # 24 saat bekleyip tekrar mesaj gönder
        await send_anime_schedule()

# Botu başlatma
bot.run(DISCORD_TOKEN)

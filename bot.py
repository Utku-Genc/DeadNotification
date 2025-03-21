
import requests
from bs4 import BeautifulSoup
import discord
from discord.ext import tasks
import os

# Config dosyasından bilgileri yükleme
def load_config(file_path='config.txt'):
    config = {}
    with open(file_path, 'r') as f:
        for line in f:
            key, value = line.strip().split('=')
            config[key] = value
    return config

# Config bilgilerini dosyadan yükle
config = load_config()

# Discord bot token, kanal ID'si ve rol ID'si
DISCORD_TOKEN = config['DISCORD_TOKEN']  # Discord bot token
CHANNEL_ID = int(config['CHANNEL_ID'])   # Bildirim gönderilecek kanal ID'si (int olmalı)
ROLE_ID = int(config['ROLE_ID'])         # Etiketlenecek rol ID'si (int olmalı)

# Discord istemci ayarları
intents = discord.Intents.default()
client = discord.Client(intents=intents)

# Veri çekme fonksiyonu
def fetch_data():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36'
    }
    # Proxy ayarları
    proxies = {
        'http': 'http://142.93.202.130:80',  # Proxy adresi ve portu
        'https': 'http://142.93.202.130:80'  # HTTPS için de aynı proxy kullanılabilir
    }

    try:
        # Proxy kullanarak istek gönderme
        response = requests.get("https://asyaanimeleri.com/", headers=headers, proxies=proxies)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        section = soup.find_all('div', class_='bixbox')[1]  # 2. div.bixbox'ı alıyoruz
        if not section:
            print("İlgili bölüm bulunamadı.")
            return []
        
        articles = section.find_all('article', class_='bs')
        new_data = []
        for article in articles:
            # Başlık kısmındaki veriyi alırken h2 etiketindeki metni hariç tutuyoruz
            title_div = article.find('div', class_='tt')
            if title_div:
            # H2 etiketlerini hariç tutuyoruz
                for h2 in title_div.find_all('h2'):
                    h2.decompose()  # H2 etiketini ve içeriğini kaldırıyoruz
                title = title_div.get_text(strip=True)  # Sadece kalan metni alıyoruz

            link = article.find('a')['href']
            image_url = article.find('img')['src']
            episode_number = article.find('span', class_='epx').get_text(strip=True)
            
            new_data.append((title, link, image_url, episode_number))
        
        return new_data
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"Request error occurred: {req_err}")
    return []


@client.event
async def on_ready():
    print(f'Bot {client.user} olarak giriş yaptı!')
    
    new_data = fetch_data()
    if new_data:
        latest_entry = new_data[0]  # İlk animeyi al
        await send_notification(CHANNEL_ID, ROLE_ID, *latest_entry)
    
    check_for_changes.start()

async def send_notification(channel_id, role_id, title, link, image_url, episode_number):
    channel = client.get_channel(channel_id)
    if channel:
        # Resmi cihazınıza indiriyoruz
        image_path = "downloaded_image.jpg"  # Resmin kaydedileceği geçici dosya yolu
        try:
            response = requests.get(image_url)
            with open(image_path, 'wb') as f:
                f.write(response.content)
        except Exception as e:
            print(f"Resim indirilirken hata oluştu: {e}")
            return
        
        # Embed mesajı oluşturuyoruz
        embed = discord.Embed(
            title=f"{title} Yeni Bölüm Yayınlandı!",
            url=link,
            color=discord.Color.blue()
        )
        embed.add_field(name="Bölüm", value=episode_number, inline=False)
        
        # Resmi embed mesajına ekliyoruz
        embed.set_image(url=f"attachment://{image_path}")
        print(f"Resim URL: {image_url}")  # URL’yi terminale yazdıralım

        embed.set_footer(text="Dead Community • Yeni Anime Bildirimi")
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/778330725152981064/1299683723813584977/banner.webp")
        
        # Resmi Discord'a gönderiyoruz
        with open(image_path, 'rb') as f:
            await channel.send(content=f'<@&{role_id}> {title} **{episode_number}** Yayınlandı!', embed=embed, file=discord.File(f, image_path))
        
        # Resmi cihazdan siliyoruz
        os.remove(image_path)

@tasks.loop(minutes=30)
async def check_for_changes():
    new_data = fetch_data()
    if new_data and new_data != check_for_changes.previous_data:
        latest_entry = new_data[0]  # En son eklenen anime
        await send_notification(CHANNEL_ID, ROLE_ID, *latest_entry)
        check_for_changes.previous_data = new_data

check_for_changes.previous_data = fetch_data()
client.run(DISCORD_TOKEN)

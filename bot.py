import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import discord
from discord.ext import tasks

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

# Headless modda Chrome tarayıcıyı ayarlama
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

# Selenium ile veri çekme fonksiyonu
def fetch_data():
    driver = webdriver.Chrome()
    driver.get("https://diziwatch.net/episodes/")
    
    # XPath ile ana veri, resim ve açıklamayı çekme
    main_element = driver.find_element(By.XPATH, '//*[@id="listehizala"]/div[1]')
    main_data = main_element.text

    # Resim URL'sini alma
    image_element = driver.find_element(By.XPATH, '//*[@id="listehizala"]/div[1]/a/picture/img')
    image_url = image_element.get_attribute("src")
    
    # Ek açıklama verisini alma
    extra_element = driver.find_element(By.XPATH, '//*[@id="listehizala"]/div[1]/a/div')
    extra_data = extra_element.text

    # Dizi isim verisini alma
    dizi_element = driver.find_element(By.XPATH, '//*[@id="listehizala"]/div[1]/a/div/div[1]/span')
    dizi_name = dizi_element.text
    
    # Sezon numarası verisini alma
    season_element = driver.find_element(By.XPATH, '//*[@id="listehizala"]/div[1]/a/div/span[1]')
    season_number = season_element.text
    
    # Bölüm numarası verisini alma
    episodes_element = driver.find_element(By.XPATH, '//*[@id="listehizala"]/div[1]/a/div/span[2]')
    episodes_number = episodes_element.text

    # Ana linki alma (buton için kullanılacak link)
    link_element = driver.find_element(By.XPATH, '//*[@id="listehizala"]/div[1]/a')
    main_link = link_element.get_attribute("href")

    print(dizi_name, season_number, episodes_number, image_url, main_link)

    driver.quit()  # Tarayıcıyı kapatmayı unutmayın
    return main_data, image_url, extra_data, main_link, dizi_name, season_number, episodes_number

# Discord botu hazır olduğunda çalışacak olay
@client.event
async def on_ready():
    print(f'Bot {client.user} olarak giriş yaptı!')
    check_for_changes.start()  # Veri kontrol görevini başlat

# Discord kanalına embed formatında bildirim gönderme fonksiyonu
async def send_notification(channel_id, role_id, main_data, image_url, extra_data, dizi_name, season_number, episodes_number, main_link):
    channel = client.get_channel(channel_id)
    if channel:
        # Embed mesajını oluşturma
        embed = discord.Embed(
            title=f"{dizi_name} Yeni Bölüm Yayınlandı!",  # Başlık
            url=main_link,  # Tıklanabilir URL ekliyoruz
            color=discord.Color.blue()
        )
        embed.add_field(name="Anime", value=dizi_name, inline=False)
        embed.add_field(name="Sezon", value=season_number, inline=True)
        embed.add_field(name="Bölüm", value=episodes_number, inline=True)
        embed.set_image(url=image_url) 
        embed.set_footer(text="Dead Community • Yeni Anime Bildirimi")
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/778330725152981064/1299683723813584977/banner.webp?ex=671e184a&is=671cc6ca&hm=503213ac85f88762bf9eea682bdf194dc5db65bbe3199cbd5cdb507ca87229a1&")

        
        # Kanalda mesajı gönderiyoruz, rolü de etiketleyerek
        await channel.send(content=f'<@&{role_id}> {dizi_name} Yeni Bölüm Yayınlandı!', embed=embed)

# Veri değişikliği kontrol fonksiyonu
@tasks.loop(minutes=1)  # Her dakika çalışacak
async def check_for_changes():
    new_data = fetch_data()
    
    # Veride değişiklik olup olmadığını kontrol et
    if new_data != check_for_changes.previous_data:
        main_data, image_url, extra_data, main_link, dizi_name, season_number, episodes_number = new_data
        await send_notification(CHANNEL_ID, ROLE_ID, main_data, image_url, extra_data, dizi_name, season_number, episodes_number, main_link)
        check_for_changes.previous_data = new_data  # Yeni veriyi kaydet

# Başlangıç verisini ilk kez alıyoruz
check_for_changes.previous_data = fetch_data()

# Discord botunu başlatıyoruz
client.run(DISCORD_TOKEN)

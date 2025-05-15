import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
from dotenv import load_dotenv
import os

# .env 로드
load_dotenv()

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = int(os.environ.get("CHANNEL_ID"))

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
scheduler = AsyncIOScheduler()

@bot.event
async def on_ready():
    print(f'✅ 봇 로그인됨: {bot.user.name}')
    await asyncio.sleep(2)
    await bot.wait_until_ready()
    scheduler.start()

async def scheduled_message():
    """지정된 시간에 메시지를 보내는 함수"""
    try:
        channel_id = CHANNEL_ID  # 메시지를 보낼 채널 ID
        channel = bot.get_channel(channel_id)
        if channel:
            await channel.send("[결계알람] 5분뒤 결계시간입니다.\n@everyone")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

# 5~20시 55분에 scheduled_message()를 실행
for hour in range(5, 21, 1):
    scheduler.add_job(scheduled_message, 'cron', hour=hour, minute=55)

bot.run(BOT_TOKEN)
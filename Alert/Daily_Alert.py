import discord
from discord import app_commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
from dotenv import load_dotenv
import os

# .env 로드
load_dotenv()

BOT_TOKEN = os.environ.get("BOT_TOKEN")

intents = discord.Intents.default()
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)
scheduler = AsyncIOScheduler()
alarm_messages = {}
alarm_group = app_commands.Group(name="알림", description="알림 관련 명령어")

@bot.event
async def on_ready():
    tree.add_command(alarm_group)
    await tree.sync()   # 슬래시 커맨드 동기화
    print("✅ 슬래시 명령어 동기화 완료!")
    await asyncio.sleep(2)  # 봇이 완전히 실행된 후 스케줄러 시작
    scheduler.start()
    print(f'✅ 봇 로그인됨: {bot.user.name}')

@alarm_group.command(name="설정", description="매일 지정된 시간에 알림을 설정합니다.")
async def 설정(interaction: discord.Interaction, 시간: str, *, 메시지: str):
    """매일 지정된 시간에 알림을 보냄"""
    try:
        hour, minute = map(int, 시간.split(":"))
        job_id = f"{interaction.guild.id}_{interaction.channel.id}_{interaction.user.id}_{시간}"
        
        if interaction.user.id not in alarm_messages:
            alarm_messages[interaction.user.id] = []

        alarm_messages[interaction.user.id].append((시간, 메시지))
        existing_job = scheduler.get_job(job_id)

        if existing_job:
            scheduler.remove_job(job_id)

        async def send_alarm():
            print(f"📢 알림 실행 중: {job_id}")
            await interaction.channel.send(f"[매일 알림] {메시지}: {시간}\n{interaction.user.mention}")

        scheduler.add_job(lambda: bot.loop.create_task(send_alarm()), 'cron', hour=hour, minute=minute, id=job_id)
        await interaction.response.defer()
        await interaction.followup.send(f"✅ {interaction.user.mention} 매일 {시간}에 알림이 설정되었습니다: '{메시지}'")
        
    except ValueError:
        await interaction.response.defer()  #예외 발생시 응답 연기
        await interaction.followup.send("⚠️ 시간 형식 오류. 예: !매일알림 08:00 일어나세요!", ephemeral=True)

@alarm_group.command(name="삭제", description="설정된 알림을 삭제합니다.")
async def 삭제(interaction: discord.Interaction, 시간: str):
    """설정된 알림 삭제"""
    try:
        job_id = f"{interaction.guild.id}_{interaction.channel.id}_{interaction.user.id}_{시간}"

        if interaction.user.id in alarm_messages:
            alarm_messages[interaction.user.id] = [msg for msg in alarm_messages[interaction.user.id] if msg[0] != 시간]

        existing_job = scheduler.get_job(job_id)

        if not existing_job:
            await interaction.response.defer()  # 응답 연기
            await interaction.followup.send("⚠️ 해당 시간에 설정된 알림을 찾을 수 없습니다!", ephemeral=True)
            return
        
        scheduler.remove_job(job_id)
        await interaction.response.defer()
        await interaction.followup.send(f"✅ {interaction.user.mention} {시간}에 설정된 알림이 삭제되었습니다!")
    
    except Exception:
        await interaction.response.defer()  #예외 발생시 응답 연기
        await interaction.followup.send("⚠️ 알림 삭제 중 오류가 발생했습니다.", ephemeral=True)

@alarm_group.command(name="수정", description="설정된 알림을 수정합니다.")
async def 수정(interaction: discord.Interaction, 기존시간: str, 변경시간: str, 메시지: str):
    """설정된 알림을 수정"""
    old_job_id = f"{interaction.guild.id}_{interaction.channel.id}_{interaction.user.id}_{기존시간}"
    new_job_id = f"{interaction.guild.id}_{interaction.channel.id}_{interaction.user.id}_{변경시간}"

    existing_job = scheduler.get_job(old_job_id)
    if not existing_job:
        await interaction.response.defer()  #응답 연기
        await interaction.followup.send("⚠️ 해당 시간의 알림을 찾을 수 없습니다!", ephemeral=True)
        return
    
    scheduler.remove_job(old_job_id)
    alarm_messages[interaction.user.id] = [
        (변경시간, 메시지) if msg[0] == 기존시간 else msg
        for msg in alarm_messages.get(interaction.user.id, [])
    ]
    
    try:
        hour, minute = map(int, 변경시간.split(":"))

        async def send_alarm():
            await interaction.channel.send(f"[매일 알림] {메시지}: {변경시간}\n{interaction.user.mention}")
        scheduler.add_job(
            lambda: bot.loop.create_task(send_alarm()),
            'cron', hour=hour, minute=minute, id=new_job_id
        )
        await interaction.response.defer()
        await interaction.followup.send(
            f"✅ {interaction.user.mention} 알림이 수정되었습니다!\n"
            f"⏰ **기존 시간:** {기존시간} → **변경 시간:** {변경시간}\n"
            f"📢 **메시지:** '{메시지}'"
            )
    except ValueError:
        await interaction.response.defer()  #예외 발생시 응답 연기
        await interaction.followup.send("⚠️ 시간 형식 오류. 예: !알림수정 08:00 09:00 새로운 메시지!", ephemeral=True)

@alarm_group.command(name="목록", description="설정된 알림 목록을 출력합니다.")
async def 목록(interection: discord.Interaction):
    """설정된 알림 목록 출력"""
    jobs = scheduler.get_jobs()
    message = alarm_messages.get(interection.user.id, "저장된 메시지가 없습니다!")

    if not jobs:
        await interection.response.defer()  #응답 대기
        await interection.followup.send("⚠️ 현재 설정된 알림이 없습니다!", ephemeral=True)
        return
    
    messages = "**📌 알림 목록:**\n"

    if interection.user.id in alarm_messages:
        for time, message in alarm_messages[interection.user.id]:
            next_run_time = None

            for job in jobs:
                if f"{interection.guild.id}_{interection.channel.id}_{interection.user.id}_{time}" == job.id:
                    next_run_time = job.next_run_time.strftime("%Y-%m-%d %H:%M")
                    break
                
            messages += f"- ⏰ {message}: {time} → 다음 알림: {next_run_time or "시간 설정 오류"}\n"
    else:
        messages += "⚠️ 현재 설정된 알림이 없습니다!\n"

    await interection.response.defer()
    await interection.followup.send(messages)
    print(f"📜 알림 목록 요청됨: {interection.user.name}")

bot.run(BOT_TOKEN)
import discord
from discord.ext import commands
import asyncio
import random
import os
from dotenv import load_dotenv

# 🔑 환경 변수에서 토큰 불러오기
load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# ✅ 디스코드 봇 설정
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# 🏆 게임 상태 및 점수판 저장
games = {}

# 🟢 봇이 준비되었을 때 출력
@bot.event
async def on_ready():
    print(f'🎲 크래커 주사위 봇이 로그인되었습니다! {bot.user}')

# 🎯 게임 시작 명령어
@bot.command(name='게임시작')
async def start_game(ctx):
    server_id = ctx.guild.id

    if games.get(server_id, {}).get('is_running', False):
        await ctx.send('⚠️ 이미 게임이 진행 중입니다!')
        return

    games[server_id] = {
        'is_running': True,
        'scores': {},
        'participants': set(),
        'timer_task': None,
        'dashboard_message': None
    }

    await ctx.send('🎮 **CRACKER 분배 주사위가 일하고 있어요!**\n🕒 **5분** 동안 한 번만 주사위를 굴리세요! (!주사위 [@사용자])')

    dashboard_embed = discord.Embed(
        title="🎲 크래커 분배 주사위",
        description="**게임이 시작되었습니다!**",
        color=discord.Color.blue()
    )
    dashboard_embed.add_field(name="⏱️ 남은 시간", value="**300초** 남았습니다!", inline=False)
    dashboard_embed.add_field(name="🏆 실시간 순위", value="아직 기록된 점수가 없습니다!", inline=False)

    dashboard_message = await ctx.send(embed=dashboard_embed)
    games[server_id]['dashboard_message'] = dashboard_message

    games[server_id]['timer_task'] = asyncio.create_task(game_timer(ctx, server_id))

# ⏱️ 타이머 함수 (5분 후 자동 종료)
async def game_timer(ctx, server_id):
    remaining_time = 300
    dashboard_message = games[server_id].get('dashboard_message')

    while remaining_time > 0 and games[server_id]['is_running']:
        if dashboard_message:
            embed = dashboard_message.embeds[0]
            embed.set_field_at(0, name="⏱️ 남은 시간", value=f"**{remaining_time}초** 남았습니다!", inline=False)
            await dashboard_message.edit(embed=embed)

        await asyncio.sleep(1)
        remaining_time -= 1

    if games[server_id]['is_running']:
        await end_game(ctx, server_id)

# 🎲 주사위 굴리기 명령어
@bot.command(name='주사위')
async def roll_dice(ctx):
    guild_id = ctx.guild.id

    if guild_id not in games or not games[guild_id]['is_running']:
        await ctx.send('🚫 현재 진행 중인 게임이 없습니다. !게임시작으로 새로운 게임을 시작하세요.')
        return

    mentioned_user = ctx.message.mentions[0] if ctx.message.mentions else ctx.author

    if mentioned_user.id in games[guild_id]['participants']:
        await ctx.send(f'⚠️ {mentioned_user.display_name}님은 이미 주사위를 굴렸습니다!')
        return

    dice_result = random.randint(1, 100)
    games[guild_id]['scores'][mentioned_user.id] = {'name': mentioned_user.display_name, 'score': dice_result}
    games[guild_id]['participants'].add(mentioned_user.id)

    await ctx.send(f'🎲 **{mentioned_user.display_name}님**이 주사위를 굴렸습니다! 결과: **{dice_result}**')

    await update_scoreboard(ctx, guild_id)

# 🛑 게임 종료 명령어
@bot.command(name='게임종료')
async def stop_game(ctx):
    guild_id = ctx.guild.id

    if not games.get(guild_id, {}).get('is_running', False):
        await ctx.send('🚫 현재 진행 중인 게임이 없습니다.')
        return

    games[guild_id]['is_running'] = False

    if games[guild_id]['timer_task']:
        games[guild_id]['timer_task'].cancel()

    await ctx.send('🛑 분배주사위가 마감되었습니다! 결과를 발표합니다...')
    await end_game(ctx, guild_id)

# 📢 게임 종료 및 최종 결과 발표
async def end_game(ctx, guild_id):
    games[guild_id]['is_running'] = False
    scores = games[guild_id]['scores']
    dashboard_message = games[guild_id].get('dashboard_message')

    if not dashboard_message:
        return

    embed = dashboard_message.embeds[0]
    embed.set_field_at(0, name="⏱️ 게임 종료", value="타이머가 종료되었습니다!", inline=False)
    embed.color = discord.Color.gold()
    await dashboard_message.edit(embed=embed)

    if not scores:
        embed.set_field_at(1, name="🏆 최종 순위", value="아무도 주사위를 굴리지 않았습니다.", inline=False)
        await dashboard_message.edit(embed=embed)
        await ctx.send('⏰ **게임 종료!** 아무도 주사위를 굴리지 않았습니다.')
        return

    sorted_scores = sorted(scores.items(), key=lambda x: x[1]['score'], reverse=True)
    final_leaderboard = "\n".join([f"{idx+1}. {data['name']} - **{data['score']}점**" for idx, (user_id, data) in enumerate(sorted_scores[:5])])
    embed.set_field_at(1, name="🏆 최종 순위", value=final_leaderboard, inline=False)
    await dashboard_message.edit(embed=embed)

    await ctx.send(f"🔔 **최종 순위가 업데이트되었습니다!** [분배 주사위 결과 확인하기]({dashboard_message.jump_url})")

# 📊 실시간 순위 업데이트
async def update_scoreboard(ctx, guild_id):
    scores = games[guild_id]['scores']
    dashboard_message = games[guild_id].get('dashboard_message')

    if not dashboard_message:
        return

    embed = dashboard_message.embeds[0]

    if not scores:
        embed.set_field_at(1, name="🏆 실시간 순위", value="아직 기록된 점수가 없습니다!", inline=False)
        await dashboard_message.edit(embed=embed)
        return

    sorted_scores = sorted(scores.items(), key=lambda x: x[1]['score'], reverse=True)
    leaderboard = "\n".join([f"{idx+1}. {data['name']} - **{data['score']}점**" for idx, (user_id, data) in enumerate(sorted_scores[:5])])

    embed.set_field_at(1, name="🏆 실시간 순위", value=leaderboard, inline=False)
    await dashboard_message.edit(embed=embed)

# 🔑 봇 실행
bot.run(TOKEN)
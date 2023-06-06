import os

import discord
from discord import Client
from analyze import analyze

TOKEN = os.environ['DISCORD_BOT_TOKEN']
intents = discord.Intents.all()  # デフォルトのIntentsオブジェクトを生成
intents.typing = False  # typingを受け取らないように
client = Client(intents=intents)
print(f'画像分析: {discord.__version__}')


@client.event
async def on_message(message):
    submit = message.guild.get_channel(897784178958008322)  # bot用チャット
    if message.author.bot:
        return

    if message.content == "s.test":
        await message.channel.send(f"{str(client.user)}\n{discord.__version__}")
        return

    if len(message.attachments) != 2 and message.channel == submit:  # 画像提出
        admin = message.author.get_role(904368977092964352)  # ビト森杯運営
        if bool(admin):
            return
        await message.delete(delay=1)
        await message.channel.send(f"{message.author.mention}\nError: 画像を2枚同時に投稿してください。", delete_after=5)
        if len(message.attachments) == 1:
            await message.channel.send("画像1枚では、すべての設定項目が画像内に収まりません。", delete_after=5)
        return

    if len(message.attachments) == 2 and message.channel == submit:  # 画像提出
        await analyze(message)

client.run(TOKEN)

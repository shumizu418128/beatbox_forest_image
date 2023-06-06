import os

import discord
from discord import Client, Interaction
from analyze import analyze

TOKEN = os.environ['DISCORD_BOT_TOKEN']
intents = discord.Intents.all()  # デフォルトのIntentsオブジェクトを生成
intents.typing = False  # typingを受け取らないように
client = Client(intents=intents)
print(f'画像分析: {discord.__version__}')


@client.event
async def on_message(message):
    # submit = message.guild.get_channel(897784178958008322)  # bot用チャット
    if message.author.bot:
        return

    if message.content == "s.test":
        await message.channel.send(f"{str(client.user)}\n{discord.__version__}")
        return

    """if len(message.attachments) != 2 and message.channel.id == 897784178958008322:  # bot用チャット
        admin = message.author.get_role(904368977092964352)  # ビト森杯運営
        if bool(admin):
            return
        await message.delete(delay=1)
        await message.channel.send(f"{message.author.mention}\nError: 画像を2枚同時に投稿してください。", delete_after=5)
        if len(message.attachments) == 1:
            await message.channel.send("画像1枚では、すべての設定項目が画像内に収まりません。", delete_after=5)
        return"""

    if len(message.attachments) == 2 and message.channel.id == 897784178958008322:  # 画像提出
        await analyze(message)


@client.event
async def on_interaction(interaction: Interaction):
    if interaction.custom_id == "button_support":
        await interaction.response.defer(ephemeral=True, thinking=False)
        bot_channel = interaction.guild.get_channel(897784178958008322)  # bot用チャット
        tari3210 = interaction.guild.get_member(412082841829113877)
        await bot_channel.send(f"{tari3210.mention}\nエラー報告\n\n{interaction.channel.jump_url}")
        await interaction.followup.send(f"{interaction.user.mention}\n運営メンバーに通知を送信しました。まもなく対応しますので、しばらくお待ちください。")

client.run(TOKEN)

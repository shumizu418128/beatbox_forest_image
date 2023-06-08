import os

import discord
from discord import ChannelType, Client, Interaction, Message
from analyze import analyze

TOKEN = os.environ['DISCORD_BOT_TOKEN']
intents = discord.Intents.all()  # デフォルトのIntentsオブジェクトを生成
intents.typing = False  # typingを受け取らないように
client = Client(intents=intents)
print(f'画像分析: {discord.__version__}')


@client.event
async def on_message(message: Message):
    if message.author.bot:
        return

    if message.content == "s.test":
        await message.channel.send(f"{str(client.user)}\n{discord.__version__}")
        return

    if message.channel.type == ChannelType.private_thread:
        if len(message.attachments) == 0:
            return
        channel_id = message.channel.parent_id
    else:
        channel_id = message.channel.id

    if len(message.attachments) != 2 and channel_id in [1115986804026392627, 897784178958008322]:  # マイクチェックチャンネル bot用チャット
        if message.author.id == 412082841829113877:  # tari3210
            return
        await message.delete(delay=1)
        await message.channel.send(f"{message.author.mention}\nError: 画像を2枚同時に投稿してください。", delete_after=5)
        if len(message.attachments) == 1:
            await message.channel.send("ほとんどの端末では、画像1枚では、すべての設定項目が画像内に収まりません。\n画像1枚ですべての設定項目が画像内に収まる場合、同じ画像を2枚提出してください。", delete_after=5)
        return

    if len(message.attachments) == 2 and channel_id in [1115986804026392627, 897784178958008322]:  # マイクチェックチャンネル bot用チャット
        await analyze(message)


@client.event
async def on_interaction(interaction: Interaction):
    await interaction.response.defer(ephemeral=True, thinking=False)
    custom_id = interaction.data["custom_id"]

    if custom_id == "button_support":
        bot_channel = interaction.guild.get_channel(897784178958008322)  # bot用チャット
        tari3210 = interaction.guild.get_member(412082841829113877)
        await bot_channel.send(f"{tari3210.mention}\nエラー報告\n\n{interaction.channel.jump_url}")
        await interaction.followup.send(f"{interaction.user.mention}\n運営メンバーに通知を送信しました。まもなく対応します。\nご用件をこのチャンネルにご記入ください。")

client.run(TOKEN)

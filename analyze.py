import re
from asyncio import sleep
from datetime import datetime

import discord
from discord import ButtonStyle, Embed, File
from discord.ui import Button, View
from scipy.spatial import distance

import mobile_check


async def analyze(message: discord.Message):
    # 初期設定
    file_names = []

    await message.delete()
    threads = message.channel.threads
    thread_names = [thread.name for thread in threads]
    if str(message.author.id) not in thread_names:
        try:
            channel = await message.channel.create_thread(name=f"{message.author.id}")
        except AttributeError:  # スレッド作成失敗 -> 送信チャンネルがスレッド
            if len(message.attachments) != 2:
                return
            channel = message.channel
    else:
        index = thread_names.index(str(message.author.id))
        channel = threads[index]
    await channel.send(f"{message.author.mention}\nご提出ありがとうございます。\n分析を行います。しばらくお待ちください。")
    if bool(message.content):
        await channel.send("※画像と一緒に送信されたメッセージ文は削除されました。")

    # 画像保存
    for attachment in message.attachments:
        if attachment.content_type not in ["image/jpeg", "image/png"]:
            await channel.send(f"{message.author.mention}\nError: \n画像を認識できませんでした。\nJPG, JPEG, PNG画像を提出してください。")
            return
        dt_now = datetime.now()
        name = f"/tmp/{message.author.id}." + dt_now.strftime("%H.%M.%S.png")
        file_names.append(name)
        await attachment.save(name)
        await channel.send(name.replace('/tmp/', ''), file=discord.File(name))
        await sleep(1)

    # 画像ファイル判定、縦横比判定
    image_size_check = (message.attachments[0].height - message.attachments[1].height) + (message.attachments[0].width - message.attachments[1].width)
    if message.attachments[0].height < message.attachments[0].width or bool(image_size_check):  # たて < よこ ならPCと判定
        # PC版
        await channel.send(f"{message.author.mention}\nError: PC版Discordの画像と判定されました。\nPC版Discordの画像分析は、近日対応予定です。")
        return

    # モバイル版
    else:
        # 初期設定
        error_msg = []
        log = ""

        # 感度設定
        error_msg, log = await mobile_check.sensitive_check(file_names, error_msg, log)

        # モバイルボイスオーバーレイ の座標検出
        all_text, mobile_voice_overlay, log = await mobile_check.text_check(file_names, log)

        # ノイズ抑制チェックマーク座標
        error_msg, noise_suppression, log = await mobile_check.noise_suppression_check(file_names, error_msg, log)

        # 必要な設定項目があるか
        error_msg = await mobile_check.word_contain_check(all_text, error_msg)

        for file_name in file_names:
            # 外国語検出（ひらがな・カタカナが無い場合ストップ）
            if not re.search(r'[ぁ-ん]+|[ァ-ヴー]+', all_text):
                return "not_japanese"

            # 設定オン座標検出
            circle_coordinate, log = await mobile_check.setting_off_check(file_name, log)

            # モバイルボイスオーバーレイ、チェックマーク引き算
            for setting_on in circle_coordinate:
                for overlay in mobile_voice_overlay:
                    if distance.euclidean(setting_on, overlay) < 200:
                        circle_coordinate.remove(setting_on)

            # 赤丸書き出し
            error_msg = await mobile_check.circle_write(file_name, circle_coordinate, error_msg)

    # 結果通知
    tari3210 = message.guild.get_member(412082841829113877)
    embed = Embed(title="分析結果", description=":ok:\n問題なし", color=0x00ff00)
    embed.set_footer(text=f"画像分析bot 制作: {str(tari3210)}", icon_url=tari3210.avatar.url)
    if len(error_msg) > 0:
        embed.color = 0xff0000
        embed.description = ":x: \n以下の問題が見つかりました。\n\n-------------"
        value = '\n'.join(error_msg)
        embed.add_field(name="エラー内容", value=value, inline=False)
    await channel.send(message.author.mention, embed=embed, files=[File(file_name) for file_name in file_names])

    # 報告ボタン
    button = Button(label="サポートへ問い合わせる", style=ButtonStyle.red, custom_id="button_support")
    view = View()
    view.add_item(button)
    await channel.send("このbotは開発段階です。\nご不明な点があれば、お気軽に問い合わせボタンをご利用ください。\n\n* エラー内容に誤りがある・エラー内容がよくわからない\n* botが変な動作をしている", view=view)
    return

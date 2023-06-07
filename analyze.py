import random
import re
from asyncio import sleep
from datetime import datetime

import discord
from discord import ButtonStyle, Embed, File
from discord.ui import Button, View

import mobile_check


async def analyze(message: discord.Message):
    # 初期設定
    file_names = []

    await message.delete()
    try:
        threads = message.channel.threads
    except AttributeError:  # スレッド取得失敗 -> 送信チャンネルがスレッド
        channel = message.channel
    else:
        thread_names = [thread.name for thread in threads]
        if str(message.author.id) not in thread_names:  # 無いなら作る
            channel = await message.channel.create_thread(name=f"{message.author.id}")
        else:  # あるなら使う
            index = thread_names.index(str(message.author.id))
            channel = threads[index]

    await channel.send(f"ご提出ありがとうございます。\n分析を行います。しばらくお待ちください。\n\n分析が完了すると {message.author.mention} さんへ再度通知を送信します。")
    if bool(message.content):
        embed = Embed(title="画像と一緒に送信された文", description=message.content)
        await channel.send(embed=embed)

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

    # 報告ボタン
    button = Button(label="サポートへ問い合わせる", style=ButtonStyle.red, custom_id="button_support")
    view = View()
    view.add_item(button)
    await channel.send("このbotはベータ版です。\nご不明な点があれば、お気軽に問い合わせボタンをご利用ください。", view=view)

    # 画像ファイル判定、縦横比判定
    if message.attachments[0].height < message.attachments[0].width:  # たて < よこ ならPCと判定
        # PC版
        await channel.send(f"{message.author.mention}\nError: PC版Discordの画像と判定されました。\nPC版Discordの画像分析は、近日対応予定です。")
        return

    # モバイル版
    else:
        # 初期設定
        error_msg = []
        log = ""
        emoji = random.choice(message.guild.emojis)
        embed_progress = Embed(title="分析中...", description=f"{emoji}▫️▫️▫️▫️▫️▫️▫️▫️▫️▫️▫️☑️")
        progress = await channel.send(embed=embed_progress)

        # モノクロ画像を作る・上10%カット
        monochrome_file_names = await mobile_check.edit_image(file_names)
        embed_progress.description = "🟦" + embed_progress.description.replace("▫️", "", 1)
        await progress.edit(embed=embed_progress)

        # 感度設定
        error_msg, log = await mobile_check.sensitive_check(file_names, error_msg, log)
        embed_progress.description = "🟦" + embed_progress.description.replace("▫️", "", 1)
        await progress.edit(embed=embed_progress)

        # モバイルボイスオーバーレイ の座標検出
        all_text, split_overlay, log = await mobile_check.text_check(file_names, log)
        embed_progress.description = "🟦" + embed_progress.description.replace("▫️", "", 1)
        await progress.edit(embed=embed_progress)

        # 外国語検出（ひらがな・カタカナが無い場合ストップ）
        if not re.search(r'[ぁ-ん]+|[ァ-ヴー]+', all_text):
            await channel.send("Error: 外国語版Discordと判定されました。このbotは日本語のみ対応しています。")
            return

        # ノイズ抑制チェックマーク座標
        error_msg, log = await mobile_check.noise_suppression_check(file_names, monochrome_file_names, error_msg, log)
        embed_progress.description = "🟦" + embed_progress.description.replace("▫️", "", 1)
        await progress.edit(embed=embed_progress)

        # 必要な設定項目があるか
        error_msg = await mobile_check.word_contain_check(all_text, error_msg)
        embed_progress.description = "🟦" + embed_progress.description.replace("▫️", "", 1)
        await progress.edit(embed=embed_progress)

        for i, (overlay_list, file_name) in enumerate(zip(split_overlay, file_names)):
            # 設定オン座標検出
            circle_position, log = await mobile_check.setting_off_check(file_name, log)
            embed_progress.description = "🟦" + embed_progress.description.replace("▫️", "", 1)
            await progress.edit(embed=embed_progress)

            # モバイルボイスオーバーレイ引き算
            circle_position, log = await mobile_check.remove_overlay(circle_position, overlay_list, i, log)
            embed_progress.description = "🟦" + embed_progress.description.replace("▫️", "", 1)
            await progress.edit(embed=embed_progress)

            # 赤丸書き出し
            error_msg = await mobile_check.write_circle(file_name, circle_position, error_msg)
            embed_progress.description = "🟦" + embed_progress.description.replace("▫️", "", 1)
            await progress.edit(embed=embed_progress)

    # ログ表示
    embed = Embed(title="分析ログ", description=log)
    await progress.edit(embed=embed)

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
    await channel.send("このbotはベータ版です。\nご不明な点があれば、お気軽に問い合わせボタンをご利用ください。", view=view)
    return

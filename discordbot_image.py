from asyncio import sleep
from datetime import datetime
from decimal import Decimal

import cv2
import discord
import gspread_asyncio
import numpy as np
import pyocr
import pyocr.builders
from discord import Embed
from discord.ui import Button, View
from oauth2client.service_account import ServiceAccountCredentials
from PIL import Image
from scipy.spatial import distance

intents = discord.Intents.all()  # デフォルトのIntentsオブジェクトを生成
intents.typing = False  # typingを受け取らないように
client = discord.Bot(intents=intents)
print('ビト森杯bot - 画像分析: 起動完了')


def get_credits():
    return ServiceAccountCredentials.from_json_keyfile_name(
        "makesomenoise-4243a19364b1.json",
        ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive',
         'https://www.googleapis.com/auth/spreadsheets'])


@client.event
async def on_message(message):
    contact = client.get_channel(920620259810086922)  # お問い合わせ
    if message.author.bot:
        return

    if message.content == "s.test":
        await message.channel.send(f"ビト森杯 - 画像分析: {client.latency}")
        return

    if message.content == "s.mt":
        await message.channel.send("メンテナンス中...")
        gc = gspread_asyncio.AsyncioGspreadClientManager(get_credits)
        agc = await gc.authorize()
        workbook = await agc.open_by_key('1WcwdGVf7NRKerM1pnZu9kIsgA0VYy5TddyGdKHBzAu4')
        worksheet = await workbook.worksheet('botデータベース（さわらないでね）')
        error = []
        roleA = message.guild.get_role(920320926887862323)  # A部門 ビト森杯
        roleB = message.guild.get_role(920321241976541204)  # B部門 ビト森杯
        memberA = set(roleA.members)
        memberB = set(roleB.members)
        mid_A = [member.id for member in roleA.members]
        mid_B = [member.id for member in roleB.members]
        DBidA_str = await worksheet.col_values(3)
        DBidB_str = await worksheet.col_values(7)
        DBidA_str.remove("id")
        DBidB_str.remove("id")
        DBidA = [int(id) for id in DBidA_str]
        DBidB = [int(id) for id in DBidB_str]
        # メンテその1 重複ロール付与
        for member in memberA & memberB:
            error.append(f"・重複ロール付与\n{member.display_name}\nID: {member.id}")
        # メンテその2 ロール未付与
        for id in set(DBidA) - set(mid_A):
            member = message.guild.get_member(id)
            error.append(
                f"・🇦部門 ロール未付与\n{member.display_name}\nID: {member.id}")
        for id in set(DBidB) - set(mid_B):
            member = message.guild.get_member(id)
            error.append(
                f"・🅱️部門 ロール未付与\n{member.display_name}\nID: {member.id}")
        # メンテその3 DB未登録
        for id in set(mid_A) - set(DBidA):
            member = message.guild.get_member(id)
            error.append(f"・🇦部門 DB未登録\n{member.display_name}\nID: {member.id}")
        for id in set(mid_B) - set(DBidB):
            member = message.guild.get_member(id)
            error.append(
                f"・🅱️部門 DB未登録\n{member.display_name}\nID: {member.id}")
        # メンテその4 DB AB重複
        for id in set(DBidA) & set(DBidB):
            member = message.guild.get_member(id)
            error.append(f"・DB AB重複\n{member.display_name}\nID: {member.id}")
        if error == []:
            await message.channel.send("エラーなし")
            return
        await message.channel.send("<@412082841829113877>\n見つかったエラー：")
        for e in error:
            await message.channel.send(e)
        await message.channel.send("---finish---")
        return

    if len(message.attachments) != 2 and message.channel.id == 952946795573571654:  # 画像提出
        await message.delete(delay=1)
        if len(message.attachments) == 0:
            await message.channel.send(f"お問い合わせは {contact.mention} までお願いします。", delete_after=5)
            return
        await message.channel.send(f"{message.author.mention}\nError: 画像を2枚同時に投稿してください。", delete_after=5)
        if len(message.attachments) == 1:
            await message.channel.send("画像1枚では、すべての設定項目が画像内に収まりません。", delete_after=5)
        return

    # 画像提出
    if len(message.attachments) == 2 and message.channel.id == 952946795573571654:
        # 初期設定
        overwrite = discord.PermissionOverwrite()
        overwrite.send_messages = False
        overwrite.view_channel = True
        roleA = message.guild.get_role(920320926887862323)  # A部門 ビト森杯
        roleB = message.guild.get_role(920321241976541204)  # B部門 ビト森杯
        await message.channel.set_permissions(roleA, overwrite=overwrite)
        await message.channel.set_permissions(roleB, overwrite=overwrite)
        overwrite.send_messages = True
        bot_channel = client.get_channel(897784178958008322)  # bot用チャット
        admin = message.guild.get_role(904368977092964352)  # ビト森杯運営
        verified = message.guild.get_role(952951691047747655)  # verified
        await message.delete()
        close_notice = await message.channel.send(f"一時的に提出受付をストップしています。\nしばらくお待ちください。\n\n※長時間続いている場合は、\nお手数ですが {contact.mention} まで\nご連絡ください。")
        try:
            channel = await message.channel.create_thread(name=f"{message.author.display_name} 分析ログ")
        except AttributeError:
            await message.channel.set_permissions(roleA, overwrite=overwrite)
            await message.channel.set_permissions(roleB, overwrite=overwrite)
            await close_notice.delete()
            await message.channel.send("Error: ここに画像を送信しないでください。")
            await message.delete()
            return
        await channel.send(f"{message.author.mention}\nご提出ありがとうございます。\n分析を行います。しばらくお待ちください。")
        tools = pyocr.get_available_tools()
        tool = tools[0]
        langs = tool.get_available_languages()
        lang = langs[1]
        file_names = []
        error_msg = []
        error_code = 0
        # 下準備 保存、画像ファイル判定、縦横比判定
        for a in message.attachments:
            if a.content_type == "image/jpeg" or a.content_type == "image/png":
                if Decimal(f"{a.height}") / Decimal(f"{a.width}") < Decimal("1.6"):
                    button = Button(
                        label="verify", style=discord.ButtonStyle.success, emoji="🎙️")

                    async def button_callback(interaction):
                        admin = interaction.user.get_role(
                            904368977092964352)  # ビト森杯運営
                        if bool(admin):
                            await bot_channel.send(f"interaction verify: {interaction.user.display_name}\nID: {interaction.user.id}")
                            await message.author.add_roles(verified)
                            await interaction.response.send_message(f"✅{message.author.display_name}にverifiedロールを付与しました。")
                    button.callback = button_callback
                    view = View(timeout=None)
                    view.add_item(button)
                    await channel.send(f"{message.author.mention}\nbotでの画像分析ができない画像のため、運営による手動チェックに切り替えます。\nしばらくお待ちください。\n\n{admin.mention}", view=view)
                    await message.channel.set_permissions(roleA, overwrite=overwrite)
                    await message.channel.set_permissions(roleB, overwrite=overwrite)
                    await close_notice.delete()
                    return
                await channel.send(a.proxy_url)
                dt_now = datetime.now()
                name = "/tmp/" + dt_now.strftime("%H.%M.%S.png")
                file_names.append(name)
                await a.save(name)
                await sleep(1)
            else:
                await channel.send(f"{message.author.mention}\nError: jpg, jpeg, png画像を投稿してください。")
                await message.channel.set_permissions(roleA, overwrite=overwrite)
                await message.channel.set_permissions(roleB, overwrite=overwrite)
                await close_notice.delete()
                return
        if bool(message.content):
            await channel.send(f"`※画像と一緒に送信されたメッセージ文は削除されます。`\nお問い合わせは {contact.mention} までお願いします。")
        embed = Embed(title="分析中...", description="0% 完了")
        status = await channel.send(embed=embed)
        # 設定オン座標調査
        xy_lists = [[], []]
        images = [cv2.imread(file_names[0]), cv2.imread(file_names[1])]
        for xy_list, img in zip(xy_lists, images):
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)  # BGR色空間からHSV色空間への変換
            lower = np.array([113, 92, 222])  # 色検出しきい値の設定 (青)
            upper = np.array([123, 172, 252])
            frame_mask = cv2.inRange(hsv, lower, upper)
            contours, _ = cv2.findContours(
                frame_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)  # 輪郭抽出
            for c in contours:
                result = cv2.moments(c)
                try:
                    x, y = int(result["m10"] / result["m00"]
                               ), int(result["m01"] / result["m00"])
                except ZeroDivisionError:
                    continue
                xy_list.append([x, y])
        # モバイルボイスオーバーレイ検出
        log = "なし"
        all_text = ""
        for file_name, xy_list in zip(file_names, xy_lists):
            text_box1 = tool.image_to_string(Image.open(
                file_name), lang=lang, builder=pyocr.builders.LineBoxBuilder(tesseract_layout=12))
            text_box2 = tool.image_to_string(Image.open(
                file_name), lang=lang, builder=pyocr.builders.LineBoxBuilder(tesseract_layout=6))
            texts_1 = [t for t in text_box1]
            texts_2 = [t for t in text_box2]
            texts_list = texts_1 + texts_2
            for text in texts_list:
                all_text += text.content.replace(' ', '')
                if "モバイルボイスオーバーレイ" in text.content.replace(' ', ''):
                    text_position = text.position
                    place_text = [text_position[1][0], text_position[1][1]]
                    for xy in xy_list:
                        if distance.euclidean(place_text, (xy)) < 200:
                            xy_list.remove(xy)
                            log += "検知：モバイルボイスオーバーレイ\n"
                            break
            if file_name == file_names[0]:
                embed = Embed(title="分析中...", description="20% 完了")
                await status.edit(embed=embed)
        if log != "なし":
            log = log.replace('なし', '')
        embed = Embed(title="分析中...",
                      description=f"40% 完了\n\n作業ログ\n```\n{log}\n```")
        await status.edit(embed=embed)
        # ワード検出
        if "troubleshooting" in all_text:
            await channel.send("word found: troubleshooting")
            button = Button(
                label="verify", style=discord.ButtonStyle.success, emoji="🎙️")

            async def button_callback(interaction):
                admin = interaction.user.get_role(904368977092964352)  # ビト森杯運営
                if bool(admin):
                    await bot_channel.send(f"interaction verify: {interaction.user.display_name}\nID: {interaction.user.id}")
                    await message.author.add_roles(verified)
                    await interaction.response.send_message(f"✅{message.author.display_name}にverifiedロールを付与しました。")
            button.callback = button_callback
            view = View(timeout=None)
            view.add_item(button)
            await channel.send(f"{message.author.mention}\nbotでの画像分析ができない画像のため、運営による手動チェックに切り替えます。\nしばらくお待ちください。\n\n{admin.mention}", view=view)
            await message.channel.set_permissions(roleA, overwrite=overwrite)
            await message.channel.set_permissions(roleB, overwrite=overwrite)
            await close_notice.delete()
            return
        word_list = ["自動検出", "ノイズ抑制", "高度音声検出"]
        word_list2 = ["入力モード", "バックグラウンドノイズ", "入力感度自動調整"]
        for word, word2 in zip(word_list, word_list2):
            if word not in all_text and word2 not in all_text:
                error_msg.append(f"・検知失敗: 設定「{word}」")
                error_code += 1
        if error_code > 0:
            error_msg.append("上記の設定が映るようにしてください。")
        if "ハードウェア" in all_text:
            error_msg.append('・「ハードウェア拡大縮小を有効にする」の項目が映らないようにしてください。')
            error_code += 1
        # オンの設定検出
        on_exist = False
        for img, xy_list, file_name in zip(images, xy_lists, file_names):
            for xy in xy_list:
                _, width = img.shape[:2]
                if xy[0] < width * 2 / 3:
                    continue
                error_code += 1
                cv2.circle(img, (xy), 65, (0, 0, 255), 20)
                on_exist = True
            cv2.imwrite(file_name, img)
        images = [cv2.imread(file_names[0]), cv2.imread(file_names[1])]
        if on_exist:
            error_msg.append("・丸で囲われた設定をOFFにしてください。")
        embed = Embed(title="分析中...",
                      description=f"60% 完了\n\n作業ログ\n```\n{log}\n```")
        await status.edit(embed=embed)
        # 感度設定確認
        sensitive_exist = False
        sensitive_check = True
        for i, img in zip([1, 2], images):
            height, width = img.shape[:2]
            all_pixel = str(width * height)
            center = [width / 3, height / 3]
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)  # BGR色空間からHSV色空間への変換
            lower = np.array([63, 0, 0])  # 色検出しきい値の設定 (みどり)
            upper = np.array([76, 255, 255])
            # 色検出しきい値範囲内の色を抽出するマスクを作成
            frame_mask = cv2.inRange(hsv, lower, upper)
            green_pixels = cv2.countNonZero(frame_mask)
            lower = np.array([14, 0, 0])  # 色検出しきい値の設定 (きいろ)
            upper = np.array([24, 255, 255])
            # 色検出しきい値範囲内の色を抽出するマスクを作成
            frame_mask = cv2.inRange(hsv, lower, upper)
            yellow_pixels = cv2.countNonZero(frame_mask)
            color_pixel = str(green_pixels + yellow_pixels)
            fraction_pixel = Decimal(color_pixel) / \
                Decimal(all_pixel) * Decimal("100")
            log += f"{i}枚目: {fraction_pixel}\n"
            log = log.replace('なし', '')
            if Decimal(fraction_pixel) > Decimal("1.2"):
                await channel.send("感度設定判別失敗")
                button = Button(
                    label="verify", style=discord.ButtonStyle.success, emoji="🎙️")

                async def button_callback(interaction):
                    admin = interaction.user.get_role(
                        904368977092964352)  # ビト森杯運営
                    if bool(admin):
                        await bot_channel.send(f"interaction verify: {interaction.user.display_name}\nID: {interaction.user.id}")
                        await message.author.add_roles(verified)
                        await interaction.response.send_message(f"✅{message.author.display_name}にverifiedロールを付与しました。")
                button.callback = button_callback
                view = View(timeout=None)
                view.add_item(button)
                await channel.send(f"{message.author.mention}\nbotでの画像分析ができない画像のため、運営による手動チェックに切り替えます。\nしばらくお待ちください。\n\n{admin.mention}", view=view)
                await message.channel.set_permissions(roleA, overwrite=overwrite)
                await message.channel.set_permissions(roleB, overwrite=overwrite)
                await close_notice.delete()
                return
            if Decimal("0.5") < Decimal(fraction_pixel):  # 0.5以上で感度あり
                sensitive_exist = True
                if green_pixels < yellow_pixels * 3:  # 感度が低すぎる
                    sensitive_check = False
                    contours, _ = cv2.findContours(
                        frame_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)  # 輪郭抽出
                    xy_sensitive = []
                    for c in contours:
                        result = cv2.moments(c)
                        try:
                            x, y = int(
                                result["m10"] / result["m00"] * 2 / 3), int(result["m01"] / result["m00"])
                        except ZeroDivisionError:
                            continue
                        xy_sensitive.append([x, y])
                    closest = 99999999
                    for xy in xy_sensitive:
                        color_distance = distance.euclidean(xy, center)
                        if color_distance < closest:
                            closest = color_distance
                            closest_xy = xy
                    cv2.circle(img, closest_xy, 65, (0, 0, 255), 20)
            if i == 1:
                embed = Embed(title="分析中...",
                              description=f"80% 完了\n\n作業ログ\n```\n{log}\n```")
                await status.edit(embed=embed)
        if sensitive_exist is False:
            error_msg.append(
                "・感度設定が映るようにしてください。一部端末では「マイクのテスト」ボタンを押すと表示されます。")
            error_code += 1
        if sensitive_check is False:
            error_msg.append(
                "・設定感度が低すぎます。丸印のところまで感度を上げてください。※丸印は目安です。なるべく感度を上げてください。")
            error_code += 1
        embed = Embed(title="分析中...", description=f"作業ログ\n```\n{log}\n```")
        await status.edit(embed=embed)
        # 結果通知
        files = []
        if error_code == 0:
            color = 0x00ff00
            description = ":ok: \n\n🙇‍♂️ご協力ありがとうございました！🙇‍♂️"
            await message.author.add_roles(verified)
        else:
            color = 0xff0000
            description = ":x: \n\n以下の問題が見つかりました。再提出をお願いします。"
            for file_name, img in zip(file_names, images):
                cv2.imwrite(file_name, img)
                files.append(discord.File(file_name))
        embed = Embed(
            title="分析結果", description=description, color=color)
        embed.set_footer(text="made by tari3210#9924")
        value = "なし"
        if len(error_msg) > 0:
            error_msg = str(error_msg)[1:-1]
            error_msg = error_msg.replace(',', '\n')
            value = error_msg.replace('\'', '') + f"\n\nエラーコード：{error_code}"
            embed.add_field(name="エラーログ", value=value, inline=False)
        await channel.send(content=f"{message.author.mention}", embed=embed, files=files)
        if error_code > 0:
            await channel.send(f"エラーログの内容に関するご質問は、 {contact.mention} までお願いします。")
        await message.channel.set_permissions(roleA, overwrite=overwrite)
        await message.channel.set_permissions(roleB, overwrite=overwrite)
        await close_notice.delete()
        return

client.run("OTg5NTQwNjA0ODYwMDU5Njg4.Gd7nvg.spOU7ibuT8-mc3qhChaLxkcKQ30piQkQibUTHg")

from decimal import Decimal
import re

import cv2
import numpy as np
import pyocr
import pyocr.builders
from PIL import Image
from scipy.spatial import distance


async def sensitive_check(file_names: list[str], error_msg: list[str]):  # 感度設定
    # 初期設定
    sensitive_exist = False
    sensitive_high = True

    # 感度設定確認
    for file_name in file_names:
        image = cv2.imread(file_name)
        height, width = image.shape[:2]  # height -> Y座標  width -> X座標
        image_crop = image[int(height / 10): height, 0: width]  # y, x    ここで上10%カット
        all_pixel = str(width * height)
        center = [width / 3, height / 3]  # 3で割っているのは、感度設定の座標を検出するため

        hsv = cv2.cvtColor(image_crop, cv2.COLOR_BGR2HSV)  # BGR色空間からHSV色空間への変換

        lower = np.array([63, 0, 0])  # しきい値 みどり
        upper = np.array([76, 255, 255])
        frame_mask = cv2.inRange(hsv, lower, upper)  # 色検出しきい値範囲内の色を抽出するマスクを作成
        green_pixels = cv2.countNonZero(frame_mask)

        lower = np.array([14, 0, 0])  # しきい値 きいろ
        upper = np.array([24, 255, 255])
        frame_mask = cv2.inRange(hsv, lower, upper)  # 色検出しきい値範囲内の色を抽出するマスクを作成
        yellow_pixels = cv2.countNonZero(frame_mask)

        color_pixel = str(green_pixels + yellow_pixels)  # みどり + きいろ
        fraction_pixel = Decimal(color_pixel) / Decimal(all_pixel) * Decimal("100")  # みどり + きいろ の比率(パーセント)

        if Decimal(fraction_pixel) > Decimal("1.2"):  # 感度設定のピクセルが全体の1.2%以上ある = ノイズを検知している
            error_msg.append("* 感度設定を判定できませんでした。感度設定のバーの大部分が緑色になっていることをご確認ください。")
        elif Decimal(fraction_pixel) > Decimal("0.5"):  # 0.5以上で感度あり
            sensitive_exist = True
            if green_pixels < yellow_pixels * 3:  # 感度が低すぎる
                sensitive_high = False
                contours, _ = cv2.findContours(frame_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)  # 輪郭抽出
                xy_sensitive = []
                for c in contours:
                    result = cv2.moments(c)
                    try:
                        x, y = int(result["m10"] / result["m00"] * 2 / 3), int(result["m01"] / result["m00"])
                    except ZeroDivisionError:
                        continue
                    xy_sensitive.append([x, y])
                closest = 99999999
                for xy in xy_sensitive:  # 感度設定の座標を探す
                    color_distance = distance.euclidean(xy, center)
                    if color_distance < closest:
                        closest = color_distance
                        closest_xy = xy
                # 感度設定に関してはここで書き出しを行う
                cv2.circle(image_crop, (75, closest_xy[1]), 65, (0, 0, 255), 20)  # x = 75にして常に最高感度を要求
                cv2.imwrite(file_name, image_crop)
    if sensitive_exist is False:
        error_msg.append("* 感度設定が映るようにしてください。一部端末では「マイクのテスト」ボタンを押すと表示されます。")
    if sensitive_high is False:
        error_msg.append("* 設定感度が低すぎます。赤丸のところまで感度を上げてください。")
    return error_msg


async def text_check(file_names: list[str]):  # 各種設定項目チェック
    # 初期設定
    tools = pyocr.get_available_tools()
    tool = tools[0]
    lang = "jpn"
    all_text = ""
    mobile_voice_overlay = []

    # モバイルボイスオーバーレイのチェック
    for file_name in file_names:
        PIL_image = Image.open(file_name)
        text_box = tool.image_to_string(PIL_image, lang, pyocr.builders.LineBoxBuilder(tesseract_layout=12))
        for text in text_box:
            all_text += text.content.replace(' ', '')
            if "モバイルボイスオーバーレイ" in text.content.replace(' ', ''):
                text_position = text.position
                center_text = [int((text_position[0][0] + text_position[1][0]) / 2),
                               int((text_position[0][1] + text_position[1][1]) / 2)]
                mobile_voice_overlay.append(center_text)
    return [all_text, mobile_voice_overlay]


async def noise_suppression_check(file_names: list[str], error_msg: list[str]):
    # 初期設定
    tools = pyocr.get_available_tools()
    tool = tools[0]
    lang = "jpn"

    noise_suppression = []  # noise_suppressionは保存
    for file_name in file_names:
        center_text = []  # center_textは毎回クリア
        PIL_image = Image.open(file_name)
        cv2_image = cv2.imread(file_name)

        # 白黒判定
        img_gray = cv2.imread(file_name, cv2.IMREAD_GRAYSCALE)
        _, img_monochrome = cv2.threshold(img_gray, 0, 255, cv2.THRESH_OTSU)
        white_pixel = cv2.countNonZero(img_monochrome)
        black_pixel = img_monochrome.size - white_pixel
        if white_pixel > black_pixel:
            template = cv2.imread("template_white.png")
        else:
            template = cv2.imread("template_black.png")

        # テンプレートマッチング
        result = cv2.matchTemplate(cv2_image, template, cv2.TM_CCOEFF_NORMED)
        _, precision, _, top_left = cv2.minMaxLoc(result)  # precision = 精度
        if precision < 0.7:  # 精度7割未満は検知失敗
            continue
        bottom_right = [top_left[0] + 60, top_left[1] + 60]
        center_check_mark = [top_left[0] + 30, top_left[1] + 30]
        noise_suppression.append(center_check_mark)

        # 「設定しない」の位置チェック
        text_box = tool.image_to_string(PIL_image, lang, pyocr.builders.LineBoxBuilder(tesseract_layout=6))
        for text in text_box:
            if "設定しない" in text.content.replace(' ', ''):
                text_position = text.position  # (top_left(x, y), bottom_right(x, y))
                center_text = [int((text_position[0][0] + text_position[1][0]) / 2),
                               int((text_position[0][1] + text_position[1][1]) / 2)]

        if bool(center_text):  # 「設定しない」があるとき
            # チェックマーク &「設定しない」の、y座標の距離
            distance_y = abs(center_check_mark[1] - center_text[1])

        if distance_y > 20 or bool(center_text) is False:  # 理論上は距離0 このifに引っかかる = ノイキャン設定不適切
            # チェックマークに斜線
            cv2.line(cv2_image, top_left, bottom_right, (0, 0, 255), 3)

            # 正しい場所
            correct_place = [center_check_mark[0], center_text[1]]
            cv2.circle(cv2_image, correct_place, 20, (0, 0, 255), 2)
            error_msg.append('* ノイズ抑制設定に誤りがあります。赤丸のところをタップして「設定しない」に変更してください。')

    if bool(noise_suppression) is False:  # 中身が空なら失敗
        error_msg.append('* ノイズ抑制設定のチェックマーク検出に失敗しました。')
    return [error_msg, noise_suppression]


async def word_contain_check(all_text: str, error_msg: list[str]):  # 必要事項があるかチェック
    # 初期設定
    word_missing = False

    # ハードウェア拡大縮小があるとアウト（必要事項が無い可能性大）
    if "ハードウェア" in all_text:
        error_msg.append('* 「ハードウェア拡大縮小を有効にする」の項目が映らないようにしてください。')

    # 必要事項
    word_list = ["自動検出", "ノイズ抑制", "高度音声検出"]
    word_list2 = ["入力モード", "バックグラウンドノイズ", "入力感度自動調整"]
    for word, word2 in zip(word_list, word_list2):
        if word not in all_text and word2 not in all_text:
            error_msg.append(f"検知失敗: 設定「{word}」")
            word_missing = True
    if word_missing:
        error_msg.append("* 上記の検知失敗した設定が映るようにしてください。")
    return error_msg


async def setting_off_check(file_name: str):  # 設定オン座標検出
    # 初期設定
    coordinate_list = []
    cv2_image = cv2.imread(file_name)

    # 設定オン検知
    hsv = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2HSV)  # BGR色空間からHSV色空間への変換
    lower = np.array([113, 92, 222])  # 色検出しきい値の設定 (青)
    upper = np.array([123, 172, 252])
    frame_mask = cv2.inRange(hsv, lower, upper)
    contours, _ = cv2.findContours(frame_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)  # 輪郭抽出
    for c in contours:
        area = cv2.contourArea(c, False)
        if area > 4:
            result = cv2.moments(c)
            x, y = int(result["m10"] / result["m00"]), int(result["m01"] / result["m00"])
            coordinate_list.append([x, y])
    return coordinate_list


async def circle_write(file_name: str, coordinate_list: list, error_msg: list[str]):  # 赤丸書き込み
    # 初期設定
    on_exist = False
    cv2_image = cv2.imread(file_name)

    # 設定がオンの部分に赤丸を書き込む
    for xy in coordinate_list:
        _, width = cv2_image.shape[:2]
        if xy[0] < width * 2 / 3:  # 左側にあるやつは無視
            continue
        cv2.circle(cv2_image, (xy), 65, (0, 0, 255), 20)
        on_exist = True
    if on_exist:
        error_msg.append("* 赤丸で囲われた設定をOFFにしてください。")

    # 書き出し
    cv2.imwrite(file_name, cv2_image)
    return error_msg


async def mobile_check(file_names: list[str]):
    # 初期設定
    error_msg = []

    # 感度設定
    error_msg = await sensitive_check(file_names, error_msg)

    # モバイルボイスオーバーレイ の座標検出
    all_text, mobile_voice_overlay = await text_check(file_names)

    # ノイズ抑制チェックマーク座標
    error_msg, noise_suppression = await noise_suppression_check(file_names, error_msg)

    # 必要な設定項目があるか
    error_msg = await word_contain_check(all_text, error_msg)

    for file_name in file_names:
        # 外国語検出（ひらがな・カタカナが無い場合ストップ）
        if not re.search(r'[ぁ-ん]+|[ァ-ヴー]+', all_text):
            return "not_japanese"

        # 設定オン座標検出
        circle_coordinate = await setting_off_check(file_name)

        # モバイルボイスオーバーレイ、チェックマーク引き算
        for setting_on in circle_coordinate:
            for overlay in mobile_voice_overlay:
                if distance.euclidean(setting_on, overlay) < 200:
                    circle_coordinate.remove(setting_on)
            for noise in noise_suppression:
                if distance.euclidean(setting_on, noise) < 20:
                    circle_coordinate.remove(setting_on)

        # 赤丸書き出し
        error_msg = await circle_write(file_name, circle_coordinate, error_msg)

    return error_msg

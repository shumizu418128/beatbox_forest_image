# 各種ファイル
- main.py
  - エンドポイント処理
- analyze.py
  - ユーザーが提出した画像が、スマホかPCか確認
- mobile_check.py
  - スマホ版に対するチェック

# 画像処理の作業工程
- edit_image
  - 充電中のiphoneのみ、画面上部通知バーがが緑色に変わる。これがノイズになるため、あらかじめ上部10%をカット
- sensitive_check
  - Discordの音声設定・感度設定をチェック
    - 著しく低い or 感度設定が"自動検出"だと問題ありとして処理
    - 感度おおよそ7割程度で合格
- text_check
  - 音声設定を確認するために文字を抽出
    - ここではなにもチェックしない。文字をとるだけ
- noise_suppression_check
  - ノイズ抑制設定の確認
    - Beatboxをするうえで、ノイズ抑制設定は天敵。絶対オフにさせる
- word_contain_check
  - 音声設定を確認するために必要な文字が映っているか確認
    - 文字認識の精度を考慮し、必要なワードは複数設定
- setting_off_check
  - ある1つの設定を除き、すべての設定はオフになっていなければならない
  - Discordの仕様上、設定がオンの項目は青色になるため、それを検知
- remove_ignore
  - 上記「ある1つの設定」を見つけ、除外
- write_circle
  - これまでのチェックで見つけた問題点を赤丸で囲い、ユーザーに改善を促す

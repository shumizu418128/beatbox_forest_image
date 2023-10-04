# ベースイメージとしてPython 3.11を使用
FROM python:3.11


# 環境変数を一度に設定
ENV LANG=ja_JP.UTF-8 \
    LANGUAGE=ja_JP:ja \
    LC_ALL=ja_JP.UTF-8 \
    TZ=JST-9 \
    TERM=xterm

# Pythonパッケージのアップグレードとtesseract-ocrのインストールを1つのRUN命令で実行
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y tesseract-ocr tesseract-ocr-eng tesseract-ocr-jpn libtesseract-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && /usr/local/bin/python -m pip install --upgrade pip

# requirements.txtをコピーしてパッケージをインストール
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# ファイルをコピー
COPY main.py /app/
COPY *.py /app/
COPY *.png /app/
COPY *.json /app/
COPY *.traineddata /app/

# tesseractのバージョン情報を表示
RUN tesseract -v

# 作業ディレクトリを/appに設定
WORKDIR /app

# コマンドを指定
CMD ["python", "-u", "main.py"]

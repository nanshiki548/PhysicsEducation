import os

# モジュールの親ディレクトリのフルパスを取得
basedir = os.path.dirname(os.path.dirname(__file__))
# 親ディレクトリのapp.sqliteをデータベースに設定
SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(basedir, "app.sqlite")
# シークレットキーの値として10バイトの文字列をランダムに生成
SECRET_KEY = os.urandom(10)

# 管理者ユーザーのユーザー名とパスワード
USERNAME = "a"
PASSWORD = "a"

openai_api_key = "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"
spreadsheet_url = "https://docs.google.com/spreadsheets/d/1oBY6tSmwxsLod2kiULVNbQelUmgAWLWiFcGlxl_bRdw/edit#gid=0"
json_keyfile_path = (
    "/Users/matsudatatsuya/gpt_sample/voltaic-space-388911-7adfbc11d865.json"
)
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

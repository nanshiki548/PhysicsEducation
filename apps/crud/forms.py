from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField
from wtforms.validators import DataRequired


class AdminForm(FlaskForm):
    """ログイン画面のフォームクラス

    Attributes:
        username: ユーザー名
        password: パスワード
        submit: 送信ボタン
    """

    username = StringField("管理者名", validators=[DataRequired(message="入力が必要です。")])
    password = PasswordField("パスワード", validators=[DataRequired(message="入力が必要です。")])
    # フォームのsubmitボタン
    submit = SubmitField(("ログイン"))


class MakeClass(FlaskForm):
    """ホームページのフォームクラス

    Attributes:
        classname: クラス名
        subject: 教科名
        submit: 送信ボタン
    """

    class_name = StringField(
        "クラス名",
        validators=[
            DataRequired(message="入力が必要です。"),
        ],
    )

    subject = StringField(
        "教科名",
        validators=[
            DataRequired(message="入力が必要です。"),
        ],
    )
    # フォームのsubmitボタン
    submit = SubmitField(("投稿する"))


class JoinClass(FlaskForm):
    """ホームページのフォームクラス

    Attributes:
        classcode: クラスコード
        submit: 送信ボタン
    """

    class_code = StringField(
        "クラスコード",
        validators=[
            DataRequired(message="入力が必要です。"),
        ],
    )
    # フォームのsubmitボタン
    submit = SubmitField(("投稿する"))


class AnnouncementForm(FlaskForm):
    """クラスへの連絡事項を投稿するためのフォームクラス

    Attributes:
        message: 連絡事項のメッセージ
        submit: 送信ボタン
    """

    # 連絡事項のメッセージ入力フィールド
    message = StringField("連絡事項", validators=[DataRequired(message="メッセージの入力は必須です。")])

    # フォームの送信ボタン
    submit = SubmitField("投稿")


class AssignmentForm(FlaskForm):
    title = StringField("タイトル", validators=[DataRequired()])
    description = TextAreaField("説明", validators=[DataRequired()])
    temp_save = SubmitField("コンセプトテスト作成")
    final_save = SubmitField("最終保存")


class MakeTopic(FlaskForm):
    """ホームページのフォームクラス

    Attributes:
        title: トピックタイトル
        submit: 送信ボタン
    """

    title = StringField(
        "トピックタイトル",
        validators=[
            DataRequired(message="入力が必要です。"),
        ],
    )
    # フォームのsubmitボタン
    submit = SubmitField(("投稿する"))


class MakeConcept(FlaskForm):
    """コンセプトテストのフォームクラス
    Attributes:
        question_text: 問題文
        submit: 送信ボタン
    """

    question_text = StringField(
        "問題文", validators=[DataRequired(message="問題文の入力は必須です。")]
    )
    submit = SubmitField("選択肢生成")


class MakemisConcept(FlaskForm):
    """コンセプトテストのフォームクラス
    Attributes:
        updated_option: 選択肢
        submit: 送信ボタン
    """

    updated_option = StringField(validators=[DataRequired(message="選択肢の入力は必須です。")])
    submit = SubmitField("選択肢を確定")


class FinishConcept(FlaskForm):
    """コンセプトテストのフォームクラス
    Attributes:
        misconception: 誤概念
        submit: 送信ボタン
    """

    misconception = StringField(validators=[DataRequired(message="誤概念の入力は必須です。")])
    submit = SubmitField("誤概念を確定")

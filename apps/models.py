from datetime import datetime
from .extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin


class User(db.Model, UserMixin):
    """ユーザー情報を格納するモデルクラス"""

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_student = db.Column(db.Boolean, default=False, nullable=False)

    def set_password(self, password):
        """パスワードをハッシュ化して設定する"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """パスワードのチェックを行う"""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"


# 関連テーブルの定義
class_members = db.Table(
    "class_members",
    db.Column("user_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
    db.Column("class_id", db.Integer, db.ForeignKey("classes.id"), primary_key=True),
)


class Classpost(db.Model):
    """クラス情報を格納するモデルクラス"""

    __tablename__ = "classes"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    class_name = db.Column(db.String(20), nullable=False)
    subject = db.Column(db.String(20), nullable=False)
    create_at = db.Column(db.DateTime, default=datetime.utcnow)
    creator_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    class_code = db.Column(db.String(7), unique=True, nullable=False)

    # Userモデルとのリレーション（作成者）
    creator = db.relationship("User", backref="created_classes")

    # Userモデルとの多対多リレーション（クラスメンバー）
    members = db.relationship(
        "User",
        secondary=class_members,
        lazy="subquery",
        backref=db.backref("joined_classes", lazy=True),
    )

    # SeatAssignmentモデルとのリレーションを定義
    seat_assignments = db.relationship("SeatAssignment", backref="classpost", lazy=True)


class SeatAssignment(db.Model):
    """座席割り当て情報を格納するモデルクラス"""

    __tablename__ = "seat_assignments"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False)
    title = db.Column(db.String(100))
    layout = db.Column(db.Text)  # JSON形式の座席割り当てデータ


class Announcement(db.Model):
    """クラスへの連絡を格納するモデルクラス"""

    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(500), nullable=False)
    posted_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False)


class Topic(db.Model):
    """トピックを格納するモデルクラス"""

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)  # トピックタイトル
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # 作成日時
    class_id = db.Column(
        db.Integer, db.ForeignKey("classes.id"), nullable=False
    )  # クラスID

    # クラスモデルとのリレーション
    classpost = db.relationship("Classpost", backref="topics")

    def __repr__(self):
        return f"<Topic {self.title}>"


class Assignment(db.Model):
    """課題を格納するモデルクラス"""

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=True)  # タイトル（任意）
    description = db.Column(db.Text, nullable=True)  # 説明（任意）
    due_date = db.Column(db.DateTime, nullable=True)  # 提出期限（任意）
    class_id = db.Column(
        db.Integer, db.ForeignKey("classes.id"), nullable=False
    )  # クラスID（必須）
    creator_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False
    )  # 作成者ID（必須）
    created_at = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=True
    )  # 作成日時（任意）
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True
    )  # 更新日時（任意）
    attachment = db.Column(db.String(255), nullable=True)  # 添付ファイル（任意）
    question_text = db.Column(db.Text, nullable=True)  # 課題文（任意）
    topic_id = db.Column(
        db.Integer, db.ForeignKey("topic.id"), nullable=True
    )  # トピックID（任意）
    seat_assignment_id = db.Column(
        db.Integer, db.ForeignKey("seat_assignments.id"), nullable=True
    )  # 座席割り当てID
    original_filename = db.Column(db.String(255), nullable=True)  # 元のファイル名
    preview_image = db.Column(db.String(255), nullable=True)  # PDFプレビュー画像のパス

    # リレーション
    seat_assignment = db.relationship("SeatAssignment", backref="assignments")
    topic = db.relationship("Topic", backref="assignments")


class Options(db.Model):
    """選択肢を格納するモデルクラス"""

    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey("assignment.id"), nullable=True)

    options = db.Column(db.String(255), nullable=False)  # 選択肢

    assignment = db.relationship("Assignment", backref=db.backref("options", lazy=True))

    def __repr__(self):
        return f"<Announcement {self.id}>"


class MisConception(db.Model):
    """選択肢を格納するモデルクラス"""

    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey("assignment.id"), nullable=True)

    mis_conception = db.Column(db.String(255), nullable=False)  # 誤概念

    assignment = db.relationship(
        "Assignment", backref=db.backref("misconception", lazy=True)
    )

    def __repr__(self):
        return f"<Announcement {self.id}>"


class Submission(db.Model):
    """課題提出を格納するモデルクラス"""

    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(
        db.Integer, db.ForeignKey("assignment.id"), nullable=False
    )
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    seat_assignment_id = db.Column(
        db.Integer, db.ForeignKey("seat_assignments.id"), nullable=True
    )
    content = db.Column(db.Text, nullable=False)  # 生徒の提出内容
    classification_result = db.Column(db.Text, nullable=False)  # 生徒の分類結果
    provisional_question = db.Column(db.Text, nullable=False)  # 質問の提案

    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)  # 提出日時

    # リレーションシップ
    user = db.relationship("User", backref=db.backref("submissions", lazy=True))
    assignment = db.relationship(
        "Assignment", backref=db.backref("submissions", lazy=True)
    )
    seat_assignment = db.relationship(
        "SeatAssignment", backref=db.backref("submissions", lazy=True)
    )

    def __repr__(self):
        return f"<Submission {self.id}>"

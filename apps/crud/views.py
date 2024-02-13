import settings
from flask import (
    Blueprint,
    current_app,
    render_template,
    url_for,
    redirect,
    session,
    jsonify,
    request,
    flash,
)
import openai
from flask_login import current_user
from flask_login import login_user
import random
import string
import json
from apps.crud import forms
from apps import models
from apps.app import db
import re
import time
from datetime import datetime
from werkzeug.utils import secure_filename
import os
from sqlalchemy import func
from pdf2image import convert_from_path


crud = Blueprint(
    "crud",
    __name__,
    template_folder="templates",
    static_folder="static_crud",
)


# クラスコードを生成する関数
def generate_class_code(length=7):
    characters = string.ascii_letters + string.digits
    return "".join(random.choice(characters) for _ in range(length))


@crud.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        role = request.form.get("role")  # ラジオボタンからroleを取得
        is_student = role == "student"  # 生徒ならTrue、教師ならFalse

        # 既存のユーザーのチェック
        existing_user = models.User.query.filter(
            (models.User.username == username) | (models.User.email == email)
        ).first()
        if existing_user:
            return render_template("register.html", error="ユーザー名またはメールが既に存在します")

        # 新規ユーザーの作成
        new_user = models.User(username=username, email=email, is_student=is_student)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for("crud.login"))

    return render_template("register.html")


# @crud.route("/crudlogin", methods=["GET", "POST"])
# def login():
#     form = forms.AdminForm()
#     session["logged_in"] = False

#     if form.validate_on_submit():
#         if (
#             form.username.data != current_app.config["USERNAME"]
#             or form.password.data != current_app.config["PASSWORD"]
#         ):
#             return render_template("crud-login.html", form=form)
#         else:
#             session["logged_in"] = True
#             return redirect(url_for("crud.index"))

#     return render_template("crud-login.html", form=form)


@crud.route("/crudlogin", methods=["GET", "POST"])
def login():
    form = forms.AdminForm()
    if form.validate_on_submit():
        # フォームからユーザー名とパスワードを取得
        username = form.username.data
        password = form.password.data

        # データベースでユーザーを検索
        user = models.User.query.filter_by(username=username).first()

        # ユーザーが存在し、パスワードが正しい場合
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("crud.index"))
        else:
            flash("無効なユーザー名またはパスワードです。")

    return render_template("crud-login.html", form=form)


@crud.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("crud.login"))


@crud.route("/api/classes", methods=["GET"])
def get_classes():
    # 現在ログインしているユーザーが作成したクラスのみを取得
    classes = models.Classpost.query.filter_by(creator_id=current_user.id).all()
    classes_data = [
        {"className": cls.class_name, "classDetails": cls.subject} for cls in classes
    ]
    return jsonify(classes_data)


@crud.route("/create-class", methods=["POST"])
def create_class():
    form_make_class = forms.MakeClass()
    # クラス作成用のフォーム処理
    if request.method == "POST":
        if form_make_class.validate_on_submit():
            class_code = generate_class_code()  # クラスコードを生成
            classpost = models.Classpost(
                class_name=form_make_class.class_name.data,
                subject=form_make_class.subject.data,
                creator_id=current_user.id,  # ログインしているユーザーのIDを設定
                class_code=class_code,
            )
            db.session.add(classpost)
            db.session.commit()

            flash("クラスが作成されました。", "success")
            return redirect(url_for("crud.index"))


@crud.route("/class/<int:class_id>/create-topic", methods=["POST"])
def create_topic(class_id):
    form_make_topic = forms.MakeTopic()
    if form_make_topic.validate_on_submit():
        topic = models.Topic(title=form_make_topic.title.data, class_id=class_id)
        db.session.add(topic)
        db.session.commit()
        flash("トピックが作成されました。", "success")
        return redirect(url_for("crud.classcontents", class_id=class_id))
    # フォームのバリデーションに失敗した場合の処理を追加
    else:
        flash("トピックの作成に失敗しました。", "error")
        return redirect(url_for("crud.classcontents", class_id=class_id))


@crud.route("/join-class", methods=["POST"])
def join_class():
    form_join_class = forms.JoinClass()  # JoinClassフォームのインスタンスを作成

    if form_join_class.validate_on_submit():
        class_code = form_join_class.class_code.data

        # クラスコードを使用してクラスを検索
        class_to_join = models.Classpost.query.filter_by(class_code=class_code).first()

        if class_to_join:
            # 現在のユーザーが既にクラスのメンバーでないことを確認
            if current_user not in class_to_join.members:
                # ユーザーをクラスのメンバーに追加
                class_to_join.members.append(current_user)
                db.session.commit()
                flash("クラスに参加しました。", "success")
            else:
                flash("すでにクラスに参加しています。", "info")
        else:
            flash("クラスが見つかりませんでした。", "danger")
    else:
        flash("入力データにエラーがあります。", "danger")

    return redirect(url_for("crud.index"))


@crud.route("/index", endpoint="index", methods=["GET"])
def index():
    form_make_class = forms.MakeClass()
    form_join_class = forms.JoinClass()
    # 現在ログインしているユーザーが作成したクラスのみを取得
    classes = models.Classpost.query.filter_by(creator_id=current_user.id).all()
    # 現在のユーザーが参加しているクラスを取得
    joined_classes = models.Classpost.query.filter(
        models.Classpost.members.any(id=current_user.id)
    ).all()
    return render_template(
        "index.html",
        form_make_class=form_make_class,
        form_join_class=form_join_class,
        classes=classes,
        joined_classes=joined_classes,
    )


@crud.route("/class/<int:class_id>")
def class_detail(class_id):
    class_data = models.Classpost.query.get(class_id)
    # 現在ログインしているユーザーが作成したクラスのみを取得
    classes = models.Classpost.query.filter_by(creator_id=current_user.id).all()
    # 現在のユーザーが参加しているクラスを取得
    joined_classes = models.Classpost.query.filter(
        models.Classpost.members.any(id=current_user.id)
    ).all()
    announcements = (
        models.Announcement.query.filter_by(class_id=class_id)
        .order_by(models.Announcement.posted_at.desc())
        .all()
    )
    if class_data is None:
        return "クラスが見つかりません", 404
    return render_template(
        "crud-blank1.html",
        class_data=class_data,
        announcements=announcements,
        classes=classes,
        joined_classes=joined_classes,
    )


@crud.route("/class/<int:class_id>/announce", methods=["POST"])
def save_announcement(class_id):
    data = request.json
    if not data or "announcement" not in data:
        return jsonify({"success": False, "error": "Invalid request"}), 400

    message = data["announcement"]

    try:
        announcement = models.Announcement(message=message, class_id=class_id)
        db.session.add(announcement)
        db.session.commit()
        return jsonify({"success": True, "message": "Announcement saved."})
    except Exception as e:
        current_app.logger.error(f"Error posting announcement: {e}")
        return jsonify({"success": False, "error": str(e)})


@crud.route("/class/<int:class_id>/classcontents", methods=["GET", "POST"])
def classcontents(class_id):
    form_make_topic = forms.MakeTopic()
    class_data = models.Classpost.query.get(class_id)
    # 現在ログインしているユーザーが作成したクラスのみを取得
    classes = models.Classpost.query.filter_by(creator_id=current_user.id).all()
    # 現在のユーザーが参加しているクラスを取得
    joined_classes = models.Classpost.query.filter(
        models.Classpost.members.any(id=current_user.id)
    ).all()
    # クラスに所属する生徒の総数を取得
    class_member_count = (
        db.session.query(models.User)
        .join(models.class_members, models.class_members.c.user_id == models.User.id)
        .filter(models.class_members.c.class_id == class_id)
        .count()
    )
    # トピック一覧を取得
    topic = (
        models.Topic.query.filter_by(class_id=class_id)
        .order_by(models.Topic.created_at.desc())
        .all()
    )
    # 各トピックに対応する課題を取得
    assignments_by_topic = {}
    for topic_item in topic:
        assignments = (
            models.Assignment.query.filter_by(topic_id=topic_item.id)
            .order_by(models.Assignment.created_at.desc())
            .all()
        )
        assignments_by_topic[topic_item.id] = assignments

    # 各課題の提出数を集計
    submission_counts = (
        db.session.query(
            models.Submission.assignment_id,
            func.count(models.Submission.id).label("submission_count"),
        )
        .group_by(models.Submission.assignment_id)
        .all()
    )

    submission_count_dict = {
        count.assignment_id: count.submission_count for count in submission_counts
    }

    return render_template(
        "crud-blank2.html",
        form_make_topic=form_make_topic,
        class_data=class_data,
        classes=classes,
        joined_classes=joined_classes,
        topic=topic,
        assignments_by_topic=assignments_by_topic,
        current_user=current_user,
        class_member_count=class_member_count,
        submission_count_dict=submission_count_dict,
    )


# @crud.route("/class/<int:class_id>/assignment/<int:assignment_id>/responseStatus")
# def responseStatus(class_id, assignment_id):
#     # クラス情報の取得
#     class_info = models.Classpost.query.get(class_id)
#     if not class_info:
#         flash("クラスが見つかりません。", "danger")
#         return redirect(url_for("index"))

#     # 課題情報の取得
#     assignment = models.Assignment.query.get(assignment_id)
#     if not assignment:
#         flash("課題が見つかりません。", "danger")
#         return redirect(url_for("index"))

#     # 座席割り当てデータの取得
#     seat_assignment = models.SeatAssignment.query.filter_by(class_id=class_id).first()
#     if not seat_assignment:
#         flash("座席割り当てデータが見つかりません。", "danger")
#         return redirect(url_for("index"))

#     # options と mis_conception のデータを取得
#     options = models.Options.query.filter_by(assignment_id=assignment_id).all()
#     print(options)
#     misconceptions = models.MisConception.query.filter_by(
#         assignment_id=assignment_id
#     ).all()
#     print(misconceptions)

#     return render_template(
#         "response_status.html",
#         class_info=class_info,
#         assignment=assignment,
#         seat_assignment=seat_assignment,
#         options=options,
#         misconceptions=misconceptions,
#     )


@crud.route("/student/answer_page")
def student_answer_page():
    class_id = request.args.get("class_id")
    assignment_id = request.args.get("assignment_id")
    # クラス情報の取得
    class_info = models.Classpost.query.get(class_id)
    if not class_info:
        flash("クラスが見つかりません。", "danger")
        return redirect(url_for("index"))

    # 課題情報の取得
    assignment = models.Assignment.query.get(assignment_id)
    if not assignment:
        flash("課題が見つかりません。", "danger")
        return redirect(url_for("index"))

    # 生徒用の回答作成ページを表示
    return render_template(
        "student_answer_page.html",
        class_id=class_id,
        assignment_id=assignment_id,
        class_info=class_info,
        assignment=assignment,
        current_user=current_user,
    )


@crud.route("/teacher/response_status")
def teacher_response_status():
    try:
        class_id = request.args.get("class_id", type=int)
        assignment_id = request.args.get("assignment_id", type=int)

        # クラス情報の取得
        class_info = models.Classpost.query.get(class_id)
        if not class_info:
            flash("クラスが見つかりません。", "danger")
            return redirect(url_for("index"))

        # 課題情報の取得
        assignment = models.Assignment.query.get(assignment_id)
        if not assignment:
            flash("課題が見つかりません。", "danger")
            return redirect(url_for("index"))

        # 課題に紐づく座席割り当てデータを取得
        seat_assignment = assignment.seat_assignment
        if not seat_assignment:
            flash("座席割り当てデータが見つかりません。", "danger")
            return redirect(url_for("index"))

        # 提出されたものを課題IDと座席割り当てIDでフィルタリング
        submissions = models.Submission.query.filter_by(
            assignment_id=assignment_id, seat_assignment_id=seat_assignment.id
        ).all()

        # 生徒の回答、分類結果、質問の提案を含む辞書を作成
        submissions_data = {}
        for submission in submissions:
            submissions_data[submission.student_id] = {
                "content": submission.content,
                "classification_result": submission.classification_result,
                "provisional_question": submission.provisional_question,
            }

        # クラスに所属する全生徒のデータを取得
        students = models.User.query.filter(
            models.User.joined_classes.any(id=class_id)
        ).all()
        students_dict = {student.id: student.username for student in students}

        # 座席に提出情報をマッピング
        seat_layout = json.loads(seat_assignment.layout) if seat_assignment else []
        for row_index, row in enumerate(seat_layout):
            for seat_index, seat_id in enumerate(row):
                if seat_id:
                    try:
                        seat_id_int = int(seat_id)
                        student_name = students_dict.get(seat_id_int, "不明")
                        submission_info = submissions_data.get(seat_id_int, None)
                    except ValueError:
                        student_name = "不明"
                        submission_info = None

                    seat_layout[row_index][seat_index] = {
                        "id": seat_id,
                        "name": student_name,
                        "submitted": submission_info is not None,
                        "submission_info": submission_info,  # 提出情報の追加
                    }
                else:
                    seat_layout[row_index][seat_index] = {
                        "id": None,
                        "name": "",
                        "submitted": False,
                    }

        # options と mis_conception のデータを取得
        option = models.Options.query.filter_by(assignment_id=assignment_id).first()
        misconception = models.MisConception.query.filter_by(
            assignment_id=assignment_id
        ).first()

        # 教師用の座席表ページを表示
        return render_template(
            "response_status.html",
            class_info=class_info,
            assignment=assignment,
            seat_layout=seat_layout,  # 更新された座席情報を渡す
            option=option,
            misconception=misconception,
            submissions_data=submissions_data,  # 提出データの追加
        )
    except Exception as e:
        # 適切なエラーハンドリング
        return "エラーが発生しました: " + str(e), 500


@crud.route("/class/<int:class_id>/classanalytics", methods=["GET", "POST"])
def classanalytics(class_id):
    class_data = models.Classpost.query.get(class_id)
    # 現在ログインしているユーザーが作成したクラスのみを取得
    classes = models.Classpost.query.filter_by(creator_id=current_user.id).all()
    # 現在のユーザーが参加しているクラスを取得
    joined_classes = models.Classpost.query.filter(
        models.Classpost.members.any(id=current_user.id)
    ).all()

    return render_template(
        "crud-blank3.html",
        class_data=class_data,
        classes=classes,
        joined_classes=joined_classes,
    )


@crud.route("/seat-assignment/class/<int:class_id>")
def seat_assignment_page(class_id):
    class_data = models.Classpost.query.get(class_id)
    if class_data is None:
        return "クラスが見つかりません", 404

    students = class_data.members  # 生徒データの取得
    return render_template(
        "seet.html", class_data=class_data, students=students, class_id=class_id
    )


@crud.route("/class/<int:class_id>/students", methods=["GET"])
def get_students_for_class(class_id):
    class_data = models.Classpost.query.get(class_id)
    if class_data is None:
        return jsonify({"error": "クラスが見つかりません"}), 404

    # この例では、クラスに登録されている生徒が 'members' 属性を介してアクセスできると仮定しています。
    students = [
        {"id": student.id, "name": student.username} for student in class_data.members
    ]
    return jsonify({"students": students})


@crud.route("/save-seat-assignment", methods=["POST"])
def save_seat_assignment():
    try:
        data = request.get_json()
        class_id = data.get("classId")
        title = data.get("title")
        layout = json.dumps(data.get("layout"))  # layoutをJSON文字列に変換

        seat_assignment = models.SeatAssignment(
            class_id=class_id, title=title, layout=layout
        )
        db.session.add(seat_assignment)
        db.session.commit()

        return jsonify(
            {"message": "座席割り当てが保存されました", "redirectUrl": f"/class/{class_id}"}
        )
    except Exception as e:
        current_app.logger.error(f"Error saving seat assignment: {e}")
        return jsonify({"error": "データの保存中にエラーが発生しました"}), 500


@crud.route("/class/<int:class_id>/seat-assignments")
def get_seat_assignments_for_class(class_id):
    seat_assignments = models.SeatAssignment.query.filter_by(class_id=class_id).all()
    assignments_data = [
        {
            "id": assignment.id,
            "title": assignment.title,
            "layout": json.loads(assignment.layout),  # JSON文字列をPythonオブジェクトに変換
        }
        for assignment in seat_assignments
    ]
    return jsonify(assignments_data)


@crud.route("/class/<int:class_id>/assignment", endpoint="assignment")
def assignment(class_id):
    class_data = models.Classpost.query.get(class_id)
    # User モデルを使用して、特定のクラスに属する生徒のリストを取得
    students = (
        models.User.query.join(models.class_members)
        .filter(models.class_members.c.class_id == class_id)
        .all()
    )
    classes = models.Classpost.query.all()
    # ログインしているユーザーが作成したクラスの一覧を取得
    user_classes = models.Classpost.query.filter_by(creator_id=current_user.id).all()
    topic = (
        models.Topic.query.filter_by(class_id=class_id)
        .order_by(models.Topic.created_at.desc())
        .all()
    )
    assignment_id = session.get("assignment_id")
    editing_assignment = (
        models.Assignment.query.get(assignment_id) if assignment_id else None
    )
    print(editing_assignment)

    # 座席割り当てのリストを取得
    seat_assignments = models.SeatAssignment.query.filter_by(class_id=class_id).all()

    return render_template(
        "assignment.html",
        class_data=class_data,
        classes=classes,
        user_classes=user_classes,
        students=students,
        topic=topic,
        editing_assignment=editing_assignment,
        seat_assignments=seat_assignments,
    )


@crud.route("/class/<int:class_id>/create_concept_test", methods=["POST"])
def create_concept_test(class_id):
    creator_id = current_user.id  # 現在のユーザーID
    action = request.form.get("action")  # フォームからのアクションを取得
    title = request.form.get("title")
    description = request.form.get("description")
    due_date = request.form.get("due_date_time")  # 提出期限の取得
    topic_id = request.form.get("topic_id")  # トピックIDの取得
    seat_assignment_id = request.form.get("seat_assignment_id")  # 座席表IDの取得
    original_filename = None  # original_filenameの初期化
    # PDFファイルがアップロードされたかチェック
    if "file" in request.files:
        file = request.files["file"]
        if file and file.filename != "":
            original_filename = file.filename  # 元のファイル名を保存
            filename = secure_filename(file.filename)
            upload_folder = os.path.join(current_app.root_path, "static", "uploads")
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)
            filepath = os.path.join(upload_folder, filename)
            file.save(filepath)

            if filename.endswith(".pdf"):
                images = convert_from_path(filepath)
                preview_filename = filename.replace(".pdf", "_preview.png")
                preview_path = os.path.join(upload_folder, preview_filename)
                images[0].save(preview_path, "PNG")
                # データベースに保存するための相対パスを設定
                preview_db_path = os.path.join("uploads", preview_filename)
            else:
                preview_db_path = None
        else:
            filepath = None
            preview_db_path = None
    else:
        filepath = None
        preview_db_path = None

    if action == "temp_save":
        # 一時保存の処理
        new_assignment = models.Assignment(
            class_id=class_id,
            creator_id=creator_id,
            title=title,
            description=description,
            due_date=datetime.strptime(due_date, "%Y-%m-%dT%H:%M")
            if due_date
            else None,
            topic_id=topic_id,
            seat_assignment_id=seat_assignment_id,
            attachment=os.path.join("uploads", filename)
            if filepath
            else None,  # 相対パスを保存
            original_filename=original_filename,
            preview_image=preview_db_path,
        )
        db.session.add(new_assignment)
        db.session.commit()
        session["assignment_id"] = new_assignment.id  # セッションに課題IDを保存
        # コンセプトテスト作成ページへリダイレクト
        return redirect(
            url_for("crud.concept", class_id=class_id, assignment_id=new_assignment.id)
        )
    elif action == "final_save":
        # 最終保存の処理
        assignment_id = session.get("assignment_id", None)
        if assignment_id:
            assignment = models.Assignment.query.get(assignment_id)
        else:
            assignment = models.Assignment(class_id=class_id, creator_id=creator_id)

        # フォームデータで課題を更新
        assignment.title = title
        assignment.description = description
        assignment.due_date = (
            datetime.strptime(due_date, "%Y-%m-%dT%H:%M") if due_date else None
        )
        assignment.topic_id = topic_id
        # 座席割り当てIDを課題に保存
        assignment.seat_assignment_id = seat_assignment_id

        db.session.add(assignment)
        db.session.commit()

        # 課題の詳細ページなどにリダイレクト
        return redirect(
            url_for(
                "crud.classcontents", class_id=class_id, assignment_id=assignment.id
            )
        )

    return "Invalid action", 400


@crud.route("/class/<int:class_id>/concept", methods=["GET"])
def concept(class_id):
    class_data = models.Classpost.query.get(class_id)
    # セッションからassignment_idを取得
    assignment_id = session.get("assignment_id")
    classes = models.Classpost.query.all()
    user_classes = models.Classpost.query.filter_by(creator_id=current_user.id).all()
    # セッションからfirst_optionを取得
    first_option = session.get("first_option")
    misconception = session.get("misconception", "")
    question_text = session.get("question_text", "")

    return render_template(
        "concept.html",
        class_data=class_data,
        classes=classes,
        user_classes=user_classes,
        form=forms.MakeConcept(),
        form_make_misconcept=forms.MakemisConcept(),
        form_finish_concept=forms.FinishConcept(),
        misconception=misconception,
        first_option=first_option,
        class_id=class_id,
        question_text=question_text,
        assignment_id=assignment_id,
    )


@crud.route("/class/<int:class_id>/concept", methods=["POST"])
def create_concept(class_id):
    openai.api_key = settings.openai_api_key
    form_make_concept = forms.MakeConcept()
    if form_make_concept.validate_on_submit():
        # ここにフォームのデータを処理するコードを追加
        question_text = form_make_concept.question_text.data
        session["question_text"] = question_text
        if form_make_concept.validate_on_submit():
            question_text = form_make_concept.question_text.data

            # セッションからassignment_idを取得
            assignment_id = session.get("assignment_id")

            # データベースからAssignmentオブジェクトを取得
            assignment = models.Assignment.query.get(assignment_id)

            # question_textを設定し、データベースに保存
            if assignment:
                assignment.question_text = question_text
                db.session.commit()
        start = time.time()  # 開始時間
        # 自動で回答用意
        messages1 = [
            {
                "role": "system",
                "content": """経験豊富な物理教育者として、5つの異なる答えを草案してください。
            次の質問に日本語で回答します。それぞれは異なる物理概念に基づいています。 その中で、
            最初の選択肢のみが正しい回答を用意してください。残りの4つは誤解または間違いに基づいて回答を用意してください。
            各選択肢が選択肢番号から始まることを確認してください。5つ目の誤答は「わからない」とする。
            回答は合計 400 文字以内に制限してください。
            以下は生成する選択肢の例です。
            1.同時に着地する。
            2.２倍の重さの金属球の方が早く地面に達する。
            3.軽い金属球の方が早く地面に達する。
            4.2倍の重さの金属球が２倍早く地面に達する。
            5.わからない
            """,
            },
            {"role": "user", "content": question_text},
        ]
        # answer_options = analyze_with_gpt3(messages1, 0.45)
        answer_options = analyze_with_gpt4(messages1, 0.45)
        answer_options_list = answer_options.split(" . ")
        # print(f"answer_option\n{answer_options_list}")
        answer_options = list_to_string(
            [f"{opt} . " for opt in answer_options_list[:-1]]
            + [answer_options_list[-1]]
        )
        end = time.time() - start  # 終了時間 - 開始時間でかかった時間を計測
        print(f"選択肢生成に{end}秒かかりました！")
        first_option = answer_options_list[0] + " . "
        # 選択肢の生成が完了したら、first_optionをセッションに保存
        print(first_option)
        session["first_option"] = first_option
        return redirect(
            url_for(
                "crud.concept",
                class_id=class_id,
            )
        )

    # フォームのバリデーションに失敗した場合、元のページにリダイレクト
    return redirect(url_for("crud.concept", class_id=class_id))


# 選択肢の更新
@crud.route("/class/<int:class_id>/update_concept", methods=["POST"])
def update_concept(class_id):
    openai.api_key = settings.openai_api_key
    form_make_misconcept = forms.MakemisConcept()
    if form_make_misconcept.validate_on_submit():
        start = time.time()  # 開始時間
        # セッションからassignment_idを取得
        assignment_id = session.get("assignment_id")
        updated_option = form_make_misconcept.updated_option.data
        session["first_option"] = updated_option  # 編集された選択肢をセッションに保存
        options = models.Options(assignment_id=assignment_id, options=updated_option)
        db.session.add(options)
        db.session.commit()
        print(update_concept)
        # どのような誤概念を持っているか
        messages2 = [
            {
                "role": "system",
                "content": """経験豊富な物理教育者として、それぞれの事柄を深く分析します。間違った4つの選択肢について、
                根底にある物理学の誤解や誤りを解明してください。明確さと簡潔さを優先し、選択肢ごとに50文字以内、
                合計で200文字以内を目指します。 日本語で返事してください。
        """,
            },
            {"role": "user", "content": updated_option},
        ]
        misconception = analyze_with_gpt4(messages2)
        # misconception = analyze_with_gpt3(messages2, 0.7, 200)
        # print(f"misconception\n{misconception}")
        misconception_list = misconception.split(" . ")
        # print(f"misconception_list\n{misconception_list}")
        misconception = list_to_string(
            [f"{opt} . " for opt in misconception_list[:-1]] + [misconception_list[-1]]
        )
        session["misconception"] = misconception
        print(f"misconception\n{misconception}")
        end = time.time() - start  # 終了時間 - 開始時間でかかった時間を計測
        print(f"誤概念提案に{end}秒かかりました！")
        # ...

    return redirect(url_for("crud.concept", class_id=class_id))


# 誤概念の更新
@crud.route("/class/<int:class_id>/update_misconception", methods=["POST"])
def update_misconception(class_id):
    form_finish_concept = forms.FinishConcept()
    if form_finish_concept.validate_on_submit():
        # 誤概念のデータ処理
        # セッションからassignment_idを取得
        assignment_id = session.get("assignment_id")
        misconception = form_finish_concept.misconception.data
        session["misconception"] = misconception
        # ここでデータベースに保存したり、別の処理を行う
        misconception_data = models.MisConception(
            assignment_id=assignment_id, mis_conception=misconception
        )
        db.session.add(misconception_data)
        db.session.commit()
        print(misconception)

        return redirect(url_for("crud.concept", class_id=class_id))
    return redirect(url_for("crud.concept", class_id=class_id))


@crud.route("/submit_assignment", methods=["POST"])
def submit_assignment():
    data = request.get_json()
    student_id = data.get("studentId")
    assignment_id = data.get("assignmentId")
    content = data.get("answer")  # 'answer' から 'content' への名前変更
    seat_assignment_id = data.get("seatAssignmentId")  # 座席割り当てIDの取得

    options = models.Options.query.filter_by(assignment_id=assignment_id)
    # 回答分類
    messages3 = [
        {
            "role": "system",
            "content": f"""あなたは経験豊富な物理の専門家です。
            userから生徒の回答が送られます。
            以下の選択肢から最も似ているものを分類し、その番号のみを返答してください。{options}。
                """,
        },
        {"role": "user", "content": content},
    ]

    classification_result = analyze_with_gpt4(messages3, 0.8, 2).strip()
    # classification_result = analyze_with_gpt3(messages3, 0.8, 2).strip()
    # 選択肢の番号を抽出
    print(classification_result)
    classification_result = extract_choice_number(classification_result)

    # つまづきの特定と質問文生成
    messages4 = [
        {
            "role": "system",
            "content": f"""あなたは経験豊富な物理教育者です。 生徒たちの意見について、正解「{options}」と比較し、
            誤解、混乱している領域を特定し、生徒が自分の意見を明確にするために教師に投げかけるであろう質問を予測します。
            核となる概念・把握し、返答は 200 文字以内の簡潔な日本語の質問 で行う必要があります。
                """,
        },
        {"role": "user", "content": content},
    ]
    provisional_question = analyze_with_gpt4(messages4, 0.6, 100)

    # 新しい提出を作成
    submission = models.Submission(
        student_id=student_id,
        assignment_id=assignment_id,
        content=content,  # 'content' を使用
        seat_assignment_id=seat_assignment_id,  # 座席割り当てIDを設定
        classification_result=classification_result,  # 分類結果
        provisional_question=provisional_question,  # 質問の提案
    )

    # データベースに保存
    try:
        db.session.add(submission)
        db.session.commit()
        return jsonify({"success": True, "message": "回答が提出されました。"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": "回答の提出に失敗しました。"})


# OpenAI GPT-4 APIを使って問題を解析する関数
def analyze_with_gpt4(messages, temperature=0.5, max_tokens=300):
    return openai.ChatCompletion.create(
        model="gpt-4-1106-preview",
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )["choices"][0]["message"]["content"]


def list_to_string(lst):
    return "</n>".join(lst)


def extract_choice_number(response_text):
    # 正規表現で選択肢の番号を抽出
    match = re.search(r"\b\d+\b", response_text)
    if match:
        return match.group()
    else:
        return None

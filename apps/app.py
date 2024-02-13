import settings
from flask import Flask, render_template, request, jsonify
import openai
import gspread
import gspread_dataframe as gd
from oauth2client.service_account import ServiceAccountCredentials
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import time
from sklearn.metrics.pairwise import cosine_similarity
import re
from .extensions import db, login_manager
from .models import User


student_datas = []
teams = []
# 会話履歴を保存するためのリスト
conversation_history = []


def create_app():
    app = Flask(__name__)
    app.config.from_pyfile("settings.py")

    db.init_app(app)
    login_manager.init_app(app)

    migrate = Migrate(app, db)

    @app.template_filter("count_lines")
    def count_lines(s):
        if s is None:
            return 0
        return len(s.split("\n"))

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.route("/", endpoint="about")
    def about():
        return render_template("about.html")

    @app.route("/cards", endpoint="cards")
    def index():
        return render_template("cards.html")

    @app.route("/index2", endpoint="index2")
    def index2():
        return render_template("index2.html")

    @app.route("/forgot_password", endpoint="forgotpassword")
    def forgotpassword():
        return render_template("forgot-password.html")

    @app.route("/blank1", endpoint="blank1")
    def blank1():
        return render_template("blank1.html")

    @app.route("/blank2", endpoint="blank2")
    def blank2():
        return render_template("blank2.html")

    @app.route("/blank3", endpoint="blank3")
    def blank3():
        return render_template("blank3.html")

    @app.route("/seet", endpoint="seet")
    def seet():
        return render_template("seet.html")

    @app.route("/login", endpoint="login")
    def login():
        return render_template("login.html")

    @app.route("/register", endpoint="register")
    def register():
        return render_template("register.html")

    @app.route("/404", endpoint="404")
    def error():
        return render_template("404.html")

    @app.route("/buttons", endpoint="buttons")
    def buttons():
        return render_template("buttons.html")

    @app.route("/tables", endpoint="tables")
    def tables():
        return render_template("tables.html")

    @app.route("/charts", endpoint="charts")
    def charts():
        return render_template("charts.html")

    @app.route("/utilitiesanimation", endpoint="utilitiesanimation")
    def utilitiesanimation():
        return render_template("utilities-animation.html")

    @app.route("/utilitiesborder", endpoint="utilitiesborder")
    def utilitiesborder():
        return render_template("utilities-border.html")

    @app.route("/utilitiescolor", endpoint="utilitiescolor")
    def utilitiescolor():
        return render_template("utilities-color.html")

    @app.route("/utilitiesother", endpoint="utilitiesother")
    def utilitiesother():
        return render_template("utilities-other.html")

    @app.route("/teacher")
    def teacher():
        global student_datas, teams
        student_datas = []
        teams = []
        start = time.time()  # 開始時間
        # 初期質問
        initial_question = """同じ大きさの 2 つの金属球がある。一方の重さは他方の2倍である。2階の窓から
                            2つの金属球を、同時に落とすとき、地面に着くまでの時間はどうなるか"""

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
            {"role": "user", "content": initial_question},
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
        # 新しい変数を定義
        first_option = answer_options_list[0] + " . "
        # 「正しい答えは」で文字列を分割
        parts = first_option.split("正しい")
        # 最初の部分（選択肢のみを含む）を取り出す
        first_option = parts[0].strip()
        print(f"first_option\n{first_option}")
        rest_options = list_to_string(answer_options_list[1:])
        # print(f"rest_options\n{rest_options}")
        # correct_answer_optionの取得
        correct_answer_option = answer_options.split("2.")[0].strip()
        # print(f"correct_answer_option\n{correct_answer_option}")
        # どのような誤概念を持っているか
        messages2 = [
            {
                "role": "system",
                "content": """経験豊富な物理教育者として、それぞれの事柄を深く分析します。間違った4つの選択肢について、
                根底にある物理学の誤解や誤りを解明してください。明確さと簡潔さを優先し、選択肢ごとに50文字以内、
                合計で200文字以内を目指します。 日本語で返事してください。
        """,
            },
            {"role": "user", "content": first_option},
        ]
        misconception = analyze_with_gpt4(messages2)
        # misconception = analyze_with_gpt3(messages2, 0.7, 200)
        # print(f"misconception\n{misconception}")
        misconception_list = misconception.split(" . ")
        # print(f"misconception_list\n{misconception_list}")
        misconception = list_to_string(
            [f"{opt} . " for opt in misconception_list[:-1]] + [misconception_list[-1]]
        )
        print(f"misconception\n{misconception}")
        end = time.time() - start  # 終了時間 - 開始時間でかかった時間を計測
        print(f"誤概念提案に{end}秒かかりました！")

        # 回答分類
        # options = first_option.split("\n")[:-1]  # 最後の空行を除外
        # # 各選択肢のエンベッディングを取得
        # option_embeddings = [get_embedding(option_text) for option_text in options]

        for idx, student_text in enumerate(student_texts):
            student_name = student_names[idx]
            student_id = student_ids[idx]
            # # 学生の回答のエンベッディングを取得
            # student_answer_embedding = get_embedding(student_text)
            # # 各選択肢と学生の回答の類似度を計算
            # similarities = [
            #     calculate_cosine_similarity(student_answer_embedding, option_embedding)
            #     for option_embedding in option_embeddings
            # ]
            # # 最も類似度が高い選択肢を見つける
            # most_similar_index = np.argmax(similarities)
            # classification_result = options[most_similar_index]
            # match = re.match(r"(\d+)\.", classification_result)
            # classification_result = match.group(1) if match else "番号不明"

            # # classification_result = analyze_with_gpt4(messages3, 0, 1).strip()
            messages3 = [
                {
                    "role": "system",
                    "content": f"""あなたは経験豊富な物理の専門家です。
                    userから生徒の回答が送られます。
                    以下の選択肢から最も似ているものを分類し、その番号のみを返答してください。{first_option}。
                        """,
                },
                {"role": "user", "content": student_text},
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
                    "content": f"""あなたは経験豊富な物理教育者です。 生徒たちの意見について、正解「{first_option}」と比較し、
                    誤解、混乱している領域を特定し、生徒が自分の意見を明確にするために教師に投げかけるであろう質問を予測します。
                    核となる概念・把握し、返答は 200 文字以内の簡潔な日本語の質問 で行う必要があります。
                        """,
                },
                {"role": "user", "content": student_text},
            ]
            provisional_question = analyze_with_gpt4(messages4, 0.6, 100)
            # provisional_question = analyze_with_gpt3(messages4, 0.6, 100)

            student_data = {
                "name": student_name,
                "id": student_id,
                "answer": student_text,
                "classification": classification_result,
                "question": provisional_question,
            }
            student_datas.append(student_data)
            print(student_id)
            # print(classification_result)
            end = time.time() - start  # 終了時間 - 開始時間でかかった時間を計測
            print(f"この生徒に{end}秒かかりました！")

            # チームを作成
            teams = create_teams(student_datas, 4)
            # print(teams)

        end = time.time() - start  # 終了時間 - 開始時間でかかった時間を計測
        print(f"{end}秒かかりました！")

        return render_template(
            "teacher.html",
            student_datas=student_datas,
            answer_options=answer_options,
            misconception=misconception,
            # seat_map=seat_map,
            correct_answer_option=correct_answer_option,
            first_option=first_option,
            rest_options=rest_options,
            teams=teams,
        )

    @app.route("/student/<int:student_id>")
    def student_info(student_id):
        global student_datas, teams
        # student_id を使用して、student_datas リストから生徒情報を取得します。
        student = next((s for s in student_datas if s["id"] == student_id), None)
        if not student:
            return "生徒が見つかりません", 404

        # 生徒が所属する班を探索します。
        team_index = None
        for i, team in enumerate(teams):
            # チーム内の生徒のIDを確認
            if any(s["id"] == student_id for s in team):
                team_index = i
                break

        if team_index is None:
            return "班が見つかりません", 404

        team_members = teams[team_index]
        return render_template(
            "student_info.html",
            student=student,
            team_members=team_members,
            num_students_per_team=4,
        )

    # In-memory storage for chat messages
    messages = []

    @app.route("/send_message", methods=["POST"])
    def send_message():
        try:
            user_message = request.json.get("message")
            question_requirements = (
                "生徒の回答は自由落下に関連する物理法則を正しく説明し、"
                "異なる質量の物体が地面に到達するまでの時間に違いがあるかどうかについて分析し、"
                "その理由を論理的に説明している必要があります。"
            )
            if user_message:
                response_message = generate_response(
                    user_message, question_requirements
                )
                return jsonify(success=True, response_message=response_message)
        except Exception as e:
            return jsonify(success=False, message=str(e)), 500

    def is_question(message):
        # 簡単な質問判断ロジック（実際にはもっと複雑になる可能性があります）
        return message.endswith("？")

    @app.route("/get_messages", methods=["GET"])
    def get_messages():
        return jsonify(messages=messages)

    # 生徒の記述画面へのルート
    @app.route("/student_input")
    def student_input():
        return render_template("student_input.html")

    # Googleスプレッドシートへのアクセス設定
    # この部分は、グローバル変数として定義しても良いですが、
    # 必要に応じてアプリケーションコンテキスト内で使用することをお勧めします。
    spreadsheet_url = settings.spreadsheet_url
    json_keyfile_path = settings.json_keyfile_path
    openai.api_key = settings.openai_api_key

    scope = settings.scope
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        json_keyfile_path, scope
    )
    gc = gspread.authorize(credentials)
    spreadsheet = gc.open_by_url(spreadsheet_url)

    # Googleスプレッドシートへのアクセスとデータ取得
    gc = gspread.authorize(credentials)
    spreadsheet = gc.open_by_url(spreadsheet_url)
    worksheet = spreadsheet.get_worksheet(0)
    df = gd.get_as_dataframe(worksheet)
    student_texts = df.iloc[:, 0].dropna().tolist()
    student_names = df.iloc[:, 2].dropna().tolist()
    student_ids = df.iloc[:, 3].dropna().tolist()

    # OpenAI GPT-3 APIを使って問題を解析する関数
    def analyze_with_gpt3(messages, temperature=0.5, max_tokens=200):
        return openai.ChatCompletion.create(
            model="gpt-3.5-turbo-16k",
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )["choices"][0]["message"]["content"]

    # OpenAI GPT-4 APIを使って問題を解析する関数
    def analyze_with_gpt4(messages, temperature=0.5, max_tokens=300):
        return openai.ChatCompletion.create(
            model="gpt-4-1106-preview",
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )["choices"][0]["message"]["content"]

    def get_embedding(text, model="text-embedding-ada-002"):
        # テキストの前処理：改行と特殊文字を取り除く
        text = text.replace("\n", " ").strip()

        # APIリクエストを実行
        try:
            response = openai.Embedding.create(input=[text], model=model)
            return response["data"][0]["embedding"]
        except Exception as e:
            print(f"エラーが発生しました: {e}")
            return None

    def calculate_cosine_similarity(embedding1, embedding2):
        return cosine_similarity([embedding1], [embedding2])[0][0]

    def extract_category(text):
        # レスポンステキストを行に分割
        lines = text.split("\n")
        # 各行をループして"Classification:"を探す
        for line in lines:
            if "Classification:" in line:
                # "Classification:"の後のテキストを取り出す
                return line.split("Classification:")[1].strip()
        # もし"Classification:"が見つからない場合はNoneを返す
        return None

    # 会話履歴を保存するためのグローバルリスト
    conversation_history = []

    def generate_response(user_message, question_requirements):
        # ユーザーメッセージを会話履歴に追加
        conversation_history.append({"role": "user", "content": user_message})

        try:
            # メッセージをGPT-4に送り、カテゴリを分類
            system_message_for_classification = {
                "role": "system",
                "content": """このAIは、メッセージを以下のカテゴリーに分類するよう訓練されています: 'answer-seeking',
                'information-seeking', 'instruction-seeking', 'explanation-seeking', または 'other'. 
                各メッセージに適切なカテゴリーを割り当ててください。""",
            }
            classification_response = openai.ChatCompletion.create(
                model="gpt-4-1106-preview",
                messages=[
                    system_message_for_classification,
                    {"role": "user", "content": user_message},
                ],
                temperature=0.5,
                max_tokens=300,
            )
            category = (
                "answer-seeking"
                if "answer-seeking"
                in classification_response["choices"][0]["message"]["content"]
                else "other"
            )

            # 分類結果に基づいて応答を生成
            if category == "answer-seeking":
                return "申し訳ございません、直接答えをお教えすることはできません。"
            else:
                # GPT-4を使用して応答を生成（履歴を含む）
                system_message_for_response = {
                    "role": "system",
                    "content": f"""経験豊富な教育者として、以下の生徒の回答を評価してください。
                            物理的概念や自然法則の理解が正しいかどうかは絶対に教えないでください。
                            物理的概念や自然法則の理解が間違っていても間違っていると教えないでください。
                            回答が論理的な整合性を持っているかを確認し、主語の不足や論理的矛盾、理由の不足を指摘することで、
                            論理的に矛盾していたら、指摘してください。
                            生徒が回答を改善するための具体的な提案をしてください。
                            100文字以内で、生徒に対して話すように返答してください。100文字以内です。
                            生徒が直接的に答えを求めていると感じたら、怒ってください。
                            
                            ３ラリーを超えたら、提出しましょう！といっていください。。{question_requirements}""",
                }
                response = openai.ChatCompletion.create(
                    model="gpt-4-1106-preview",
                    messages=conversation_history + [system_message_for_response],
                    temperature=0.5,
                    max_tokens=150,
                )
                response_message = response["choices"][0]["message"]["content"].strip()

                # 応答を会話履歴に追加
                conversation_history.append(
                    {"role": "assistant", "content": response_message}
                )

                return response_message
        except Exception as e:
            print(f"An error occurred: {e}")
            return "すみません、お教えすることはできません。"

    # リストを改行区切りの文字列に変換する関数
    def list_to_string(lst):
        return "</n>".join(lst)

    student_datas = []
    teams = []

    def chunk_list(lst, n):
        """リストをn個の要素ごとに分割します。"""
        return [lst[i : i + n] for i in range(0, len(lst), n)]

    def create_teams(student_datas, team_size=4, max_id=40):
        if not student_datas:
            return []

        # 出席番号1から40までのリストを作成
        all_ids = list(range(1, max_id + 1))

        # チームの枠組みを作成
        team_frames = [
            all_ids[i : i + team_size] for i in range(0, len(all_ids), team_size)
        ]

        # 実際の生徒データを走査し、適切なチームに割り当て
        teams = [[] for _ in range(len(team_frames))]
        for student in student_datas:
            for i, frame in enumerate(team_frames):
                if student["id"] in frame:
                    teams[i].append(student)
                    break

        return teams

    def extract_choice_number(response_text):
        # 正規表現で選択肢の番号を抽出
        match = re.search(r"\b\d+\b", response_text)
        if match:
            return match.group()
        else:
            return None

    # teacher関数内での使用方法
    # student_datas = [...]
    teams = create_teams(student_datas, 4, 40)

    """
    ブループリントの登録
    """
    # crudアプリのモジュールviews.pyからBlueprint「crud」をインポート
    from apps.crud.views import crud

    # FlaskオブジェクトにBlueprint「crud」を登録
    app.register_blueprint(crud)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)

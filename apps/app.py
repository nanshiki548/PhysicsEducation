import config
from flask import Flask, render_template, request, jsonify
import openai
import gspread
import gspread_dataframe as gd
from oauth2client.service_account import ServiceAccountCredentials
import time

app = Flask(__name__, static_folder="static")

# 設定ファイルから情報を取得
spreadsheet_url = config.spreadsheet_url
json_keyfile_path = (
    "/Users/matsudatatsuya/gpt_sample/voltaic-space-388911-7adfbc11d865.json"
)
openai.api_key = config.openai_api_key

# スコープ設定と認証情報の設定
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
credentials = ServiceAccountCredentials.from_json_keyfile_name(json_keyfile_path, scope)

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


def classify_chat_message(message):
    # GPT-4に渡すシステムメッセージ
    system_message = {
        "role": "system",
        "content": """このAIは、メッセージを以下のカテゴリーに分類するよう訓練されています: 'answer-seeking',
        'information-seeking', 'instruction-seeking', 'explanation-seeking',
        または 'other'. 各メッセージに適切なカテゴリーを割り当ててください。""",
    }
    # ユーザーメッセージ
    user_message = {"role": "user", "content": message}

    # GPT-4に送るメッセージリスト
    messages = [system_message, user_message]

    # GPT-4による分析実行
    response = openai.ChatCompletion.create(
        model="gpt-4-1106-preview", messages=messages, temperature=0.5, max_tokens=300
    )

    # レスポンスからカテゴリとその根拠を取得
    full_response = response["choices"][0]["message"]["content"]
    print(full_response)

    # "answer-seeking"という文字列がfull_responseに含まれているかを確認し、抽出
    if "answer-seeking" in full_response:
        return "answer-seeking"
    else:
        return "No 'answer-seeking' category found in the response."


# 分類結果に基づいてユーザーに返答を生成します。
def generate_response(user_message):
    # ユーザーのメッセージを分類
    category = classify_chat_message(user_message)

    # 分類結果に基づいて返答を生成
    if category == "answer-seeking":
        response = "申し訳ございません、直接答えをお教えすることはできません。"
    else:
        # 他のカテゴリの場合は、chat_gpt4関数を使用して応答を生成
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": user_message},
        ]
        response = chat_gpt4(messages)

    return response


# 答えを教えてくれないチャット
def chat_gpt4(messages, temperature=0.5, max_tokens=100):
    try:
        response = openai.ChatCompletion.create(
            # model="gpt-4-1106-preview",
            model="gpt-3.5-turbo-16k",
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stop=[
                "答え",
                "正解",
                "回答",
            ],
        )
        return response.choices[0].message.content
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


@app.route("/")
def index():
    start = time.time()  # 開始時間
    global student_datas, teams
    # 初期質問
    initial_question = """同じ大きさの 2 つの金属球がある。一方の重さは他方の 2 倍である。2階の窓から
                        2 つの金属 球を，同時に落とすとき，地面に着くまでの時間はどうなるか"""

    # 自動で回答用意
    messages1 = [
        {
            "role": "system",
            "content": """経験豊富な物理教育者として、5つの異なる答えを草案してください。
        次の質問に日本語で回答します。それぞれは異なる物理概念に基づいています。 その中で、
        最初の選択肢のみが正しい回答を用意してください。残りの4つは誤解または間違いに基づいて回答を用意してください。
        各選択肢が選択肢番号から始まることを確認してください。 回答は合計 400 文字以内に制限してください。
        """,
        },
        {"role": "user", "content": initial_question},
    ]
    answer_options = analyze_with_gpt4(messages1, 0.45)
    # answer_options = analyze_with_gpt3(messages1, 0.45)
    answer_options_list = answer_options.split(" . ")
    # print(answer_options_list)
    answer_options = list_to_string(
        [f"{opt} . " for opt in answer_options_list[:-1]] + [answer_options_list[-1]]
    )

    # 新しい変数を定義
    first_option = answer_options_list[0] + " . "
    rest_options = list_to_string(answer_options_list[1:])

    # correct_answer_optionの取得
    correct_answer_option = answer_options.split("2.")[0].strip()

    # どのような誤概念を持っているか
    messages2 = [
        {
            "role": "system",
            "content": """経験豊富な物理教育者として、それぞれの事柄を深く分析します。間違った4つの選択肢について、
            根底にある物理学の誤解や誤りを解明してください。明確さと簡潔さを優先し、選択肢ごとに 100 文字以内、
            合計で400 文字以内を目指します。 日本語で返事してください。
    """,
        },
        {"role": "user", "content": answer_options},
    ]
    misconception = analyze_with_gpt4(messages2)
    # misconception = analyze_with_gpt3(messages2)
    misconception_list = misconception.split(" . ")
    misconception = list_to_string(
        [f"{opt} . " for opt in misconception_list[:-1]] + [misconception_list[-1]]
    )

    for idx, student_text in enumerate(student_texts):
        student_name = student_names[idx]
        student_id = student_ids[idx]

        # 回答分類
        messages3 = [
            {
                "role": "system",
                "content": f"""経験豊富な物理の専門家として、提供された文章を分析し、5 つの選択肢のいずれかと一致させます。
                最も一致する文章に基づいて、選択肢番号を返します。回答のテキストでは必ず数値を先頭に置きます。
                前回のインタラクションのコンテキストは: {answer_options}です。
                    """,
            },
            {"role": "user", "content": student_text},
        ]
        classification_result = analyze_with_gpt4(messages3, 0, 1).strip()
        # classification_result = analyze_with_gpt3(messages3, 0, 1).strip()

        # つまづきの特定と質問文生成
        messages4 = [
            {
                "role": "system",
                "content": f"""あなたは経験豊富な物理教育者です。 生徒たちの意見について、正解「{correct_answer_option}」と比較し、
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

    # student_datas を4人ごとに分割して班に分けます。
    teams = chunk_list(student_datas, 4)

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
    # student_id を使用して、student_datas リストから生徒情報を取得します。
    student = next((s for s in student_datas if s["id"] == student_id), None)
    if not student:
        return "生徒が見つかりません", 404

    # 生徒が所属する班を取得します。
    team_index = None
    for i, team in enumerate(teams):
        if student in team:
            team_index = i
            break

    if team_index is None:
        return "班が見つかりません", 404

    team_members = teams[team_index]

    # 生徒の詳細情報ページを表示するテンプレートをレンダリングします。
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
    user_message = request.json.get("message")
    if user_message:
        # ユーザーのメッセージに応じた返答を生成
        response_message = generate_response(user_message)
        return jsonify(
            success=True, user_message=user_message, response_message=response_message
        )
    return jsonify(success=False, message="Message content is missing."), 400


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


if __name__ == "__main__":
    app.run(debug=True)

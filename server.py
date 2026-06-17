from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import random
from datetime import datetime, timedelta
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
app.secret_key = 'farloveway'  # 記得更換為安全的 key
app.permanent_session_lifetime = timedelta(minutes=30)

@app.route('/')
def index():
    return render_template('firstscreen.html')

@app.route('/select_mode', methods=['POST'])
def select_mode():
    mode = request.form['mode']
    session['mode'] = mode
    return redirect(url_for('secondscreen'))

@app.route('/second')
def secondscreen():
    return render_template('secondscreen.html')

@app.route('/select_level', methods=['POST'])
def select_level():
    level = request.form['level']
    session['level'] = level
    return redirect(url_for('thirdscreen'))

@app.route('/third')
def thirdscreen():
    mode = session.get('mode')
    level = session.get('level')

    mode_text = {
        'add': '加法',
        'sub': '減法',
        'mix': '加(減)法'
    }.get(mode, '')

    level_text = {
        'easy': '易',
        'medium': '中',
        'hard': '難'
    }.get(level, '')

    description = generate_instruction(mode, level)

    return render_template('thirdscreen.html',
                           mode_text=mode_text,
                           level_text=level_text,
                           description=description)

@app.route('/game')
def game():
    return render_template('forthscreen.html')

@app.route('/generate_questions')
def generate_questions():
    mode = session.get('mode')
    level = session.get('level')

    num_per_question = {
        'easy': 4,
        'medium': 7,
        'hard': 10
    }.get(level, 4)

    num_questions = {
        'easy': 4,
        'medium': 7,
        'hard': 10
    }.get(level, 4)

    questions = []
    for _ in range(num_questions):
        nums = []
        last_num = None
        for _ in range(num_per_question):
            while True:
                n = random.randint(1, 9)
                if n != last_num:  # 不讓它與前一個數字重複
                    break
            last_num = n
            if mode == 'sub':
                n = -n
            elif mode == 'mix':
                n *= random.choice([-1, 1])
            nums.append(n)
        questions.append(nums)

    start_value = 30 if mode == 'sub' else 0
    return jsonify({'questions': questions, 'start_value': start_value})



def generate_instruction(mode, level):
    count = {
        'easy': 4,
        'medium': 7,
        'hard': 10
    }.get(level, '')

    question_count = count

    op_text = {
        'add': '加法',
        'sub': '減法【起始為 30】',
        'mix': '加(減)法'
    }.get(mode, '')

    return f"玩法說明：進入測驗畫面，按下「開始出題」後，每 2 秒會隨機出現數字，每題 {count} 個數字，共 {question_count} 題。請使用「{op_text}」依序計算！"

def get_leaderboard_by_mode(mode):
    result = supabase.table('leaderboard') \
            .select('*') \
            .eq("mode", mode) \
            .order('score', desc=True) \
            .limit(10) \
            .execute()
    return result.data

@app.route('/submit_score', methods=['POST'])
def submit_score():
    data = request.get_json()
    nickname = data.get('nickname')
    
    # 模式轉換字典
    mode_map = {
        'add': '加法',
        'sub': '減法',
        'mix': '加(減)法'
    }
    mode_key = data.get('mode')
    mode = mode_map.get(mode_key, mode_key)
    score = data.get('score')
    print("received json", request.json)

    if nickname and mode and isinstance(score, int):
        supabase.table('leaderboard').insert({
            'nickname': nickname,
            'mode': mode,
            'score': score
        }).execute()

        leaderboard_data = get_leaderboard_by_mode(mode)

        # 組成 HTML 排行榜
        html = "<table style='width:100%; border-collapse: collapse;'>"
        html += "<tr><th>名次</th><th>暱稱</th><th>模式</th><th>成績</th></tr>"
        for i, row in enumerate(leaderboard_data, start=1):
            html += f"<tr><td>{i}</td><td>{row['nickname']}</td><td>{row['mode']}</td><td>{row['score']}</td></tr>"
        html += "</table>"

        return jsonify({'message': '成績已提交', 'leaderboard_html': html})

    else:
        return jsonify({'error': '資料格式錯誤'}), 400



@app.route('/get_leaderboard', methods=['GET'])
def get_leaderboard():
    mode = request.args.get('mode')
    if not mode:
        return jsonify({'error': '請提供模式參數'}), 400

    leaderboard_data = get_leaderboard_by_mode(mode)

    # 模式轉換字典
    mode_map = {
        'add': '加法',
        'sub': '減法',
        'mix': '加(減)法'
    }

    # 將每筆資料的 mode 轉為中文
    for row in leaderboard_data:
        row['mode'] = mode_map.get(row['mode'], row['mode'])  # 預設保留原本文字

    return jsonify(leaderboard_data)

if __name__ == '__main__':
    app.run()

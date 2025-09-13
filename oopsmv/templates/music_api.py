# unified_music_server.py
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime
import threading, time, webbrowser, json, requests, random
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# 추천 관련 클래스 임포트
from music_select import BalancedRatioRecommender, EmotionTag, ActivityTag, Weather
from music_recommender import WeatherService  # location_server용

# Flask 앱 초기화
app = Flask(__name__)
CORS(app)

# 위치 저장용 글로벌 변수
location_data = {"lat": None, "lon": None, "accuracy": None, "timestamp": None}
recommender = BalancedRatioRecommender()

# ---------- [1] 정적 페이지 ----------
@app.route('/')
def index():
    return send_from_directory('templates', 'front1.html')


# ---------- [2] 위치 저장 ----------
@app.route('/save_location', methods=['POST'])
def save_location():
    data = request.get_json()
    location_data.update({
        "lat": data['lat'],
        "lon": data['lon'],
        "accuracy": data.get('accuracy', 0),
        "timestamp": datetime.now().isoformat()
    })
    with open('user_location.json','w',encoding='utf-8') as f:
        json.dump(location_data, f, ensure_ascii=False, indent=2)
    return jsonify({'success': True})


# ---------- [3] 단순 추천 API ----------
@app.route('/recommend', methods=['POST'])
def recommend():
    data = request.json
    print("[FLASK] 🔍 요청 데이터:", data, flush=True)

    # 사용자 선택값 Enum으로 변환
    emotion = EmotionTag[data['emotion'].upper()]
    activity = ActivityTag[data['activity'].upper()]
    weather = Weather[data['weather'].upper()]

    print(f"[FLASK] 🎭 감정: {emotion}, ⚙️ 활동: {activity}, 🌤️ 날씨: {weather}", flush=True)

    result = recommender.recommend_music(emotion, activity, weather)

    if not result:
        return jsonify({'error': '추천 실패'}), 500

    analysis = recommender.get_detailed_analysis(result)
    base_url = "https://api.jamendo.com/v3.0/tracks/"
    client_id = "602b9767"
    query_string = "&".join(f"{k}={v}" for k, v in result.api_params.items())
    full_url = f"{base_url}?client_id={client_id}&{query_string}"

    try:
        resp = requests.get(full_url)
        if resp.status_code != 200:
            return jsonify({'error': 'API 요청 실패'}), 502

        data = resp.json()
        tracks = data.get('results', [])
        random.shuffle(tracks)
        selected = tracks[:20]

        return jsonify({
            'api_params': result.api_params,
            'analysis': analysis,
            'tracks': selected
        })

    except Exception as e:
        print("[FLASK] ❗예외 발생:", e, flush=True)
        return jsonify({'error': '서버 내부 오류'}), 500


# ---------- [4] 위치 기반 통합 추천 ----------
@app.route('/recommend_with_location', methods=['POST'])
def recommend_with_location():
    data = request.get_json()
    emo = data.get('emotion')
    try:
        emotion = EmotionTag(emo)
    except:
        return jsonify({'success': False, 'error': 'Invalid emotion'}), 400

    lat = location_data.get('lat')
    lon = location_data.get('lon')
    if lat is None or lon is None:
        return jsonify({'success': False, 'error': 'Location missing'}), 400

    now_h = datetime.now().hour
    time_of_day = recommender.get_time_of_day(now_h)

    ws = WeatherService()
    weather_res = ws.get_weather_by_coordinates(lat, lon)
    if weather_res:
        weather_enum, weather_info, _ = weather_res
    else:
        weather_enum, weather_info, _ = ws.get_weather_wttr() or ws.get_fallback_weather()

    music = recommender.recommend_music(
        emotion, 
        ActivityTag.COMMUTE, 
        weather_enum, 
        time_of_day, 
        randomize=True
    )

    params = "&".join(f"{k}={v}" for k,v in music.api_params.items())
    url = f"https://api.jamendo.com/v3.0/tracks/?client_id=602b9767&{params}"
    tracks = []
    try:
        response = requests.get(url, timeout=5).json()
        results = response.get('results', [])
        for t in results[:20]:
            tracks.append({
                'name': t.get('name'),
                'artist': t.get('artist_name'),
                'audio': t.get('audio')
            })
    except Exception as e:
        print(f"⚠️ Jamendo API 요청 실패: {e}")

    return jsonify({
        'success': True,
        'emotion': emotion.value,
        'weather': weather_info,
        'timeOfDay': time_of_day.value,
        'tracks': tracks
    })


# ---------- [5] 서버 실행 ----------
def start_server(port=5000):
    def run(): 
        app.run(host='0.0.0.0', port=port, debug=True, use_reloader=False)
    t = threading.Thread(target=run, daemon=True)
    t.start()
    time.sleep(1)
    webbrowser.open(f'http://localhost:{port}')
    return t

if __name__ == '__main__':
    print("🌐 Starting unified music recommendation server...")
    start_server()
    input("Press Enter to quit.")

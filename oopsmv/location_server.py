# location_server.py
from flask import Flask, request, jsonify, send_from_directory
import json, threading, time, webbrowser
from datetime import datetime
import requests

# music_recommender에서 필요한 것들 import
from music_recommender import (
    BalancedRatioRecommender, WeatherService,
    EmotionTag, ActivityTag
)

app = Flask(__name__)
location_data = {"lat": None, "lon": None, "accuracy": None, "timestamp": None}

# 1) 정적 페이지
@app.route('/')
def index():
    return send_from_directory('templates', 'front1.html')

# 2) 위치 저장
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

# 3) 통합 추천 API
@app.route('/recommend', methods=['POST'])
def recommend():
    data = request.get_json()
    # 3-1) 감정 파싱
    emo = data.get('emotion')
    try:
        emotion = EmotionTag(emo)
    except:
        return jsonify({'success': False, 'error': 'Invalid emotion'}), 400

    # 3-2) 위치 확인
    lat = location_data.get('lat')
    lon = location_data.get('lon')
    if lat is None or lon is None:
        return jsonify({'success': False, 'error': 'Location missing'}), 400

    # 3-3) 시간대 계산
    now_h = datetime.now().hour
    rec = BalancedRatioRecommender()
    time_of_day = rec.get_time_of_day(now_h)

    # 3-4) 날씨 조회
    ws = WeatherService()
    weather_res = ws.get_weather_by_coordinates(lat, lon)
    if weather_res:
        weather_enum, weather_info, _ = weather_res
    else:
        backup = ws.get_weather_wttr()
        if backup:
            weather_enum, weather_info, _ = backup
        else:
            weather_enum, weather_info, _ = ws.get_fallback_weather()

    # 3-5) 음악 추천 생성
    music = rec.recommend_music(
        emotion, 
        ActivityTag.COMMUTE, 
        weather_enum, 
        time_of_day, 
        randomize=True
    )

    # 3-6) Jamendo API 호출 (limit은 이미 20으로 설정되어 있습니다)
    params = "&".join(f"{k}={v}" for k,v in music.api_params.items())
    url = f"https://api.jamendo.com/v3.0/tracks/?client_id=602b9767&{params}"
    tracks = []
    try:
        response = requests.get(url, timeout=5).json()
        results = response.get('results', [])
        # ◀ 최대 20개까지 잘라서 수집
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

def start_server(port=5000):
    def run(): 
        app.run(host='localhost', port=port, debug=False, use_reloader=False)
    t = threading.Thread(target=run, daemon=True)
    t.start()
    time.sleep(1)
    webbrowser.open(f'http://localhost:{port}')
    return t

if __name__ == '__main__':
    print("Starting unified server on http://localhost:5000")
    start_server()
    input("Press Enter to quit")

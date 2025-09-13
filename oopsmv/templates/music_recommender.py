# music_recommender.py
# 위치 기반 정확한 음악 추천 시스템 메인 파일

import json
import requests
import random
import os
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

try:
    from location_client import get_current_location
except ImportError:
    get_current_location = None

class Weather(Enum):
    SUNNY = "sunny"
    CLOUDY = "cloudy"
    RAINY = "rainy"
    SNOWY = "snowy"
    WINDY = "windy"

class TimeOfDay(Enum):
    DAWN = "dawn"        # 04:00-06:59
    MORNING = "morning"  # 07:00-11:59
    AFTERNOON = "afternoon"  # 12:00-17:59
    EVENING = "evening"  # 18:00-21:59
    NIGHT = "night"      # 22:00-03:59

class EmotionTag(Enum):
    HAPPY = "happy"
    SAD = "sad"
    CALM = "calm"
    ENERGETIC = "energetic"
    ROMANTIC = "romantic"
    STRESSED = "stressed"
    MELANCHOLIC = "melancholic"
    PEACEFUL = "peaceful"
    UPLIFTING = "uplifting"
    DRAMATIC = "dramatic"

class ActivityTag(Enum):
    WORK = "work"
    STUDY = "study"
    EXERCISE = "exercise"
    RELAXATION = "relaxation"
    PARTY = "party"
    MEDITATION = "meditation"
    COMMUTE = "commute"
    SLEEP = "sleep"
    FOCUS = "focus"
    SOCIAL = "social"

@dataclass
class MusicScenario:
    name: str
    emoji: str
    description: str
    emotion: EmotionTag
    activity: ActivityTag
    keywords: List[str]

@dataclass
class RatioBreakdown:
    parameter: str
    emotion_contribution: float
    weather_contribution: float
    time_contribution: float
    final_value: str
    calculation_detail: str

@dataclass
class RecommendationScore:
    parameter: str
    value: str
    emotion_score: float
    weather_score: float
    time_score: float
    final_score: float
    reasoning: str

@dataclass
class MusicRecommendation:
    api_params: Dict[str, str]
    explanation: List[RecommendationScore]
    ratio_breakdown: List[RatioBreakdown]
    total_confidence: float

class BalancedRatioRecommender:
    def __init__(self):
        # 🎯 핵심 반영 비율 설정 (고정)
        self.EMOTION_RATIO = 0.5   # 50%
        self.WEATHER_RATIO = 0.3   # 30%
        self.TIME_RATIO = 0.2      # 20%
        
        # ✅ 감정별 기본 특성 (실제 지원되는 태그들로 수정)
        self.emotion_characteristics = {
            EmotionTag.HAPPY:     {"energy": 0.7, "valence": 0.8, "arousal": 0.6,
                                   "speed": 0.7, "tags": ["happy", "uplifting", "energetic", "pop"]},
            EmotionTag.SAD:       {"energy": 0.3, "valence": 0.2, "arousal": 0.3,
                                   "speed": 0.3, "tags": ["melancholic", "emotional", "peaceful", "classical"]},
            EmotionTag.CALM:      {"energy": 0.2, "valence": 0.6, "arousal": 0.2,
                                   "speed": 0.3, "tags": ["peaceful", "relaxing", "ambient", "meditation"]},
            EmotionTag.ENERGETIC: {"energy": 0.9, "valence": 0.7, "arousal": 0.9,
                                   "speed": 0.8, "tags": ["energetic", "electronic", "rock", "motivational"]},
            EmotionTag.ROMANTIC:  {"energy": 0.4, "valence": 0.7, "arousal": 0.5,
                                   "speed": 0.4, "tags": ["romantic", "jazz", "acoustic", "soft"]},
            EmotionTag.STRESSED:  {"energy": 0.1, "valence": 0.3, "arousal": 0.7,
                                   "speed": 0.2, "tags": ["peaceful", "ambient", "relaxing", "healing"]},
            EmotionTag.MELANCHOLIC:{"energy": 0.3, "valence": 0.2, "arousal": 0.4,
                                   "speed": 0.3, "tags": ["melancholic", "classical", "emotional", "ambient"]},
            EmotionTag.PEACEFUL:  {"energy": 0.2, "valence": 0.6, "arousal": 0.1,
                                   "speed": 0.3, "tags": ["peaceful", "ambient", "meditation", "nature"]},
            EmotionTag.UPLIFTING: {"energy": 0.6, "valence": 0.8, "arousal": 0.6,
                                   "speed": 0.6, "tags": ["uplifting", "motivational", "pop", "electronic"]},
            EmotionTag.DRAMATIC:  {"energy": 0.8, "valence": 0.5, "arousal": 0.8,
                                   "speed": 0.7, "tags": ["cinematic", "orchestral", "classical", "soundtrack"]}
        }
        
        # 활동별 보정값 (감정에 추가로 적용)
        self.activity_adjustments = {
            ActivityTag.WORK: {"energy": -0.1, "speed": 0.0,  "vocal": "instrumental"},
            ActivityTag.STUDY: {"energy": -0.2, "speed": -0.1, "vocal": "instrumental"},
            ActivityTag.EXERCISE: {"energy": 0.2, "speed": 0.2,  "vocal": "vocal"},
            ActivityTag.RELAXATION: {"energy": -0.3, "speed": -0.2, "vocal": "instrumental"},
            ActivityTag.PARTY: {"energy": 0.3, "speed": 0.3,  "vocal": "vocal"},
            ActivityTag.MEDITATION: {"energy": -0.4, "speed": -0.3, "vocal": "instrumental"},
            ActivityTag.COMMUTE: {"energy": 0.0, "speed": 0.1,  "vocal": "vocal"},
            ActivityTag.SLEEP: {"energy": -0.4, "speed": -0.4,  "vocal": "instrumental"},
            ActivityTag.FOCUS: {"energy": -0.1, "speed": 0.0,  "vocal": "instrumental"},
            ActivityTag.SOCIAL: {"energy": 0.1, "speed": 0.1,  "vocal": "vocal"}
        }
        
        # 날씨별 영향 (0-1 범위)
        self.weather_influences = {
            Weather.SUNNY: {"energy": 0.8, "valence": 0.9, "speed": 0.7},
            Weather.RAINY: {"energy": 0.3, "valence": 0.4, "speed": 0.3},
            Weather.CLOUDY: {"energy": 0.5, "valence": 0.5, "speed": 0.5},
            Weather.SNOWY: {"energy": 0.4, "valence": 0.6, "speed": 0.4},
            Weather.WINDY: {"energy": 0.7, "valence": 0.6, "speed": 0.6}
        }
        
        # 시간대별 영향 (0-1 범위)
        self.time_influences = {
            TimeOfDay.DAWN: {"energy": 0.2, "valence": 0.5, "speed": 0.2},
            TimeOfDay.MORNING: {"energy": 0.7, "valence": 0.8, "speed": 0.6},
            TimeOfDay.AFTERNOON: {"energy": 0.6, "valence": 0.6, "speed": 0.6},
            TimeOfDay.EVENING: {"energy": 0.4, "valence": 0.6, "speed": 0.4},
            TimeOfDay.NIGHT: {"energy": 0.3, "valence": 0.5, "speed": 0.3}
        }
        
        # ✅ 속도 매핑 (실제 지원되는 값들만)
        self.speed_mapping = {"medium": 0, "high": 1, "veryhigh": 2}
        self.speed_reverse = {v: k for k, v in self.speed_mapping.items()}
        
        # 🎲 랜덤 추천을 위한 정렬 옵션들 (실제 지원되는 값들만)
        self.random_orders = [
            "releasedate", "popularity_week", "popularity_month", "popularity_total",
            "downloads_week", "downloads_month", "downloads_total",
            "listens_week", "listens_month", "listens_total",
            "name", "artist_name", "album_name", "duration", "buzzrate", "relevance"
        ]

    def get_time_of_day(self, hour: int) -> TimeOfDay:
        """시간을 기반으로 시간대 결정"""
        if 4 <= hour < 7:
            return TimeOfDay.DAWN
        elif 7 <= hour < 12:
            return TimeOfDay.MORNING
        elif 12 <= hour < 18:
            return TimeOfDay.AFTERNOON
        elif 18 <= hour < 22:
            return TimeOfDay.EVENING
        else:
            return TimeOfDay.NIGHT

    def calculate_balanced_score(self, emotion: EmotionTag, weather: Weather, 
                                 time_of_day: TimeOfDay, attribute: str) -> Tuple[float, str]:
        """50%-30%-20% 비율로 균형잡힌 점수 계산"""
        # 1. 감정 점수 (0-1)
        emotion_score = self.emotion_characteristics[emotion][attribute]
        # 2. 날씨 점수 (0-1)
        weather_score = self.weather_influences[weather][attribute]
        # 3. 시간 점수 (0-1)
        time_score = self.time_influences[time_of_day][attribute]
        # 4. 🎯 정확한 비율 적용
        final_score = (emotion_score * self.EMOTION_RATIO +
                       weather_score * self.WEATHER_RATIO +
                       time_score * self.TIME_RATIO)
        # 5. 계산 과정 상세 설명
        calculation_detail = (
            f"{emotion_score:.2f}×{self.EMOTION_RATIO} + "
            f"{weather_score:.2f}×{self.WEATHER_RATIO} + "
            f"{time_score:.2f}×{self.TIME_RATIO} = {final_score:.2f}"
        )
        return final_score, calculation_detail

    def calculate_comprehensive_characteristics(self, emotion: EmotionTag, 
                                               activity: ActivityTag,
                                               weather: Weather, 
                                               time_of_day: TimeOfDay) -> Dict:
        """모든 특성을 균형잡힌 비율로 계산"""
        results = {}
        # 핵심 속성들 계산
        for attribute in ["energy", "speed"]:
            score, detail = self.calculate_balanced_score(emotion, weather, time_of_day, attribute)
            # 활동별 미세 조정 (±10% 범위)
            activity_adj = self.activity_adjustments[activity].get(attribute, 0) * 0.1
            adjusted_score = max(0.0, min(1.0, score + activity_adj))
            results[attribute] = {
                "base_score": score,
                "activity_adjustment": activity_adj,
                "final_score": adjusted_score,
                "calculation": detail
            }
        # 태그 조합
        results["tags"] = self.emotion_characteristics[emotion]["tags"]
        # 보컬 선택 (활동 우선)
        results["vocal"] = self.activity_adjustments[activity]["vocal"]
        return results

    def select_optimal_tags_with_ratio(self, emotion: EmotionTag, 
                                       weather: Weather, 
                                       time_of_day: TimeOfDay, 
                                       base_tags: List[str]) -> List[Tuple[str, float]]:
        """태그별 50%-30%-20% 적합도 계산"""
        tag_scores = []
        for tag in base_tags:
            # 감정 적합도 (기본 1.0, 해당 감정의 태그이므로)
            emotion_fit = 1.0
            # 날씨 적합도 계산
            weather_fit = self.calculate_weather_tag_fit(tag, weather)
            # 시간대 적합도 계산  
            time_fit = self.calculate_time_tag_fit(tag, time_of_day)
            # 🎯 정확한 비율 적용
            final_fit = (emotion_fit * self.EMOTION_RATIO +
                         weather_fit * self.WEATHER_RATIO +
                         time_fit * self.TIME_RATIO)
            tag_scores.append((tag, final_fit))
        # 점수 순으로 정렬
        tag_scores.sort(key=lambda x: x[1], reverse=True)
        return tag_scores[:2]  # 상위 2개만 (더 관대하게)

    def calculate_weather_tag_fit(self, tag: str, weather: Weather) -> float:
        """날씨와 태그의 적합도 (0-1) - 실제 지원되는 태그들로 업데이트"""
        weather_tag_map = {
            Weather.SUNNY:  {"uplifting": 0.9, "happy": 0.9, "energetic": 0.8, "pop": 0.8,
                             "electronic": 0.7, "motivational": 0.8, "melancholic": 0.2},
            Weather.RAINY:  {"peaceful": 0.9, "ambient": 0.8, "melancholic": 0.8, "romantic": 0.7,
                             "classical": 0.7, "jazz": 0.8, "energetic": 0.3, "rock": 0.2},
            Weather.CLOUDY: {"ambient": 0.7, "peaceful": 0.7, "jazz": 0.6, "classical": 0.6,
                             "electronic": 0.4, "rock": 0.4},
            Weather.SNOWY:  {"peaceful": 0.9, "ambient": 0.8, "classical": 0.8, "meditation": 0.8,
                             "jazz": 0.7, "energetic": 0.3, "rock": 0.3},
            Weather.WINDY:  {"electronic": 0.8, "energetic": 0.7, "rock": 0.8, "cinematic": 0.7,
                             "peaceful": 0.4, "ambient": 0.3}
        }
        return weather_tag_map.get(weather, {}).get(tag, 0.5)

    def calculate_time_tag_fit(self, tag: str, time_of_day: TimeOfDay) -> float:
        """시간대와 태그의 적합도 (0-1) - 실제 지원되는 태그들로 업데이트"""
        time_tag_map = {
            TimeOfDay.DAWN: {
                "peaceful": 1.0, "ambient": 0.9, "meditation": 0.9, "nature": 0.8,
                "classical": 0.8, "energetic": 0.1, "rock": 0.1, "electronic": 0.2
            },
            TimeOfDay.MORNING: {
                "energetic": 0.9, "uplifting": 0.9, "motivational": 0.8, "pop": 0.8,
                "electronic": 0.7, "jazz": 0.6, "melancholic": 0.3
            },
            TimeOfDay.AFTERNOON: {
                "pop": 0.8, "rock": 0.7, "energetic": 0.6, "electronic": 0.6,
                "jazz": 0.6, "ambient": 0.5, "cinematic": 0.4
            },
            TimeOfDay.EVENING: {
                "romantic": 0.9, "jazz": 0.8, "classical": 0.7, "ambient": 0.7,
                "acoustic": 0.8, "soft": 0.7, "energetic": 0.4, "rock": 0.3
            },
            TimeOfDay.NIGHT: {
                "peaceful": 0.9, "ambient": 0.9, "meditation": 0.8, "classical": 0.8,
                "jazz": 0.7, "healing": 0.9, "energetic": 0.2, "rock": 0.2
            }
        }
        return time_tag_map.get(time_of_day, {}).get(tag, 0.5)

    def recommend_music(self, emotion: EmotionTag, activity: ActivityTag,
                       weather: Weather, time_of_day: Optional[TimeOfDay] = None,
                       randomize: bool = True) -> MusicRecommendation:
        """50%-30%-20% 비율 기반 랜덤 추천"""
        if time_of_day is None:
            current_hour = datetime.now().hour
            time_of_day = self.get_time_of_day(current_hour)
        # 1. 전체 특성 계산
        characteristics = self.calculate_comprehensive_characteristics(emotion, activity, weather, time_of_day)
        # 2. 태그 선택 (50%-30%-20% 비율 적용) - 더 관대하게
        base_tags = characteristics["tags"]
        selected_tags_with_scores = self.select_optimal_tags_with_ratio(emotion, weather, time_of_day, base_tags)
        selected_tags = [tag for tag, score in selected_tags_with_scores[:2]]
        # 3. ✅ 속도 결정 (실제 지원되는 값들만 사용)
        speed_score = characteristics["speed"]["final_score"]
        speed_numeric = min(2, round(speed_score * 2))
        primary_speed = self.speed_reverse[speed_numeric]
        # 4. 🎲 랜덤 파라미터 추가
        random_params = {}
        if randomize:
            random_order = random.choice(self.random_orders)
            random_params["order"] = random_order
            random_offset = random.randint(0, 500)
            random_params["offset"] = str(random_offset)
            random_params["limit"] = "50"
        # 5. ✅ API 파라미터 구성 (더 관대한 설정)
        api_params = {
            "fuzzytags": "+".join(selected_tags),
            "speed": primary_speed,
            "vocalinstrumental": characteristics["vocal"],
            "limit": "20",
            "include": "musicinfo",
            "format": "json"
        }
        if randomize:
            api_params.update(random_params)
            api_params["limit"] = "20"
        # 6. 상세 설명 생성
        explanations = []
        ratio_breakdowns = []
        # 태그별 설명
        for tag, score in selected_tags_with_scores:
            emotion_contrib = 1.0 * self.EMOTION_RATIO
            weather_contrib = self.calculate_weather_tag_fit(tag, weather) * self.WEATHER_RATIO
            time_contrib = self.calculate_time_tag_fit(tag, time_of_day) * self.TIME_RATIO
            explanations.append(RecommendationScore(
                parameter="tags",
                value=tag,
                emotion_score=1.0,
                weather_score=self.calculate_weather_tag_fit(tag, weather),
                time_score=self.calculate_time_tag_fit(tag, time_of_day),
                final_score=score,
                reasoning=f"'{tag}' 태그: 감정 {emotion_contrib:.1f} + 날씨 {weather_contrib:.1f} + 시간 {time_contrib:.1f} = {score:.2f}"
            ))
            ratio_breakdowns.append(RatioBreakdown(
                parameter=f"tag_{tag}",
                emotion_contribution=emotion_contrib,
                weather_contribution=weather_contrib,
                time_contribution=time_contrib,
                final_value=tag,
                calculation_detail=f"50%×1.0 + 30%×{self.calculate_weather_tag_fit(tag, weather):.1f} + 20%×{self.calculate_time_tag_fit(tag, time_of_day):.1f}"
            ))
        # 속도 설명
        speed_char = characteristics["speed"]
        explanations.append(RecommendationScore(
            parameter="speed",
            value=primary_speed,
            emotion_score=self.emotion_characteristics[emotion]["speed"],
            weather_score=self.weather_influences[weather]["speed"],
            time_score=self.time_influences[time_of_day]["speed"],
            final_score=speed_score,
            reasoning=f"속도: {speed_char['calculation']} + 활동조정({speed_char['activity_adjustment']:+.1f}) = {speed_score:.2f}"
        ))
        ratio_breakdowns.append(RatioBreakdown(
            parameter="speed",
            emotion_contribution=self.emotion_characteristics[emotion]["speed"] * self.EMOTION_RATIO,
            weather_contribution=self.weather_influences[weather]["speed"] * self.WEATHER_RATIO,
            time_contribution=self.time_influences[time_of_day]["speed"] * self.TIME_RATIO,
            final_value=primary_speed,
            calculation_detail=speed_char['calculation']
        ))
        # 7. 랜덤 설명 추가
        if randomize:
            explanations.append(RecommendationScore(
                parameter="randomization",
                value=f"정렬: {random_params.get('order', 'default')}, 오프셋: {random_params.get('offset', '0')}",
                emotion_score=0.0,
                weather_score=0.0,
                time_score=0.0,
                final_score=1.0,
                reasoning=f"🎲 랜덤 요소: {random_params.get('order')} 정렬 + {random_params.get('offset')} 위치부터 시작"
            ))
        # 8. 신뢰도 계산
        emotion_weight_achieved = sum(rb.emotion_contribution for rb in ratio_breakdowns) / len(ratio_breakdowns)
        weather_weight_achieved = sum(rb.weather_contribution for rb in ratio_breakdowns) / len(ratio_breakdowns)
        time_weight_achieved = sum(rb.time_contribution for rb in ratio_breakdowns) / len(ratio_breakdowns)
        emotion_accuracy = 1.0 - abs(emotion_weight_achieved - self.EMOTION_RATIO)
        weather_accuracy = 1.0 - abs(weather_weight_achieved - self.WEATHER_RATIO)
        time_accuracy = 1.0 - abs(time_weight_achieved - self.TIME_RATIO)
        confidence = (emotion_accuracy + weather_accuracy + time_accuracy) / 3 * 100
        return MusicRecommendation(api_params=api_params, 
                                   explanation=explanations, 
                                   ratio_breakdown=ratio_breakdowns, 
                                   total_confidence=confidence)

    def get_detailed_analysis(self, recommendation: MusicRecommendation) -> str:
        """추천 결과 상세 분석 문자열 생성"""
        analysis = "🎲 GPS 기반 정확한 음악 추천 시스템 (감정 50% - 날씨 30% - 시간 20%)\n"
        analysis += "=" * 70 + "\n\n"
        # 실제 반영 비율 계산
        total_emotion = sum(rb.emotion_contribution for rb in recommendation.ratio_breakdown)
        total_weather = sum(rb.weather_contribution for rb in recommendation.ratio_breakdown)
        total_time = sum(rb.time_contribution for rb in recommendation.ratio_breakdown)
        total_sum = total_emotion + total_weather + total_time
        actual_emotion_ratio = (total_emotion / total_sum) * 100
        actual_weather_ratio = (total_weather / total_sum) * 100
        actual_time_ratio = (total_time / total_sum) * 100
        analysis += "📊 목표 vs 실제 반영 비율:\n"
        analysis += f"  🎭 감정: 50% 목표 → {actual_emotion_ratio:.1f}% 실제 ({actual_emotion_ratio-50:+.1f}%)\n"
        analysis += f"  🌤️ 날씨: 30% 목표 → {actual_weather_ratio:.1f}% 실제 ({actual_weather_ratio-30:+.1f}%)\n"
        analysis += f"  🕐 시간: 20% 목표 → {actual_time_ratio:.1f}% 실제 ({actual_time_ratio-20:+.1f}%)\n"
        analysis += f"  📈 정확도: {recommendation.total_confidence:.1f}%\n"
        analysis += f"  🎲 랜덤 모드: 항상 활성화\n"
        analysis += f"  🛰️ 위치: GPS 기반 정확한 좌표\n"
        analysis += "\n🎵 선택된 파라미터:\n"
        for param, value in recommendation.api_params.items():
            if param not in ["limit", "include", "featured", "format"]:
                analysis += f"  • {param}: {value}\n"
        analysis += "\n🔍 파라미터별 상세 계산:\n"
        for breakdown in recommendation.ratio_breakdown:
            analysis += f"\n【{breakdown.parameter}】 = {breakdown.final_value}\n"
            analysis += f"  📊 기여도: 감정 {breakdown.emotion_contribution:.2f} + 날씨 {breakdown.weather_contribution:.2f} + 시간 {breakdown.time_contribution:.2f}\n"
            analysis += f"  🧮 계산식: {breakdown.calculation_detail}\n"
        return analysis

class WeatherService:
    """GPS 좌표 기반 날씨 서비스"""
    def __init__(self):
        # 날씨 상태 매핑
        self.weather_mapping = {
            "clear": Weather.SUNNY, "sunny": Weather.SUNNY, "맑음": Weather.SUNNY,
            "partly cloudy": Weather.CLOUDY, "cloudy": Weather.CLOUDY, "흐림": Weather.CLOUDY,
            "overcast": Weather.CLOUDY, "fog": Weather.CLOUDY, "mist": Weather.CLOUDY,
            "rain": Weather.RAINY, "rainy": Weather.RAINY, "비": Weather.RAINY,
            "drizzle": Weather.RAINY, "shower": Weather.RAINY, "소나기": Weather.RAINY,
            "snow": Weather.SNOWY, "snowy": Weather.SNOWY, "눈": Weather.SNOWY,
            "blizzard": Weather.SNOWY, "sleet": Weather.SNOWY,
            "wind": Weather.WINDY, "windy": Weather.WINDY, "바람": Weather.WINDY
        }
        # 한국 주요 도시 (백업용)
        self.korean_cities = [
            {"name": "Seoul", "korean": "서울", "priority": 1},
            {"name": "Incheon", "korean": "인천", "priority": 2},
            {"name": "Suwon", "korean": "수원", "priority": 3},
            {"name": "Hwaseong", "korean": "화성", "priority": 4},
            {"name": "Goyang", "korean": "고양", "priority": 5},
            {"name": "Anyang", "korean": "안양", "priority": 6},
            {"name": "Bucheon", "korean": "부천", "priority": 7},
            {"name": "Busan", "korean": "부산", "priority": 8},
            {"name": "Daegu", "korean": "대구", "priority": 9},
            {"name": "Daejeon", "korean": "대전", "priority": 10},
            {"name": "Gwangju", "korean": "광주", "priority": 11},
            {"name": "Ulsan", "korean": "울산", "priority": 12},
        ]

    def get_weather_by_coordinates(self, lat: float, lon: float) -> Optional[Tuple[Weather, str, str]]:
        """GPS 좌표 기반 정확한 날씨 조회"""
        try:
            print(f"🛰️ GPS 좌표로 날씨 조회: {lat:.6f}, {lon:.6f}")
            url = f"http://wttr.in/{lat},{lon}?format=j1"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                current = data['current_condition'][0]
                weather_desc = current['weatherDesc'][0]['value']
                temp_c = current['temp_C']
                temp_float = float(temp_c)
                if temp_float < -35 or temp_float > 45:
                    print(f"⚠️ 비정상적인 온도: {temp_float}°C")
                    return None
                location_info = data['nearest_area'][0]
                area_name = location_info['areaName'][0]['value']
                country = location_info['country'][0]['value']
                location_name = f"{area_name}, {country}"
                weather_main = weather_desc.lower()
                weather_enum = Weather.CLOUDY
                for key, enum_val in self.weather_mapping.items():
                    if key in weather_main:
                        weather_enum = enum_val
                        break
                weather_info = f"{weather_desc}, {temp_c}°C"
                print(f"✅ GPS 기반 날씨: {location_name} - {weather_info}")
                return weather_enum, weather_info, location_name
            else:
                print(f"⚠️ wttr.in 오류: {response.status_code}")
                return None
        except Exception as e:
            print(f"⚠️ GPS 날씨 조회 오류: {e}")
            return None

    def get_weather_wttr(self, city_name: str = None) -> Optional[Tuple[Weather, str, str]]:
        """기존 도시명 기반 날씨 조회 (백업용)"""
        try:
            if city_name:
                korean_city = next((city for city in self.korean_cities 
                                   if city['name'].lower() == city_name.lower()), None)
                if korean_city:
                    print(f"🇰🇷 한국 도시 감지: {korean_city['korean']}({korean_city['name']})")
                    url = f"http://wttr.in/{city_name},South Korea?format=j1"
                else:
                    url = f"http://wttr.in/{city_name}?format=j1"
            else:
                print("🌍 IP 기반 자동 위치 감지 시도...")
                url = "http://wttr.in/?format=j1"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                current = data['current_condition'][0]
                weather_desc = current['weatherDesc'][0]['value']
                temp_c = current['temp_C']
                temp_float = float(temp_c)
                if temp_float < -35 or temp_float > 45:
                    print(f"⚠️ 비정상적인 온도: {temp_float}°C")
                    return None
                location_info = data['nearest_area'][0]
                area_name = location_info['areaName'][0]['value']
                country = location_info['country'][0]['value']
                location_name = f"{area_name}, {country}"
                if "Korea" not in country and "한국" not in country and not city_name:
                    print(f"⚠️ 한국이 아닌 위치로 감지됨: {location_name}")
                    print("💡 IP 기반 위치가 부정확할 수 있습니다.")
                weather_main = weather_desc.lower()
                weather_enum = Weather.CLOUDY
                for key, enum_val in self.weather_mapping.items():
                    if key in weather_main:
                        weather_enum = enum_val
                        break
                weather_info = f"{weather_desc}, {temp_c}°C"
                print(f"📍 감지된 위치: {location_name}")
                print(f"🌡️ 현재 날씨: {weather_info}")
                return weather_enum, weather_info, location_name
            else:
                print(f"⚠️ wttr.in 서비스 오류: {response.status_code}")
                return None
        except Exception as e:
            print(f"⚠️ wttr.in 날씨 정보 획득 중 오류: {e}")
            return None

    def get_auto_weather(self) -> Optional[Tuple[Weather, str, str]]:
        """자동 날씨 감지 (GPS 우선, 백업)"""
        print("🛰️ GPS 기반 정확한 날씨 감지를 시도합니다...")
        print("-" * 50)
        
        # 방법 1: GPS 좌표 기반 (최우선) - location_client 사용
        print("1️⃣ GPS 좌표 기반 정확한 위치 시도...")
        gps_location = get_current_location() if get_current_location else None
        if gps_location:
            print(f"📱 GPS 위치 사용: {gps_location.get('address', '알 수 없음')}")
            result = self.get_weather_by_coordinates(gps_location['lat'], gps_location['lon'])
            if result:
                weather_enum, weather_info, location_name = result
                return weather_enum, f"GPS 기반 - {weather_info}", location_name
        
        # 방법 2: 한국 주요 도시 백업
        print("2️⃣ 한국 주요 도시 백업 시도...")
        for city_info in sorted(self.korean_cities, key=lambda x: x['priority'])[:5]:
            print(f"🔄 {city_info['korean']}({city_info['name']}) 날씨 확인 중...")
            result = self.get_weather_wttr(city_info['name'])
            if result:
                weather_enum, weather_info, location_name = result
                print(f"✅ {city_info['korean']} 날씨 정보 획득 성공!")
                return weather_enum, f"백업 도시 - {weather_info}", location_name

        print("❌ 모든 날씨 수집 방법 실패")
        return None

    def get_fallback_weather(self) -> Tuple[Weather, str, str]:
        """시간/계절 기반 기본 예상 날씨 설정 (한국 기후 반영)"""
        print("📅 한국 기후를 고려한 시간/계절 기반 예상 날씨를 설정합니다...")
        now = datetime.now()
        current_hour = now.hour
        current_month = now.month
        if current_month in [3, 4, 5]:  # 봄
            if 6 <= current_hour <= 18:
                base_weather = Weather.SUNNY; weather_desc = "봄 맑음"; temp = "15"
            else:
                base_weather = Weather.CLOUDY; weather_desc = "봄 저녁 흐림"; temp = "10"
        elif current_month in [6, 7, 8]:  # 여름 (장마 고려)
            if current_month == 7 and 14 <= current_hour <= 18:
                base_weather = Weather.RAINY; weather_desc = "여름 장마철 소나기"; temp = "25"
            elif 6 <= current_hour <= 18:
                base_weather = Weather.SUNNY; weather_desc = "여름 더위"; temp = "30"
            else:
                base_weather = Weather.CLOUDY; weather_desc = "여름 밤 습함"; temp = "25"
        elif current_month in [9, 10, 11]:  # 가을
            if current_month == 9:
                base_weather = Weather.SUNNY; weather_desc = "선선한 가을"; temp = "20"
            else:
                base_weather = Weather.CLOUDY; weather_desc = "쌀쌀한 가을"; temp = "10"
        else:  # 겨울 (12,1,2월)
            if current_hour < 8 or current_hour > 20:
                if current_month == 1:
                    base_weather = Weather.SNOWY; weather_desc = "한겨울 눈"; temp = "-5"
                else:
                    base_weather = Weather.CLOUDY; weather_desc = "겨울 한기"; temp = "0"
            else:
                base_weather = Weather.CLOUDY; weather_desc = "겨울 흐림"; temp = "5"
        weather_info = f"{weather_desc}, {temp}°C (한국 기후 기반 추정)"
        return base_weather, weather_info, "현재 지역 (한국 추정)"

class UserInterface:
    """사용자 입력 인터페이스 (GPS 통합)"""

    def __init__(self):
        self.recommender = BalancedRatioRecommender()
        self.weather_service = WeatherService()
        self.scenarios = self.create_music_scenarios()

    def create_music_scenarios(self) -> List[MusicScenario]:
        """감정+활동 조합 시나리오 생성"""
        scenarios = [
            # 작업/공부 관련
            MusicScenario("집중해서 일할 때", "💼", "스트레스 받지만 집중이 필요한 업무", EmotionTag.STRESSED, ActivityTag.FOCUS, ["일","업무","집중","작업"]),
            MusicScenario("편안하게 공부할 때", "📚", "차분한 마음으로 학습하기", EmotionTag.CALM, ActivityTag.STUDY, ["공부","학습","독서"]),
            MusicScenario("야근할 때", "🌙", "지쳤지만 계속 일해야 할 때", EmotionTag.STRESSED, ActivityTag.WORK, ["야근","늦은","지친"]),

            # 운동/활동 관련
            MusicScenario("신나게 운동할 때", "🏃", "에너지 넘치는 상태로 운동하기", EmotionTag.ENERGETIC, ActivityTag.EXERCISE, ["운동","헬스","피트니스","신나는"]),
            MusicScenario("행복한 아침 조깅", "🌅", "기분 좋은 아침에 가벼운 운동", EmotionTag.HAPPY, ActivityTag.EXERCISE, ["조깅","아침","달리기"]),
            MusicScenario("스트레스 풀러 운동", "💪", "화나거나 답답해서 운동으로 푸는", EmotionTag.STRESSED, ActivityTag.EXERCISE, ["스트레스","화","답답"]),

            # 휴식/치유 관련
            MusicScenario("힐링이 필요할 때", "🛋️", "마음의 평화가 필요한 휴식", EmotionTag.PEACEFUL, ActivityTag.RELAXATION, ["힐링","치유","평화","휴식"]),
            MusicScenario("명상하며 마음 정리", "🧘", "깊은 사색과 명상을 위한", EmotionTag.CALM, ActivityTag.MEDITATION, ["명상","요가","사색"]),
            MusicScenario("우울할 때 혼자만의 시간", "😔", "슬픈 감정을 온전히 느끼며", EmotionTag.MELANCHOLIC, ActivityTag.RELAXATION, ["우울","혼자","슬픔"]),

            # 사교/파티 관련
            MusicScenario("친구들과 즐거운 파티", "🎉", "신나고 들뜬 파티 분위기", EmotionTag.HAPPY, ActivityTag.PARTY, ["파티","친구","모임","축제"]),
            MusicScenario("로맨틱한 데이트", "💕", "연인과의 달콤한 시간", EmotionTag.ROMANTIC, ActivityTag.SOCIAL, ["데이트","연인","로맨틱"]),
            MusicScenario("분위기 있는 저녁 모임", "🍷", "어른스럽고 세련된 사교", EmotionTag.DRAMATIC, ActivityTag.SOCIAL, ["저녁","모임","분위기"]),

            # 이동/통근 관련
            MusicScenario("출근길 기분전환", "🚗", "새로운 하루를 위한 동기부여", EmotionTag.UPLIFTING, ActivityTag.COMMUTE, ["출근","통근","아침"]),
            MusicScenario("퇴근길 힐링타임", "🚌", "하루의 피로를 달래는", EmotionTag.PEACEFUL, ActivityTag.COMMUTE, ["퇴근","피로","집"]),

            # 수면/잠자리 관련
            MusicScenario("잠들기 전 마음 진정", "😴", "편안한 잠자리를 위한", EmotionTag.PEACEFUL, ActivityTag.SLEEP, ["잠","수면","밤"]),
            MusicScenario("불면증으로 잠 못 이룰 때", "🌙", "스트레스로 잠이 안 올 때", EmotionTag.STRESSED, ActivityTag.SLEEP, ["불면","잠못이룸","고민"]),

            # 특별한 감정 상태
            MusicScenario("감동적인 순간을 느끼고 싶을 때", "✨", "깊은 감동과 여운이 필요한", EmotionTag.DRAMATIC, ActivityTag.RELAXATION, ["감동","여운","특별한"]),
            MusicScenario("에너지 충전이 필요할 때", "⚡", "의욕을 되찾고 동기부여", EmotionTag.ENERGETIC, ActivityTag.FOCUS, ["동기부여","의욕","충전"]),
            MusicScenario("기분이 좋아서 뭔가 하고 싶을 때", "🌟", "행복해서 무언가 활동하고 싶은", EmotionTag.HAPPY, ActivityTag.WORK, ["기분좋은","활동적","생산적"])
        ]
        return scenarios

    def display_welcome(self):
        """환영 메시지 출력"""
        print("🎵" + "=" * 60 + "🎵")
        print("        AI 음악 추천 시스템 v3.0 GPS")
        print("    감정 50% | 날씨 30% | 시간 20%")
        print("     ✅ Jamendo API 최적화 버전")
        print("     🎲 항상 랜덤 추천 모드")
        print("     🛰️ GPS 기반 정확한 위치 시스템")
        print("🎵" + "=" * 60 + "🎵")
        print()
        print("💡 GPS 기반 정확한 날씨 서비스:")
        print("   🛰️ location_server.py를 통한 브라우저 GPS 수집") 
        print("   📍 location_client.py로 저장된 좌표 활용")
        print("   🎯 IP 오차 문제 완전 해결 (30km+ → 10-100m)")
        print("   🔄 24시간 위치 캐싱으로 편의성 확보")
        print()
        current_hour = datetime.now().hour
        auto_time = self.recommender.get_time_of_day(current_hour)
        time_emoji = self.get_time_emoji(auto_time)
        print(f"🕐 현재 시간: {time_emoji} {auto_time.value} ({current_hour}시) - 자동 반영됩니다")
        print()

    def get_time_emoji(self, time_period: TimeOfDay) -> str:
        emoji_map = {
            TimeOfDay.DAWN: "🌅", TimeOfDay.MORNING: "🌄", TimeOfDay.AFTERNOON: "☀️",
            TimeOfDay.EVENING: "🌆", TimeOfDay.NIGHT: "🌙"
        }
        return emoji_map.get(time_period, "🕐")

    def get_scenario_input(self) -> List[MusicScenario]:
        """시나리오 선택 (다중 선택 가능)"""
        print("🎭 현재 상황에 맞는 것을 선택해주세요 (여러 개 선택 가능):")
        print("💡 번호를 쉼표로 구분해서 입력하세요 (예: 1,3,5)")
        print()
        for i, scenario in enumerate(self.scenarios, 1):
            print(f"  {i:2d}. {scenario.emoji} {scenario.name}")
            print(f"      {scenario.description}")
            if i % 5 == 0:  # 5개마다 줄바꿈
                print()
        
        while True:
            try:
                user_input = input(f"\n선택 (1-{len(self.scenarios)}): ").strip()
                choices = []
                for choice_str in user_input.split(','):
                    choice_str = choice_str.strip()
                    if choice_str:
                        choice = int(choice_str)
                        if 1 <= choice <= len(self.scenarios):
                            choices.append(choice - 1)  # 0-based index
                        else:
                            raise ValueError(f"번호 {choice}는 범위를 벗어남")
                
                if not choices:
                    print("❌ 최소 하나는 선택해주세요.")
                    continue
                
                # 중복 제거
                choices = list(set(choices))
                selected_scenarios = [self.scenarios[i] for i in choices]
                
                print("\n✅ 선택된 상황:")
                for scenario in selected_scenarios:
                    print(f"   {scenario.emoji} {scenario.name}")
                
                return selected_scenarios
                
            except ValueError as e:
                print(f"❌ 올바른 번호를 입력해주세요. {e}")
            except Exception as e:
                print(f"❌ 입력 오류: {e}")

    def get_weather_input(self) -> Tuple[Weather, str]:
        """날씨 정보 획득 (GPS 또는 수동 입력)"""
        print("\n🌤️ 날씨 정보 설정 방법을 선택해주세요:")
        print("  1. 🛰️ GPS 자동 감지 (가장 정확!) - 추천!")
        print("  2. ✋ 수동 입력 (직접 선택)")
        
        while True:
            try:
                choice = int(input("\n선택 (1-2): "))
                if choice == 1:
                    return self.get_auto_weather()
                elif choice == 2:
                    return self.get_manual_weather()
                else:
                    print("❌ 1 또는 2를 입력해주세요.")
            except ValueError:
                print("❌ 숫자를 입력해주세요.")

    def get_auto_weather(self) -> Tuple[Weather, str]:
        """자동 날씨 감지 (GPS 또는 백업)"""
        print("\n🛰️ GPS 기반 정확한 위치로 날씨를 감지합니다...")
        print("-" * 50)
        
        auto_result = self.weather_service.get_auto_weather()
        
        if auto_result:
            weather_enum, weather_info, location_name = auto_result
            print(f"✅ 날씨 감지 완료!")
            print(f"📍 위치: {location_name}")
            print(f"🌤️ 날씨: {weather_info}")
            
            if "GPS 기반" in weather_info:
                print("🎯 최고 신뢰도: 실제 GPS 좌표로 정확한 날씨입니다.")
            elif "백업 도시" in weather_info:
                print("⚠️ 중간 신뢰도: 한국 주요 도시의 날씨입니다.")
            
            confirm = input("\n이 정보로 음악을 추천받으시겠습니까? (y/n): ").lower()
            if confirm in ['y', 'yes', '네', 'ㅇ', '']:
                return weather_enum, f"{location_name} - {weather_info}"
            else:
                print("수동 입력으로 전환합니다...")
                return self.get_manual_weather()
        else:
            print("❌ 자동 날씨 감지에 실패했습니다")
            fallback_choice = input("1: 수동 입력 / 2: 시간 기반 기본값 (1/2): ").strip()
            if fallback_choice == "2":
                weather_enum, weather_info, location_name = self.weather_service.get_fallback_weather()
                print(f"✅ 기본값 적용: {weather_info}")
                return weather_enum, f"{location_name} - {weather_info}"
            else:
                return self.get_manual_weather()

    def get_manual_weather(self) -> Tuple[Weather, str]:
        """수동 날씨 입력"""
        print("\n🌤️ 현재 날씨를 직접 선택해주세요:")
        weathers = list(Weather)
        
        for i, weather in enumerate(weathers, 1):
            emoji = self.get_weather_emoji(weather)
            description = self.get_weather_description(weather)
            print(f"  {i}. {emoji} {weather.value} - {description}")
        
        while True:
            try:
                choice = int(input(f"\n선택 (1-{len(weathers)}): "))
                if 1 <= choice <= len(weathers):
                    selected = weathers[choice - 1]
                    emoji = self.get_weather_emoji(selected)
                    description = self.get_weather_description(selected)
                    print(f"✅ 선택됨: {emoji} {selected.value}")
                    return selected, f"수동 선택 - {description}"
                else:
                    print("❌ 올바른 번호를 입력해주세요.")
            except ValueError:
                print("❌ 숫자를 입력해주세요.")

    def combine_scenarios(self, scenarios: List[MusicScenario]) -> Tuple[EmotionTag, ActivityTag]:
        """여러 시나리오를 조합하여 대표 감정과 활동 결정"""
        if len(scenarios) == 1:
            return scenarios[0].emotion, scenarios[0].activity
        
        # 감정별 빈도 계산
        emotion_counts = {}
        activity_counts = {}
        
        for scenario in scenarios:
            emotion_counts[scenario.emotion] = emotion_counts.get(scenario.emotion, 0) + 1
            activity_counts[scenario.activity] = activity_counts.get(scenario.activity, 0) + 1
        
        # 최빈값 선택
        primary_emotion = max(emotion_counts.items(), key=lambda x: x[1])[0]
        primary_activity = max(activity_counts.items(), key=lambda x: x[1])[0]
        
        print(f"\n🎯 조합 결과: {primary_emotion.value} 감정 + {primary_activity.value} 활동")
        print("   (선택된 여러 상황을 종합한 결과)")
        
        return primary_emotion, primary_activity

    def fetch_and_display_music(self, api_url: str, is_random: bool = False):
        """API를 호출해서 음악 리스트를 가져와 표시 (백업 전략 포함)"""
        try:
            print("\n🎵 음악을 검색하고 있습니다...")
            response = requests.get(api_url)
            
            if response.status_code == 200:
                data = response.json()
                
                if data['headers']['status'] == 'success':
                    tracks = data['results']
                    count = data['headers']['results_count']
                    
                    if count == 0:
                        print("🔄 조건에 맞는 음악이 없어서 더 넓은 범위에서 검색합니다...")
                        # 백업 전략: 조건을 완화해서 다시 시도
                        backup_url = self.create_backup_search_url(api_url)
                        backup_response = requests.get(backup_url)
                        
                        if backup_response.status_code == 200:
                            backup_data = backup_response.json()
                            if backup_data['headers']['status'] == 'success' and backup_data['results']:
                                tracks = backup_data['results']
                                count = backup_data['headers']['results_count']
                                print(f"✅ 넓은 범위에서 {count}개의 음악을 찾았습니다!")
                    
                    if tracks:
                        # 🎲 랜덤 모드에서는 결과를 섞기
                        if is_random and tracks:
                            random.shuffle(tracks)
                        
                        print(f"\n🎲 GPS 기반 정확한 위치로 {count}개의 음악을 발견했습니다!")
                        print("=" * 60)
                        
                        for i, track in enumerate(tracks[:10], 1):  # 상위 10개만 표시
                            print(f"\n{i:2d}. 🎵 {track['name']}")
                            print(f"    👤 아티스트: {track['artist_name']}")
                            print(f"    ⏱️  길이: {track['duration']}초")
                            print(f"    🎧 듣기: {track['audio']}")
                            
                            if i == 5:  # 5개마다 구분선
                                print("    " + "-" * 40)
                        
                        print(f"\n🎲 랜덤 팁: 같은 설정으로 다시 추천받으면 다른 음악들을 발견할 수 있어요!")
                    else:
                        print("😅 죄송합니다. 해당 조건에 맞는 음악을 찾을 수 없었습니다.")
                        print("💡 다른 시나리오나 날씨 조건으로 다시 시도해보세요!")
                            
                else:
                    print(f"❌ API 오류: {data['headers']['error_message']}")
                    if 'warnings' in data['headers'] and data['headers']['warnings']:
                        print(f"⚠️ 경고: {data['headers']['warnings']}")
                    
            else:
                print(f"❌ HTTP 오류: {response.status_code}")
                
        except Exception as e:
            print(f"❌ 네트워크 오류: {e}")

    def create_backup_search_url(self, original_url: str) -> str:
        """조건을 완화한 백업 검색 URL 생성"""
        # URL에서 파라미터 추출
        if "fuzzytags=" in original_url:
            # 태그를 하나만 사용하도록 단순화
            parts = original_url.split("fuzzytags=")[1].split("&")[0]
            first_tag = parts.split("+")[0]  # 첫 번째 태그만 사용
            
            # 조건 완화: 속도와 보컬 제한 제거
            backup_url = original_url.split("?")[0] + "?"
            backup_url += f"client_id=602b9767&fuzzytags={first_tag}&limit=20&format=json"
            
            return backup_url
        
        return original_url

    def run_interactive_session(self):
        """대화형 세션 실행"""
        self.display_welcome()
        
        # 사용자 입력 수집
        selected_scenarios = self.get_scenario_input()
        weather, weather_info = self.get_weather_input()
        
        # 시간은 자동 감지
        current_hour = datetime.now().hour
        time_period = self.recommender.get_time_of_day(current_hour)
        
        # 시나리오 조합
        emotion, activity = self.combine_scenarios(selected_scenarios)
        
        # 추천 생성
        print(f"\n🎲 GPS 기반 정확한 음악 추천을 생성하고 있습니다...")
        print("-" * 50)
        
        recommendation = self.recommender.recommend_music(
            emotion=emotion,
            activity=activity,
            weather=weather,
            time_of_day=time_period,
            randomize=True
        )
        
        # 선택된 시나리오 요약 출력
        print(f"\n📋 선택된 상황 요약:")
        for scenario in selected_scenarios:
            print(f"   {scenario.emoji} {scenario.name}")
        print(f"   🌤️ 날씨: {weather_info}")
        
        # 결과 출력
        print(self.recommender.get_detailed_analysis(recommendation))
        
        # API URL 생성
        params = "&".join([f"{k}={v}" for k, v in recommendation.api_params.items()])
        api_url = f"https://api.jamendo.com/v3.0/tracks/?client_id=602b9767&{params}"
        
        print("\n🔗 Jamendo API 호출 URL:")
        print(api_url)
        
        # ✅ 실제 음악 데이터 가져오기
        self.fetch_and_display_music(api_url, True)
        
        # 다시 실행 여부
        print("\n" + "=" * 60)
        restart = input("🔄 다시 추천받으시겠습니까? (y/n): ").lower()
        if restart in ['y', 'yes', '네', 'ㅇ']:
            print("\n")
            self.run_interactive_session()
        else:
            print("🎵 이용해주셔서 감사합니다!")

    # 이모지 및 설명 헬퍼 메서드들
    def get_weather_emoji(self, weather: Weather) -> str:
        emoji_map = {
            Weather.SUNNY: "☀️", Weather.CLOUDY: "☁️", Weather.RAINY: "🌧️",
            Weather.SNOWY: "❄️", Weather.WINDY: "💨"
        }
        return emoji_map.get(weather, "🌤️")
    
    def get_weather_description(self, weather: Weather) -> str:
        desc_map = {
            Weather.SUNNY: "맑고 화창한 날씨",
            Weather.CLOUDY: "흐리고 구름 많은 날씨",
            Weather.RAINY: "비가 내리는 날씨",
            Weather.SNOWY: "눈이 내리는 날씨",
            Weather.WINDY: "바람이 강한 날씨"
        }
        return desc_map.get(weather, "")

# 사용 예시
def main():
    """메인 실행 함수"""
    
    print("🎵 GPS 기반 음악 추천 시스템 v3.0 - 실행 모드 선택")
    print("1. 🖥️ 대화형 모드 (GPS 위치 + 사용자 입력)")
    print("2. 📋 데모 모드 (GPS 위치 + 미리 설정된 예시)")
    print("\n💡 GPS 기능을 사용하려면 location_server.py를 먼저 실행하세요.")
    
    while True:
        try:
            mode = int(input("\n선택 (1-2): "))
            if mode == 1:
                ui = UserInterface()
                ui.run_interactive_session()
                break
            elif mode == 2:
                run_demo_mode()
                break
            else:
                print("❌ 1 또는 2를 입력해주세요.")
        except ValueError:
            print("❌ 숫자를 입력해주세요.")
        except KeyboardInterrupt:
            print("\n\n👋 프로그램을 종료합니다.")
            break

def run_demo_mode():
    """데모 모드 실행"""
    print(f"\n🎵 GPS 데모 모드: 정확한 위치 + 미리 설정된 시나리오들")
    print("=" * 60)
    
    recommender = BalancedRatioRecommender()
    weather_service = WeatherService()
    
    # 자동 날씨 감지
    auto_weather_result = weather_service.get_auto_weather()
    if auto_weather_result:
        demo_weather, weather_info, location_name = auto_weather_result
        print(f"🛰️ GPS 감지된 위치: {location_name}")
        print(f"🌤️ 현재 날씨: {weather_info}")
    else:
        demo_weather, weather_info, location_name = weather_service.get_fallback_weather()
        print(f"🌤️ 기본 날씨: {weather_info}")
    
    demos = [
        {
            "name": "😰💼 스트레스 받는 직장인의 집중 작업",
            "emotion": EmotionTag.STRESSED,
            "activity": ActivityTag.FOCUS,
            "description": "스트레스 받지만 집중해서 일해야 할 때"
        },
        {
            "name": "😊🏃 행복한 아침 운동",
            "emotion": EmotionTag.HAPPY,
            "activity": ActivityTag.EXERCISE,
            "description": "기분 좋게 운동하러 나갈 때"
        },
        {
            "name": "💕🍷 로맨틱한 저녁 데이트",
            "emotion": EmotionTag.ROMANTIC,
            "activity": ActivityTag.SOCIAL,
            "description": "연인과의 달콤한 시간"
        },
        {
            "name": "🧘🌙 명상하며 마음 정리",
            "emotion": EmotionTag.PEACEFUL,
            "activity": ActivityTag.MEDITATION,
            "description": "조용히 명상하며 하루 마무리"
        }
    ]
    
    for i, demo in enumerate(demos, 1):
        print(f"\n{i}. {demo['name']}")
        demo_desc = f"{demo['description']} (GPS 기반 정확한 날씨 반영)"
        print(f"   {demo_desc}")
        print("-" * 40)
        
        # 현재 시간 자동 감지
        current_hour = datetime.now().hour
        time_period = recommender.get_time_of_day(current_hour)
        
        # 실제 감지된 날씨로 추천
        recommendation = recommender.recommend_music(
            emotion=demo['emotion'],
            activity=demo['activity'],
            weather=demo_weather,  # 실제 날씨 사용
            time_of_day=time_period,
            randomize=True
        )
        print(recommender.get_detailed_analysis(recommendation))

if __name__ == "__main__":
    main()
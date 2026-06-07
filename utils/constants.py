from __future__ import annotations

MAIN_MENU_LABELS = {
    "worship": "📿 العبادة",
    "health": "🏋️ الرياضة والصحة",
    "notes": "🗒 المفكرة",
    "tasks": "✅ المهام",
    "goals": "🎯 الأهداف",
    "leaderboard": "🏆 الترتيب",
    "reports": "📊 التقارير",
    "settings": "⚙️ الإعدادات",
}

HOME_LABEL = "🏠 الرئيسية"
BACK_LABEL = "🔙 رجوع"
CANCEL_LABEL = "❌ إلغاء"
REFRESH_LABEL = "🔄 تحديث"

PRAYERS = ["الفجر", "الظهر", "العصر", "المغرب", "العشاء"]

POINTS = {
    "prayer": 15,
    "morning_adhkar": 10,
    "evening_adhkar": 10,
    "quran_page": 2,
    "quran_khatma": 120,
    "exercise": 20,
    "water_cup": 2,
    "task": 25,
}

LEVELS = [
    (0, "مبتدئ"),
    (1000, "مجتهد"),
    (2500, "ملتزم"),
    (5000, "محترف"),
    (10000, "أسطورة"),
    (20000, "وحش الانضباط"),
]

ACHIEVEMENTS = {
    "first_exercise": {"title": "أول تمرين", "emoji": "🏋️"},
    "first_khatma": {"title": "أول ختمة", "emoji": "📚"},
    "streak_7": {"title": "7 أيام متتالية", "emoji": "🔥"},
    "streak_30": {"title": "30 يوم متتالي", "emoji": "⚡"},
    "points_1000": {"title": "1000 نقطة", "emoji": "🥉"},
    "points_5000": {"title": "5000 نقطة", "emoji": "🥇"},
}

QURAN_PAGE_PER_KHATMA = 604


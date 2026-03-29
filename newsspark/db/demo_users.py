"""
db/demo_users.py — Expanded to 8 user roles.
"""

DEMO_USERS = {
    "investor": {
        "user_id": "demo_investor",
        "name": "Arjun Mehta",
        "role": "investor",
        "language_pref": "en",
        "language": "en",
        "avatar": "💼",
        "interests": ["business", "markets", "technology", "politics"],
    },
    "student": {
        "user_id": "demo_student",
        "name": "Priya Sharma",
        "role": "student",
        "language_pref": "en",
        "language": "en",
        "avatar": "🎓",
        "interests": ["education", "technology", "politics", "health"],
    },
    "founder": {
        "user_id": "demo_founder",
        "name": "Kiran Rao",
        "role": "founder",
        "language_pref": "en",
        "language": "en",
        "avatar": "🚀",
        "interests": ["business", "technology", "politics", "crime"],
    },
    "general": {
        "user_id": "demo_general",
        "name": "Rahul Verma",
        "role": "general",
        "language_pref": "en",
        "language": "en",
        "avatar": "📰",
        "interests": ["politics", "health", "crime", "entertainment"],
    },
    "sports_fan": {
        "user_id": "demo_sports_fan",
        "name": "Vikas Reddy",
        "role": "sports_fan",
        "language_pref": "en",
        "language": "en",
        "avatar": "🏏",
        "interests": ["sports", "entertainment", "politics"],
    },
    "tech_enthusiast": {
        "user_id": "demo_tech_enthusiast",
        "name": "Sneha Iyer",
        "role": "tech_enthusiast",
        "language_pref": "en",
        "language": "en",
        "avatar": "💻",
        "interests": ["technology", "business", "education", "crime"],
    },
    "job_seeker": {
        "user_id": "demo_job_seeker",
        "name": "Amit Gupta",
        "role": "job_seeker",
        "language_pref": "en",
        "language": "en",
        "avatar": "🔍",
        "interests": ["education", "business", "technology", "politics"],
    },
    "homemaker": {
        "user_id": "demo_homemaker",
        "name": "Deepa Nair",
        "role": "homemaker",
        "language_pref": "en",
        "language": "en",
        "avatar": "🏠",
        "interests": ["health", "entertainment", "crime", "education"],
    },
}

# Category mapping per interest keyword
INTEREST_CATEGORY_MAP = {
    "cricket": "sports",
    "sports": "sports",
    "technology": "technology",
    "tech": "technology",
    "bollywood": "entertainment",
    "entertainment": "entertainment",
    "business": "business",
    "markets": "business",
    "politics": "politics",
    "health": "health",
    "education": "education",
    "crime": "crime",
}

# Role -> default interest categories
ROLE_CATEGORIES = {
    "investor": ["business", "markets", "technology", "politics"],
    "student": ["education", "technology", "politics", "health"],
    "founder": ["business", "technology", "politics"],
    "general": ["politics", "health", "crime", "entertainment"],
    "sports_fan": ["sports", "entertainment", "politics"],
    "tech_enthusiast": ["technology", "business", "education"],
    "job_seeker": ["education", "business", "technology"],
    "homemaker": ["health", "entertainment", "crime", "education"],
    # legacy
    "startup": ["business", "technology", "politics"],
    "salaried": ["business", "politics", "health"],
}

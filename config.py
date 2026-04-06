"""
NBA Parlay Generator — Configuration & Constants
"""
from datetime import datetime

# ─── App Settings ───────────────────────────────────────────────
APP_TITLE = "🏀 NBA Parlay Generator"
APP_ICON = "🏀"
CURRENT_SEASON = "2025-26"
SEASON_TYPE = "Regular Season"

# ─── Analysis Parameters ───────────────────────────────────────
RECENT_GAMES_WINDOW = 10          # Last N games for recent form
PLAYER_GAMES_WINDOW = 10          # Last N games for player trends
HOME_COURT_ADVANTAGE = 3.5        # Historical home court advantage in points
MIN_MINUTES_KEY_PLAYER = 20.0     # Minimum MPG to be considered a key player
TOP_PLAYERS_PER_TEAM = 6          # Number of key players to analyze per team
CACHE_TTL = 1800                  # Cache expiry in seconds (30 minutes)

# ─── Risk & Confidence Thresholds ──────────────────────────────
RISK_THRESHOLDS = {
    "low": 0.65,       # Probability >= 65% = Low Risk
    "medium": 0.50,    # Probability >= 50% = Medium Risk
    # Below 50% = Avoid
}

# ─── Parlay Constraints ────────────────────────────────────────
PARLAY_CONFIG = {
    "min_legs": 4,
    "max_legs": 8,
    "min_probability": {
        4: 0.10,   # 4-leg >= 10%
        5: 0.05,   # 5-leg >= 5%
        6: 0.02,   # 6-leg >= 2%
        7: 0.01,   # 7-leg >= 1%
        8: 0.005,  # 8-leg >= 0.5%
    },
    "max_parlays_displayed": 10,
    "max_one_bet_per_game": True,
}

# ─── Bet Type Configuration ────────────────────────────────────
BET_TYPES = {
    "moneyline": {
        "label": "Moneyline",
        "icon": "🏆",
        "min_probability": 0.65,
        "description": "Straight win pick on the favorite",
    },
    "point_spread": {
        "label": "Point Spread",
        "icon": "⚖️",
        "min_probability": 0.60,
        "description": "Team to cover a conservative alt-spread handicap",
    },
    "game_total_over": {
        "label": "Game Total Over",
        "icon": "📈",
        "min_probability": 0.58,
        "description": "Combined score over a conservative total",
    },
    "game_total_under": {
        "label": "Game Total Under",
        "icon": "📉",
        "min_probability": 0.58,
        "description": "Combined score under a conservative total",
    },
    "first_half_spread": {
        "label": "First Half Spread",
        "icon": "⏱️",
        "min_probability": 0.60,
        "description": "Team to beat the 1H margin",
    },
    "first_half_total_over": {
        "label": "1H Total Over",
        "icon": "🔥",
        "min_probability": 0.58,
        "description": "1st Half Combined Score over line",
    },
    "first_half_total_under": {
        "label": "1H Total Under",
        "icon": "🧊",
        "min_probability": 0.58,
        "description": "1st Half Combined Score under line",
    },
    "team_total_over": {
        "label": "Team Total Over",
        "icon": "📈",
        "min_probability": 0.60,
        "description": "Team scores over a safe total",
    },
    "team_total_under": {
        "label": "Team Total Under",
        "icon": "📉",
        "min_probability": 0.60,
        "description": "Team scores under a safe total",
    },
}

# ─── Team Strength Score Weights ────────────────────────────────
TEAM_STRENGTH_WEIGHTS = {
    "recent_win_rate": 0.25,
    "offensive_rating": 0.20,
    "defensive_rating": 0.20,
    "home_away_adj": 0.15,
    "h2h_factor": 0.10,
    "streak_momentum": 0.10,
}

# ─── Player Impact Score Weights ────────────────────────────────
PLAYER_IMPACT_WEIGHTS = {
    "performance_trend": 0.30,
    "consistency": 0.25,
    "usage_rate": 0.20,
    "minutes_played": 0.15,
    "fatigue_adj": 0.10,
}

# ─── Advanced Model Parameters ────────────────────────────────
# Rest/Fatigue Adjustments
REST_PENALTIES = {
    "b2b": 4.5,            # Penalty for second night of back-to-back (points equivalent)
    "3_in_4": 6.0,         # Penalty for 3rd game in 4 nights
    "travel_bonus": 1.5,   # Extra penalty if travel > 1000 miles (simulated)
}

# Simple Rating System (SRS) & SOS
SOS_WEIGHT = 0.20          # How much Strength of Schedule affects the base rating
SOS_WINDOW = 15            # Number of recent opponents to evaluate for SOS

# Injury & Impact Multipliers
STAR_ABSENCE_PPG_MULTIPLIER = 0.85  # Offset for missing scorer (% of their PPG)
STAR_ABSENCE_ORTG_MULTIPLIER = 0.10  # % reduction in OffRtg per star absence
STAR_ABSENCE_DRTG_MULTIPLIER = 0.08  # % increase in DefRtg per defensive star absence
USAGE_REDISTRIBUTION_BOOST = 1.15    # Boost to remaining stars' impact score when a teammate is out

# ─── NBA Team Colors (for charts) ─────────────────────────────
TEAM_COLORS = {
    "ATL": {"primary": "#E03A3E", "secondary": "#C1D32F"},
    "BOS": {"primary": "#007A33", "secondary": "#BA9653"},
    "BKN": {"primary": "#000000", "secondary": "#FFFFFF"},
    "CHA": {"primary": "#1D1160", "secondary": "#00788C"},
    "CHI": {"primary": "#CE1141", "secondary": "#000000"},
    "CLE": {"primary": "#860038", "secondary": "#FDBB30"},
    "DAL": {"primary": "#00538C", "secondary": "#002B5E"},
    "DEN": {"primary": "#0E2240", "secondary": "#FEC524"},
    "DET": {"primary": "#C8102E", "secondary": "#1D42BA"},
    "GSW": {"primary": "#1D428A", "secondary": "#FFC72C"},
    "HOU": {"primary": "#CE1141", "secondary": "#000000"},
    "IND": {"primary": "#002D62", "secondary": "#FDBB30"},
    "LAC": {"primary": "#C8102E", "secondary": "#1D428A"},
    "LAL": {"primary": "#552583", "secondary": "#FDB927"},
    "MEM": {"primary": "#5D76A9", "secondary": "#12173F"},
    "MIA": {"primary": "#98002E", "secondary": "#F9A01B"},
    "MIL": {"primary": "#00471B", "secondary": "#EEE1C6"},
    "MIN": {"primary": "#0C2340", "secondary": "#236192"},
    "NOP": {"primary": "#0C2340", "secondary": "#C8102E"},
    "NYK": {"primary": "#006BB6", "secondary": "#F58426"},
    "OKC": {"primary": "#007AC1", "secondary": "#EF6020"},
    "ORL": {"primary": "#0077C0", "secondary": "#C4CED4"},
    "PHI": {"primary": "#006BB6", "secondary": "#ED174C"},
    "PHX": {"primary": "#1D1160", "secondary": "#E56020"},
    "POR": {"primary": "#E03A3E", "secondary": "#000000"},
    "SAC": {"primary": "#5A2D81", "secondary": "#63727A"},
    "SAS": {"primary": "#C4CED4", "secondary": "#000000"},
    "TOR": {"primary": "#CE1141", "secondary": "#000000"},
    "UTA": {"primary": "#002B5C", "secondary": "#00471B"},
    "WAS": {"primary": "#002B5C", "secondary": "#E31837"},
}

# ─── NBA Team Full Names Mapping ──────────────────────────────
TEAM_ABBR_TO_NAME = {
    "ATL": "Atlanta Hawks", "BOS": "Boston Celtics", "BKN": "Brooklyn Nets",
    "CHA": "Charlotte Hornets", "CHI": "Chicago Bulls", "CLE": "Cleveland Cavaliers",
    "DAL": "Dallas Mavericks", "DEN": "Denver Nuggets", "DET": "Detroit Pistons",
    "GSW": "Golden State Warriors", "HOU": "Houston Rockets", "IND": "Indiana Pacers",
    "LAC": "LA Clippers", "LAL": "Los Angeles Lakers", "MEM": "Memphis Grizzlies",
    "MIA": "Miami Heat", "MIL": "Milwaukee Bucks", "MIN": "Minnesota Timberwolves",
    "NOP": "New Orleans Pelicans", "NYK": "New York Knicks", "OKC": "Oklahoma City Thunder",
    "ORL": "Orlando Magic", "PHI": "Philadelphia 76ers", "PHX": "Phoenix Suns",
    "POR": "Portland Trail Blazers", "SAC": "Sacramento Kings", "SAS": "San Antonio Spurs",
    "TOR": "Toronto Raptors", "UTA": "Utah Jazz", "WAS": "Washington Wizards",
}

# ─── Risk Level Colors & Labels ────────────────────────────────
RISK_DISPLAY = {
    "low":    {"color": "#00D4AA", "bg": "rgba(0,212,170,0.15)", "label": "LOW RISK",    "emoji": "🟢"},
    "medium": {"color": "#FFB800", "bg": "rgba(255,184,0,0.15)", "label": "MEDIUM RISK", "emoji": "🟡"},
    "avoid":  {"color": "#FF4757", "bg": "rgba(255,71,87,0.15)", "label": "AVOID",       "emoji": "🔴"},
}

# ─── UI Theme Colors ──────────────────────────────────────────
UI_COLORS = {
    "bg_primary": "#0E1117",
    "bg_secondary": "#1A1F2E",
    "bg_card": "#1E2333",
    "bg_card_hover": "#252B3D",
    "accent": "#00D4AA",
    "accent_secondary": "#7C5CFC",
    "text_primary": "#E0E0E0",
    "text_secondary": "#8899AA",
    "success": "#00D4AA",
    "warning": "#FFB800",
    "danger": "#FF4757",
    "info": "#3B82F6",
    "gold": "#FFD700",
    "border": "rgba(255,255,255,0.08)",
}

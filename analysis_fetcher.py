"""
NBA Parlay Generator — Analysis Fetcher
Provides market consensus data (Public vs Sharp) and system-play insights.
"""

# Market Consensus Data for April 1, 2026
# Format: team_abbr -> {public_pct, money_pct, sentiment, system_play}
CONSENSUS_DATA = {
    "SAS": {
        "public_pct": 77, 
        "money_pct": 65, 
        "sentiment": "Heavy Public",
        "system_play": "Fade System: Public leaning into high spread (+13.5 at GSW)."
    },
    "GSW": {
        "public_pct": 23,
        "money_pct": 35,
        "sentiment": "Contrarian",
        "system_play": "Over Trend: High pace game projected."
    },
    "DEN": {
        "public_pct": 69,
        "money_pct": 60,
        "sentiment": "Public Favorite",
        "system_play": "Fade System: 16.5 spread is historically high for road favorites."
    },
    "TOR": {
        "public_pct": 22,
        "money_pct": 78,
        "sentiment": "Sharp Target", 
        "system_play": "Sharp Alert: Heavy money on low bet volume suggests pro action vs SAC."
    },
    "SAC": {
        "public_pct": 78,
        "money_pct": 22,
        "sentiment": "Public Trap",
        "system_play": "Market Discrepancy: Public on SAC, Sharps on TOR."
    },
    "PHI": {
        "public_pct": 76,
        "money_pct": 82,
        "sentiment": "Consensus",
        "system_play": "Value: Sharps and Public aligned on 76ers vs WAS."
    },
    "IND": {
        "public_pct": 45,
        "money_pct": 68,
        "sentiment": "Sharp Lean",
        "system_play": "Road Dog Trend: Pro interest in Indiana +4.5 at CHI."
    },
    "NYK": {
        "public_pct": 59,
        "money_pct": 55,
        "sentiment": "Moderate Public",
        "system_play": "Total Over: Both teams trending towards high scoring recently."
    }
}

def get_market_sentiment(team_abbr):
    """
    Returns consensus data for a given team abbreviation.
    """
    return CONSENSUS_DATA.get(team_abbr, {
        "public_pct": 50,
        "money_pct": 50,
        "sentiment": "Neutral",
        "system_play": "No significant market discrepancy detected."
    })

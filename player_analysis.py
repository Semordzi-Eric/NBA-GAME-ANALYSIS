"""
NBA Parlay Generator — Player Impact Analysis
Analyzes key players, trends, consistency, and fatigue.
"""
import pandas as pd
import numpy as np
from config import (
    PLAYER_IMPACT_WEIGHTS, MIN_MINUTES_KEY_PLAYER,
    TOP_PLAYERS_PER_TEAM, PLAYER_GAMES_WINDOW
)


def get_key_players(team_player_stats_df):
    """
    Identify key players from team player dashboard.
    Returns top N players by minutes played.
    """
    if team_player_stats_df is None or team_player_stats_df.empty:
        return []

    df = team_player_stats_df.copy()

    # Filter by minimum minutes
    if "MIN" in df.columns:
        df["MIN_FLOAT"] = pd.to_numeric(df["MIN"], errors="coerce").fillna(0)
        df = df[df["MIN_FLOAT"] >= MIN_MINUTES_KEY_PLAYER]
        df = df.sort_values("MIN_FLOAT", ascending=False)
    elif "GP" in df.columns and "MIN" in df.columns:
        df = df.sort_values("MIN", ascending=False)

    # Take top N
    df = df.head(TOP_PLAYERS_PER_TEAM)

    players = []
    for _, row in df.iterrows():
        player_info = {
            "player_id": row.get("PLAYER_ID", row.get("GROUP_VALUE", 0)),
            "player_name": row.get("PLAYER_NAME", row.get("GROUP_VALUE", "Unknown")),
            "gp": int(row.get("GP", 0)),
            "min_per_game": round(float(row.get("MIN", 0)), 1),
            "pts_per_game": round(float(row.get("PTS", 0)), 1),
            "reb_per_game": round(float(row.get("REB", 0)), 1),
            "ast_per_game": round(float(row.get("AST", 0)), 1),
            "fg_pct": round(float(row.get("FG_PCT", 0)), 3),
            "fg3_pct": round(float(row.get("FG3_PCT", 0)), 3),
            "ft_pct": round(float(row.get("FT_PCT", 0)), 3),
        }
        players.append(player_info)

    return players


def analyze_player_trends(player_game_log_df, player_info=None):
    """
    Analyze a player's recent performance trends.
    Returns trend data for PPG, APG, RPG, shooting, etc.
    """
    if player_game_log_df is None or player_game_log_df.empty:
        return _empty_player_analysis(player_info)

    df = player_game_log_df.copy()
    n = len(df)

    # Basic averages over the window
    avg_pts = df["PTS"].mean() if "PTS" in df.columns else 0
    avg_reb = df["REB"].mean() if "REB" in df.columns else 0
    avg_ast = df["AST"].mean() if "AST" in df.columns else 0
    avg_min = pd.to_numeric(df["MIN"], errors="coerce").mean() if "MIN" in df.columns else 0
    avg_fg_pct = df["FG_PCT"].mean() if "FG_PCT" in df.columns else 0
    avg_fg3_pct = df["FG3_PCT"].mean() if "FG3_PCT" in df.columns else 0
    avg_ft_pct = df["FT_PCT"].mean() if "FT_PCT" in df.columns else 0

    # Standard deviations for consistency
    std_pts = df["PTS"].std() if "PTS" in df.columns and n > 1 else 0
    std_reb = df["REB"].std() if "REB" in df.columns and n > 1 else 0
    std_ast = df["AST"].std() if "AST" in df.columns and n > 1 else 0

    # Performance trend (are they trending up or down?)
    pts_trend = _compute_trend_direction(df["PTS"].tolist() if "PTS" in df.columns else [])
    reb_trend = _compute_trend_direction(df["REB"].tolist() if "REB" in df.columns else [])
    ast_trend = _compute_trend_direction(df["AST"].tolist() if "AST" in df.columns else [])

    # Game-by-game data for charts (reverse for chronological order)
    pts_history = df["PTS"].tolist()[::-1] if "PTS" in df.columns else []
    reb_history = df["REB"].tolist()[::-1] if "REB" in df.columns else []
    ast_history = df["AST"].tolist()[::-1] if "AST" in df.columns else []

    # Usage approximation (FGA + 0.44*FTA + TOV) / Minutes
    usage_rate = 0.0
    if all(col in df.columns for col in ["FGA", "FTA", "TOV", "MIN"]):
        mins = pd.to_numeric(df["MIN"], errors="coerce").fillna(1)
        usage = (df["FGA"] + 0.44 * df["FTA"] + df["TOV"]) / mins.replace(0, 1)
        usage_rate = round(usage.mean() * 100, 1)

    return {
        "player_id": player_info.get("player_id", 0) if player_info else 0,
        "player_name": player_info.get("player_name", "Unknown") if player_info else "Unknown",
        "games_analyzed": n,
        "avg_pts": round(avg_pts, 1),
        "avg_reb": round(avg_reb, 1),
        "avg_ast": round(avg_ast, 1),
        "avg_min": round(avg_min, 1),
        "avg_fg_pct": round(avg_fg_pct, 3),
        "avg_fg3_pct": round(avg_fg3_pct, 3),
        "avg_ft_pct": round(avg_ft_pct, 3),
        "std_pts": round(std_pts, 1),
        "std_reb": round(std_reb, 1),
        "std_ast": round(std_ast, 1),
        "pts_trend": pts_trend,
        "reb_trend": reb_trend,
        "ast_trend": ast_trend,
        "pts_history": pts_history,
        "reb_history": reb_history,
        "ast_history": ast_history,
        "usage_rate": usage_rate,
    }


def _empty_player_analysis(player_info=None):
    """Return empty analysis when no data is available."""
    return {
        "player_id": player_info.get("player_id", 0) if player_info else 0,
        "player_name": player_info.get("player_name", "Unknown") if player_info else "Unknown",
        "games_analyzed": 0,
        "avg_pts": 0, "avg_reb": 0, "avg_ast": 0, "avg_min": 0,
        "avg_fg_pct": 0, "avg_fg3_pct": 0, "avg_ft_pct": 0,
        "std_pts": 0, "std_reb": 0, "std_ast": 0,
        "pts_trend": "flat", "reb_trend": "flat", "ast_trend": "flat",
        "pts_history": [], "reb_history": [], "ast_history": [],
        "usage_rate": 0,
    }


def _compute_trend_direction(values):
    """Determine if a stat is trending up, down, or flat."""
    if len(values) < 3:
        return "flat"

    # Values are most recent first, so reverse for chronological
    vals = list(reversed(values))
    mid = len(vals) // 2
    first_half_avg = np.mean(vals[:mid]) if mid > 0 else 0
    second_half_avg = np.mean(vals[mid:]) if len(vals) > mid else 0

    diff_pct = (second_half_avg - first_half_avg) / max(first_half_avg, 1) * 100

    if diff_pct > 8:
        return "up"
    elif diff_pct < -8:
        return "down"
    return "flat"


def compute_consistency_score(player_analysis):
    """
    Compute player consistency score (0-100).
    Uses coefficient of variation — lower variance = higher consistency.
    """
    if player_analysis["games_analyzed"] < 3:
        return 50.0  # Default when insufficient data

    avg_pts = max(player_analysis["avg_pts"], 1)
    std_pts = player_analysis["std_pts"]

    # Coefficient of variation (lower is more consistent)
    cv = std_pts / avg_pts

    # Convert to 0-100 score (CV of 0 = 100, CV of 1+ = 0)
    consistency = max(0, min(100, (1 - cv) * 100))

    return round(consistency, 1)


def detect_fatigue(player_game_log_df):
    """
    Detect player fatigue signals.
    Checks for back-to-back games and heavy recent workload.
    """
    if player_game_log_df is None or player_game_log_df.empty:
        return {"is_fatigued": False, "b2b": False, "games_last_7_days": 0, "fatigue_score": 0}

    df = player_game_log_df.copy()

    # Parse game dates
    if "GAME_DATE" in df.columns:
        try:
            dates = pd.to_datetime(df["GAME_DATE"])
            dates_sorted = dates.sort_values(ascending=False)

            # Check back-to-back
            b2b = False
            if len(dates_sorted) >= 2:
                day_diff = (dates_sorted.iloc[0] - dates_sorted.iloc[1]).days
                b2b = day_diff <= 1

            # Games in last 7 days
            if len(dates_sorted) > 0:
                cutoff = dates_sorted.iloc[0] - pd.Timedelta(days=7)
                games_7d = len(dates_sorted[dates_sorted >= cutoff])
            else:
                games_7d = 0

            # Fatigue score (0-100, higher = more fatigued)
            fatigue = 0
            if b2b:
                fatigue += 40
            if games_7d >= 4:
                fatigue += 30
            elif games_7d >= 3:
                fatigue += 15

            # Check if minutes are increasing (overworked)
            if "MIN" in df.columns and len(df) >= 3:
                recent_mins = pd.to_numeric(df["MIN"].head(3), errors="coerce").mean()
                if recent_mins > 36:
                    fatigue += 20
                elif recent_mins > 33:
                    fatigue += 10

            return {
                "is_fatigued": fatigue >= 40,
                "b2b": b2b,
                "games_last_7_days": games_7d,
                "fatigue_score": min(100, fatigue),
            }
        except Exception:
            pass

    return {"is_fatigued": False, "b2b": False, "games_last_7_days": 0, "fatigue_score": 0}


def compute_player_impact_score(player_analysis, consistency_score, fatigue_data):
    """
    Compute composite player impact score (0-100).
    
    Weights from config:
    - performance_trend: 30%
    - consistency: 25%
    - usage_rate: 20%
    - minutes_played: 15%
    - fatigue_adj: 10%
    """
    w = PLAYER_IMPACT_WEIGHTS

    # Performance trend score
    trend_map = {"up": 80, "flat": 60, "down": 35}
    pts_trend_score = trend_map.get(player_analysis.get("pts_trend", "flat"), 60)

    # Scale by actual production level
    pts_level = min(100, (player_analysis["avg_pts"] / 30) * 100)
    performance_score = (pts_trend_score * 0.5 + pts_level * 0.5)

    # Consistency score (already 0-100)
    consist_score = consistency_score

    # Usage rate score (normalized: typical range 15-35%)
    usage = player_analysis.get("usage_rate", 20)
    usage_score = min(100, max(0, (usage / 35) * 100))

    # Minutes played score (normalized: 20-40 min range)
    mins = player_analysis.get("avg_min", 25)
    mins_score = min(100, max(0, ((mins - 15) / 25) * 100))

    # Fatigue adjustment (inverted: high fatigue = lower score)
    fatigue_score = 100 - fatigue_data.get("fatigue_score", 0)

    # Weighted composite
    impact = (
        w["performance_trend"] * performance_score +
        w["consistency"] * consist_score +
        w["usage_rate"] * usage_score +
        w["minutes_played"] * mins_score +
        w["fatigue_adj"] * fatigue_score
    )

    return round(max(0, min(100, impact)), 1)


def get_full_player_analysis(team_id):
    """Run full player analysis pipeline for a team's key players."""
    from data_fetcher import get_team_players_stats, get_player_game_log

    # Get team's player stats to identify key players
    team_stats = get_team_players_stats(team_id)
    key_players = get_key_players(team_stats)

    player_analyses = []
    for player_info in key_players:
        player_id = player_info["player_id"]
        if not player_id:
            continue

        # Get game log
        game_log = get_player_game_log(player_id)

        # Analyze trends
        analysis = analyze_player_trends(game_log, player_info)

        # Compute scores
        consistency = compute_consistency_score(analysis)
        fatigue = detect_fatigue(game_log)
        impact = compute_player_impact_score(analysis, consistency, fatigue)

        player_analyses.append({
            **analysis,
            "season_ppg": player_info.get("pts_per_game", 0),
            "season_rpg": player_info.get("reb_per_game", 0),
            "season_apg": player_info.get("ast_per_game", 0),
            "consistency_score": consistency,
            "fatigue": fatigue,
            "impact_score": impact,
        })

    # Sort by impact score
    player_analyses.sort(key=lambda x: x["impact_score"], reverse=True)
    return player_analyses

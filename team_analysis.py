"""
NBA Parlay Generator — Team Analysis Engine
Computes team strength scores, recent form, and matchup analysis.
"""
import pandas as pd
import numpy as np
from config import TEAM_STRENGTH_WEIGHTS, HOME_COURT_ADVANTAGE, RECENT_GAMES_WINDOW, SOS_WEIGHT


def calculate_strength_of_schedule(opponents, standings_df):
    """Get win rates of opponents from standings"""
    # Robust column detection
    cols = standings_df.columns
    win_pct_col = next((c for c in ["WinPCT", "W_PCT", "WIN_PCT"] if c in cols), None)
    abbr_col = next((c for c in ["TeamAbbreviation", "TEAM_ABBREVIATION", "Abbreviation", "TEAM_ABBR"] if c in cols), None)
    
    if not win_pct_col or not abbr_col:
        return 0.5
    
    for opp in opponents:
        opp_row = standings_df[standings_df[abbr_col] == opp]
        if not opp_row.empty:
            # Use .iloc[0][win_pct_col] instead of .get() for consistency
            try:
                opp_win_rates.append(float(opp_row.iloc[0][win_pct_col]))
            except:
                opp_win_rates.append(0.5)
        else:
            opp_win_rates.append(0.5)

    return np.mean(opp_win_rates) if opp_win_rates else 0.5


def compute_sos(game_log_df, standings_df):
    """
    Compute Strength of Schedule (SOS) based on recent opponents' win rates.
    """
    if game_log_df is None or game_log_df.empty or standings_df is None or standings_df.empty:
        return 0.5

    opponents = []
    for _, row in game_log_df.iterrows():
        matchup = str(row.get("MATCHUP", ""))
        if " @ " in matchup:
            opponents.append(matchup.split(" @ ")[1])
        elif " vs. " in matchup:
            opponents.append(matchup.split(" vs. ")[1])

    if not opponents:
        return 0.5

    return calculate_strength_of_schedule(opponents, standings_df)


def analyze_recent_form(game_log_df):
    """Analyze a team's recent form from game log data."""
    if game_log_df is None or game_log_df.empty:
        return {
            "games_played": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.5,
            "avg_points": 105.0,
            "avg_opp_points": 105.0,
            "avg_margin": 0.0,
            "current_streak": 0,
            "streak_type": "N/A",
            "avg_fg_pct": 0.45,
            "avg_ft_pct": 0.77,
            "avg_fg3_pct": 0.35,
            "avg_rebounds": 44.0,
            "avg_assists": 24.0,
            "avg_turnovers": 14.0,
            "last_5_record": "N/A",
            "point_trend": [],
        }

    df = game_log_df.copy()
    n = len(df)

    # Parse W/L from WL column
    wins = len(df[df["WL"] == "W"]) if "WL" in df.columns else 0
    losses = n - wins
    win_rate = wins / n if n > 0 else 0.5

    # Average stats
    avg_points = df["PTS"].mean() if "PTS" in df.columns else 105.0
    avg_fg_pct = df["FG_PCT"].mean() if "FG_PCT" in df.columns else 0.45
    avg_ft_pct = df["FT_PCT"].mean() if "FT_PCT" in df.columns else 0.77
    avg_fg3_pct = df["FG3_PCT"].mean() if "FG3_PCT" in df.columns else 0.35
    avg_rebounds = df["REB"].mean() if "REB" in df.columns else 44.0
    avg_assists = df["AST"].mean() if "AST" in df.columns else 24.0
    avg_turnovers = df["TOV"].mean() if "TOV" in df.columns else 14.0

    # Compute opponent points from PLUS_MINUS
    if "PLUS_MINUS" in df.columns and "PTS" in df.columns:
        avg_opp_points = avg_points - df["PLUS_MINUS"].mean()
    else:
        avg_opp_points = 105.0

    avg_margin = avg_points - avg_opp_points

    # Current streak
    streak = 0
    streak_type = "N/A"
    if "WL" in df.columns and n > 0:
        first_result = df.iloc[0]["WL"]
        streak_type = "W" if first_result == "W" else "L"
        for _, row in df.iterrows():
            if row["WL"] == first_result:
                streak += 1
            else:
                break

    # Last 5 record
    last_5 = df.head(5) if n >= 5 else df
    last_5_wins = len(last_5[last_5["WL"] == "W"]) if "WL" in last_5.columns else 0
    last_5_losses = len(last_5) - last_5_wins
    last_5_record = f"{last_5_wins}-{last_5_losses}"

    # Point trend (for sparkline chart)
    point_trend = df["PTS"].tolist()[::-1] if "PTS" in df.columns else []

    # B2B Detection (Last game was yesterday)
    is_b2b = False
    if n > 0 and "GAME_DATE" in df.columns:
        try:
            # Sort by date to get the most recent game
            df['GAME_DATE_DT'] = pd.to_datetime(df['GAME_DATE'], format='mixed')
            last_game_date = df['GAME_DATE_DT'].max().date()
            
            # Use US/Eastern as reference for 'today' or just today
            from datetime import datetime
            import pytz
            tz = pytz.timezone('US/Eastern')
            today = datetime.now(tz).date()
            
            if (today - last_game_date).days <= 1:
                is_b2b = True
        except:
            pass

    # Pace Calculation (Approximate: Possession count)
    # Pace = 48 * ((Tm Pos + Opp Pos) / (2 * (Tm MP / 5)))
    # A simplified version using box stats:
    # Possessions = 0.96 * (FGA + TOV + 0.44 * FTA - OREB)
    if all(col in df.columns for col in ["FGA", "TOV", "FTA", "OREB"]):
        df["POSS"] = 0.96 * (df["FGA"] + df["TOV"] + 0.44 * df["FTA"] - df["OREB"])
        avg_pace = df["POSS"].mean()
    else:
        avg_pace = 100.0

    # Four Factors (Offensive)
    # 1. eFG% = (FGM + 0.5 * FG3M) / FGA
    # 2. TOV% = TOV / (FGA + 0.44 * FTA + TOV)
    # 3. ORB% = OREB / (OREB + Opp DREB) -- Simplified as OREB / (OREB + Opp REB - Opp OREB)
    # 4. FTR = FTA / FGA
    
    efg_pct = (df["FGM"].sum() + 0.5 * df["FG3M"].sum()) / df["FGA"].sum() if "FGA" in df.columns else 0.5
    tov_pct = df["TOV"].sum() / (df["FGA"].sum() + 0.44 * df["FTA"].sum() + df["TOV"].sum()) if "FGA" in df.columns else 0.15
    orb_pct = df["OREB"].sum() / (df["REB"].sum()) if "REB" in df.columns else 0.25 # Simplified proxy
    ft_rate = df["FTA"].sum() / df["FGA"].sum() if "FGA" in df.columns else 0.2
    
    return {
        "games_played": n,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "avg_points": round(avg_points, 1),
        "avg_opp_points": round(avg_opp_points, 1),
        "avg_margin": round(avg_margin, 1),
        "current_streak": streak,
        "streak_type": streak_type,
        "avg_fg_pct": round(avg_fg_pct, 3),
        "avg_ft_pct": round(avg_ft_pct, 3),
        "avg_fg3_pct": round(avg_fg3_pct, 3),
        "avg_rebounds": round(avg_rebounds, 1),
        "avg_assists": round(avg_assists, 1),
        "avg_turnovers": round(avg_turnovers, 1),
        "last_5_record": last_5_record,
        "point_trend": point_trend,
        "is_b2b": is_b2b,
        "pace": round(avg_pace, 1),
        "four_factors": {
            "efg_pct": round(efg_pct * 100, 1),
            "tov_pct": round(tov_pct * 100, 1),
            "orb_pct": round(orb_pct * 100, 1),
            "ft_rate": round(ft_rate, 3)
        }
    }


def analyze_home_away_splits(full_game_log_df, is_home=True):
    """Analyze home or away performance from full season game log."""
    if full_game_log_df is None or full_game_log_df.empty:
        return {
            "games": 0,
            "win_rate": 0.5,
            "avg_points": 105.0,
            "avg_margin": 0.0,
        }

    df = full_game_log_df.copy()

    # MATCHUP column contains "@" for away games, "vs." for home games
    if "MATCHUP" in df.columns:
        if is_home:
            split_df = df[df["MATCHUP"].str.contains("vs.", na=False)]
        else:
            split_df = df[df["MATCHUP"].str.contains("@", na=False)]
    else:
        split_df = df

    if split_df.empty:
        return {
            "games": 0,
            "win_rate": 0.5,
            "avg_points": 105.0,
            "avg_margin": 0.0,
        }

    n = len(split_df)
    wins = len(split_df[split_df["WL"] == "W"]) if "WL" in split_df.columns else 0
    win_rate = wins / n if n > 0 else 0.5

    avg_points = split_df["PTS"].mean() if "PTS" in split_df.columns else 105.0
    avg_margin = split_df["PLUS_MINUS"].mean() if "PLUS_MINUS" in split_df.columns else 0.0

    return {
        "games": n,
        "win_rate": round(win_rate, 3),
        "avg_points": round(avg_points, 1),
        "avg_margin": round(avg_margin, 1),
    }


def compute_offensive_rating(game_log_df):
    """Estimate offensive rating (points per 100 possessions)."""
    if game_log_df is None or game_log_df.empty:
        return 110.0

    df = game_log_df.copy()
    if all(col in df.columns for col in ["PTS", "FGA", "FTA", "TOV", "OREB"]):
        # Possessions estimate: FGA - OREB + TOV + 0.44 * FTA
        poss = df["FGA"] - df.get("OREB", 0) + df["TOV"] + 0.44 * df["FTA"]
        poss = poss.replace(0, 1)  # Avoid division by zero
        off_rtg = (df["PTS"] / poss * 100).mean()
        return round(off_rtg, 1)

    # Fallback: use raw PPG
    return round(df["PTS"].mean(), 1) if "PTS" in df.columns else 110.0


def compute_defensive_rating(game_log_df):
    """Estimate defensive rating (opponent points per 100 possessions)."""
    if game_log_df is None or game_log_df.empty:
        return 110.0

    df = game_log_df.copy()
    if "PTS" in df.columns and "PLUS_MINUS" in df.columns:
        opp_pts = df["PTS"] - df["PLUS_MINUS"]
        if all(col in df.columns for col in ["FGA", "FTA", "TOV"]):
            poss = df["FGA"] + df["TOV"] + 0.44 * df["FTA"]
            poss = poss.replace(0, 1)
            def_rtg = (opp_pts / poss * 100).mean()
            return round(def_rtg, 1)
        return round(opp_pts.mean(), 1)

    return 110.0


def compute_pace(game_log_df):
    """Estimate team pace (possessions per game)."""
    if game_log_df is None or game_log_df.empty:
        return 100.0

    df = game_log_df.copy()
    if all(col in df.columns for col in ["FGA", "FTA", "TOV"]):
        oreb = df["OREB"] if "OREB" in df.columns else 0
        poss = df["FGA"] - oreb + df["TOV"] + 0.44 * df["FTA"]
        return round(poss.mean(), 1)

    return 100.0


def analyze_head_to_head(h2h_df):
    """Analyze head-to-head matchup history."""
    if h2h_df is None or h2h_df.empty:
        return {
            "games_played": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.5,
            "avg_point_diff": 0.0,
        }

    n = len(h2h_df)
    wins = len(h2h_df[h2h_df["WL"] == "W"]) if "WL" in h2h_df.columns else 0
    losses = n - wins
    win_rate = wins / n if n > 0 else 0.5
    avg_diff = h2h_df["PLUS_MINUS"].mean() if "PLUS_MINUS" in h2h_df.columns else 0.0

    return {
        "games_played": n,
        "wins": wins,
        "losses": losses,
        "win_rate": round(win_rate, 3),
        "avg_point_diff": round(avg_diff, 1),
    }


def _normalize_score(value, min_val, max_val):
    """Normalize a value to 0-100 scale."""
    if max_val == min_val:
        return 50.0
    return max(0, min(100, ((value - min_val) / (max_val - min_val)) * 100))


def compute_team_strength_score(recent_form, home_split, away_split, off_rating,
                                 def_rating, h2h, is_home=True):
    """
    Compute composite team strength score (0-100).
    
    Weights from config:
    - recent_win_rate: 25%
    - offensive_rating: 20%
    - defensive_rating: 20%
    - home_away_adj: 15%
    - h2h_factor: 10%
    - streak_momentum: 10%
    """
    w = TEAM_STRENGTH_WEIGHTS

    # Win rate component (0-100)
    win_rate_score = recent_form["win_rate"] * 100

    # Offensive rating component (normalized: 95-125 range typical)
    off_score = _normalize_score(off_rating, 95, 125)

    # Defensive rating component (INVERTED: lower is better)
    def_score = 100 - _normalize_score(def_rating, 95, 125)

    # Home/Away adjustment
    if is_home:
        ha_score = home_split["win_rate"] * 100
    else:
        ha_score = away_split["win_rate"] * 100

    # Head-to-head factor
    h2h_score = h2h["win_rate"] * 100

    # Streak momentum
    streak_val = recent_form["current_streak"]
    if recent_form["streak_type"] == "L":
        streak_val = -streak_val
    streak_score = _normalize_score(streak_val, -10, 10)

    # SOS factor (normalized around 0.5)
    sos_val = recent_form.get("sos", 0.5)
    sos_score = _normalize_score(sos_val, 0.35, 0.65)

    # Weighted composite
    strength = (
        (1 - SOS_WEIGHT) * (
            w["recent_win_rate"] * win_rate_score +
            w["offensive_rating"] * off_score +
            w["defensive_rating"] * def_score +
            w["home_away_adj"] * ha_score +
            w["h2h_factor"] * h2h_score +
            w["streak_momentum"] * streak_score
        ) +
        SOS_WEIGHT * sos_score
    )

    return round(max(0, min(100, strength)), 1)


def get_full_team_analysis(team_id, vs_team_id, is_home=True):
    """Run full team analysis pipeline and return all metrics."""
    from data_fetcher import (
        get_team_game_log, get_team_full_game_log,
        get_head_to_head, get_league_standings
    )

    # Fetch data
    recent_log = get_team_game_log(team_id)
    full_log = get_team_full_game_log(team_id)
    h2h_log = get_head_to_head(team_id, vs_team_id)
    standings = get_league_standings()

    # Analyze
    recent_form = analyze_recent_form(recent_log)
    
    # Add SOS to recent form
    sos = compute_sos(recent_log, standings)
    recent_form["sos"] = sos
    home_split = analyze_home_away_splits(full_log, is_home=True)
    away_split = analyze_home_away_splits(full_log, is_home=False)
    off_rtg = compute_offensive_rating(recent_log)
    def_rtg = compute_defensive_rating(recent_log)
    pace = compute_pace(recent_log)
    h2h = analyze_head_to_head(h2h_log)

    # Compute strength score
    strength = compute_team_strength_score(
        recent_form, home_split, away_split,
        off_rtg, def_rtg, h2h, is_home
    )

    # Efficiency Ratings (Per 100 Possessions)
    # ORtg = 100 * (PTS / POSS)
    # DRtg = 100 * (Opp PTS / POSS)
    # POSS calculation needs TOV, FGA, FTA, OREB
    if all(col in recent_log.columns for col in ["FGA", "TOV", "FTA", "OREB"]):
        poss = 0.96 * (recent_log["FGA"] + recent_log["TOV"] + 0.44 * recent_log["FTA"] - recent_log["OREB"])
        poss_sum = poss.sum()
        pts_sum = recent_log["PTS"].sum()
        
        # Pro-level Defensive Rating calculation (Safely Handle Opponent PTS)
        if "PLUS_MINUS" in recent_log.columns:
            opp_pts_sum = recent_log["PTS"].sum() - recent_log["PLUS_MINUS"].sum()
        else:
            opp_pts_sum = recent_form["avg_opp_points"] * len(recent_log)
        
        if poss_sum > 0:
            ortg = 100 * (pts_sum / poss_sum)
            drtg = 100 * (opp_pts_sum / poss_sum)
        else:
            ortg = recent_form["avg_points"]
            drtg = recent_form["avg_opp_points"]
    else:
        ortg = recent_form["avg_points"]
        drtg = recent_form["avg_opp_points"]

    # Home/Away Split Detection
    home_win_rate = home_split.get("win_rate", 0.5)
    away_win_rate = away_split.get("win_rate", 0.5)

    return {
        "team_id": team_id,
        "is_home": is_home,
        "strength_score": strength,
        "offensive_rating": round(ortg, 1),
        "defensive_rating": round(drtg, 1),
        "pace": round(pace, 1),
        "recent_form": recent_form,
        "league_rank": recent_form.get("league_rank", 15),
        "sos": sos,
        "home_win_rate": round(home_win_rate, 3),
        "away_win_rate": round(away_win_rate, 3),
    }

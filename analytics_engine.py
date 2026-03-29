"""
NBA Parlay Generator — Advanced Analytics Engine
Predicts game outcomes, identifies mismatches, and computes expected totals.
"""
import numpy as np
import pandas as pd
from config import HOME_COURT_ADVANTAGE


def predict_game_outcome(home_team_analysis, away_team_analysis, home_players=None, away_players=None):
    """
    Predict game outcome probabilities using team strength differential.
    Uses logistic function calibrated to NBA historical data.
    
    Returns: dict with win probabilities for both teams and injury news metadata.
    """
    home_strength = home_team_analysis["strength_score"]
    away_strength = away_team_analysis["strength_score"]

    # --- NEWS/INJURY PENALTY LOGIC ---
    def calculate_missing_player_penalty(players_list):
        penalty = 0.0
        missing_players = []
        if players_list:
            # Check the top 3 players by inherent impact
            for p in players_list[:3]:
                # If they played extremely few games in the recent window, they are likely injured.
                if p.get("games_analyzed", 0) <= 2:
                    impact = p.get("impact_score", 50)
                    penalty += (impact * 0.15)
                    missing_players.append(p.get("player_name", "Key Player"))
        return penalty, missing_players

    home_penalty, home_missing = calculate_missing_player_penalty(home_players) if home_players else (0, [])
    away_penalty, away_missing = calculate_missing_player_penalty(away_players) if away_players else (0, [])

    home_strength -= home_penalty
    away_strength -= away_penalty

    # Strength differential (positive = home team stronger)
    strength_diff = home_strength - away_strength

    # Add home court advantage (equivalent to ~3.5 points historically)
    # Convert to strength score units: 3.5 points ≈ 5 strength units
    home_advantage_units = 5.0
    adjusted_diff = strength_diff + home_advantage_units

    # Logistic function for win probability
    # Steepness calibrated: 10-point diff ≈ 70% win probability
    k = 0.08  # steepness parameter
    home_win_prob = 1 / (1 + np.exp(-k * adjusted_diff))

    # Clamp probabilities to realistic ranges
    home_win_prob = max(0.15, min(0.92, home_win_prob))
    away_win_prob = 1 - home_win_prob

    # Compute predicted spread
    # Rough conversion: strength_diff * 0.35 ≈ point spread
    predicted_spread = adjusted_diff * 0.35

    # Confidence in prediction (based on data quality)
    home_games = home_team_analysis["recent_form"]["games_played"]
    away_games = away_team_analysis["recent_form"]["games_played"]
    data_confidence = min(100, ((home_games + away_games) / 20) * 100)

    return {
        "home_win_prob": round(home_win_prob, 3),
        "away_win_prob": round(away_win_prob, 3),
        "predicted_spread": round(predicted_spread, 1),
        "predicted_winner": "home" if home_win_prob > 0.5 else "away",
        "margin_of_victory": abs(round(predicted_spread, 1)),
        "data_confidence": round(data_confidence, 1),
        "home_missing_players": home_missing,
        "away_missing_players": away_missing,
    }


def compute_expected_total(home_team_analysis, away_team_analysis):
    """
    Compute expected combined game total.
    Uses pace-adjusted offensive/defensive ratings.
    """
    home_off = home_team_analysis["offensive_rating"]
    home_def = home_team_analysis["defensive_rating"]
    away_off = away_team_analysis["offensive_rating"]
    away_def = away_team_analysis["defensive_rating"]
    home_pace = home_team_analysis["pace"]
    away_pace = away_team_analysis["pace"]

    # League average pace and ratings for normalization
    league_avg_pace = 100.0
    league_avg_rating = 112.0

    # Average pace for the game
    game_pace = (home_pace + away_pace) / 2

    # Pace adjustment factor
    pace_factor = game_pace / league_avg_pace

    # Expected points for each team
    # Home team scores based on their offense vs away defense
    home_expected = ((home_off + away_def) / 2) * pace_factor
    # Away team scores based on their offense vs home defense  
    away_expected = ((away_off + home_def) / 2) * pace_factor

    # Small home court bump
    home_expected += HOME_COURT_ADVANTAGE / 2
    away_expected -= HOME_COURT_ADVANTAGE / 2

    total = home_expected + away_expected

    # Standard deviation for total (typically ~12-15 points in NBA)
    total_std = 13.0

    return {
        "expected_total": round(total, 1),
        "home_expected_points": round(home_expected, 1),
        "away_expected_points": round(away_expected, 1),
        "total_std": total_std,
        "total_range_low": round(total - total_std, 1),
        "total_range_high": round(total + total_std, 1),
        "game_pace": round(game_pace, 1),
    }


def identify_mismatches(home_players, away_players):
    """
    Identify statistical mismatches between team rosters.
    Looks for major impact score differentials at matched positions.
    """
    mismatches = []

    # Compare top players by impact
    for i, home_p in enumerate(home_players[:5]):
        if i < len(away_players):
            away_p = away_players[i]
            impact_diff = home_p["impact_score"] - away_p["impact_score"]

            if abs(impact_diff) >= 15:  # Significant mismatch threshold
                advantage_team = "home" if impact_diff > 0 else "away"
                advantage_player = home_p if impact_diff > 0 else away_p
                disadvantage_player = away_p if impact_diff > 0 else home_p

                mismatches.append({
                    "advantage_team": advantage_team,
                    "advantage_player": advantage_player["player_name"],
                    "advantage_impact": advantage_player["impact_score"],
                    "disadvantage_player": disadvantage_player["player_name"],
                    "disadvantage_impact": disadvantage_player["impact_score"],
                    "impact_differential": abs(round(impact_diff, 1)),
                    "description": (
                        f"{advantage_player['player_name']} "
                        f"(Impact: {advantage_player['impact_score']}) has a significant "
                        f"advantage over {disadvantage_player['player_name']} "
                        f"(Impact: {disadvantage_player['impact_score']})"
                    ),
                })

    # Sort by impact differential
    mismatches.sort(key=lambda x: x["impact_differential"], reverse=True)
    return mismatches


def compute_team_total_projection(team_analysis, opp_analysis):
    """
    Project individual team total points.
    """
    off_rtg = team_analysis["offensive_rating"]
    opp_def_rtg = opp_analysis["defensive_rating"]
    pace = (team_analysis["pace"] + opp_analysis["pace"]) / 2

    league_avg_pace = 100.0
    pace_factor = pace / league_avg_pace

    # Expected points based on offense vs opponent defense
    expected = ((off_rtg + opp_def_rtg) / 2) * pace_factor

    # Home court adjustment
    if team_analysis["is_home"]:
        expected += HOME_COURT_ADVANTAGE / 2
    else:
        expected -= HOME_COURT_ADVANTAGE / 2

    # Standard deviation (typically 10-12 for individual team)
    team_std = 11.0

    return {
        "projected_points": round(expected, 1),
        "std": team_std,
        "range_low": round(expected - team_std, 1),
        "range_high": round(expected + team_std, 1),
        "recent_avg": team_analysis["recent_form"]["avg_points"],
    }


def compute_segment_projections(game_total):
    """
    Compute 1H projections.
    1st half is usually ~49% of the total scoring (second half has fouling/OT risk).
    """
    first_half_total = game_total["expected_total"] * 0.49
    fh_home_points = game_total["home_expected_points"] * 0.49
    fh_away_points = game_total["away_expected_points"] * 0.49
    fh_spread = fh_home_points - fh_away_points
    
    return {
        "expected_total": round(first_half_total, 1),
        "home_points": round(fh_home_points, 1),
        "away_points": round(fh_away_points, 1),
        "predicted_spread": round(fh_spread, 1),
        "total_std": game_total["total_std"] * 0.5, # Reduced variance for half
    }


def generate_game_analysis(game, home_team_analysis, away_team_analysis,
                            home_players, away_players):
    """
    Generate comprehensive game analysis combining all metrics.
    """
    # Predict outcome incorporating news/injuries
    prediction = predict_game_outcome(home_team_analysis, away_team_analysis, home_players, away_players)

    # Expected total
    total = compute_expected_total(home_team_analysis, away_team_analysis)
    
    # First half segments
    first_half = compute_segment_projections(total)

    # Team total projections
    home_total_proj = compute_team_total_projection(home_team_analysis, away_team_analysis)
    away_total_proj = compute_team_total_projection(away_team_analysis, home_team_analysis)

    # Mismatches
    mismatches = identify_mismatches(home_players, away_players)

    # Determine predicted winner details
    if prediction["predicted_winner"] == "home":
        winner_abbr = game["home_team_abbr"]
        winner_name = f"{game['home_team_city']} {game['home_team_name']}"
        winner_prob = prediction["home_win_prob"]
    else:
        winner_abbr = game["away_team_abbr"]
        winner_name = f"{game['away_team_city']} {game['away_team_name']}"
        winner_prob = prediction["away_win_prob"]

    return {
        "game": game,
        "home_analysis": home_team_analysis,
        "away_analysis": away_team_analysis,
        "home_players": home_players,
        "away_players": away_players,
        "prediction": prediction,
        "expected_total": total,
        "first_half_projection": first_half,
        "home_total_projection": home_total_proj,
        "away_total_projection": away_total_proj,
        "mismatches": mismatches,
        "predicted_winner_abbr": winner_abbr,
        "predicted_winner_name": winner_name,
        "predicted_winner_prob": winner_prob,
    }

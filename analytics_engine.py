"""
NBA Parlay Generator — Advanced Analytics Engine
Predicts game outcomes, identifies mismatches, and computes expected totals.
"""
import numpy as np
import pandas as pd
from config import (
    HOME_COURT_ADVANTAGE, REST_PENALTIES, 
    STAR_ABSENCE_ORTG_MULTIPLIER, STAR_ABSENCE_DRTG_MULTIPLIER,
    USAGE_REDISTRIBUTION_BOOST
)


import math
import os
import joblib
import pandas as pd

# Try loading the ML model globally
MODEL_PATH = "nba_model.joblib"
ml_model_payload = None
if os.path.exists(MODEL_PATH):
    try:
        ml_model_payload = joblib.load(MODEL_PATH)
    except Exception as e:
        print(f"Failed to load ML model: {e}")

def predict_game_outcome(home_team_analysis, away_team_analysis, home_players=None, away_players=None):
    """
    Predict game outcome probabilities using Proficiency/Efficiency differentials.
    Uses Pace-adjusted efficiency margins and Mismatch detection.
    """
    # 1. Base Efficiency Margin
    # Adjust for B2B/Rest
    h_rest_penalty = REST_PENALTIES["b2b"] if home_team_analysis["recent_form"].get("is_b2b") else 0
    a_rest_penalty = REST_PENALTIES["b2b"] if away_team_analysis["recent_form"].get("is_b2b") else 0
    
    # Base Ratings
    h_ortg = home_team_analysis["offensive_rating"]
    h_drtg = home_team_analysis["defensive_rating"]
    a_ortg = away_team_analysis["offensive_rating"]
    a_drtg = away_team_analysis["defensive_rating"]
    
    # Player absence impacts (ORtg reduction)
    h_penalty = sum([p["impact_score"] * STAR_ABSENCE_ORTG_MULTIPLIER for p in home_players if p.get("is_missing")])
    a_penalty = sum([p["impact_score"] * STAR_ABSENCE_ORTG_MULTIPLIER for p in away_players if p.get("is_missing")])
    h_def_pen = sum([p["impact_score"] * STAR_ABSENCE_DRTG_MULTIPLIER for p in home_players if p.get("is_missing")])
    a_def_pen = sum([p["impact_score"] * STAR_ABSENCE_DRTG_MULTIPLIER for p in away_players if p.get("is_missing")])

    h_ortg -= h_penalty
    h_drtg += h_def_pen
    a_ortg -= a_penalty
    a_drtg += a_def_pen
    
    # Home/Away win rate bonus (0.1 win rate diff ≈ 1.0 efficiency unit)
    h_bonus = (home_team_analysis.get("home_win_rate", 0.5) - 0.5) * 10
    a_bonus = (away_team_analysis.get("away_win_rate", 0.5) - 0.5) * 10
    
    # 2. Predicted Efficiency Margin (per 100 possessions)
    h_adv = (h_ortg - a_drtg)
    a_adv = (a_ortg - h_drtg)
    
    # 3. Pace Scaling
    h_pace = home_team_analysis["recent_form"].get("pace", 100.0)
    a_pace = away_team_analysis["recent_form"].get("pace", 100.0)
    game_pace = (h_pace + a_pace) / 2
    
    # Margin per game
    net_margin = (h_adv - a_adv) * (game_pace / 100)
    net_margin += HOME_COURT_ADVANTAGE + h_bonus - a_bonus
    net_margin -= (h_rest_penalty - a_rest_penalty)
    
    # 4. Mismatch Detection (Four Factors)
    mismatch_score = 0
    mismatch_reasons = []
    
    h_ff = home_team_analysis["recent_form"]["four_factors"]
    a_ff = away_team_analysis["recent_form"]["four_factors"]
    
    # Highlighted Game for Mismatch Labels
    home_abbr = home_team_analysis.get("team_id", "Home")
    away_abbr = away_team_analysis.get("team_id", "Away")

    # ORB vs DRB Mismatch
    if h_ff["orb_pct"] > 28 and a_ff["orb_pct"] < 21:
        mismatch_score += 1.5
        mismatch_reasons.append(f"{home_abbr} Glass Dominance")
    elif a_ff["orb_pct"] > 28 and h_ff["orb_pct"] < 21:
        mismatch_score -= 1.5
        mismatch_reasons.append(f"{away_abbr} Glass Dominance")
        
    # TOV Pressure
    if a_ff["tov_pct"] > 16.5 and h_ff["tov_pct"] < 13:
        mismatch_score += 1.0
        mismatch_reasons.append(f"{home_abbr} Possession Security")
        
    net_margin += mismatch_score
    
    # ---------------------------------------------------------
    # MACHINE LEARNING ENGINE OVERRIDE
    # ---------------------------------------------------------
    if ml_model_payload is not None:
        clf = ml_model_payload["model"]
        feature_names = ml_model_payload["features"]
        
        # Build features according to how ml_pipeline.py extracts them
        h_rest_advantage = (1 if not home_team_analysis["recent_form"].get("is_b2b") else 0) - (1 if not away_team_analysis["recent_form"].get("is_b2b") else 0)
        form_diff = home_team_analysis.get("home_win_rate", 0.5) - away_team_analysis.get("away_win_rate", 0.5)
        injury_impact_diff = a_penalty - h_penalty
        
        # We calculate the raw pre-injury stats to match the training data
        net_ortg_diff = home_team_analysis["offensive_rating"] - away_team_analysis["defensive_rating"]
        net_drtg_diff = home_team_analysis["defensive_rating"] - away_team_analysis["offensive_rating"]
        net_efficiency_margin = net_ortg_diff - net_drtg_diff
        
        # Note: in training, h_adv incorporated injuries, but the network learns the weights directly from diffs.
        
        feature_dict = {
            "net_ortg_diff": net_ortg_diff,
            "net_drtg_diff": net_drtg_diff,
            "net_efficiency_margin": net_efficiency_margin,
            "home_rest_advantage": h_rest_advantage,
            "form_diff": form_diff,
            "injury_impact_diff": injury_impact_diff
        }
        
        # Ensure correct exact order
        try:
            X_input = pd.DataFrame([[feature_dict[f] for f in feature_names]], columns=feature_names)
            home_win_prob = clf.predict_proba(X_input)[0][1]
            away_win_prob = 1.0 - home_win_prob
            
            # Map probabilities back to an implied spread using heuristic approximation for display
            # net_margin = ln(p/(1-p)) / 0.16
            if home_win_prob > 0.99: net_margin = 25.0
            elif home_win_prob < 0.01: net_margin = -25.0
            else: net_margin = math.log(home_win_prob / away_win_prob) / 0.15
        except Exception as e:
            # Fallback to heuristic
            home_win_prob = 1 / (1 + math.exp(-0.16 * net_margin))
            away_win_prob = 1 - home_win_prob
    else:
        # Win Probability (Logistic Heuristic)
        home_win_prob = 1 / (1 + math.exp(-0.16 * net_margin))
        away_win_prob = 1 - home_win_prob
    
    return {
        "home_win_prob": round(home_win_prob, 3),
        "away_win_prob": round(away_win_prob, 3),
        "predicted_winner": "home" if net_margin >= 0 else "away",
        "predicted_spread": round(net_margin, 1),
        "home_penalty": round(h_penalty, 1),
        "away_penalty": round(a_penalty, 1),
        "game_pace": round(game_pace, 1),
        "mismatch_score": round(mismatch_score, 1),
        "mismatch_reasons": mismatch_reasons
    }


def compute_expected_total(home_ana, away_ana, home_players=None, away_players=None):
    # Use Efficiency Ratings * Pace
    h_ortg = home_ana["offensive_rating"]
    a_ortg = away_ana["offensive_rating"]
    h_drtg = home_ana["defensive_rating"]
    a_drtg = away_ana["defensive_rating"]
    
    # Average expected efficiency per side
    h_exp = (h_ortg + a_drtg) / 2
    a_exp = (a_ortg + h_drtg) / 2
    
    # Scaling for missing players
    h_penalty = sum([p["impact_score"] * STAR_ABSENCE_ORTG_MULTIPLIER for p in home_players if p.get("is_missing")])
    a_penalty = sum([p["impact_score"] * STAR_ABSENCE_ORTG_MULTIPLIER for p in away_players if p.get("is_missing")])
    
    h_exp -= (h_penalty / 2)
    a_exp -= (a_penalty / 2)
    
    # Final projection based on game-specific pace
    h_pace = home_ana["recent_form"].get("pace", 100.0)
    a_pace = away_ana["recent_form"].get("pace", 100.0)
    game_pace = (h_pace + a_pace) / 2
    
    expected_total = (h_exp + a_exp) * (game_pace / 100)
    
    return {
        "expected_total": round(expected_total, 1),
        "home_proj_pts": round(h_exp * (game_pace / 100), 1),
        "away_proj_pts": round(a_exp * (game_pace / 100), 1),
        "total_std": 15.0, # Box score totals have higher variance
        "pace": round(game_pace, 1)
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
    fh_home_points = game_total["home_proj_pts"] * 0.49
    fh_away_points = game_total["away_proj_pts"] * 0.49
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
    total = compute_expected_total(home_team_analysis, away_team_analysis, home_players, away_players)
    
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

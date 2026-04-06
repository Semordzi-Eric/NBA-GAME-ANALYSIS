"""
NBA Parlay Generator — Betting Intelligence
Identifies low-risk Team Performance bets from game analysis data.
"""
import numpy as np
from config import BET_TYPES, RISK_THRESHOLDS, RISK_DISPLAY


def assign_risk_level(probability):
    if probability >= RISK_THRESHOLDS["low"]:
        return "low"
    elif probability >= RISK_THRESHOLDS["medium"]:
        return "medium"
    return "avoid"


def calculate_expected_value(probability, decimal_odds):
    """
    EV = (Win Prob * Profit) - (Loss Prob * Bet Amount)
    Profit = (Decimal Odds - 1)
    """
    if not decimal_odds or decimal_odds <= 1:
        return 0.0
    profit = decimal_odds - 1
    loss_prob = 1 - probability
    ev = (probability * profit) - (loss_prob * 1.0)
    return round(ev, 3)


def probability_to_american_odds(probability):
    if probability <= 0 or probability >= 1:
        return 0
    if probability >= 0.5:
        return round(-100 * probability / (1 - probability))
    else:
        return round(100 * (1 - probability) / probability)


def probability_to_decimal_odds(probability):
    if probability <= 0:
        return 1.0
    return round(1 / probability, 2)


def generate_bet_explanation(bet):
    bet_type = bet["bet_type"]
    prob = bet["probability"]
    team = bet.get("team_name", "")

    if bet_type == "moneyline":
        explanation = f"{team} is projected to win outright ({prob*100:.0f}% confidence) based on superior team metrics."
        if bet.get("missing_players"):
            explanation += f" Adjusted positively against opponent missing: {', '.join(bet['missing_players'])}."
        return explanation

    elif bet_type == "point_spread":
        line = bet["line"]
        pred_spread = bet["predicted_margin"]
        sign = "+" if line > 0 else ""
        explanation = f"{team} {sign}{line:.1f} Alt-Spread. Our engine predicts them to perform at a {pred_spread:+.1f} margin, giving a safe ~{abs(pred_spread + line):.1f} point cushion."
        if bet.get("missing_players"):
            explanation += f" Factors in opponent missing key player(s)."
        return explanation

    elif bet_type in ["game_total_over", "game_total_under", "first_half_total_over", "first_half_total_under"]:
        line = bet["line"]
        direction = "Over" if "over" in bet_type else "Under"
        segment = "1st Half" if "first_half" in bet_type else "Full Game"
        proj = bet["projected_points"]
        explanation = f"{segment} expected total is {proj:.1f} points. The {direction} {line:.1f} provides a mathematical safety buffer based on pace and defensive ratings."
        return explanation

    elif bet_type == "first_half_spread":
        line = bet["line"]
        pred_spread = bet["predicted_margin"]
        sign = "+" if line > 0 else ""
        explanation = f"{team} {sign}{line:.1f} 1st Half Spread. Predicted 1H margin is {pred_spread:+.1f}."
        return explanation

    elif "team_total" in bet_type:
        direction = "Over" if "over" in bet_type else "Under"
        line = bet["line"]
        projected = bet["projected_points"]
        return f"{team} is projected to score {projected:.1f} points. {direction} {line:.1f} offers a comfortable analytical margin."

    return f"Selected with {prob*100:.0f}% confidence."


def _approx_normal_sf(z):
    if z > 6: return 0.0
    if z < -6: return 1.0
    t = 1 / (1 + 0.2316419 * abs(z))
    d = 0.3989422804014327 
    p = d * np.exp(-z * z / 2) * (t * (0.319381530 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429)))))
    if z > 0: return p
    return 1 - p

def get_spread_prob(predicted_margin, alt_line, std=12.5):
    """
    predicted_margin > 0 means the team is favored by that much.
    alt_line is the handicap (-3.5, +5.5).
    They cover if (actual_margin + alt_line) > 0.
    """
    expected_diff = predicted_margin + alt_line
    z = expected_diff / std
    try:
        from scipy.stats import norm
        prob = norm.cdf(z)
    except ImportError:
        prob = 1 - _approx_normal_sf(z)
    return min(0.85, max(0.40, prob))

def get_total_prob(projected_total, line, std, is_over):
    z = (line - projected_total) / max(std, 1)
    try:
        from scipy.stats import norm
        prob = norm.sf(z) if is_over else norm.cdf(z)
    except ImportError:
        prob = _approx_normal_sf(z) if is_over else (1 - _approx_normal_sf(z))
    return min(0.85, max(0.40, prob))


def identify_moneyline_picks(game_analysis):
    bets = []
    pred = game_analysis["prediction"]
    game = game_analysis["game"]

    for is_home in [True, False]:
        side = "home" if is_home else "away"
        opp = "away" if is_home else "home"
        prob = pred[f"{side}_win_prob"]
        team_abbr = game[f"{side}_team_abbr"]
        team_name = f"{game[f'{side}_team_city']} {game[f'{side}_team_name']}"
        
        if prob >= BET_TYPES["moneyline"]["min_probability"]:
            # Initial odds based on our probability
            odds = probability_to_decimal_odds(prob)
            
            bet = {
                "bet_id": f"{game['game_id']}_ml_{side}",
                "game_id": game["game_id"],
                "bet_type": "moneyline",
                "bet_label": f"{team_abbr} Moneyline",
                "bet_icon": BET_TYPES["moneyline"]["icon"],
                "team_abbr": team_abbr,
                "team_name": team_name,
                "is_home": is_home,
                "probability": round(prob, 3),
                "risk_level": assign_risk_level(prob),
                "american_odds": probability_to_american_odds(prob),
                "decimal_odds": odds,
                "expected_value": calculate_expected_value(prob, odds),
                "missing_players": pred.get(f"{opp}_missing_players", []),
            }
            bet["explanation"] = generate_bet_explanation(bet)
            bets.append(bet)
    return bets


def identify_point_spread_picks(game_analysis):
    bets = []
    pred = game_analysis["prediction"]
    game = game_analysis["game"]
    
    # predicted_spread positive means Home is favored
    pred_spread = pred["predicted_spread"]
    
    for is_home in [True, False]:
        side = "home" if is_home else "away"
        opp = "away" if is_home else "home"
        team_abbr = game[f"{side}_team_abbr"]
        team_name = f"{game[f'{side}_team_city']} {game[f'{side}_team_name']}"
        
        margin = pred_spread if is_home else -pred_spread
        
        # Fallback to a conservative alt-spread (giving 4.5 points of cushion)
        # Note: apply_live_odds will later override this with real market lines if available
        alt_line = round(-(margin - 4.5) * 2) / 2
        
        prob = get_spread_prob(margin, alt_line, std=12.5)
        
        if prob >= BET_TYPES["point_spread"]["min_probability"]:
            sign = "+" if alt_line > 0 else ""
            odds = probability_to_decimal_odds(prob)
            bet = {
                "bet_id": f"{game['game_id']}_spread_{side}",
                "game_id": game["game_id"],
                "bet_type": "point_spread",
                "bet_label": f"{team_abbr} {sign}{alt_line}",
                "bet_icon": BET_TYPES["point_spread"]["icon"],
                "team_abbr": team_abbr,
                "team_name": team_name,
                "is_home": is_home,
                "line": alt_line,
                "predicted_margin": margin,
                "probability": round(prob, 3),
                "risk_level": assign_risk_level(prob),
                "american_odds": probability_to_american_odds(prob),
                "decimal_odds": odds,
                "expected_value": calculate_expected_value(prob, odds),
                "missing_players": pred.get(f"{opp}_missing_players", []),
            }
            bet["explanation"] = generate_bet_explanation(bet)
            bets.append(bet)
    
    return bets


def identify_game_totals(game_analysis):
    bets = []
    game = game_analysis["game"]
    total_data = game_analysis["expected_total"]
    
    projected = total_data["expected_total"]
    std = total_data["total_std"]
    
    # Over computation
    over_line = round((projected - 0.5 * std) * 2) / 2
    over_prob = get_total_prob(projected, over_line, std, is_over=True)
    
    if over_prob >= BET_TYPES["game_total_over"]["min_probability"]:
        odds = probability_to_decimal_odds(over_prob)
        bet = {
            "bet_id": f"{game['game_id']}_gto",
            "game_id": game["game_id"],
            "bet_type": "game_total_over",
            "bet_label": f"Game Total O{over_line}",
            "bet_icon": BET_TYPES["game_total_over"]["icon"],
            "line": over_line,
            "projected_points": projected,
            "probability": round(over_prob, 3),
            "risk_level": assign_risk_level(over_prob),
            "american_odds": probability_to_american_odds(over_prob),
            "decimal_odds": odds,
            "expected_value": calculate_expected_value(over_prob, odds),
        }
        bet["explanation"] = generate_bet_explanation(bet)
        bets.append(bet)

    # Under computation
    under_line = round((projected + 0.5 * std) * 2) / 2
    under_prob = get_total_prob(projected, under_line, std, is_over=False)
    
    if under_prob >= BET_TYPES["game_total_under"]["min_probability"]:
        odds = probability_to_decimal_odds(under_prob)
        bet = {
            "bet_id": f"{game['game_id']}_gtu",
            "game_id": game["game_id"],
            "bet_type": "game_total_under",
            "bet_label": f"Game Total U{under_line}",
            "bet_icon": BET_TYPES["game_total_under"]["icon"],
            "line": under_line,
            "projected_points": projected,
            "probability": round(under_prob, 3),
            "risk_level": assign_risk_level(under_prob),
            "american_odds": probability_to_american_odds(under_prob),
            "decimal_odds": odds,
            "expected_value": calculate_expected_value(under_prob, odds),
        }
        bet["explanation"] = generate_bet_explanation(bet)
        bets.append(bet)
        
    return bets


def identify_first_half_bets(game_analysis):
    bets = []
    game = game_analysis["game"]
    fh = game_analysis["first_half_projection"]
    
    # First Half Spread
    for is_home in [True, False]:
        side = "home" if is_home else "away"
        team_abbr = game[f"{side}_team_abbr"]
        team_name = f"{game[f'{side}_team_city']} {game[f'{side}_team_name']}"
        
        margin = fh["predicted_spread"] if is_home else -fh["predicted_spread"]
        alt_line = round(-(margin - 2.5) * 2) / 2  # 2.5 pts cushion for half
        
        prob = get_spread_prob(margin, alt_line, std=6.5) # std dev is lower for half
        
        if prob >= BET_TYPES["first_half_spread"]["min_probability"]:
            sign = "+" if alt_line > 0 else ""
            bet = {
                "bet_id": f"{game['game_id']}_1h_spread_{side}",
                "game_id": game["game_id"],
                "bet_type": "first_half_spread",
                "bet_label": f"{team_abbr} 1H {sign}{alt_line}",
                "bet_icon": BET_TYPES["first_half_spread"]["icon"],
                "team_abbr": team_abbr,
                "team_name": team_name,
                "line": alt_line,
                "predicted_margin": margin,
                "probability": round(prob, 3),
                "risk_level": assign_risk_level(prob),
                "american_odds": probability_to_american_odds(prob),
                "decimal_odds": probability_to_decimal_odds(prob),
            }
            bet["explanation"] = generate_bet_explanation(bet)
            bets.append(bet)
            
    # First Half Totals
    projected = fh["expected_total"]
    std = fh["total_std"]
    
    over_line = round((projected - 0.5 * std) * 2) / 2
    over_prob = get_total_prob(projected, over_line, std, is_over=True)
    if over_prob >= BET_TYPES["first_half_total_over"]["min_probability"]:
        bet = {
            "bet_id": f"{game['game_id']}_1h_gto",
            "game_id": game["game_id"],
            "bet_type": "first_half_total_over",
            "bet_label": f"1H Total O{over_line}",
            "bet_icon": BET_TYPES["first_half_total_over"]["icon"],
            "line": over_line,
            "projected_points": projected,
            "probability": round(over_prob, 3),
            "risk_level": assign_risk_level(over_prob),
            "american_odds": probability_to_american_odds(over_prob),
            "decimal_odds": probability_to_decimal_odds(over_prob),
        }
        bet["explanation"] = generate_bet_explanation(bet)
        bets.append(bet)

    return bets


def get_all_bets_for_game(game_analysis):
    """Generate all individual Team Performance bets for a game."""
    all_bets = []
    all_bets.extend(identify_moneyline_picks(game_analysis))
    all_bets.extend(identify_point_spread_picks(game_analysis))
    all_bets.extend(identify_game_totals(game_analysis))
    all_bets.extend(identify_first_half_bets(game_analysis))
    
    # Filter to only low/med risk bets based on thresholds
    low_risk_bets = [b for b in all_bets if b["risk_level"] in ("low", "medium")]
    
    # Sort by probability descending
    low_risk_bets.sort(key=lambda x: x["probability"], reverse=True)
    return low_risk_bets

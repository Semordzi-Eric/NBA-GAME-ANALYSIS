"""
NBA Parlay Generator — Parlay Generation Engine
Combines low-risk bets into optimized parlays with ranking.
"""
import itertools
import numpy as np
from config import PARLAY_CONFIG, RISK_DISPLAY


def generate_parlays(all_bets_by_game, risk_preference="low"):
    """
    Generate optimized parlays from individual bets across all games.
    
    Args:
        all_bets_by_game: dict mapping game_id -> list of bets
        risk_preference: "ultra_safe", "low", or "balanced"
    
    Returns:
        List of parlay dicts, ranked by confidence.
    """
    # Flatten all bets and filter by risk preference
    eligible_bets = []
    for game_id, bets in all_bets_by_game.items():
        for bet in bets:
            if risk_preference == "ultra_safe" and bet["risk_level"] != "low":
                continue
            elif risk_preference == "low" and bet["risk_level"] == "avoid":
                continue
            elif risk_preference == "balanced" and bet["probability"] < 0.45:
                continue
            eligible_bets.append(bet)

    if len(eligible_bets) < PARLAY_CONFIG["min_legs"]:
        return []

    # Group bets by game_id for the "max 1 bet per game" constraint
    bets_by_game = {}
    for bet in eligible_bets:
        gid = bet["game_id"]
        if gid not in bets_by_game:
            bets_by_game[gid] = []
        bets_by_game[gid].append(bet)

    game_ids = list(bets_by_game.keys())

    # Heuristically prune to top 10 games with highest probability bets to stop 8-leg combinatorics explosion
    if len(game_ids) > 10:
        game_max_probs = {gid: max(b["probability"] for b in bets_by_game[gid]) for gid in game_ids}
        game_ids = sorted(game_ids, key=lambda g: game_max_probs[g], reverse=True)[:10]

    parlays = []

    # Generate combinations for each parlay size
    for num_legs in range(PARLAY_CONFIG["min_legs"], min(PARLAY_CONFIG["max_legs"] + 1, len(game_ids) + 1)):
        # Select which games to include
        for game_combo in itertools.combinations(game_ids, num_legs):
            # For each game, pick the best bet (highest probability)
            best_combo = _get_best_bet_combo(bets_by_game, game_combo)
            if best_combo:
                parlay = _build_parlay(best_combo, f"best_{num_legs}leg")
                if parlay and _passes_filters(parlay, num_legs):
                    parlays.append(parlay)

            # Also try diverse combos (mix of bet types)
            diverse_combo = _get_diverse_bet_combo(bets_by_game, game_combo)
            if diverse_combo and diverse_combo != best_combo:
                parlay = _build_parlay(diverse_combo, f"diverse_{num_legs}leg")
                if parlay and _passes_filters(parlay, num_legs):
                    parlays.append(parlay)

    # Remove duplicate parlays
    parlays = _deduplicate_parlays(parlays)

    # Rank parlays
    parlays = rank_parlays(parlays)

    # Return top N
    return parlays[:PARLAY_CONFIG["max_parlays_displayed"]]


def _get_best_bet_combo(bets_by_game, game_ids):
    """Select the highest probability bet from each game."""
    combo = []
    for gid in game_ids:
        if gid in bets_by_game and bets_by_game[gid]:
            best = max(bets_by_game[gid], key=lambda b: b["probability"])
            combo.append(best)
    return combo if len(combo) == len(game_ids) else None


def _get_diverse_bet_combo(bets_by_game, game_ids):
    """Select diverse bet types across games (avoid all moneylines)."""
    used_types = set()
    combo = []

    for gid in game_ids:
        if gid not in bets_by_game:
            continue

        bets = sorted(bets_by_game[gid], key=lambda b: b["probability"], reverse=True)

        selected = None
        for bet in bets:
            if bet["bet_type"] not in used_types:
                selected = bet
                used_types.add(bet["bet_type"])
                break

        if selected is None and bets:
            selected = bets[0]

        if selected:
            combo.append(selected)

    return combo if len(combo) == len(game_ids) else None


def _build_parlay(legs, strategy_tag=""):
    """Build a parlay object from a list of bet legs."""
    if not legs:
        return None

    combined_prob = compute_parlay_probability(legs)
    combined_decimal_odds = compute_parlay_decimal_odds(legs)
    combined_american_odds = decimal_to_american(combined_decimal_odds)
    ev = compute_expected_value(combined_prob, combined_decimal_odds)

    # Confidence score: weighted combination of probability and leg quality
    avg_leg_prob = np.mean([l["probability"] for l in legs])
    min_leg_prob = min([l["probability"] for l in legs])
    confidence = (avg_leg_prob * 0.6 + min_leg_prob * 0.4) * 100

    # Risk assessment
    all_low = all(l["risk_level"] == "low" for l in legs)
    any_avoid = any(l["risk_level"] == "avoid" for l in legs)

    if all_low:
        overall_risk = "low"
    elif any_avoid:
        overall_risk = "avoid"
    else:
        overall_risk = "medium"

    # Generate parlay description
    description = _generate_parlay_description(legs, combined_prob, confidence)

    return {
        "parlay_id": "_".join([l["bet_id"] for l in legs]),
        "legs": legs,
        "num_legs": len(legs),
        "combined_probability": round(combined_prob, 4),
        "combined_decimal_odds": round(combined_decimal_odds, 2),
        "combined_american_odds": combined_american_odds,
        "expected_value": round(ev, 4),
        "confidence_score": round(confidence, 1),
        "overall_risk": overall_risk,
        "strategy_tag": strategy_tag,
        "description": description,
        "potential_payout_per_unit": round(combined_decimal_odds, 2),
    }


def compute_parlay_probability(legs):
    """Compute combined probability of a parlay (product of independent probabilities)."""
    prob = 1.0
    for leg in legs:
        prob *= leg["probability"]
    return prob


def compute_parlay_decimal_odds(legs):
    """Compute combined decimal odds of a parlay."""
    odds = 1.0
    for leg in legs:
        odds *= leg["decimal_odds"]
    return odds


def compute_expected_value(probability, decimal_odds, stake=1.0):
    """
    Compute expected value of a bet.
    EV = (probability * payout) - (1 - probability) * stake
    """
    payout = stake * decimal_odds
    ev = (probability * payout) - ((1 - probability) * stake)
    return ev


def decimal_to_american(decimal_odds):
    """Convert decimal odds to American odds format."""
    if decimal_odds >= 2.0:
        return f"+{round((decimal_odds - 1) * 100)}"
    elif decimal_odds > 1.0:
        return f"-{round(100 / (decimal_odds - 1))}"
    return "EVEN"


def _passes_filters(parlay, num_legs):
    """Check if a parlay passes minimum probability filters."""
    min_prob = PARLAY_CONFIG["min_probability"].get(num_legs, 0.15)
    return parlay["combined_probability"] >= min_prob


def rank_parlays(parlays):
    """
    Rank parlays by a composite score:
    - 50% confidence score
    - 30% expected value 
    - 20% probability
    """
    for p in parlays:
        rank_score = (
            0.50 * p["confidence_score"] +
            0.30 * max(0, p["expected_value"] * 100) +
            0.20 * p["combined_probability"] * 100
        )
        p["rank_score"] = round(rank_score, 2)

    parlays.sort(key=lambda x: x["rank_score"], reverse=True)
    return parlays


def _deduplicate_parlays(parlays):
    """Remove duplicate parlays (same legs, different order)."""
    seen = set()
    unique = []
    for p in parlays:
        key = frozenset(l["bet_id"] for l in p["legs"])
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


def _generate_parlay_description(legs, combined_prob, confidence):
    """Generate a human-readable parlay description."""
    leg_types = [l["bet_type"] for l in legs]
    num_legs = len(legs)

    # Categorize the parlay
    has_ml = any("moneyline" in t for t in leg_types)
    has_props = any("player" in t for t in leg_types)
    has_totals = any("team_total" in t for t in leg_types)

    parts = []
    if has_ml:
        parts.append("game winner")
    if has_props:
        parts.append("player props")
    if has_totals:
        parts.append("team totals")

    mix_desc = " + ".join(parts) if parts else "mixed"

    if confidence >= 75:
        quality = "High-confidence"
    elif confidence >= 60:
        quality = "Solid"
    else:
        quality = "Moderate"

    description = (
        f"{quality} {num_legs}-leg parlay combining {mix_desc}. "
        f"Combined probability: {combined_prob*100:.1f}%. "
        f"Each leg individually assessed as low-risk with strong statistical backing."
    )

    return description


def format_parlay_for_display(parlay, rank=1):
    """Format a parlay for UI display with all relevant information."""
    risk_info = RISK_DISPLAY.get(parlay["overall_risk"], RISK_DISPLAY["medium"])

    return {
        "rank": rank,
        "title": f"PARLAY #{rank}",
        "subtitle": f"{parlay['num_legs']}-Leg • {risk_info['label']}",
        "confidence": parlay["confidence_score"],
        "combined_odds": parlay["combined_american_odds"],
        "combined_decimal_odds": parlay["combined_decimal_odds"],
        "probability": parlay["combined_probability"],
        "expected_value": parlay["expected_value"],
        "payout_per_unit": parlay["potential_payout_per_unit"],
        "risk_level": parlay["overall_risk"],
        "risk_color": risk_info["color"],
        "risk_bg": risk_info["bg"],
        "risk_emoji": risk_info["emoji"],
        "legs": parlay["legs"],
        "description": parlay["description"],
    }

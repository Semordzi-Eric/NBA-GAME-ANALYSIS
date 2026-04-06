import requests
import streamlit as st

def fetch_live_odds(api_key):
    """
    Fetch live NBA odds (ML, Spread, Totals) from The-Odds-API.
    Returns a dictionary mapping team names and game IDs to consensus market data.
    """
    if not api_key:
        return {}
        
    # Request multiple markets: h2h, spreads, totals
    url = f"https://api.the-odds-api.com/v4/sports/basketball_nba/odds/?apiKey={api_key}&regions=us&markets=h2h,spreads,totals&oddsFormat=decimal"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return _process_odds_data(data)
        else:
            st.warning(f"Odds API Error: {response.json().get('message', 'Unknown error')}")
            return {}
    except Exception as e:
        st.warning(f"Failed to fetch live odds: {str(e)}")
        return {}


def _process_odds_data(data):
    """
    Process multi-market data to find consensus (mean) lines and best odds.
    """
    market_map = {}
    
    for game in data:
        game_id = game.get("id")
        home_team = game.get("home_team")
        away_team = game.get("away_team")
        
        # Track all available lines for consensus
        h2h_home_prices = []
        h2h_away_prices = []
        spread_values = [] # Always relative to HOME team
        total_values = []
        
        for bookmaker in game.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                if market["key"] == "h2h":
                    for outcome in market.get("outcomes", []):
                        if outcome["name"] == home_team: h2h_home_prices.append(outcome["price"])
                        else: h2h_away_prices.append(outcome["price"])
                
                elif market["key"] == "spreads":
                    for outcome in market.get("outcomes", []):
                        # Use home team spread as the benchmark
                        if outcome["name"] == home_team:
                            spread_values.append(outcome["point"])
                
                elif market["key"] == "totals":
                    for outcome in market.get("outcomes", []):
                        # 'Over' line is the same as 'Under' line
                        if outcome["name"] == "Over":
                            total_values.append(outcome["point"])
                            
        # Aggregate consensus
        consensus = {
            "ml_home": round(np.mean(h2h_home_prices), 2) if h2h_home_prices else None,
            "ml_away": round(np.mean(h2h_away_prices), 2) if h2h_away_prices else None,
            "spread": round(np.mean(spread_values) * 2) / 2 if spread_values else None, # round to 0.5
            "total": round(np.mean(total_values) * 2) / 2 if total_values else None,
            "is_live": True
        }
        
        market_map[game_id] = consensus
        # Also map by team names for easier lookup in legacy functions
        market_map[home_team] = consensus
        market_map[away_team] = consensus
            
    return market_map

def apply_live_odds(bets, live_odds_map, team_abbr_to_name):
    """
    Inject real market context (ML, Spread, Total) into model-generated bets.
    """
    if not live_odds_map:
        return bets
        
    for bet in bets:
        team_abbr = bet.get("team_abbr")
        full_name = team_abbr_to_name.get(team_abbr)
        
        if full_name and full_name in live_odds_map:
            market = live_odds_map[full_name]
            from betting_intelligence import (
                get_spread_prob, get_total_prob, calculate_expected_value, 
                probability_to_decimal_odds
            )
            
            if bet["bet_type"] == "moneyline" and market["ml_home"]:
                is_home = bet.get("is_home", True)
                real_odds = market["ml_home"] if is_home else market["ml_away"]
                bet["decimal_odds"] = real_odds
                # Re-calculate EV with new odds
                bet["expected_value"] = calculate_expected_value(bet["probability"], real_odds)
            
            elif bet["bet_type"] == "point_spread" and market["spread"] is not None:
                is_home = bet.get("is_home", True)
                mkt_line = market["spread"] if is_home else -market["spread"]
                bet["line"] = mkt_line
                # Re-calculate probability based on market line
                margin = bet.get("predicted_margin", 0)
                new_prob = get_spread_prob(margin, mkt_line, std=12.5)
                bet["probability"] = round(new_prob, 3)
                # Re-calculate EV
                bet["expected_value"] = calculate_expected_value(new_prob, bet["decimal_odds"])
                
            elif "total" in bet["bet_type"] and market["total"] is not None:
                mkt_total = market["total"]
                bet["line"] = mkt_total
                # Re-calculate probability
                proj_pts = bet.get("projected_points", 0)
                is_over = "over" in bet["bet_type"]
                # Full game std is ~15
                new_prob = get_total_prob(proj_pts, mkt_total, std=15.0, is_over=is_over)
                bet["probability"] = round(new_prob, 3)
                # Re-calculate EV
                bet["expected_value"] = calculate_expected_value(new_prob, bet["decimal_odds"])
                
    return bets

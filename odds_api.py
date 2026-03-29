import requests
import streamlit as st

@st.cache_data(ttl=600, show_spinner=False)
def fetch_live_odds(api_key):
    """
    Fetch live NBA odds from The-Odds-API.
    Returns a dictionary mapping team names to their best moneyline decimal odds.
    """
    if not api_key:
        return {}
        
    url = f"https://api.the-odds-api.com/v4/sports/basketball_nba/odds/?apiKey={api_key}&regions=us&markets=h2h&oddsFormat=decimal"
    
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
    Extract best available decimal odds for each team from the bookmakers.
    """
    odds_map = {}
    
    for game in data:
        home_team = game.get("home_team")
        away_team = game.get("away_team")
        
        home_best = 0
        away_best = 0
        
        for bookmaker in game.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                if market["key"] == "h2h":
                    for outcome in market.get("outcomes", []):
                        team_name = outcome["name"]
                        price = outcome["price"]
                        
                        if team_name == home_team and price > home_best:
                            home_best = price
                        elif team_name == away_team and price > away_best:
                            away_best = price
                            
        if home_best > 0 and away_best > 0:
            odds_map[home_team] = home_best
            odds_map[away_team] = away_best
            
    return odds_map

def apply_live_odds(bets, live_odds_map, team_abbr_to_name):
    """
    Override the statistically estimated decimal odds with actual live odds.
    """
    if not live_odds_map:
        return bets
        
    for bet in bets:
        if bet["bet_type"] == "moneyline":
            team_abbr = bet.get("team_abbr")
            full_name = team_abbr_to_name.get(team_abbr)
            
            if full_name and full_name in live_odds_map:
                real_odds = live_odds_map[full_name]
                bet["decimal_odds"] = real_odds
                # Re-calculate implied probability based on live bookmaker odds
                # P = 1 / decimal_odds
                implied_prob = 1.0 / real_odds
                # Average our statistical prob with the implied prob
                blended_prob = (bet["probability"] + implied_prob) / 2
                bet["probability"] = round(blended_prob, 3)
                bet["explanation"] += f" (Live odds applied: {real_odds})"
                
    return bets

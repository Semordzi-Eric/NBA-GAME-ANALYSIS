import numpy as np
import pandas as pd
from analytics_engine import predict_game_outcome, compute_expected_total
from config import TEAM_STRENGTH_WEIGHTS

def test_rest_and_injury_logic():
    # Mock data
    home_team = {
        "strength_score": 80.0,
        "offensive_rating": 115.0,
        "defensive_rating": 110.0,
        "pace": 100.0,
        "recent_form": {"games_played": 10, "is_b2b": False},
        "is_home": True
    }
    
    away_team = {
        "strength_score": 75.0,
        "offensive_rating": 112.0,
        "defensive_rating": 112.0,
        "pace": 102.0,
        "recent_form": {"games_played": 10, "is_b2b": True}, # Away on B2B
        "is_home": False
    }

    home_players = [
        {"player_name": "Home Star", "impact_score": 85.0, "is_missing": False},
        {"player_name": "Home Role", "impact_score": 50.0, "is_missing": False}
    ]
    
    away_players = [
        {"player_name": "Away Star", "impact_score": 80.0, "is_missing": True}, # Missing Star
        {"player_name": "Away Role", "impact_score": 48.0, "is_missing": False}
    ]

    game = {
        "game_id": "TEST_001",
        "home_team_abbr": "HOM",
        "away_team_abbr": "AWY",
        "home_team_city": "Home City",
        "home_team_name": "Team",
        "away_team_city": "Away City",
        "away_team_name": "Team"
    }

    print("--- BASELINE ANALYSIS (MOCKED) ---")
    prediction = predict_game_outcome(home_team, away_team, home_players, away_players)
    total = compute_expected_total(home_team, away_team, home_players, away_players)

    print(f"Home Win Prob: {prediction['home_win_prob']:.3f}")
    print(f"Away Win Prob: {prediction['away_win_prob']:.3f}")
    print(f"Predicted Spread: {prediction['predicted_spread']}")
    print(f"Expected Total: {total['expected_total']}")
    print(f"Away Missing: {prediction['away_missing_players']}")
    
    # Simple assertions (qualitative)
    # Expected: Home favored more because Away is B2B and Missing Star
    assert prediction['home_win_prob'] > 0.6
    assert "Away Star (Star)" in prediction['away_missing_players']
    print("\n✅ Verification Successful: Rest and Injury factors are integrated.")

if __name__ == "__main__":
    test_rest_and_injury_logic()

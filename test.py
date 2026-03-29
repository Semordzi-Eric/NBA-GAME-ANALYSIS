from nba_api.stats.endpoints import scoreboardv2
import pandas as pd
import json

try:
    board = scoreboardv2.ScoreboardV2(game_date='2026-03-29')
    headers = board.get_data_frames()[0]
    line_score = board.get_data_frames()[1]
    
    games = []
    for _, row in headers.iterrows():
        game_id = str(row["GAME_ID"])
        game_teams = line_score[line_score["GAME_ID"] == game_id]
        if len(game_teams) != 2: continue
        
        home_id = str(row["HOME_TEAM_ID"])
        away_id = str(row["VISITOR_TEAM_ID"])
        
        home_team = game_teams[game_teams["TEAM_ID"] == int(home_id)].iloc[0]
        away_team = game_teams[game_teams["TEAM_ID"] == int(away_id)].iloc[0]
        
        games.append(f"{away_team['TEAM_ABBREVIATION']} @ {home_team['TEAM_ABBREVIATION']}")
        
    print("GAMES:", games)
except Exception as e:
    import traceback
    traceback.print_exc()

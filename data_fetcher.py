"""
NBA Parlay Generator — Data Fetcher
Handles all NBA API interactions with Streamlit caching.
"""
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import traceback

from config import CURRENT_SEASON, CACHE_TTL, RECENT_GAMES_WINDOW, PLAYER_GAMES_WINDOW


def _safe_api_call(func, *args, max_retries=3, delay=1.0, **kwargs):
    """Safely call NBA API with retry logic and rate limiting."""
    for attempt in range(max_retries):
        try:
            time.sleep(delay)  # Rate limiting
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(delay * (attempt + 1))
            else:
                st.warning(f"API call failed after {max_retries} attempts: {str(e)[:100]}")
                return None
    return None


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_games_for_date(target_date=None):
    """Fetch NBA games for a specific date from the scoreboard."""
    try:
        from nba_api.stats.endpoints import scoreboardv2
        from datetime import datetime
        import pytz

        # Get date string
        if target_date is None:
            tz = pytz.timezone('US/Eastern')
            target_date = datetime.now(tz).date()
            
        date_str = target_date.strftime('%Y-%m-%d')

        board = scoreboardv2.ScoreboardV2(game_date=date_str)
        headers = board.get_data_frames()[0]
        line_score = board.get_data_frames()[1]

        games = []
        for _, row in headers.iterrows():
            game_id = str(row.get("GAME_ID"))
            # Get teams from line_score
            game_teams = line_score[line_score["GAME_ID"] == game_id]
            if len(game_teams) != 2:
                continue
            
            home_id = str(row.get("HOME_TEAM_ID"))
            away_id = str(row.get("VISITOR_TEAM_ID"))
            
            home_team = game_teams[game_teams["TEAM_ID"] == int(home_id)].iloc[0]
            away_team = game_teams[game_teams["TEAM_ID"] == int(away_id)].iloc[0]

            games.append({
                "game_id": game_id,
                "game_status": int(row.get("GAME_STATUS_ID", 1)),
                "game_status_text": str(row.get("GAME_STATUS_TEXT", "")),
                "game_time_utc": "",
                "game_et": str(row.get("GAME_STATUS_TEXT", "")),
                "home_team_id": int(home_id),
                "home_team_abbr": str(home_team.get("TEAM_ABBREVIATION", "")),
                "home_team_name": str(home_team.get("TEAM_NAME", "")),
                "home_team_city": str(home_team.get("TEAM_CITY_NAME", "")),
                "home_score": int(home_team.get("PTS", 0)) if not pd.isna(home_team.get("PTS")) else 0,
                "home_wins": 0,
                "home_losses": 0,
                "away_team_id": int(away_id),
                "away_team_abbr": str(away_team.get("TEAM_ABBREVIATION", "")),
                "away_team_name": str(away_team.get("TEAM_NAME", "")),
                "away_team_city": str(away_team.get("TEAM_CITY_NAME", "")),
                "away_score": int(away_team.get("PTS", 0)) if not pd.isna(away_team.get("PTS")) else 0,
                "away_wins": 0,
                "away_losses": 0,
                "arena": str(row.get("ARENA_NAME", "")),
            })
        return games
    except Exception as e:
        st.error(f"Error fetching today's games: {e}")
        return []


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_team_game_log(team_id, season=CURRENT_SEASON, last_n=RECENT_GAMES_WINDOW):
    """Fetch recent game log for a team."""
    try:
        from nba_api.stats.endpoints import teamgamelog
        result = _safe_api_call(
            teamgamelog.TeamGameLog,
            team_id=team_id,
            season=season,
            season_type_all_star="Regular Season"
        )
        if result is None:
            return pd.DataFrame()

        df = result.get_data_frames()[0]
        if len(df) > last_n:
            df = df.head(last_n)
        return df
    except Exception as e:
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_team_full_game_log(team_id, season=CURRENT_SEASON):
    """Fetch full season game log for a team (for home/away splits)."""
    try:
        from nba_api.stats.endpoints import teamgamelog
        result = _safe_api_call(
            teamgamelog.TeamGameLog,
            team_id=team_id,
            season=season,
            season_type_all_star="Regular Season"
        )
        if result is None:
            return pd.DataFrame()
        return result.get_data_frames()[0]
    except Exception as e:
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_player_game_log(player_id, season=CURRENT_SEASON, last_n=PLAYER_GAMES_WINDOW):
    """Fetch recent game log for a player."""
    try:
        from nba_api.stats.endpoints import playergamelog
        result = _safe_api_call(
            playergamelog.PlayerGameLog,
            player_id=player_id,
            season=season,
            season_type_all_star="Regular Season"
        )
        if result is None:
            return pd.DataFrame()

        df = result.get_data_frames()[0]
        if len(df) > last_n:
            df = df.head(last_n)
        return df
    except Exception as e:
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_team_roster(team_id, season=CURRENT_SEASON):
    """Fetch current roster for a team."""
    try:
        from nba_api.stats.endpoints import commonteamroster
        result = _safe_api_call(
            commonteamroster.CommonTeamRoster,
            team_id=team_id,
            season=season
        )
        if result is None:
            return pd.DataFrame()
        return result.get_data_frames()[0]
    except Exception as e:
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_team_stats_advanced(team_id, season=CURRENT_SEASON):
    """Fetch advanced team stats (off/def rating, pace, etc.)."""
    try:
        from nba_api.stats.endpoints import teamdashboardbygeneralsplits
        result = _safe_api_call(
            teamdashboardbygeneralsplits.TeamDashboardByGeneralSplits,
            team_id=team_id,
            season=season,
            measure_type_detailed_defense="Advanced",
            season_type_all_star="Regular Season"
        )
        if result is None:
            return pd.DataFrame()
        return result.get_data_frames()[0]
    except Exception as e:
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_head_to_head(team_id, vs_team_id, season=CURRENT_SEASON):
    """Fetch head-to-head matchup history for current season."""
    try:
        from nba_api.stats.endpoints import leaguegamefinder
        result = _safe_api_call(
            leaguegamefinder.LeagueGameFinder,
            team_id_nullable=team_id,
            vs_team_id_nullable=vs_team_id,
            season_nullable=season,
            season_type_nullable="Regular Season"
        )
        if result is None:
            return pd.DataFrame()
        return result.get_data_frames()[0]
    except Exception as e:
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_league_standings(season=CURRENT_SEASON):
    """Fetch current league standings."""
    try:
        from nba_api.stats.endpoints import leaguestandings
        result = _safe_api_call(
            leaguestandings.LeagueStandings,
            season=season,
            season_type="Regular Season"
        )
        if result is None:
            return pd.DataFrame()
        return result.get_data_frames()[0]
    except Exception as e:
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_player_info(player_id):
    """Fetch player common info."""
    try:
        from nba_api.stats.endpoints import commonplayerinfo
        result = _safe_api_call(
            commonplayerinfo.CommonPlayerInfo,
            player_id=player_id
        )
        if result is None:
            return {}
        df = result.get_data_frames()[0]
        if len(df) > 0:
            return df.iloc[0].to_dict()
        return {}
    except Exception as e:
        return {}


def get_team_players_stats(team_id, season=CURRENT_SEASON):
    """Get player stats for a team to identify key players."""
    try:
        from nba_api.stats.endpoints import teamplayerdashboard
        result = _safe_api_call(
            teamplayerdashboard.TeamPlayerDashboard,
            team_id=team_id,
            season=season,
            season_type_all_star="Regular Season"
        )
        if result is None:
            return pd.DataFrame()
        # Index 1 is player stats (index 0 is team overall)
        dfs = result.get_data_frames()
        if len(dfs) > 1:
            return dfs[1]
        return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()


def generate_demo_games():
    """Generate realistic demo games when no live games are available."""
    demo_games = [
        {
            "game_id": "DEMO001",
            "game_status": 1,
            "game_status_text": "7:30 PM ET",
            "game_time_utc": "",
            "game_et": "7:30 PM ET",
            "home_team_id": 1610612738,
            "home_team_abbr": "BOS",
            "home_team_name": "Celtics",
            "home_team_city": "Boston",
            "home_score": 0,
            "home_wins": 52,
            "home_losses": 18,
            "away_team_id": 1610612748,
            "away_team_abbr": "MIA",
            "away_team_name": "Heat",
            "away_team_city": "Miami",
            "away_score": 0,
            "away_wins": 40,
            "away_losses": 30,
            "arena": "TD Garden",
        },
        {
            "game_id": "DEMO002",
            "game_status": 1,
            "game_status_text": "8:00 PM ET",
            "game_time_utc": "",
            "game_et": "8:00 PM ET",
            "home_team_id": 1610612749,
            "home_team_abbr": "MIL",
            "home_team_name": "Bucks",
            "home_team_city": "Milwaukee",
            "home_score": 0,
            "home_wins": 46,
            "home_losses": 24,
            "away_team_id": 1610612741,
            "away_team_abbr": "CHI",
            "away_team_name": "Bulls",
            "away_team_city": "Chicago",
            "away_score": 0,
            "away_wins": 33,
            "away_losses": 37,
            "arena": "Fiserv Forum",
        },
        {
            "game_id": "DEMO003",
            "game_status": 1,
            "game_status_text": "10:00 PM ET",
            "game_time_utc": "",
            "game_et": "10:00 PM ET",
            "home_team_id": 1610612747,
            "home_team_abbr": "LAL",
            "home_team_name": "Lakers",
            "home_team_city": "Los Angeles",
            "home_score": 0,
            "home_wins": 42,
            "home_losses": 28,
            "away_team_id": 1610612743,
            "away_team_abbr": "DEN",
            "away_team_name": "Nuggets",
            "away_team_city": "Denver",
            "away_score": 0,
            "away_wins": 50,
            "away_losses": 20,
            "arena": "Crypto.com Arena",
        },
        {
            "game_id": "DEMO004",
            "game_status": 1,
            "game_status_text": "10:30 PM ET",
            "game_time_utc": "",
            "game_et": "10:30 PM ET",
            "home_team_id": 1610612744,
            "home_team_abbr": "GSW",
            "home_team_name": "Warriors",
            "home_team_city": "Golden State",
            "home_score": 0,
            "home_wins": 38,
            "home_losses": 32,
            "away_team_id": 1610612760,
            "away_team_abbr": "OKC",
            "away_team_name": "Thunder",
            "away_team_city": "Oklahoma City",
            "away_score": 0,
            "away_wins": 55,
            "away_losses": 15,
            "arena": "Chase Center",
        },
    ]
    return demo_games

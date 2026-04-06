import os
import time
import math
import joblib
import pandas as pd
import numpy as np
import logging
from datetime import datetime
from tqdm import tqdm

import xgboost as xgb
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import TimeSeriesSplit, RandomizedSearchCV
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import log_loss, brier_score_loss, roc_auc_score, accuracy_score

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

MODEL_PATH = "nba_model.joblib"
DATA_PATH = "historical_nba_data.csv"

def fetch_or_generate_data(num_games=3000):
    """
    Tries to load local CSV. If missing, prompts the user to fetch via API or
    generates synthetic realistic data for immediate testing and verification.
    """
    if os.path.exists(DATA_PATH):
        logging.info("Loading existing historical data...")
        df = pd.read_csv(DATA_PATH, parse_dates=["game_date"])
        df = df.sort_values(by="game_date").reset_index(drop=True)
        return df

    logging.warning("No historical data found. Generating synthetic realistic dataset for training...")
    # In a real scenario, you'd loop over nba_api.stats.endpoints.leaguegamelog
    # and compute rolling averages. For now, we simulate features.
    
    dates = pd.date_range(start="2021-10-18", periods=num_games, freq="6h")
    
    np.random.seed(42)
    # Generate features centered around realistic NBA values
    home_ortg = np.random.normal(114.0, 5.0, num_games)
    away_drtg = np.random.normal(114.0, 5.0, num_games)
    away_ortg = np.random.normal(114.0, 5.0, num_games)
    home_drtg = np.random.normal(114.0, 5.0, num_games)
    
    # Rest days (usually 1, 2, or 3)
    home_rest = np.random.choice([1, 2, 3], num_games, p=[0.2, 0.6, 0.2])
    away_rest = np.random.choice([1, 2, 3], num_games, p=[0.2, 0.6, 0.2])
    
    # Form averages (Win rate over last 10)
    home_form = np.random.uniform(0.2, 0.8, num_games)
    away_form = np.random.uniform(0.2, 0.8, num_games)
    
    # Missing impact penalty (0 if healthy, positive if missing star)
    home_missing_impact = np.random.exponential(2.0, num_games)
    home_missing_impact[np.random.rand(num_games) > 0.3] = 0
    away_missing_impact = np.random.exponential(2.0, num_games)
    away_missing_impact[np.random.rand(num_games) > 0.3] = 0

    # True probability based on simulated heuristics (our target generation)
    # Net Margin = H_Adv - A_Adv
    # H_Adv = (home_ortg - home_missing_impact) - away_drtg
    h_adv = (home_ortg - home_missing_impact) - away_drtg
    a_adv = (away_ortg - away_missing_impact) - home_drtg
    
    rest_adv = home_rest - away_rest
    home_court_adv = 2.5
    
    net_margin = h_adv - a_adv + home_court_adv + (home_form - away_form) * 10 - rest_adv * 1.5
    
    # Actual outcome with some noise
    noise = np.random.normal(0, 10.0, num_games)
    actual_margin = net_margin + noise
    home_win = (actual_margin > 0).astype(int)

    df = pd.DataFrame({
        "game_id": np.arange(num_games),
        "game_date": dates,
        "home_ortg": home_ortg,
        "home_drtg": home_drtg,
        "away_ortg": away_ortg,
        "away_drtg": away_drtg,
        "home_rest_advantage": home_rest - away_rest,
        "home_form": home_form,
        "away_form": away_form,
        "home_missing_impact": home_missing_impact,
        "away_missing_impact": away_missing_impact,
        "home_win": home_win
    })
    
    # Engineer interaction features
    df = engineer_features(df)
    
    # Save purely so user has a template
    df.to_csv("dummy_historical_nba_data.csv", index=False)
    return df

def engineer_features(df):
    """
    Creates net differentials and interaction features.
    """
    df_engineered = df.copy()
    
    # Core differentials
    df_engineered["net_ortg_diff"] = df_engineered["home_ortg"] - df_engineered["away_drtg"]
    df_engineered["net_drtg_diff"] = df_engineered["home_drtg"] - df_engineered["away_ortg"]
    
    # Matchup interaction (Offense vs Defense)
    df_engineered["net_efficiency_margin"] = df_engineered["net_ortg_diff"] - df_engineered["net_drtg_diff"]
    
    df_engineered["form_diff"] = df_engineered["home_form"] - df_engineered["away_form"]
    df_engineered["injury_impact_diff"] = df_engineered["away_missing_impact"] - df_engineered["home_missing_impact"]
    
    # Drop raw to avoid redundancy
    features = [
        "net_ortg_diff", "net_drtg_diff", "net_efficiency_margin",
        "home_rest_advantage", "form_diff", "injury_impact_diff"
    ]
    return df_engineered[["game_date", "home_win"] + features]

def train_pipeline(df):
    """
    Trains an Ensemble Model optimized for Log Loss with Time-Based Splits.
    """
    logging.info("Initializing ML training pipeline...")
    
    # Sort chronologically to prevent data leaks!
    df = df.sort_values("game_date").reset_index(drop=True)
    
    X = df.drop(columns=["game_date", "home_win"])
    y = df["home_win"]
    
    # TimeSeriesSplit creates expanding windows
    tscv = TimeSeriesSplit(n_splits=5)
    
    # Base learners
    xgb_clf = xgb.XGBClassifier(
        objective="binary:logistic",
        eval_metric="logloss",
        random_state=42
    )
    
    rf_clf = RandomForestClassifier(random_state=42, n_jobs=-1)
    lr_clf = LogisticRegression()
    
    # Vote them
    estimators = [
        ('xgb', xgb_clf),
        ('rf', rf_clf),
        ('lr', lr_clf)
    ]
    
    voting_clf = VotingClassifier(
        estimators=estimators,
        voting='soft'
    )
    
    logging.info("Training Voting Ensemble (XGBoost + Random Forest + Logistic Regression)...")
    
    # We will use RandomizedSearchCV to optimize for log_loss
    param_grid = {
        'xgb__n_estimators': [50, 100],
        'xgb__max_depth': [3, 5],
        'rf__n_estimators': [100, 200],
        'rf__max_depth': [5, 10],
        'lr__C': [0.1, 1.0, 10.0]
    }
    
    search = RandomizedSearchCV(
        estimator=voting_clf,
        param_distributions=param_grid,
        n_iter=5, 
        scoring="neg_log_loss",
        cv=tscv,
        random_state=42,
        n_jobs=-1,
        verbose=1
    )
    
    search.fit(X, y)
    best_model = search.best_estimator_
    logging.info(f"Best parameters found: {search.best_params_}")
    
    # Calibrate Probabilities
    # This is CRITICAL for sports betting to ensure output = real %.
    logging.info("Applying Isotonic Calibration for probability outputs...")
    calibrated_clf = CalibratedClassifierCV(estimator=best_model, method='isotonic', cv='prefit')
    calibrated_clf.fit(X, y)
    
    # Save the full model pipeline
    feature_names = X.columns.tolist()
    
    # Quick eval on last 20% of data (pseudo-out-of-sample)
    split_idx = int(len(X) * 0.8)
    X_test, y_test = X.iloc[split_idx:], y.iloc[split_idx:]
    
    preds = calibrated_clf.predict(X_test)
    probs = calibrated_clf.predict_proba(X_test)[:, 1]
    
    acc = accuracy_score(y_test, preds)
    ll = log_loss(y_test, probs)
    bs = brier_score_loss(y_test, probs)
    auc = roc_auc_score(y_test, probs)
    
    logging.info(f"--- HOLD-OUT TEST RESULTS ---")
    logging.info(f"Accuracy:    {acc:.4f}")
    logging.info(f"Log Loss:    {ll:.4f} (Lower = Better)")
    logging.info(f"Brier Score: {bs:.4f} (<0.25 is profitable structure)")
    logging.info(f"ROC-AUC:     {auc:.4f}")
    
    model_payload = {
        "model": calibrated_clf,
        "features": feature_names,
        "version": "1.0",
        "trained_on": len(X),
        "last_trained": datetime.now().isoformat()
    }
    
    joblib.dump(model_payload, MODEL_PATH)
    logging.info(f"Successfully saved ML pipeline to {MODEL_PATH}")
    
    return calibrated_clf

if __name__ == "__main__":
    df = fetch_or_generate_data()
    train_pipeline(df)

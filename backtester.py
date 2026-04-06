import os
import joblib
import pandas as pd
import numpy as np
import logging
from sklearn.metrics import log_loss, brier_score_loss, roc_auc_score, accuracy_score
import matplotlib.pyplot as plt

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

MODEL_PATH = "nba_model.joblib"
DATA_PATH = "dummy_historical_nba_data.csv"

def load_data_and_model():
    if not os.path.exists(MODEL_PATH):
        logging.error("Model not found. Please run ml_pipeline.py first.")
        return None, None
        
    if not os.path.exists(DATA_PATH):
        logging.error("Historical data not found. Please run ml_pipeline.py first.")
        return None, None

    model_payload = joblib.load(MODEL_PATH)
    clf = model_payload["model"]
    feature_names = model_payload["features"]
    
    df = pd.read_csv(DATA_PATH, parse_dates=["game_date"])
    df = df.sort_values(by="game_date").reset_index(drop=True)
    
    return clf, df, feature_names

def run_backtest():
    clf, df, feature_names = load_data_and_model()
    if clf is None:
        return
        
    logging.info(f"Loaded model trained on {len(feature_names)} features.")
    
    # We will simulate a backtest on the final 20% of the dataset
    split_idx = int(len(df) * 0.8)
    test_df = df.iloc[split_idx:].copy()
    
    X_test = test_df[feature_names]
    y_test = test_df["home_win"].values
    
    logging.info(f"Running backtest on {len(test_df)} games...")
    
    # Generate Probabilities
    probs = clf.predict_proba(X_test)[:, 1]
    preds = clf.predict(X_test)
    
    test_df["predicted_home_win_prob"] = probs
    test_df["predicted_winner"] = preds
    test_df["correct"] = (test_df["predicted_winner"] == test_df["home_win"]).astype(int)
    
    # Core Evaluation Metrics
    acc = accuracy_score(y_test, preds)
    ll = log_loss(y_test, probs)
    bs = brier_score_loss(y_test, probs)
    auc = roc_auc_score(y_test, probs)
    
    logging.info(f"\n===== BACKTEST RESULTS =====")
    logging.info(f"Matches Evaluated:   {len(test_df)}")
    logging.info(f"Accuracy:            {acc:.4f}")
    logging.info(f"ROC-AUC:             {auc:.4f}")
    logging.info(f"Log Loss:            {ll:.4f}")
    logging.info(f"Brier Score:         {bs:.4f}")
    
    # Simulate Betting PnL (Flat betting on ML)
    # Assume 1 unit bet on home if prob > 50%, away otherwise.
    # We will assume standard -110 juice (implied prob 52.38%)
    # To be profitable on -110, we must hit >52.38%
    units = 0.0
    bets_placed = 0
    bets_won = 0
    
    for _, row in test_df.iterrows():
        is_home_bet = row["predicted_home_win_prob"] >= 0.5
        
        # Did our bet win?
        if (is_home_bet and row["home_win"] == 1) or (not is_home_bet and row["home_win"] == 0):
            units += 0.909  # Win 100 on 110 risk
            bets_won += 1
        else:
            units -= 1.000  # Lose 1 unit
        bets_placed += 1
        
    roi = (units / bets_placed) * 100 if bets_placed > 0 else 0
    
    logging.info(f"\n===== SIMULATED BETTING (Flat -110 ML) =====")
    logging.info(f"Bets Placed:         {bets_placed}")
    logging.info(f"Bets Won:            {bets_won} ({bets_won/bets_placed*100:.1f}%)")
    logging.info(f"Units Profit:        {units:+.2f} U")
    logging.info(f"R.O.I.:              {roi:+.2f}%")
    
    # Plotting calibration and performance
    plot_calibration(y_test, probs)

def plot_calibration(y_true, y_prob, bins=10):
    """Generates a crude calibration output in console, and a matplot if run visually."""
    try:
        from sklearn.calibration import calibration_curve
        prob_true, prob_pred = calibration_curve(y_true, y_prob, n_bins=bins)
        
        logging.info("\n===== CALIBRATION CHECK =====")
        logging.info("Model_Prob | Actual_Win%")
        for p_pred, p_true in zip(prob_pred, prob_true):
            logging.info(f"{p_pred*100:>8.1f}% | {p_true*100:>10.1f}%")
        
        # Save plot
        plt.figure(figsize=(8, 6))
        plt.plot(prob_pred, prob_true, marker='o', label="Stacked Ensemble")
        plt.plot([0, 1], [0, 1], linestyle='--', color='gray', label="Perfectly Calibrated")
        plt.xlabel("Predicted Probability")
        plt.ylabel("Actual Win Fraction")
        plt.title("Reliability Diagram (Calibration Curve)")
        plt.legend()
        plt.grid(True)
        plt.savefig("calibration_curve.png")
        logging.info("\nSaved calibration plot to calibration_curve.png")
        
    except Exception as e:
        logging.warning(f"Could not generate plot: {e}")

if __name__ == "__main__":
    run_backtest()

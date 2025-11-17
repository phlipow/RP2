import numpy as np
from sklearn.metrics import f1_score, roc_auc_score, precision_recall_curve

def get_f1_score(X_test, y_test, model):
    y_pred = model.predict(X_test)
    return f1_score(y_test, y_pred)

def get_auroc(X_test, y_test, model):
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    return roc_auc_score(y_test, y_pred_proba)

def find_best_threshold(model, X, y):
    """
    Finds the best threshold to maximize the F1-score using precision-recall curve.
    """
    y_pred_proba = model.predict_proba(X)[:, 1]
    precision, recall, thresholds = precision_recall_curve(y, y_pred_proba)
    
    # The last precision and recall values are 1. and 0. respectively.
    # The F1 score for this point is 0, and there is no corresponding threshold.
    # So we slice the arrays to exclude this point.
    precision = precision[:-1]
    recall = recall[:-1]

    # Calculate F1 score for each threshold
    f1_scores = np.divide(2 * precision * recall, precision + recall, out=np.zeros_like(precision), where=(precision + recall) != 0)
    
    if len(f1_scores) == 0:
        return 0.5

    # Find the best threshold
    best_threshold_index = np.argmax(f1_scores)
    best_threshold = thresholds[best_threshold_index]
    
    return best_threshold

def get_f1_score_with_threshold(X_test, y_test, model, threshold):
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    y_pred = (y_pred_proba >= threshold).astype(int)
    return f1_score(y_test, y_pred)

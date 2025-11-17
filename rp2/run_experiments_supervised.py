from main_supervised import run_model_supervised
import pandas as pd

def run_experiments():
    results = []
    for num_chars in [1, 2, 3, 4]:
        print(f"--- Running experiment for num_chars = {num_chars} ---")
        result = run_model_supervised(num_chars)
        results.append(result)
        print(f"--- Finished experiment for num_chars = {num_chars} ---")

    df_results = pd.DataFrame(results)
    print("\n--- Supervised Experiment Results ---")
    print(df_results)

    best_f1_svm = df_results.loc[df_results['f1_svm'].idxmax()]
    best_f1_rf = df_results.loc[df_results['f1_rf'].idxmax()]
    best_auroc_svm = df_results.loc[df_results['auroc_svm'].idxmax()]
    best_auroc_rf = df_results.loc[df_results['auroc_rf'].idxmax()]

    print("\n--- Best Settings (Supervised) ---")
    print(f"Best F1-Score SVM: {best_f1_svm['f1_svm']:.4f} (num_chars = {best_f1_svm['num_chars']})")
    print(f"Best F1-Score RF: {best_f1_rf['f1_rf']:.4f} (num_chars = {best_f1_rf['num_chars']})")
    print(f"Best AUROC SVM: {best_auroc_svm['auroc_svm']:.4f} (num_chars = {best_auroc_svm['num_chars']})")
    print(f"Best AUROC RF: {best_auroc_rf['auroc_rf']:.4f} (num_chars = {best_auroc_rf['num_chars']})")

if __name__ == '__main__':
    run_experiments()

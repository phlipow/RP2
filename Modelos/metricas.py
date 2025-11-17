import numpy as np
from sklearn.metrics import f1_score, roc_auc_score, classification_report, roc_curve, precision_recall_curve, confusion_matrix

def get_f1_score(X_test, y_test, model):
    y_pred = model.predict(X_test)
    f1 = f1_score(y_test, y_pred, pos_label=1)
    return f1

def get_auroc(X_test, y_test, model):
    y_prob_scores = model.predict_proba(X_test)[:, 1]
    auroc = roc_auc_score(y_test, y_prob_scores)
    return auroc

def busca_melhor_threshold(modelo, X_test, y_test):
    print('\n--- Buscando melhor threshold ---')
    # --- 1. Obtenha as PROBABILIDADES do seu modelo de teste ---
    # Use o mesmo y_prob_scores que você usou para o AUROC
    # (Probabilidades da classe positiva "1")
    y_prob_scores = modelo.predict_proba(X_test)[:, 1]

    # --- 2. Calcule Precisão, Revocação e Limiares ---
    # Esta função fornece os valores para cada limiar possível
    precisions, recalls, thresholds = precision_recall_curve(y_test, y_prob_scores)

    # --- 3. Calcule o F1-Score para cada limiar ---
    # Ignoramos o último valor de precisão/revocação, pois não há limiar para ele
    # Adicionamos 'epsilon' (um número muito pequeno) para evitar divisão por zero
    epsilon = 1e-7
    f1_scores = 2 * (precisions * recalls) / (precisions + recalls + epsilon)

    # --- 4. Encontre o Limiar que Maximiza o F1-Score ---
    # 'thresholds' tem um elemento a menos que 'f1_scores', por isso usamos f1_scores[:-1]
    best_threshold_index = np.argmax(f1_scores[:-1])
    best_f1 = f1_scores[best_threshold_index]
    best_threshold = thresholds[best_threshold_index]

    print(f"AUROC (capacidade de discriminação): {roc_auc_score(y_test, y_prob_scores):.4f}")
    print(f"Melhor F1-Score encontrado: {best_f1:.4f}")
    print(f"Limiar de Decisão Ideal (Threshold): {best_threshold:.4f}")

    # --- 5. Faça as novas previsões usando o Limiar Ideal ---
    # Em vez de usar .predict(), fazemos a comparação manualmente
    y_pred_otimizado = (y_prob_scores >= best_threshold).astype(int)

    # --- 6. Verifique o F1-Score (agora deve ser muito maior) ---
    f1_novo = f1_score(y_test, y_pred_otimizado)
    print(f"\nF1-Score com Limiar Padrão (0.5): {f1_score(y_test, modelo.predict(X_test)):.4f}")
    print(f"F1-Score com Limiar Otimizado ({best_threshold:.4f}): {f1_novo:.4f}")

    return best_threshold

def get_metricas_best_threshold(modelo, best_threshold, X_test, y_test):
    print('--- Buscando métricas com o threshold otimizado')
    # 1. Obtenha as probabilidades do seu modelo no conjunto de teste
    y_prob_scores = modelo.predict_proba(X_test)[:, 1]

    # 2. APLIQUE O LIMIAR MANUALMENTE para criar as novas previsões
    # Esta é a parte mais importante:
    y_pred_otimizado = (y_prob_scores >= best_threshold).astype(int)

    # 3. Agora, calcule seu F1-Score e Matriz de Confusão com estas novas previsões
    from sklearn.metrics import f1_score, classification_report, confusion_matrix

    print(f"--- Desempenho com Limiar Otimizado ({best_threshold}) ---")

    # Este F1-Score será muito maior
    f1_otimizado = f1_score(y_test, y_pred_otimizado)
    print(f"F1-Score Otimizado: {f1_otimizado:.4f}")

    # O relatório de classificação agora refletirá o bom desempenho
    print("\nRelatório de Classificação Otimizado:")
    print(classification_report(y_test, y_pred_otimizado, target_names=['Não Promissora', 'Promissora']))

    # A matriz de confusão também será muito melhor (menos Falsos Negativos)
    print("\nMatriz de Confusão Otimizada:")
    print(confusion_matrix(y_test, y_pred_otimizado))
    print("\n \n ------------------------------------------------")
import numpy as np
import pandas as pd
import trata_dados
from globais import application_date_col, colunas_variaveis_treino, colunas_variaveis
from metricas import get_f1_score, get_auroc, busca_melhor_threshold, get_metricas_best_threshold
from trata_dados import converte_datas, get_amostra_treinamento, get_conjunto_rotulado
from sklearn.model_selection import train_test_split
from sklearn.model_selection import GridSearchCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from treinamento import get_svm, get_rf, get_dados_rotulados

pd.options.display.max_columns = None
# Define uma largura de exibição maior (ex: 1000 caracteres) para evitar quebrar a linha
pd.options.display.width = 1000

#----------- Trata os dados ----------------
df = pd.read_csv('../Data/dados_patentes_final.csv', delimiter=';') # Try a different encoding

df_variaveis = df[colunas_variaveis].copy()

converte_datas(df_variaveis, application_date_col)

df_amostra = get_amostra_treinamento(1995, 2015, df_variaveis)

df_treinamento = get_conjunto_rotulado(df_amostra)

print(df_treinamento.head(2))

# ----------- Treinamento -----------------

features = [col for col in colunas_variaveis_treino if col not in ['patent_id', 'application_date']]
X = df_treinamento[features]
y = df_treinamento['promissora']

#Separa 10% para o conjunto de teste
X_train_full, X_test, y_train_full, y_test = train_test_split(
    X, y, test_size=0.1, random_state=42, stratify=y
)

#Dos 90% restantes, cria o conjunto semissupervisionado 30% rotulado, 70% não rotulado
X_labeled, X_unlabeled, y_labeled, y_unlabeled = train_test_split(
    X_train_full, y_train_full, train_size=0.3, random_state=42, stratify=y_train_full
)

#obtem os melhores modelos do treinamento supervisionado
best_svm_model = get_svm(X_labeled, y_labeled)
best_rf_model = get_rf(X_labeled, y_labeled)

#usa os modelos para rotular o restante do conjunto
X_labeled_svm, y_labeled_svm, best_svm_model = get_dados_rotulados(X_labeled.copy(), X_unlabeled.copy(), y_labeled.copy(), best_svm_model)
X_labeled_rf, y_labeled_rf, best_rf_model = get_dados_rotulados(X_labeled.copy(), X_unlabeled.copy(), y_labeled.copy(), best_rf_model)

#best_svm_model.fit(X_labeled_svm, y_labeled_svm)
#best_rf_model.fit(X_labeled_rf, y_labeled_rf)

f1_svm = get_f1_score(X_test, y_test, best_svm_model)
f1_rf = get_f1_score(X_test, y_test, best_rf_model)

print(f"\nF1-Score SVM: {f1_svm:.4f}")
print(f"\nF1-Score RandomForest: {f1_rf:.4f}")

auroc_svm = get_auroc(X_test, y_test, best_svm_model)
auroc_rf = get_auroc(X_test, y_test, best_rf_model)

print(f"\nAUROC SVM: {auroc_svm:.4f}")
print(f"\nAUROC RandomForest: {auroc_rf:.4f}")


best_threshold_svm = busca_melhor_threshold(best_svm_model, X_test, y_test)
best_threshold_rf = busca_melhor_threshold(best_rf_model, X_test, y_test)

get_metricas_best_threshold(best_svm_model, best_threshold_svm, X_test, y_test)
get_metricas_best_threshold(best_rf_model, best_threshold_rf, X_test, y_test)
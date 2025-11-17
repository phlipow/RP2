
import numpy as np
import pandas as pd
from globais import application_date_col, colunas_variaveis_treino, colunas_variaveis
from metricas import get_f1_score, get_auroc, find_best_threshold, get_f1_score_with_threshold
from trata_dados import converte_datas, get_amostra_treinamento, get_conjunto_rotulado
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from treinamento import get_svm, get_rf, get_dados_rotulados

def run_model(num_chars):
    #----------- Trata os dados ----------------
    df = pd.read_csv('dados_patentes_final.csv', delimiter=';')
    df_variaveis = df[colunas_variaveis].copy()

    converte_datas(df_variaveis, application_date_col)

    min_year = df_variaveis['application_date'].dt.year.min()
    df_amostra = get_amostra_treinamento(min_year, 2015, df_variaveis)
    df_treinamento = get_conjunto_rotulado(df_amostra)

    #----------- Adiciona features de IPC ----------------
    df_ipc = pd.read_csv(f'patent_ipc_classes_{num_chars}.csv')
    
    # One-hot encoding
    ipc_dummies = pd.get_dummies(df_ipc['ipc_class'], prefix=f'ipc_{num_chars}')
    df_ipc = pd.concat([df_ipc['patent_id'], ipc_dummies], axis=1)
    df_ipc = df_ipc.groupby('patent_id').sum().reset_index()

    # Merge com o dataframe principal
    df_treinamento = pd.merge(df_treinamento, df_ipc, on='patent_id', how='left')
    df_treinamento.fillna(0, inplace=True)


    # ----------- Treinamento -----------------
    features = [col for col in df_treinamento.columns if col not in ['patent_id', 'application_date', 'promissora']]
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
    X_labeled_svm, y_labeled_svm = get_dados_rotulados(X_labeled.copy(), X_unlabeled.copy(), y_labeled.copy(), best_svm_model)
    X_labeled_rf, y_labeled_rf = get_dados_rotulados(X_labeled.copy(), X_unlabeled.copy(), y_labeled.copy(), best_rf_model)

    best_svm_model.fit(X_labeled_svm, y_labeled_svm)
    best_rf_model.fit(X_labeled_rf, y_labeled_rf)

    # Encontra o melhor threshold no conjunto de treinamento
    best_threshold_svm = find_best_threshold(best_svm_model, X_train_full, y_train_full)
    best_threshold_rf = find_best_threshold(best_rf_model, X_train_full, y_train_full)

    f1_svm = get_f1_score_with_threshold(X_test, y_test, best_svm_model, best_threshold_svm)
    f1_rf = get_f1_score_with_threshold(X_test, y_test, best_rf_model, best_threshold_rf)

    auroc_svm = get_auroc(X_test, y_test, best_svm_model)
    auroc_rf = get_auroc(X_test, y_test, best_rf_model)

    return {
        "num_chars": num_chars,
        "f1_svm": f1_svm,
        "f1_rf": f1_rf,
        "auroc_svm": auroc_svm,
        "auroc_rf": auroc_rf
    }

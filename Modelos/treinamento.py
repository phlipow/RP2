import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GridSearchCV
from sklearn.svm import SVC


def get_svm(X, y):
    print('\n--- Buscando melhor modelo SVM ---')
    param_grid = {
        'C': [0.1, 1, 10, 100, 1000],
        'gamma': [1, 0.1, 0.01, 0.001, 0.0001],
        'kernel': ['rbf'],  # Mantemos o kernel radial
        'class_weight': ['balanced']
    }

    grid_search = GridSearchCV(
        estimator=SVC(probability=True),
        param_grid=param_grid,
        refit=True,  # refit=True retreina o melhor modelo com todos os dados no final
        scoring='f1',  # vai otimizar para f1 score
        cv=5, #validação cruzada de 5 partes (k-fold)
        #verbose=2,  # Mostra o progresso
    )

    grid_search.fit(X, y)

    return grid_search.best_estimator_

def get_rf(X, y):
    print('\n--- Buscando melhor modelo Random Forest ---')
    param_grid_rf = {
        'n_estimators': [100, 200, 300],  # Número de árvores
        'max_depth': [10, 20, None],  # Profundidade máxima (None = sem limite)
        'min_samples_leaf': [1, 2, 4],  # Mínimo de amostras em um nó "folha"
        'bootstrap': [True],  # Usar amostragem com reposição
        'class_weight': ['balanced']
    }

    grid_search_rf = GridSearchCV(
        estimator=RandomForestClassifier(random_state=42),
        param_grid=param_grid_rf,
        refit=True,
        scoring='f1',
        cv=5,
        #n_jobs=-1,
        # verbose=2
    )

    grid_search_rf.fit(X, y)

    return grid_search_rf.best_estimator_

def get_dados_rotulados(X_labeled, X_unlabeled, y_labeled, model):

    print('\n--- Iniciando Rotulagem dos dados utilizado o modelo --- ')
    while len(X_unlabeled) > 0:
        # Preveja as probabilidades nos dados não rotulados restantes
        probas = model.predict_proba(X_unlabeled)

        # Defina um limiar de confiança (ex: 90%)
        threshold = 0.90

        # Encontre os índices das previsões altamente confiantes
        confident_indices = np.where(np.max(probas, axis=1) >= threshold)[0]

        # Se não houver mais previsões confiantes, pare o loop
        if len(confident_indices) == 0:
            break

        # Pegue os pseudo-rótulos
        pseudo_labels = model.predict(X_unlabeled.iloc[confident_indices])

        #Adicione os dados pseudo-rotulados ao conjunto de treinamento
        X_labeled = pd.concat([X_labeled, X_unlabeled.iloc[confident_indices]])
        y_labeled = pd.concat([y_labeled, pd.Series(pseudo_labels, index=X_unlabeled.iloc[confident_indices].index)])

        # Remova esses dados do conjunto não rotulado
        X_unlabeled = X_unlabeled.drop(X_unlabeled.iloc[confident_indices].index)

        model.fit(X_labeled, y_labeled)

    return X_labeled, y_labeled, model

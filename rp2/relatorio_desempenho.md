# Relatório de Desempenho dos Modelos de Machine Learning

## 1. Objetivo

O objetivo deste relatório é apresentar o desempenho dos modelos de Machine Learning (SVM e Random Forest) na tarefa de prever patentes promissoras.

## 2. Metodologia

Foram utilizados dois modelos de classificação: Support Vector Machine (SVM) e Random Forest. O treinamento foi realizado utilizando uma abordagem de aprendizado semissupervisionado. Para lidar com o desbalanceamento de classes, foi aplicada uma técnica de ajuste do limiar de classificação para otimizar o F1-Score.

A definição de "patente promissora" para esta análise foi baseada no arquivo `patents_with_newer_ipc.csv`. As patentes deste arquivo foram convertidas para o formato do Google Patents antes de serem utilizadas.

## 3. Conjunto de Dados

- **Fonte das patentes promissoras:** `patents_with_newer_ipc.csv`
- **Total de patentes no conjunto de treinamento:** 4115
- **Número de patentes promissoras:** 397 (~9.6%)

## 4. Resultados

Após o treinamento e otimização, os modelos apresentaram os seguintes resultados no conjunto de teste:

### 4.1. Support Vector Machine (SVM)

- **Melhor Limiar de Classificação:** 0.1745
- **F1-Score:** 0.4384
- **AUROC:** 0.8004

### 4.2. Random Forest

- **Melhor Limiar de Classificação:** 0.2791
- **F1-Score:** 0.5814
- **AUROC:** 0.9117

## 5. Conclusão

Ambos os modelos apresentaram uma melhora significativa no F1-Score após a utilização de um conjunto de dados mais balanceado e a otimização do limiar de classificação.

O modelo **Random Forest** obteve o melhor desempenho geral, com um F1-Score de 0.5814 e um AUROC de 0.9117, indicando uma excelente capacidade de discriminar entre patentes promissoras e não promissoras.

## 6. Experimento com diferentes níveis de agregação de IPCs

Foi conduzido um experimento para avaliar o impacto do nível de agregação dos códigos IPC (International Patent Classification) no desempenho dos modelos. Foram testadas agregações com 1, 2, 3 e 4 caracteres.

### 6.1. Resultados do Experimento

A tabela abaixo resume os resultados de F1-Score e AUROC para cada modelo e nível de agregação:

| Nível (num_chars) | F1-Score SVM | F1-Score RF | AUROC SVM | AUROC RF |
| :--- | :--- | :--- | :--- | :--- |
| 1 | 0.4058 | 0.6118 | 0.8581 | 0.8947 |
| 2 | 0.4865 | 0.6087 | 0.8317 | 0.9177 |
| 3 | 0.5278 | 0.6667 | 0.8331 | 0.9176 |
| 4 | 0.4590 | 0.6154 | 0.8140 | 0.9153 |

### 6.2. Análise dos Resultados

-   **Random Forest (RF) consistentemente superou o Support Vector Machine (SVM)** em ambas as métricas (F1-Score e AUROC) para todos os níveis de agregação testados.
-   O **melhor F1-Score geral (0.6667)** foi alcançado pelo modelo Random Forest com o nível de agregação de **3 caracteres**.
-   O **melhor AUROC geral (0.9177)** foi alcançado pelo modelo Random Forest com o nível de agregação de **2 caracteres**.

### 6.3. Conclusão do Experimento

O experimento demonstrou que o nível de agregação dos códigos IPC é um hiperparâmetro importante. O modelo **Random Forest com 3 caracteres de IPC** apresentou o melhor equilíbrio entre precisão e recall, conforme indicado pelo F1-Score, sendo considerado o modelo de melhor desempenho para esta tarefa.

## 7. Experimento com Aprendizado Supervisionado Puro

Para comparar com a abordagem semissupervisionada, foi realizado um experimento utilizando uma abordagem de aprendizado puramente supervisionado. Neste caso, os modelos foram treinados com todo o conjunto de dados de treinamento (90% do total), sem a etapa de pseudo-rotulagem.

### 7.1. Resultados do Experimento Supervisionado

| Nível (num_chars) | F1-Score SVM | F1-Score RF | AUROC SVM | AUROC RF |
| :--- | :--- | :--- | :--- | :--- |
| 1 | 0.4124 | 0.6400 | 0.8558 | 0.9118 |
| 2 | 0.4400 | 0.6567 | 0.8103 | 0.9312 |
| 3 | 0.5000 | 0.3333 | 0.8384 | 0.9310 |
| 4 | 0.5610 | 0.3673 | 0.8940 | 0.9317 |

### 7.2. Comparação: Supervisionado vs. Semissupervisionado

| Modelo | Métrica | Melhor Resultado Supervisionado | Melhor Resultado Semissupervisionado |
| :--- | :--- | :--- | :--- |
| Random Forest | F1-Score | 0.6567 (`num_chars=2`) | **0.6667 (`num_chars=3`)** |
| Random Forest | AUROC | **0.9317 (`num_chars=4`)** | 0.9177 (`num_chars=2`) |
| SVM | F1-Score | **0.5610 (`num_chars=4`)** | 0.5278 (`num_chars=3`) |
| SVM | AUROC | **0.8940 (`num_chars=4`)** | 0.8581 (`num_chars=1`) |

### 7.3. Conclusão da Comparação

-   O modelo **Random Forest com abordagem semissupervisionada** ainda apresenta o **melhor F1-Score geral (0.6667)**, que é uma métrica crucial para este problema de classes desbalanceadas.
-   A abordagem **puramente supervisionada** obteve **melhores resultados de AUROC** para ambos os modelos, e um F1-Score superior para o modelo SVM.
-   A diferença de desempenho no F1-Score do Random Forest entre as duas abordagens é pequena.

Considerando a importância do F1-Score, o modelo **Random Forest treinado com a abordagem semissupervisionada e agregação de 3 caracteres de IPC** continua sendo a melhor escolha. No entanto, a abordagem supervisionada se mostrou competitiva, especialmente em termos de AUROC.

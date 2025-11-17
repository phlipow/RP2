import pandas as pd
import numpy as np

def converte_datas(df, date_col):
    print(f"Tipo de dados original da coluna 'application_date': {df['application_date'].dtype}")
    if not pd.api.types.is_datetime64_ns_dtype(df['application_date']):

        print("Convertendo a coluna 'application_date' para datetime...")

        df['application_date'] = pd.to_datetime(df['application_date'], errors='coerce', dayfirst=True)
        #remove linhas onde a data não pôde ser convertida
        df.dropna(subset=['application_date'], inplace=True)

        print("Conversão concluída.")

def get_amostra_treinamento(ano_inicio, ano_fim, df):

    mascara_treinamento = (df['application_date'].dt.year >= ano_inicio) & (df['application_date'].dt.year <= ano_fim)

    df_filtrado =  df[mascara_treinamento].copy()

    print("\n--- Resultados da Filtragem ---")
    print(f"Total de patentes no conjunto completo: {len(df)}")
    print(f"Total de patentes no conjunto de treinamento (2005-2015): {len(df_filtrado)}")

    if not df_filtrado.empty:
        print(f"Data mínima no conjunto de treinamento: {df_filtrado['application_date'].min().strftime('%Y-%m-%d')}")
        print(f"Data máxima no conjunto de treinamento: {df_filtrado['application_date'].max().strftime('%Y-%m-%d')}")
    else:
        print("Nenhuma patente encontrada no período especificado.")

    return df_filtrado

def get_conjunto_rotulado(df):

    print("Iniciando a rotulagem de patentes promissoras...")

    # --- Etapa 1: Usar a coluna 'foward_citations_count' para criar o limiar ---
    limiar_por_ano = df.groupby(df['application_date'].dt.year)[
        'foward_citations_count'].transform('quantile', 0.9)

    # --- Etapa 2: Usar a coluna para criar o rótulo 'promissora' ---
    df['promissora'] = (df['foward_citations_count'] >= limiar_por_ano).astype(int)

    # --- Etapa 3: REMOVER a coluna para evitar vazamento de dados ---
    df.drop(columns=['foward_citations_count'], inplace=True)

    # --- Etapa 4: Verificação da Rotulagem (como você já tinha) ---
    import pandas as pd

    # Supondo que 'df' e 'application_date' já existem e estão formatados

    # --- 1. Verificação Total (Absoluta e Proporcional) ---
    print("\n--- Resultados da Rotulagem (Contagem Total) ---")
    print("Contagem Absoluta de 'promissora':")
    contagem_abs = df['promissora'].value_counts()
    contagem_abs.index = contagem_abs.index.map({1: 'Promissoras (1)', 0: 'Não Promissoras (0)'})
    print(contagem_abs)

    print("\nProporção Total de 'promissora':")
    contagem_prop = df['promissora'].value_counts(normalize=True)
    contagem_prop.index = contagem_prop.index.map({1: 'Promissoras (1)', 0: 'Não Promissoras (0)'})
    print(contagem_prop.apply(lambda x: f"{x:.2%}"))  # Formata como porcentagem
    print("-" * 50)

    # --- 2. Verificação Detalhada por Ano (Absoluta e Proporcional) ---
    print("\nVerificando a contagem e proporção de patentes por ano:")

    # Criamos uma coluna temporária 'ano'
    df['ano'] = df['application_date'].dt.year

    # Modificamos a agregação para incluir 'mean' (que é a proporção)
    # 'sum' == total de promissoras (valor 1)
    # 'count' == total de patentes
    # 'mean' == proporção de promissoras (sum / count)
    verificacao_anual = df.groupby('ano')['promissora'].agg(['sum', 'count', 'mean'])

    # Calculamos as 'nao_promissoras'
    verificacao_anual['nao_promissoras_count'] = verificacao_anual['count'] - verificacao_anual['sum']

    # Renomeamos as colunas para clareza
    verificacao_anual.rename(columns={
        'sum': 'promissoras_count',
        'count': 'total_patentes',
        'mean': 'proporcao_promissoras'
    }, inplace=True)

    # Reordenamos as colunas para melhor visualização
    verificacao_anual = verificacao_anual[[
        'promissoras_count',
        'nao_promissoras_count',
        'total_patentes',
        'proporcao_promissoras'
    ]]

    # Formatamos a coluna de proporção para ficar mais legível (opcional)
    verificacao_anual['proporcao_promissoras'] = verificacao_anual['proporcao_promissoras'].apply(lambda x: f"{x:.2%}")

    print(verificacao_anual)

    df.drop(columns=['ano'], inplace=True)

    return df.copy()
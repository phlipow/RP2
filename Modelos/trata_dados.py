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
    print("\n--- Resultados da Rotulagem ---")
    print("Contagem de valores na nova coluna 'promissora':")
    print(df['promissora'].value_counts(normalize=True))

    # Verificação detalhada por ano para garantir que a proporção está correta
    print("\nVerificando a proporção de patentes promissoras por ano:")
    # Criamos uma coluna temporária 'ano' para facilitar o groupby na verificação
    df['ano'] = df['application_date'].dt.year
    verificacao_anual = df.groupby('ano')['promissora'].agg(['mean', 'count'])
    verificacao_anual.rename(columns={'mean': 'proporcao_promissoras', 'count': 'total_patentes'}, inplace=True)

    print(verificacao_anual)

    df.drop(columns=['ano'], inplace=True)

    return df.copy()
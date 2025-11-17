import pandas as pd
import numpy as np
import re

def clean_title(title):
    if isinstance(title, str):
        return re.sub(r'[^a-zA-Z0-9]', '', title).lower()
    return title

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

    # Carrega os arquivos
    df_promissoras = pd.read_csv('patents_with_newer_ipc_google.csv')

    # Converte as datas






    # Merge para encontrar as patentes promissoras
    df_final = pd.merge(df, df_promissoras[['promising_patent_id']], left_on='patent_id', right_on='promising_patent_id', how='left', indicator=True)
    df_final['promissora'] = np.where(df_final['_merge'] == 'both', 1, 0)


    # Conta o número de patentes promissoras no conjunto de treinamento
    num_promissoras_no_treinamento = df_final['promissora'].sum()
    print(f"\nNúmero de patentes promissoras correspondentes no conjunto de treinamento: {num_promissoras_no_treinamento}")


    # --- Verificação da Rotulagem ---
    print("\n--- Resultados da Rotulagem ---")
    print("Contagem de valores na nova coluna 'promissora':")
    print(df_final['promissora'].value_counts(normalize=True))

    # Verificação detalhada por ano para garantir que a proporção está correta
    print("\nVerificando a proporção de patentes promissoras por ano:")
    df_final['ano'] = df_final['application_date'].dt.year
    verificacao_anual = df_final.groupby('ano')['promissora'].agg(
        proporcao_promissoras=('mean'),
        total_patentes=('count')
    )
    print(verificacao_anual)

    df_final.drop(columns=['ano', '_merge', 'promising_patent_id'], inplace=True)

    return df_final.copy()

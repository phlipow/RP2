import requests
import xmltodict
import csv
import re
import time
from requests.auth import HTTPBasicAuth

# ==============================================================================
# ⚠️ CONFIGURAÇÃO OBRIGATÓRIA
# ------------------------------------------------------------------------------
# SUBSTITUA PELAS SUAS CHAVES DE CONSUMO OBTIDAS NO PORTAL DO DESENVOLVEDOR DO EPO
CONSUMER_KEY = "3APxH4wxYoY7aZibQ4jDP9YGjezGbWzfcGji9xA6j3qY0ea1"
CONSUMER_SECRET = "OCeAZAVzxdlLZ80IJ4sootDyI8iKpleu3pD3qEGh1R1BYALewAfyRuhASN1XnJBk"

# Caminhos dos arquivos
INPUT_FILE = r"C:\Users\ATAF IP\COMPRAS\patentes.txt"
OUTPUT_FILE = "patentes_dados_simples.csv"  # Nome de arquivo alterado para não sobrescrever

# Variável global para armazenar o token
ACCESS_TOKEN = None


# ==============================================================================


# --- 1. FUNÇÃO DE AUTENTICAÇÃO ---
def get_access_token():
    """Obtém o Access Token via OAuth 2.0 usando as chaves de consumidor."""
    global ACCESS_TOKEN

    token_url = "https://ops.epo.org/3.2/auth/accesstoken"
    try:
        response = requests.post(
            token_url,
            data={'grant_type': 'client_credentials'},
            auth=HTTPBasicAuth(CONSUMER_KEY, CONSUMER_SECRET),
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        response.raise_for_status()

        token_data = response.json()
        ACCESS_TOKEN = token_data.get('access_token')
        print("✅ Access Token obtido com sucesso.")
        return ACCESS_TOKEN

    except requests.exceptions.HTTPError as e:
        print(f"❌ Erro HTTP ao obter o token: {e}")
        return None
    except Exception as e:
        print(f"❌ Erro desconhecido ao obter o token: {e}")
        return None


# --- 2. FUNÇÃO AUXILIAR DE EXTRAÇÃO DO NÚMERO ---
def extract_pub_number(link):
    """Extrai o número de publicação no formato EPODOC (e.g., WO2013142934)."""
    # Lógica de extração inalterada (mantém a compatibilidade com o formato BR9905240)
    epo_pattern = re.search(r'([A-Z]{2}\d+[A-Z]?\d*)', link)
    if epo_pattern:
        return epo_pattern.group(1).replace('patent/', '')
    google_match = re.search(r'patent/([A-Z]{2}\d+)', link)
    if google_match:
        return google_match.group(1)
    return None


# --- 3. FUNÇÃO DE EXTRAÇÃO DE DADOS (CORRIGIDA) ---
def get_patent_data(publication_number):
    """Consulta OPS para obter Contagem de Família, Número de IPCs e Número de CPCs."""
    global ACCESS_TOKEN, PRINTED_XML
    if not ACCESS_TOKEN:
        return None

    headers = {'Authorization': f'Bearer {ACCESS_TOKEN}'}
    base_url = "https://ops.epo.org/rest-services"

    # Inicializa variáveis
    ipc_list, cpc_list = [], []
    family_count = 'N/A'

    # ----------------------------------------------------------------------
    # A) REQUISIÇÃO PARA DADOS BIBLIOGRÁFICOS (IPC/CPC)
    # ----------------------------------------------------------------------
    biblio_url = f"{base_url}/published-data/publication/epodoc/{publication_number}/biblio"

    try:
        biblio_response = requests.get(biblio_url, headers=headers)
        biblio_response.raise_for_status()

        biblio_data = xmltodict.parse(biblio_response.text)

        # Usamos uma função aninhada para extrair o texto de classificações de forma segura
        def safe_extract_text(data):
            # Se for uma lista de classificações (o caso mais comum)
            if isinstance(data, list):
                return [c.get('text', '').strip() for c in data if isinstance(c, dict) and 'text' in c]
            # Se for um único dicionário
            elif isinstance(data, dict) and 'text' in data:
                return [data['text'].strip()]
            return []

        # Função para construir o código CPC completo
        def build_cpc_code(cpc_item):
            # Ignora classificações sem esquema (deve ser 'CPCI' ou 'CPC')
            if not isinstance(cpc_item, dict) or cpc_item.get('classification-scheme', {}).get('@scheme') not in [
                'CPCI', 'CPC']:
                return None

            # Constrói o código no formato SECTIONCLASS/MAINGROUP
            section = cpc_item.get('section', '')
            class_ = cpc_item.get('class', '')
            subclass = cpc_item.get('subclass', '')
            main_group = cpc_item.get('main-group', '')
            subgroup = cpc_item.get('subgroup', '')

            # Combina: C08B 1/00
            if section and class_ and subclass and main_group and subgroup:
                return f"{section}{class_}{subclass} {main_group}/{subgroup}"
            return None

        try:
            exchange_docs = biblio_data['ops:world-patent-data']['exchange-documents']['exchange-document']
            exchange_doc = exchange_docs[0] if isinstance(exchange_docs, list) else exchange_docs

            # 1. Extração de IPC (Corrigido para a tag 'classifications-ipcr')
            ipc_parent = exchange_doc.get('bibliographic-data', {}).get('classifications-ipcr', {})
            ipc_data = ipc_parent.get('classification-ipcr', [])
            ipc_list = safe_extract_text(ipc_data)

            # 2. Extração de CPC (Implementação de nova lógica)
            patent_classes = exchange_doc.get('bibliographic-data', {}).get('patent-classifications', {})
            cpc_items = patent_classes.get('patent-classification', [])

            # Garante que cpc_items seja sempre uma lista para iteração
            if isinstance(cpc_items, dict):
                cpc_items = [cpc_items]
            elif not isinstance(cpc_items, list):
                cpc_items = []

            # Constrói a lista de CPCs
            for item in cpc_items:
                cpc_code = build_cpc_code(item)
                if cpc_code:
                    cpc_list.append(cpc_code)

            # Remove duplicatas
            ipc_list = list(set(ipc_list))
            cpc_list = list(set(cpc_list))

        except (KeyError, TypeError, IndexError) as e:
            print(
                f"   [ERRO EXTRAÇÃO CLASSES]: Falha ao analisar estrutura de classes: {e}. O XML pode ter uma estrutura inesperada.")

    except requests.exceptions.HTTPError as e:
        print(f"   [ERRO BIBLIO]: {e.response.status_code} para {publication_number}. Classificações não obtidas.")
    except Exception as e:
        print(f"   [ERRO BIBLIO]: Falha ao processar XML de {publication_number}: {e}")

    # ----------------------------------------------------------------------
    # B) REQUISIÇÃO PARA DADOS DA FAMÍLIA DE PATENTES (Contagem) - MANTIDO
    # ----------------------------------------------------------------------
    # ... (o código para Family Count permanece o mesmo, pois já está funcionando) ...
    family_url = f"{base_url}/family/publication/epodoc/{publication_number}"

    try:
        family_response = requests.get(family_url, headers=headers)
        family_response.raise_for_status()
        family_data = xmltodict.parse(family_response.text)

        family_members = family_data['ops:world-patent-data']['ops:patent-family']['ops:family-member']
        if isinstance(family_members, list):
            family_count = len(family_members)
        elif isinstance(family_members, dict):
            family_count = 1
        else:
            family_count = 0

    except requests.exceptions.HTTPError:
        family_count = 'ERRO'
    except Exception:
        family_count = 'ERRO'

    # Retorna as 3 métricas solicitadas
    return {
        'family_count': family_count,
        'num_ipc': len(ipc_list),
        'num_cpc': len(cpc_list),
        'IPC': ipc_list,
        'CPC': cpc_list
    }


# --- 4. FLUXO PRINCIPAL DO SCRIPT ---
if __name__ == "__main__":

    if not get_access_token():
        print("\nO script não pode continuar sem um Access Token válido.")
    else:
        try:
            with open(INPUT_FILE, 'r', encoding='utf-8') as f:
                links = [line.strip() for line in f.readlines() if line.strip()]
        except FileNotFoundError:
            print(f"\n❌ ERRO: Arquivo de entrada não encontrado: {INPUT_FILE}")
            exit()

        with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            # FIELDNAMES AJUSTADOS PARA AS 3 MÉTRICAS SOLICITADAS
            fieldnames = ['link', 'publication_number', 'family_count', 'num_ipc', 'num_cpc', 'IPC', 'CPC']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for i, link in enumerate(links, 1):
                pub_number = extract_pub_number(link)
                total_links = len(links)

                if not pub_number:
                    print(f"[{i}/{total_links}] ⚠️ Não extraído do link: {link}")
                    writer.writerow(
                        {'link': link, 'publication_number': 'N/A', 'family_count': 'N/A', 'num_ipc': 'N/A',
                         'num_cpc': 'N/A', 'IPC': 'N/A', 'CPC': 'N/A'})
                    continue

                print(f"[{i}/{total_links}] Processando {pub_number}...")
                data = get_patent_data(pub_number)

                if data:
                    writer.writerow({
                        'link': link,
                        'publication_number': pub_number,
                        'family_count': data['family_count'],
                        'num_ipc': data['num_ipc'],
                        'num_cpc': data['num_cpc'],
                        'IPC': ', '.join(data['IPC']),
                        'CPC': ', '.join(data['CPC'])
                    })
                    print(
                        f"   [SUCESSO] Dados de {pub_number} salvos (Família: {data['family_count']}, IPCs: {data['num_ipc']}, CPCs: {data['num_cpc']}).")
                else:
                    print(f"   [FALHA] Não foi possível obter dados completos de {pub_number}")
                    writer.writerow(
                        {'link': link, 'publication_number': pub_number, 'family_count': 'FALHA', 'num_ipc': 'FALHA',
                         'num_cpc': 'FALHA', 'IPC': 'FALHA', 'CPC': 'FALHA'})

                # Pausa obrigatória
                time.sleep(3)

        print(f"\n✨ Processamento concluído. Resultados salvos em: {OUTPUT_FILE}")
import requests
import xmltodict
import csv
import re
import time
import datetime
from requests.auth import HTTPBasicAuth
from typing import Optional, Dict, Any, List

# ==============================================================================
# ⚠️ CONFIGURAÇÃO OBRIGATÓRIA
# ------------------------------------------------------------------------------
# SUBSTITUA PELAS SUAS CHAVES DE CONSUMO OBTIDAS NO PORTAL DO DESENVOLVEDOR DO EPO
CONSUMER_KEY = "3APxH4wxYoY7aZibQ4jDP9YGjezGbWzfcGji9xA6j3qY0ea1"
CONSUMER_SECRET = "OCeAZAVzxdlLZ80IJ4sootDyI8iKpleu3pD3qEGh1R1BYALewAfyRuhASN1XnJBk"

# Caminhos dos arquivos
INPUT_FILE = r"C:\Users\Licitações\PycharmProjects\WEBSCRAPPING\PATENTES ADAPTADAS.txt"
OUTPUT_FILE = "patentes_dados_simples_inventor.csv"

# Variáveis globais
ACCESS_TOKEN = None
MAX_RETRIES = 5  # Número máximo de tentativas em caso de falha de conexão ou 429

# CONSTANTES PARA CÁLCULO DE MÉTRICAS DO INVENTOR
PORTFOLIO_SAMPLE_SIZE = 25  # Limite de patentes do portfólio para amostrar e calcular médias
RECENCY_YEARS_PERIOD = 5  # Duração de cada período (A e B) para o cálculo da Taxa de Crescimento (5 anos)


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

    except requests.exceptions.RequestException as e:
        print(f"❌ Erro ao obter o token: {e}")
        return None


# --- FUNÇÃO AUXILIAR PARA TRATAMENTO DE RETRY E 429 ---
def make_ops_request(url: str, headers: Dict[str, str], identifier: str, max_retries: int = MAX_RETRIES) -> Optional[
    requests.Response]:
    """
    Realiza a requisição, tratando o limite de taxa (429) e erros de conexão.
    """
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers)

            if response.status_code == 429:
                retry_after = response.headers.get('Retry-After')
                try:
                    wait_time = int(retry_after)
                except (TypeError, ValueError):
                    wait_time = 60

                print(
                    f"   [ALERTA 429 - {identifier}]: Limite de requisições atingido. Tentativa {attempt + 1}/{max_retries}. Esperando por {wait_time} segundos...")
                time.sleep(wait_time)

                if attempt == max_retries - 1:
                    print(f"   [FALHA 429]: Tentativas esgotadas para {identifier}.")
                    return None
                continue

            response.raise_for_status()
            return response

        except requests.exceptions.HTTPError as e:
            if response.status_code == 404:
                return response
            return None

        except requests.exceptions.RequestException:
            if attempt < max_retries - 1:
                print(
                    f"   [ERRO CONEXÃO]: Falha de conexão para {identifier}. Tentando novamente... ({attempt + 1}/{max_retries})")
                time.sleep(5)
                continue
            return None

    return None


# --- FUNÇÃO AUXILIAR DE EXTRAÇÃO DO NÚMERO ---
def extract_pub_number(link):
    """Extrai o número de publicação no formato EPODOC."""
    wipo_docid_match = re.search(r'docId=([A-Z]{2}\d+[A-Z]?\d*)', link)
    if wipo_docid_match:
        return wipo_docid_match.group(1)

    epo_pattern = re.search(r'([A-Z]{2}\d+[A-Z]?\d*)', link)
    if epo_pattern:
        return epo_pattern.group(1).replace('patent/', '')
    google_match = re.search(r'patent/([A-Z]{2}\d+)', link)
    if google_match:
        return google_match.group(1)
    return None


# --- 2. EXTRAÇÃO DE CITAÇÕES E DATA PARA UM ID ESPECÍFICO ---
def get_citation_and_date(pub_number: str, headers: Dict[str, str]) -> Dict[str, Any]:
    """Obtém contagens de citações (forward/backward) e data de publicação."""
    base_url = "https://ops.epo.org/rest-services"
    citations_url = f"{base_url}/published-data/publication/epodoc/{pub_number}/citations"
    biblio_url = f"{base_url}/published-data/publication/epodoc/{pub_number}/biblio"

    forward_cites, backward_cites, pub_date = 0, 0, None

    # 1. Citações
    cites_response = make_ops_request(citations_url, headers, f"Citação {pub_number}")
    if cites_response and cites_response.status_code == 200:
        try:
            cites_data = xmltodict.parse(cites_response.text)

            # Citações Forward (Referenced by)
            forward_list = cites_data.get('ops:world-patent-data', {}).get('ops:biblio-search', {}).get(
                'ops:forward-citations', {}).get('citation', [])
            if isinstance(forward_list, dict): forward_list = [forward_list]
            forward_cites = len(forward_list)

            # Citações Backward (References)
            backward_list = cites_data.get('ops:world-patent-data', {}).get('ops:biblio-search', {}).get(
                'ops:backward-citations', {}).get('citation', [])
            if isinstance(backward_list, dict): backward_list = [backward_list]
            backward_cites = len(backward_list)
        except Exception:
            pass

            # 2. Data de Publicação (necessária para Recência)
    biblio_response = make_ops_request(biblio_url, headers, f"Biblio Date {pub_number}")
    if biblio_response and biblio_response.status_code == 200:
        try:
            biblio_data = xmltodict.parse(biblio_response.text)
            date_raw = \
            biblio_data.get('ops:world-patent-data', {}).get('exchange-documents', {}).get('exchange-document', {}).get(
                'bibliographic-data', {}).get('publication-reference', {}).get('document-id', [{}])[0].get('date')
            if date_raw:
                pub_date = date_raw
        except Exception:
            pass

    return {
        'forward_cites': forward_cites,
        'backward_cites': backward_cites,
        'pub_date': pub_date
    }


# --- 3. FUNÇÃO PARA EXTRAIR MÉTRICAS DO PORTFÓLIO DO INVENTOR ---
def get_inventor_portfolio_metrics(inventor_name: str) -> Dict[str, Any]:
    """
    Calcula Recência (Taxa de Crescimento Refinada), Qualidade e Cobertura do Inventor.
    """
    if not inventor_name or not ACCESS_TOKEN:
        return {'recency_growth_rate': 0, 'quality': 0, 'coverage': 0, 'portfolio_size': 0}

    headers = {'Authorization': f'Bearer {ACCESS_TOKEN}'}
    base_url = "https://ops.epo.org/rest-services"

    # Consulta de busca (in= para Inventor) - usa o nome já limpo (SOBRENOME, NOME)
    search_url = f"{base_url}/rest-services/published-data/search/biblio?query=in%3D%22{requests.utils.quote(inventor_name)}%22&range=1-{PORTFOLIO_SAMPLE_SIZE}"

    print(
        f"   [BUSCA PORTFÓLIO]: Buscando amostra de {PORTFOLIO_SAMPLE_SIZE} patentes para o Inventor '{inventor_name}'...")

    search_response = make_ops_request(search_url, headers, f"Busca {inventor_name}")

    total_patents_found = 0
    patent_ids = []

    if search_response and search_response.status_code == 200:
        try:
            search_data = xmltodict.parse(search_response.text)

            total_patents_found = int(
                search_data.get('ops:world-patent-data', {}).get('ops:biblio-search', {}).get('@total-result-count', 0))

            biblio_search = search_data.get('ops:world-patent-data', {}).get('ops:biblio-search', {})
            hits = biblio_search.get('ops:search-result', {}).get('ops:publication-reference', [])

            if isinstance(hits, dict):
                hits = [hits]

            for hit in hits:
                doc_id_list = hit.get('document-id', [])
                if isinstance(doc_id_list, dict): doc_id_list = [doc_id_list]

                for doc_id in doc_id_list:
                    if doc_id.get('doc-number'):
                        patent_ids.append(doc_id.get('doc-number'))
                        break

        except Exception as e:
            print(f"   [ERRO PARSING BUSCA]: Falha ao processar a busca para {inventor_name}: {e}")
            return {'recency_growth_rate': 0, 'quality': 0, 'coverage': 0, 'portfolio_size': 0}

    if not patent_ids:
        print(f"   [ALERTA PORTFÓLIO]: Nenhuma patente encontrada na amostra para o Inventor '{inventor_name}'.")
        return {'recency_growth_rate': 0, 'quality': 0, 'coverage': 0, 'portfolio_size': total_patents_found}

    # ----------------------------------------------------------------------
    # ITERAÇÃO SOBRE A AMOSTRA E AGREGAÇÃO DE DADOS
    # ----------------------------------------------------------------------

    total_forward_cites = 0
    total_backward_cites = 0
    total_family_size = 0
    publication_years = {}  # {year: count}

    current_year = datetime.datetime.now().year

    print(f"   [CALC. MÉTRICAS]: Processando amostra de {len(patent_ids)} patentes do Inventor...")

    for pub_id in patent_ids:

        # Coleta de Citações e Data
        metrics = get_citation_and_date(pub_id, headers)

        total_forward_cites += metrics['forward_cites']
        total_backward_cites += metrics['backward_cites']

        if metrics['pub_date']:
            try:
                year = int(metrics['pub_date'][:4])
                publication_years[year] = publication_years.get(year, 0) + 1
            except (ValueError, TypeError):
                pass

        # Coleta de Tamanho da Família
        family_url = f"{base_url}/family/publication/epodoc/{pub_id}"
        family_response = make_ops_request(family_url, headers, f"Família {pub_id}")

        family_count = 0
        if family_response and family_response.status_code == 200:
            try:
                family_data = xmltodict.parse(family_response.text)
                family_members_raw = family_data.get('ops:world-patent-data', {}).get('ops:patent-family', {}).get(
                    'ops:family-member', [])

                if isinstance(family_members_raw, dict): family_members_raw = [family_members_raw]

                family_count = len(family_members_raw)
                total_family_size += family_count
            except Exception:
                pass

        time.sleep(1)  # Pausa curta

    # ----------------------------------------------------------------------
    # CÁLCULO DAS MÉTRICAS FINAIS
    # ----------------------------------------------------------------------

    sample_count = len(patent_ids)

    # 1. Qualidade do Inventor (Média de Citações)
    total_cites = total_forward_cites + total_backward_cites
    quality = round(total_cites / sample_count, 2) if sample_count > 0 else 0

    # 2. Cobertura do Inventor (Média de Membros da Família)
    coverage = round(total_family_size / sample_count, 2) if sample_count > 0 else 0

    # 3. Recência do Inventor (Taxa de Crescimento em 5 anos) - Lógica Refinada

    # Define os anos dos períodos
    year_end_A = current_year
    year_start_A = year_end_A - RECENCY_YEARS_PERIOD + 1
    year_start_B = year_start_A - RECENCY_YEARS_PERIOD

    # Soma as patentes em cada período
    patents_A = sum(
        count for year, count in publication_years.items()
        if year >= year_start_A and year <= year_end_A
    )
    patents_B = sum(
        count for year, count in publication_years.items()
        if year >= year_start_B and year < year_start_A
    )

    recency_growth_rate = 0.0
    if patents_B > 0:
        # Crescimento percentual normal
        recency_growth_rate = round((patents_A - patents_B) / patents_B, 4)
    elif patents_A > 0:
        # TRATAMENTO REFINADO para INÍCIO DE ATIVIDADE (P_B = 0, P_A > 0)

        # Encontra o ano mais antigo de publicação no Período A
        recent_years_with_patents = [year for year in publication_years.keys()
                                     if year >= year_start_A and year <= year_end_A]

        min_recent_year = min(recent_years_with_patents) if recent_years_with_patents else year_end_A

        # Calcula o número de anos ativos (inclui o ano atual)
        years_active = current_year - min_recent_year + 1

        # Métrica: Volume Médio Anual no período A (resolve a "explosão")
        recency_growth_rate = round(patents_A / years_active, 4)

    # Se P_A=0 e P_B=0, a taxa é 0.

    print(
        f"   [MÉTRICAS INVENTOR]: Qualidade Média: {quality}, Cobertura Média: {coverage}, Recência (Taxa Cresc.): {recency_growth_rate}")

    return {
        'recency_growth_rate': recency_growth_rate,
        'quality': quality,
        'coverage': coverage,
        'portfolio_size': total_patents_found
    }


# --- 4. FUNÇÃO DE EXTRAÇÃO DE DADOS BÁSICOS E INVENTOR ---
def get_patent_data(publication_number: str) -> Optional[Dict[str, Any]]:
    """Consulta OPS para obter Classes, Família, e o nome do PRIMEIRO Inventor."""
    global ACCESS_TOKEN
    if not ACCESS_TOKEN: return None

    headers = {'Authorization': f'Bearer {ACCESS_TOKEN}'}
    base_url = "https://ops.epo.org/rest-services"

    # Inicializa variáveis
    ipc_list, cpc_list = [], []
    family_count = 'N/A'
    biblio_success = False
    family_members_list = []
    ipc_diversity = 0
    cpc_diversity = 0
    inventor_name = None

    # ----------------------------------------------------------------------
    # A) REQUISIÇÃO PARA DADOS BIBLIOGRÁFICOS (IPC/CPC/Inventor)
    # ----------------------------------------------------------------------
    biblio_url = f"{base_url}/published-data/publication/epodoc/{publication_number}/biblio"
    biblio_response = make_ops_request(biblio_url, headers, publication_number)

    if biblio_response and biblio_response.status_code == 200:
        try:
            biblio_data = xmltodict.parse(biblio_response.text)
            biblio_success = True

            # Funções auxiliares
            def safe_extract_text(data):
                if isinstance(data, list):
                    result = []
                    for item in data:
                        if isinstance(item, dict) and 'text' in item:
                            result.append(item['text'].strip())
                    return result
                elif isinstance(data, dict) and 'text' in data:
                    return [data['text'].strip()]
                return []

            def build_cpc_code(cpc_item):
                if not isinstance(cpc_item, dict) or cpc_item.get('classification-scheme', {}).get('@scheme') not in [
                    'CPCI', 'CPC']: return None
                section = cpc_item.get('section', '')
                class_ = cpc_item.get('class', '')
                subclass = cpc_item.get('subclass', '')
                main_group = cpc_item.get('main-group', '')
                subgroup = cpc_item.get('subgroup', '')
                if section and class_ and subclass and main_group and subgroup:
                    return f"{section}{class_}{subclass} {main_group}/{subgroup}"
                return None

            exchange_docs_container = biblio_data.get('ops:world-patent-data', {}).get('exchange-documents')
            if exchange_docs_container:
                exchange_docs = exchange_docs_container.get('exchange-document')

                if isinstance(exchange_docs, list):
                    exchange_doc = exchange_docs[0]
                else:
                    exchange_doc = exchange_docs

                if exchange_doc:
                    bib_data = exchange_doc.get('bibliographic-data', {})

                    # Extração e Limpeza do PRIMEIRO Inventor
                    inventors = bib_data.get('parties', {}).get('inventors', {}).get('inventor', [])
                    if isinstance(inventors, dict): inventors = [inventors]

                    if inventors:
                        first_inventor = inventors[0]
                        addressbook = first_inventor.get('addressbook', {})
                        last_name = addressbook.get('last-name')
                        first_name = addressbook.get('first-name')


                        if last_name and first_name:
                            # Formato preferido para busca EPO: "SOBRENOME, NOME"
                            inventor_name = f"{first_name}, {last_name}"
                        else:
                            # Fallback para o nome não estruturado e limpeza do código do país
                            name_container = first_inventor.get('inventor-name', {}).get('name')
                            if name_container:
                                # Remove código de país tipo [US] e espaços extras
                                inventor_name = re.sub(r'\s*\[[A-Z]{2,3}\]\s*', '', name_container).strip()
                                partes = inventor_name.split()
                                partes.append(partes.pop(0))
                                inventor_name = ' '.join(partes)
                                print(inventor_name)
                                print("até aqui funciona")


                    # Extração de IPC e CPC (mantido)
                    ipc_parent = bib_data.get('classifications-ipcr', {})
                    ipc_data = ipc_parent.get('classification-ipcr', [])
                    ipc_list = safe_extract_text(ipc_data)

                    patent_classes = bib_data.get('patent-classifications', {})
                    cpc_items = patent_classes.get('patent-classification', [])
                    if isinstance(cpc_items, dict): cpc_items = [cpc_items]
                    for item in cpc_items:
                        cpc_code = build_cpc_code(item)
                        if cpc_code: cpc_list.append(cpc_code)

                    ipc_list = list(set(ipc_list))
                    cpc_list = list(set(cpc_list))

                    ipc_diversity = len(set(ipc[:4] for ipc in ipc_list if len(ipc) >= 4))
                    cpc_diversity = len(set(re.match(r'([A-Z]\d{2}[A-Z])', cpc).group(1) for cpc in cpc_list if
                                            re.match(r'([A-Z]\d{2}[A-Z])', cpc)))


        except Exception as e:
            print(f"   [ERRO PROCESSAMENTO XML BIBLIO]: Falha ao processar XML de {publication_number}: {e}")
            biblio_success = False

    # ----------------------------------------------------------------------
    # B) REQUISIÇÃO PARA DADOS DA FAMÍLIA (Lógica anterior)
    # ----------------------------------------------------------------------
    family_url = f"{base_url}/family/publication/epodoc/{publication_number}"
    family_response = make_ops_request(family_url, headers, publication_number)

    if family_response and family_response.status_code == 200:
        try:
            family_data = xmltodict.parse(family_response.text)
            family_container = family_data.get('ops:world-patent-data', {}).get('ops:patent-family')

            # Lógica de extração de Family Count e Members (mantida)
            if family_container:
                family_members_raw = family_container.get('ops:family-member')
                if isinstance(family_members_raw, dict):
                    members_to_process = [family_members_raw]
                elif isinstance(family_members_raw, list):
                    members_to_process = family_members_raw
                else:
                    members_to_process = []
                family_count = len(members_to_process)
                for member in members_to_process:
                    try:
                        pub_ref = member.get('ops:publication-reference', {})
                        doc_ids = pub_ref.get('document-id')
                        if isinstance(doc_ids, dict): doc_ids = [doc_ids]
                        for doc_id in doc_ids:
                            doc_num = doc_id.get('doc-number')
                            if doc_num:
                                family_members_list.append(doc_num)
                                break
                    except Exception:
                        continue
            else:
                family_count = 0
        except Exception:
            family_count = 'ERRO'
    else:
        family_count = 'FALHA REQ'

    if not biblio_success and family_count in ('ERRO', 'FALHA REQ', 0, 'N/A'):
        return None

    return {
        'inventor_name': inventor_name,
        'family_count': family_count,
        'family_members': family_members_list,
        'num_ipc': len(ipc_list),
        'num_cpc': len(cpc_list),
        'ipc_diversity': ipc_diversity,
        'cpc_diversity': cpc_diversity,
        'IPC': ipc_list,
        'CPC': cpc_list
    }


# --- FLUXO PRINCIPAL DO SCRIPT ---
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

            # --- COLUNAS ATUALIZADAS PARA INVENTOR E NOVA MÉTRICA DE RECÊNCIA ---
            fieldnames = ['link', 'publication_number', 'inventor_name', 'inventor_portfolio_size',
                          'inventor_recency_growth_rate', 'inventor_quality_avg_cites', 'inventor_coverage_avg_family',
                          'family_count', 'family_members', 'num_ipc', 'num_cpc', 'ipc_diversity', 'cpc_diversity',
                          'IPC', 'CPC']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for i, link in enumerate(links, 1):
                pub_number = extract_pub_number(link)
                total_links = len(links)

                if not pub_number:
                    print(f"[{i}/{total_links}] ⚠️ Não extraído do link/número: {link}")
                    fail_data = {f: 'N/A' for f in fieldnames}
                    fail_data.update({'link': link, 'publication_number': 'N/A'})
                    writer.writerow(fail_data)
                    continue

                print(f"[{i}/{total_links}] Processando {pub_number}...")

                # 1. Extrai dados básicos e o NOME do PRIMEIRO Inventor (agora limpo)
                basic_data = get_patent_data(pub_number)

                if not basic_data:
                    print(f"   [FALHA TOTAL]: Não foi possível obter dados básicos de {pub_number}.")
                    fail_data = {f: 'FALHA' for f in fieldnames}
                    fail_data.update({'link': link, 'publication_number': pub_number,
                                      'num_ipc': 0, 'num_cpc': 0, 'ipc_diversity': 0, 'cpc_diversity': 0})
                    writer.writerow(fail_data)
                    time.sleep(3)
                    continue

                # 2. Extrai Características do Inventor (usando o nome limpo)
                inventor_name = basic_data.get('inventor_name')
                inventor_metrics = {}

                if inventor_name:
                    print(f"   [INVENTOR]: Extraindo características do Inventor principal: '{inventor_name}'.")
                    inventor_metrics = get_inventor_portfolio_metrics(inventor_name)
                else:
                    print("   [ALERTA INVENTOR]: Inventor não encontrado na patente. Métricas setadas para 0/N/A.")
                    inventor_metrics = {'recency_growth_rate': 0, 'quality': 0, 'coverage': 0, 'portfolio_size': 0}

                # 3. CONSOLIDAÇÃO E ESCRITA

                row_data = {
                    'link': link,
                    'publication_number': pub_number,
                    'inventor_name': inventor_name if inventor_name else 'N/A',
                    'inventor_portfolio_size': inventor_metrics['portfolio_size'],
                    'inventor_recency_growth_rate': inventor_metrics['recency_growth_rate'],
                    'inventor_quality_avg_cites': inventor_metrics['quality'],
                    'inventor_coverage_avg_family': inventor_metrics['coverage'],
                    'family_count': basic_data['family_count'],
                    'family_members': ', '.join(basic_data['family_members']),
                    'num_ipc': basic_data['num_ipc'],
                    'num_cpc': basic_data['num_cpc'],
                    'ipc_diversity': basic_data['ipc_diversity'],
                    'cpc_diversity': basic_data['cpc_diversity'],
                    'IPC': ', '.join(basic_data['IPC']),
                    'CPC': ', '.join(basic_data['CPC'])
                }

                writer.writerow(row_data)

                time.sleep(3)

        print(f"\n✨ Processamento concluído. Resultados salvos em: {OUTPUT_FILE}")

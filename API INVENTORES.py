import requests
import xmltodict
import csv
import re
import time
import datetime
from requests.auth import HTTPBasicAuth
from typing import Optional, Dict, Any

# ==============================================================================
# ⚠️ CONFIGURAÇÃO OBRIGATÓRIA
# ------------------------------------------------------------------------------
CONSUMER_KEY = "3APxH4wxYoY7aZibQ4jDP9YGjezGbWzfcGji9xA6j3qY0ea1"
CONSUMER_SECRET = "OCeAZAVzxdlLZ80IJ4sootDyI8iKpleu3pD3qEGh1R1BYALewAfyRuhASN1XnJBk"

# Arquivo de entrada: lista de nomes de inventores (um por linha)
INPUT_FILE = r"C:\Users\ATAF IP\COMPRAS\INVENTORES.txt"
OUTPUT_FILE = "inventores_metricas.csv"

ACCESS_TOKEN = None
MAX_RETRIES = 5
PORTFOLIO_SAMPLE_SIZE = 25  # Limite de patentes do portfólio para amostrar
RECENCY_YEARS_PERIOD = 5  # Duração de cada período para cálculo da Taxa de Crescimento


# ==============================================================================


def get_access_token():
    """Obtém o Access Token via OAuth 2.0."""
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


def make_ops_request(url: str, headers: Dict[str, str], identifier: str, max_retries: int = MAX_RETRIES) -> Optional[
    requests.Response]:
    """Realiza a requisição com tratamento de retry e 429."""
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
                    f"   [ALERTA 429 - {identifier}]: Limite atingido. Tentativa {attempt + 1}/{max_retries}. Esperando {wait_time}s...")
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
                    f"   [ERRO CONEXÃO]: Falha para {identifier}. Tentando novamente... ({attempt + 1}/{max_retries})")
                time.sleep(5)
                continue
            return None

    return None


def clean_inventor_name(name: str) -> str:
    """Limpa e formata o nome do inventor."""
    if not name:
        return None

    # Remove códigos de país [US], [BR], etc
    name = re.sub(r'\s*\[[A-Z]{2,3}\]\s*', '', name).strip()

    # Remove pontuações extras
    name = re.sub(r'[.,;]+$', '', name).strip()

    # Remove espaços múltiplos
    name = re.sub(r'\s+', ' ', name)

    return name if name else None


def get_citation_and_date(pub_number: str, headers: Dict[str, str]) -> Dict[str, Any]:
    """Obtém contagens de citações e data de publicação."""
    base_url = "https://ops.epo.org/rest-services"
    citations_url = f"{base_url}/published-data/publication/epodoc/{pub_number}/citations"
    biblio_url = f"{base_url}/published-data/publication/epodoc/{pub_number}/biblio"

    forward_cites, backward_cites, pub_date = 0, 0, None

    # Citações
    cites_response = make_ops_request(citations_url, headers, f"Citação {pub_number}")
    if cites_response and cites_response.status_code == 200:
        try:
            cites_data = xmltodict.parse(cites_response.text)

            forward_list = cites_data.get('ops:world-patent-data', {}).get('ops:biblio-search', {}).get(
                'ops:forward-citations', {}).get('citation', [])
            if isinstance(forward_list, dict): forward_list = [forward_list]
            forward_cites = len(forward_list)

            backward_list = cites_data.get('ops:world-patent-data', {}).get('ops:biblio-search', {}).get(
                'ops:backward-citations', {}).get('citation', [])
            if isinstance(backward_list, dict): backward_list = [backward_list]
            backward_cites = len(backward_list)
        except Exception:
            pass

    # Data de Publicação
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


def get_inventor_portfolio_metrics(inventor_name: str) -> Dict[str, Any]:
    """Calcula métricas completas do portfólio do inventor."""
    if not inventor_name or not ACCESS_TOKEN:
        return {
            'portfolio_size': 0,
            'recency_growth_rate': 0,
            'quality_avg_cites': 0,
            'coverage_avg_family': 0,
            'total_forward_cites': 0,
            'total_backward_cites': 0,
            'avg_forward_cites': 0,
            'avg_backward_cites': 0,
            'years_active': 0,
            'first_patent_year': 'N/A',
            'last_patent_year': 'N/A',
            'patents_last_5_years': 0
        }

    headers = {'Authorization': f'Bearer {ACCESS_TOKEN}'}
    base_url = "https://ops.epo.org/rest-services"

    # Limpa o nome do inventor
    inventor_name = clean_inventor_name(inventor_name)

    # Encoding correto para a busca
    encoded_name = requests.utils.quote(inventor_name)
    search_url = f"{base_url}/published-data/search/biblio?q=in%3D{encoded_name}&Range=1-{PORTFOLIO_SAMPLE_SIZE}"

    print(f"   [BUSCA PORTFÓLIO]: Buscando patentes do inventor '{inventor_name}'...")
    print(f"   [URL]: {search_url}")

    search_response = make_ops_request(search_url, headers, f"Busca {inventor_name}")

    total_patents_found = 0
    patent_ids = []

    if search_response and search_response.status_code == 200:
        try:
            search_data = xmltodict.parse(search_response.text)

            # Debug: salvar resposta para análise
            with open('debug_search_response.xml', 'w', encoding='utf-8') as debug_file:
                debug_file.write(search_response.text)

            total_patents_found = int(
                search_data.get('ops:world-patent-data', {}).get('ops:biblio-search', {}).get('@total-result-count', 0))

            print(f"   [RESULTADO]: {total_patents_found} patentes encontradas no portfólio total.")

            biblio_search = search_data.get('ops:world-patent-data', {}).get('ops:biblio-search', {})

            # Tentar diferentes estruturas de resposta
            search_result = biblio_search.get('ops:search-result', {})

            # Estrutura 1: ops:publication-reference
            hits = search_result.get('ops:publication-reference', [])

            # Estrutura 2: exchange-documents
            if not hits:
                exchange_docs = search_result.get('exchange-documents', {})
                if exchange_docs:
                    # Se já for lista, usa direto
                    if isinstance(exchange_docs, list):
                        hits = exchange_docs
                    else:
                        hits = exchange_docs.get('exchange-document', [])

            # Estrutura 3: Direto no biblio-search
            if not hits:
                hits = biblio_search.get('ops:publication-reference', [])

            # Estrutura 4: Verificar se search-result tem exchange-document direto
            if not hits:
                hits = search_result.get('exchange-document', [])

            if isinstance(hits, dict):
                hits = [hits]

            print(f"   [DEBUG HITS]: Encontrados {len(hits)} resultados para processar")

            for idx, hit in enumerate(hits):
                # Tentar extrair document-id de diferentes locais
                doc_id_list = hit.get('document-id', [])

                # Se não encontrou, tentar em bibliographic-data
                if not doc_id_list:
                    bib_data = hit.get('bibliographic-data', {})
                    pub_ref = bib_data.get('publication-reference', {})
                    doc_id_list = pub_ref.get('document-id', [])

                if isinstance(doc_id_list, dict):
                    doc_id_list = [doc_id_list]

                for doc_id in doc_id_list:
                    doc_num = doc_id.get('doc-number')
                    if doc_num:
                        patent_ids.append(doc_num)
                        print(f"      [{idx + 1}] Adicionado: {doc_num}")
                        break

        except Exception as e:
            print(f"   [ERRO PARSING BUSCA]: {e}")
            import traceback
            traceback.print_exc()
            return {
                'portfolio_size': 0,
                'recency_growth_rate': 0,
                'quality_avg_cites': 0,
                'coverage_avg_family': 0,
                'total_forward_cites': 0,
                'total_backward_cites': 0,
                'avg_forward_cites': 0,
                'avg_backward_cites': 0,
                'years_active': 0,
                'first_patent_year': 'N/A',
                'last_patent_year': 'N/A',
                'patents_last_5_years': 0
            }
    else:
        print(
            f"   [ALERTA]: Nenhum resultado na busca. Status: {search_response.status_code if search_response else 'None'}")

    if not patent_ids:
        print(f"   [ALERTA PORTFÓLIO]: Nenhuma patente encontrada na amostra.")
        return {
            'portfolio_size': total_patents_found,
            'recency_growth_rate': 0,
            'quality_avg_cites': 0,
            'coverage_avg_family': 0,
            'total_forward_cites': 0,
            'total_backward_cites': 0,
            'avg_forward_cites': 0,
            'avg_backward_cites': 0,
            'years_active': 0,
            'first_patent_year': 'N/A',
            'last_patent_year': 'N/A',
            'patents_last_5_years': 0
        }

    # Processamento da amostra
    total_forward_cites = 0
    total_backward_cites = 0
    total_family_size = 0
    publication_years = {}
    current_year = datetime.datetime.now().year

    print(f"   [CALC. MÉTRICAS]: Processando {len(patent_ids)} patentes da amostra...")

    for idx, pub_id in enumerate(patent_ids, 1):
        print(f"      [{idx}/{len(patent_ids)}] Processando {pub_id}...")

        metrics = get_citation_and_date(pub_id, headers)

        total_forward_cites += metrics['forward_cites']
        total_backward_cites += metrics['backward_cites']

        if metrics['pub_date']:
            try:
                year = int(metrics['pub_date'][:4])
                publication_years[year] = publication_years.get(year, 0) + 1
            except (ValueError, TypeError):
                pass

        # Família
        family_url = f"{base_url}/family/publication/epodoc/{pub_id}"
        family_response = make_ops_request(family_url, headers, f"Família {pub_id}")

        if family_response and family_response.status_code == 200:
            try:
                family_data = xmltodict.parse(family_response.text)
                family_members_raw = family_data.get('ops:world-patent-data', {}).get('ops:patent-family', {}).get(
                    'ops:family-member', [])

                if isinstance(family_members_raw, dict):
                    family_members_raw = [family_members_raw]

                family_count = len(family_members_raw)
                total_family_size += family_count
            except Exception:
                pass

        time.sleep(1)

    sample_count = len(patent_ids)

    # Cálculo das métricas
    total_cites = total_forward_cites + total_backward_cites
    quality = round(total_cites / sample_count, 2) if sample_count > 0 else 0
    avg_forward = round(total_forward_cites / sample_count, 2) if sample_count > 0 else 0
    avg_backward = round(total_backward_cites / sample_count, 2) if sample_count > 0 else 0
    coverage = round(total_family_size / sample_count, 2) if sample_count > 0 else 0

    # Anos de atividade
    years_list = list(publication_years.keys())
    first_year = min(years_list) if years_list else 'N/A'
    last_year = max(years_list) if years_list else 'N/A'
    years_active = (last_year - first_year + 1) if isinstance(first_year, int) and isinstance(last_year, int) else 0

    # Patentes nos últimos 5 anos
    patents_last_5 = sum(count for year, count in publication_years.items() if year >= current_year - 5)

    # Recência (Taxa de Crescimento)
    year_end_A = current_year
    year_start_A = year_end_A - RECENCY_YEARS_PERIOD + 1
    year_start_B = year_start_A - RECENCY_YEARS_PERIOD

    patents_A = sum(count for year, count in publication_years.items() if year >= year_start_A and year <= year_end_A)
    patents_B = sum(count for year, count in publication_years.items() if year >= year_start_B and year < year_start_A)

    recency_growth_rate = 0.0
    if patents_B > 0:
        recency_growth_rate = round((patents_A - patents_B) / patents_B, 4)
    elif patents_A > 0:
        recent_years_with_patents = [year for year in publication_years.keys() if
                                     year >= year_start_A and year <= year_end_A]
        min_recent_year = min(recent_years_with_patents) if recent_years_with_patents else year_end_A
        years_active_recent = current_year - min_recent_year + 1
        recency_growth_rate = round(patents_A / years_active_recent, 4)

    print(f"   [MÉTRICAS]: Qualidade: {quality}, Cobertura: {coverage}, Recência: {recency_growth_rate}")

    return {
        'portfolio_size': total_patents_found,
        'recency_growth_rate': recency_growth_rate,
        'quality_avg_cites': quality,
        'coverage_avg_family': coverage,
        'total_forward_cites': total_forward_cites,
        'total_backward_cites': total_backward_cites,
        'avg_forward_cites': avg_forward,
        'avg_backward_cites': avg_backward,
        'years_active': years_active,
        'first_patent_year': first_year,
        'last_patent_year': last_year,
        'patents_last_5_years': patents_last_5
    }


# === FLUXO PRINCIPAL ===
if __name__ == "__main__":

    if not get_access_token():
        print("\n❌ O script não pode continuar sem um Access Token válido.")
        exit()

    # Lê lista de inventores
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            inventors = [line.strip() for line in f.readlines() if line.strip()]

    except FileNotFoundError:
        print(f"\n❌ ERRO: Arquivo de entrada não encontrado: {INPUT_FILE}")
        exit()

    print(f"\n📋 Total de inventores a processar: {len(inventors)}\n")

    # Cria arquivo CSV de saída
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as csvfile:

        fieldnames = [
            'inventor_name',
            'portfolio_size',
            'recency_growth_rate',
            'quality_avg_cites',
            'coverage_avg_family',
            'total_forward_cites',
            'total_backward_cites',
            'avg_forward_cites',
            'avg_backward_cites',
            'years_active',
            'first_patent_year',
            'last_patent_year',
            'patents_last_5_years'
        ]

        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for i, inventor_name in enumerate(inventors, 1):
            print(f"\n[{i}/{len(inventors)}] ========== Processando Inventor: {inventor_name} ==========")

            # Extrai métricas do inventor
            metrics = get_inventor_portfolio_metrics(inventor_name)

            # Prepara dados para escrita
            row_data = {
                'inventor_name': inventor_name,
                'portfolio_size': metrics['portfolio_size'],
                'recency_growth_rate': metrics['recency_growth_rate'],
                'quality_avg_cites': metrics['quality_avg_cites'],
                'coverage_avg_family': metrics['coverage_avg_family'],
                'total_forward_cites': metrics['total_forward_cites'],
                'total_backward_cites': metrics['total_backward_cites'],
                'avg_forward_cites': metrics['avg_forward_cites'],
                'avg_backward_cites': metrics['avg_backward_cites'],
                'years_active': metrics['years_active'],
                'first_patent_year': metrics['first_patent_year'],
                'last_patent_year': metrics['last_patent_year'],
                'patents_last_5_years': metrics['patents_last_5_years']
            }

            writer.writerow(row_data)

            print(f"   ✅ Dados salvos para {inventor_name}")

            # Pausa entre inventores para não sobrecarregar a API
            time.sleep(3)

    print(f"\n✨ Processamento concluído! Resultados salvos em: {OUTPUT_FILE}")
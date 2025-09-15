import json
import re
from selenium import webdriver
from time import sleep
from bs4 import BeautifulSoup

def extract_patents_from_terminal_txt(file_path):
    """Extrai os dados das patentes já processadas do arquivo terminal.txt"""
    patents = []
    
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Encontra todos os blocos JSON no arquivo
    # Procura por padrões que começam com "Acessando URL:" seguido de JSON
    pattern = r'Acessando URL: (https://patents\.google\.com/patent/[^\n]+)\n(\{[^}]*(?:\{[^}]*\}[^}]*)*\})'
    matches = re.findall(pattern, content, re.DOTALL)
    
    for url, json_str in matches:
        try:
            # Limpa e corrige o JSON se necessário
            json_str = re.sub(r',\s*\]', ']', json_str)  # Remove vírgulas antes de ]
            json_str = re.sub(r',\s*\}', '}', json_str)  # Remove vírgulas antes de }
            
            patent_data = json.loads(json_str)
            patents.append(patent_data)
            print(f"Extraído: {patent_data.get('id', 'ID não encontrado')}")
        except json.JSONDecodeError as e:
            print(f"Erro ao decodificar JSON para URL {url}: {e}")
            continue
    
    return patents

def get_processed_urls_from_patents(patents):
    """Retorna um set com as URLs já processadas"""
    processed_urls = set()
    for patent in patents:
        if 'url' in patent:
            processed_urls.add(patent['url'])
    return processed_urls

def scrape_remaining_patents(urls_file, processed_urls, existing_patents):
    """Continua o scraping das URLs que não foram processadas"""
    
    driver = webdriver.Chrome()
    
    with open(urls_file, 'r') as file:
        all_urls = [line.strip() for line in file]
    
    # Filtra apenas as URLs que ainda não foram processadas
    remaining_urls = [url for url in all_urls if url not in processed_urls]
    
    print(f"Total de URLs: {len(all_urls)}")
    print(f"URLs já processadas: {len(processed_urls)}")
    print(f"URLs restantes: {len(remaining_urls)}")
    
    patents = existing_patents.copy()
    
    try:
        for i, url in enumerate(remaining_urls):
            print(f"Processando [{i+1}/{len(remaining_urls)}]: {url}")
            
            driver.get(url)
            sleep(3)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            patent = {}

            try:
                patent['id'] = soup.find(id="pubnum").get_text(strip=True)
            except:
                patent['id'] = url.split('/')[-2] if url.split('/')[-2] else "ID_NOT_FOUND"
            
            try:
                patent['title'] = soup.find('meta', {'name': 'DC.title'})['content']
            except:
                patent['title'] = "Título não encontrado"
            
            patent['url'] = url
            
            try:
                patent['date'] = soup.find('meta', {'name': 'DC.date'})['content']
            except:
                patent['date'] = "Data não encontrada"
            
            # Extrai citações de patentes
            patent_citations = []
            patent_citations_section = soup.find('h3', id="patentCitations")
            if patent_citations_section:
                citations_table = patent_citations_section.find_next('div', class_='responsive-table')
                if citations_table:
                    state_modifiers = citations_table.find_all('state-modifier')
                    for modifier in state_modifiers:
                        data_result = modifier.get('data-result', '')
                        if 'patent/' in data_result:
                            patent_id = data_result.split('patent/')[-1].split('/')[0]
                            patent_citations.append(patent_id)
            
            # Extrai patentes que citam esta
            cited_by = []
            cited_by_section = soup.find('h3', id="citedBy")
            if cited_by_section:
                cited_by_table = cited_by_section.find_next('div', class_='responsive-table')
                if cited_by_table:
                    state_modifiers = cited_by_table.find_all('state-modifier')
                    for modifier in state_modifiers:
                        data_result = modifier.get('data-result', '')
                        if 'patent/' in data_result:
                            patent_id = data_result.split('patent/')[-1].split('/')[0]
                            cited_by.append(patent_id)
            
            patent['patent_citations'] = patent_citations
            patent['cited_by'] = cited_by
            
            print(json.dumps(patent, indent=4, ensure_ascii=False))
            patents.append(patent)
            
            # Salva incrementalmente a cada 10 patentes processadas
            if (i + 1) % 10 == 0:
                with open('./webscrapping/patentes_backup.json', 'w', encoding='utf-8') as f:
                    json.dump(patents, f, ensure_ascii=False, indent=4)
                print(f"Backup salvo após {i + 1} patentes processadas")
    
    except Exception as e:
        print(f"Erro durante o scraping: {e}")
    finally:
        driver.quit()
    
    return patents

def main():
    print("=== Iniciando processamento de patentes ===")
    
    # 1. Extrai patentes já processadas do terminal.txt
    print("1. Extraindo dados do terminal.txt...")
    existing_patents = extract_patents_from_terminal_txt('./webscrapping/terminal.txt')
    print(f"Encontradas {len(existing_patents)} patentes já processadas")
    
    # 2. Identifica URLs já processadas
    processed_urls = get_processed_urls_from_patents(existing_patents)
    
    # 3. Continua o scraping das URLs restantes
    print("2. Continuando scraping das URLs restantes...")
    all_patents = scrape_remaining_patents('./webscrapping/urls.txt', processed_urls, existing_patents)
    
    # 4. Salva o resultado final
    print("3. Salvando resultado final...")
    with open('./webscrapping/patentes.json', 'w', encoding='utf-8') as f:
        json.dump(all_patents, f, ensure_ascii=False, indent=4)
    
    print(f"=== Processamento concluído! Total de patentes: {len(all_patents)} ===")

if __name__ == "__main__":
    main()
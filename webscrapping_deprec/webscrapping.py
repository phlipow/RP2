from selenium import webdriver
from time import sleep
from bs4 import BeautifulSoup
import json

driver = webdriver.Chrome()

with open('./webscrapping/urls.txt', 'r') as file:
    urls = [line.strip() for line in file]

patents = []

for url in urls:

    print(f"Acessando URL: {url}")
    
    driver.get(url)
    sleep(3)
    
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    patent = {}

    patent['id'] = soup.find(id="pubnum").get_text(strip=True)
    patent['title'] = soup.find('meta', {'name': 'DC.title'})['content']
    patent['url'] = url
    patent['date'] = soup.find('meta', {'name': 'DC.date'})['content']
    
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

driver.quit()

with open('./webscrapping/patentes.json', 'w', encoding='utf-8') as f:
    json.dump(patents, f, ensure_ascii=False, indent=4)

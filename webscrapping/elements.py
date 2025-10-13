from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from collections import Counter
import spacy

nlp = spacy.load("pt_core_news_sm")

def extract_patent_data(soup):

#ID
    element = soup.find(id="pubnum")
    id = element.get_text(strip=True) if element else ""

#Title
    element = soup.find('h1', class_='scroll-target style-scope patent-result')
    title = element.get_text(strip=True) if element else ""

#URL
    element = soup.find("link", rel="canonical")
    url = element.get("href") if element else ""

#Abstract
    abstract = ""
    section = soup.find("section", id="abstract")
    if section:
        abstract_text = section.find("patent-text")
        if abstract_text:
            text_section = abstract_text.find("section", class_="flex")
            if text_section:
                abstract = text_section.get_text(strip=True)

#Description
    description = ""
    section = soup.find("section", id="description")
    if section:
        patent_text = section.find("patent-text")
        if patent_text:
            text_section = patent_text.find("section", class_="flex")
            if text_section:
                paragraphs = text_section.find_all("div", class_="description-paragraph")
                description_text = ""
                for p in paragraphs:
                    description_text += p.get_text(strip=True) + "\n\n"
                description = description_text.strip()

#Inventors
    inventors = []

    inventor_elements = soup.find_all("state-modifier")
    for element in inventor_elements:
        data_inventor = element.get("data-inventor")
        if data_inventor:
            link = element.find("a")
            if link:
                inventor_name = link.get_text(strip=True)
                if inventor_name and inventor_name not in inventors:
                    inventors.append(inventor_name)

    inventors_count = len(inventors)

#Citations
    citations = []

    citations_section = soup.find("h3", id="patentCitations")
    if citations_section:
        table = citations_section.find_next("div", class_="table style-scope patent-result")
        if table:
            rows = table.find_all("div", class_="tr style-scope patent-result")
            for row in rows:
                if "thead" in row.get("class", []) or "famheader" in str(row):
                    continue
                link_element = row.find("state-modifier")
                if link_element:
                    citation_id = link_element.find("a")
                    if citation_id:
                        citations.append(citation_id.get_text(strip=True))

    citations_count = len(citations)

#Cited by
    cited_by = []

    cited_section = soup.find("h3", id="citedBy")
    if cited_section:
        table = cited_section.find_next("div", class_="table style-scope patent-result")
        if table:
            rows = table.find_all("div", class_="tr style-scope patent-result")
            for row in rows:
                if "thead" in row.get("class", []) or "famheader" in str(row):
                    continue
                link_element = row.find("state-modifier")
                if link_element:
                    citation_id = link_element.find("a")
                    if citation_id:
                        cited_by.append(citation_id.get_text(strip=True))

    cited_by_count = len(cited_by)

#Concepts
    concepts = []

    concepts_section = soup.find("h3", id="concepts")
    if concepts_section:
        table = concepts_section.find_next("div", class_="table style-scope patent-result")
        if table:
            concept_rows = table.find_all("div", class_=lambda x: x and "conceptDomain" in " ".join(x) if isinstance(x, list) else "conceptDomain" in x)

            for row in concept_rows:
                concept_mention = row.find("concept-mention")
                if concept_mention:
                    concept_spans = concept_mention.find_all("span", class_="style-scope patent-result")
                    for span in concept_spans:
                        concept_text = span.get_text(strip=True)
                        if concept_text and concept_text not in concepts:
                            concepts.append(concept_text)

#Images
    image_tags = soup.select('section#thumbnails img')
    images_count = len(image_tags)

#Priority applications
    priority_applications = []

    priority_section = soup.find('h3', id='appsClaimingPriority')
    if priority_section:
        table = priority_section.find_next('div', class_='responsive-table style-scope patent-result')
        if table:
            rows = table.find_all('div', class_='tr style-scope patent-result')
            for row_div in rows:
                if row_div.find('span', class_='th style-scope patent-result'):
                    continue
                state = row_div.find('state-modifier')
                if state and state.has_attr('data-result'):
                    priority_applications.append(state['data-result'])
                else:
                    span = row_div.find('span', class_='td nowrap style-scope patent-result')
                    if span and span.get_text(strip=True):
                        priority_applications.append(span.get_text(strip=True))

    priority_applications_count = len(priority_applications)

#Title nouns count
    title_nouns_count = 0
    if nlp and title:
        doc = nlp(title)
        title_nouns_count = sum(1 for token in doc if token.pos_ == "NOUN")

# Description-title word overlap
    description_title_word_overlap = 0

    doc_desc = nlp(description)
    desc_words = [token.lemma_.lower() for token in doc_desc if token.is_alpha and not token.is_stop]

    word_freq = Counter(desc_words)

    top_10_words = [w for w, _ in word_freq.most_common(10)]

    doc_title = nlp(title)
    title_words = [token.lemma_.lower() for token in doc_title if token.is_alpha and not token.is_stop]

    description_title_word_overlap = sum(title_words.count(w) for w in top_10_words)

#Final Dict

    patent_data = {
        "id": id,
        "title": title,
        "url": url,
        "abstract": abstract,
        "description": description,
        "inventors": inventors,
        "inventors_count": inventors_count,
        "citations": citations,
        "citations_count": citations_count,
        "cited_by": cited_by,
        "cited_by_count": cited_by_count,
        "concepts": concepts,
        "images_count": images_count,
        "priority_applications": priority_applications,
        "priority_applications_count": priority_applications_count,
        "title_nouns_count": title_nouns_count,
        "description_title_word_overlap": description_title_word_overlap,
    }

    return patent_data

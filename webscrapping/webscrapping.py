from elements import extract_patent_data
from selenium import webdriver
from time import sleep
from bs4 import BeautifulSoup
import json
from threading import Thread, Lock
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class Scraper:

    def __init__(self, urls, num_threads=8, output_file='./webscrapping/patents.jsonl', ):
        self.remaining_urls = urls
        self.urls_lock = Lock()
        self.output_file = output_file
        self.buffer = []
        self.buffer_lock = Lock()
        self.workers = []
        for _ in range(num_threads):
            self.workers.append(Thread(target=self.worker, daemon=True))
        with open(self.output_file, 'w') as f:
            pass

    def worker(self):
        driver = webdriver.Chrome()
        while True:
            with self.urls_lock:
                if not self.remaining_urls:
                    break
                url = self.remaining_urls.pop()
            self.scrap(driver, url)
        driver.quit()

    def scrap(self, driver, url):
        driver.get(url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "pubnum")))
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        patent_data = extract_patent_data(soup)
        self.buffer_append(patent_data)

    def flush(self):
        with open(self.output_file, 'a', encoding='utf-8') as f:
            for item in self.buffer:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        self.buffer = []

    def buffer_append(self, data):
        with self.buffer_lock:
            self.buffer.append(data)
            if len(self.buffer) >= 10:
                self.flush()

    def run(self):
        for worker in self.workers:
            worker.start()
        for worker in self.workers:
            worker.join()
        self.flush()

if __name__ == "__main__":

    with open('./webscrapping/urls.txt', 'r') as f:
        urls = [line.strip() for line in f if line.strip()]

    scraper = Scraper(urls, num_threads=2)
    scraper.run()
    print("Scraping completed.")
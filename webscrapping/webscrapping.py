from selenium import webdriver
from time import sleep
from bs4 import BeautifulSoup
import json
from threading import Thread, Lock

class Scraper:

    def __init__(self, urls, num_threads=8, output_file='./webscrapping/patents.json', ):
        self.remaining_urls = urls
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
        while self.remaining_urls:
            url = self.remaining_urls.pop()
            self.scrap(driver, url)
        driver.quit()

    #TODO
    def scrap(self, driver, url):
        '''Extract patent data here and append to buffer'''

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
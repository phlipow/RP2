import time
import re
import pandas as pd
from tqdm import tqdm
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ---------- CONFIG ----------
file_path = r"C:\Users\ATAF IP\COMPRAS\wipo_with_methanol (1).xlsx"
sheet_name = "ResultSet"
# small delay between requests (increase if you get blocks)
DELAY_BETWEEN = 1.0
# timeout for element load
WAIT_TIMEOUT = 20
# ----------------------------

# Ler planilha
df = pd.read_excel(file_path, sheet_name=sheet_name)

# Garante que existe uma coluna B para armazenar o ID da patente e que ela aceita strings
if df.shape[1] < 2:
    df.insert(1, 'Patent_ID', pd.NA)
else:
    # renomeia a segunda coluna para um nome consistente (opcional)
    second_col = df.columns[1]
    if second_col != "Patent_ID":
        df.rename(columns={second_col: "Patent_ID"}, inplace=True)

df['Patent_ID'] = df['Patent_ID'].astype(object)  # evita FutureWarning ao atribuir strings

# Configurações do Chrome (headless)
options = Options()
# se sua versão do Chrome for antiga, substitua por "--headless"
# options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)
wait = WebDriverWait(driver, WAIT_TIMEOUT)

# Itera por todos os índices (inclui o índice 0 — ou seja, a "primeira" linha de dados)
for idx in tqdm(df.index[1850:1900             ].tolist(), desc="Extraindo patentes"):
    link = df.at[idx, df.columns[0]]

    # pula célula vazia ou valores óbvios não-URL
    if pd.isna(link):
        continue
    if not isinstance(link, str):
        link = str(link)
    if not link.lower().startswith("http"):
        tqdm.write(f"Pulando valor não-URL na Excel linha {idx+2}: {link!r}")
        continue

    time.sleep(5)
    try:
        driver.get(link)

        # tenta localizar o elemento principal
        text = None
        try:
            el = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.ps-page-header--subtitle--text"))
            )
            text = el.text.strip()
        except Exception:
            # fallback via JS
            text = driver.execute_script(
                "const e=document.querySelector('div.ps-page-header--subtitle--text'); return e?e.innerText:null;"
            )
            if not text:
                # outro fallback por XPath (caso a estrutura varie)
                elems = driver.find_elements(By.XPATH, "/html/body/div[2]/div[2]/form/div/h1/div/div[1]")
                if elems:
                    text = elems[0].text.strip()

        if not text:
            tqdm.write(f"⚠️ Elemento não encontrado na Excel linha {idx+2} ({link})")
            df.at[idx, "Patent_ID"] = pd.NA
            continue

        # extrai o identificador com regex (procura padrão tipo 'WO2015135046' ou 'BRPI...'):
        m = re.search(r'\b([A-Z]{1,5}\d{2,}[A-Z0-9\-]*)\b', text)
        if m:
            patent_id = m.group(1)
        else:
            # fallback: pega primeiro token que contenha letra+digito
            patent_id = None
            for t in text.split():
                if re.search(r'[A-Za-z]\d', t):
                    patent_id = t
                    break
            patent_id = patent_id or text.split()[0]

        df.at[idx, "Patent_ID"] = str(patent_id)
        tqdm.write(f"✅ {patent_id} extraído da Excel linha {idx+2}")

    except Exception as e:
        tqdm.write(f"⚠️ Erro na Excel linha {idx+2}: {e}")
        df.at[idx, "Patent_ID"] = pd.NA

    time.sleep(DELAY_BETWEEN)

driver.quit()

# Faz backup do arquivo original e grava a aba substituída
backup_path = file_path.replace(".xlsx", ".backup.xlsx")
df.to_excel(backup_path, sheet_name=sheet_name, index=False)

with pd.ExcelWriter(file_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
    df.to_excel(writer, sheet_name=sheet_name, index=False)

print("✅ Processo concluído. Backup salvo em:", backup_path)
print("Verifique a célula B2 (Excel) para confirmar que o primeiro registro foi salvo.")

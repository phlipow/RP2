import csv
import sys
import re
import pandas as pd

def clean_br_app_number(app_number):
    # Removes non-alphanumeric characters
    return re.sub(r'[^a-zA-Z0-9]', '', app_number)

def extract_doc_id(link):
    if pd.isna(link):
        return None
    match = re.search(r'docId=([a-zA-Z0-9]+)', str(link))
    if match:
        return match.group(1)
    return None

def process_ipcs(num_chars):
    input_wipo_filename = 'wipo_with_methanol.csv'
    input_mapping_filename = 'PATENTS WIPO TO GOOGLE FINALIZADO revisado.csv'
    output_filename = f'patent_ipc_classes_{num_chars}.csv'

    # Load the mapping file
    try:
        df_mapping = pd.read_csv(input_mapping_filename)
        # Extract docId from the 'LINK WIPO' column
        df_mapping['docId'] = df_mapping['LINK WIPO'].apply(extract_doc_id)
        
        # Drop rows where docId could not be extracted
        df_mapping.dropna(subset=['docId'], inplace=True)

        # Create a dictionary for faster lookup: docId -> GOOGLE_ID
        wipo_to_google_map = dict(zip(df_mapping['docId'], df_mapping['PATENTES ADAPTADAS PARA O GOOGLE PATENTS']))
        print(f"Loaded {len(wipo_to_google_map)} mappings from {input_mapping_filename}")
    except FileNotFoundError:
        print(f"Error: Mapping file {input_mapping_filename} not found. Please ensure it's in the current directory.")
        sys.exit(1)
    except KeyError as e:
        print(f"Error: Missing expected column in mapping file: {e}. Expected 'LINK WIPO' and 'PATENTES ADAPTADAS PARA O GOOGLE PATENTS'.")
        sys.exit(1)


    with open(input_wipo_filename, 'r', encoding='utf-8') as infile, \
         open(output_filename, 'w', newline='', encoding='utf-8') as outfile:

        # Skip metadata lines
        for _ in range(7):
            next(infile)

        reader = csv.reader(infile)
        writer = csv.writer(outfile)
        writer.writerow(['patent_id', 'ipc_class'])

        for row in reader:
            if not row:
                continue

            application_id_wipo = row[0] # This is the 'Application Id' from wipo_with_methanol.csv
            ipc_string = row[-1]

            patent_id = None
            
            if application_id_wipo in wipo_to_google_map:
                patent_id = wipo_to_google_map[application_id_wipo]
            else:
                print(f"Warning: Patent ID '{application_id_wipo}' from '{input_wipo_filename}' not found in mapping file '{input_mapping_filename}'. Skipping this entry.")
                continue # Skip this row if no mapping is found

            if patent_id and ipc_string:
                ipc_codes = [code.strip() for code in ipc_string.split(';')]
                for ipc_code in ipc_codes:
                    if len(ipc_code) >= num_chars:
                        ipc_class = ipc_code[:num_chars]
                        writer.writerow([patent_id, ipc_class])

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python process_ipcs.py <num_chars>")
        sys.exit(1)

    try:
        num_chars = int(sys.argv[1])
        process_ipcs(num_chars)
        print(f"Successfully processed IPCs with num_chars={num_chars}")
    except ValueError:
        print("Error: <num_chars> must be an integer.")
        sys.exit(1)
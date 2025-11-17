import pandas as pd

def find_missing_in_final_data():
    try:
        promising_patents_df = pd.read_csv('promising_patents_google_correct.csv')
        promising_patent_ids = set(promising_patents_df['promising_patent_id'])
    except FileNotFoundError:
        print("Error: 'promising_patents_google_correct.csv' not found.")
        return

    try:
        final_data_df = pd.read_csv('dados_patentes_final.csv', sep=';')
        final_data_patent_ids = set(final_data_df['patent_id'])
    except FileNotFoundError:
        print("Error: 'dados_patentes_final.csv' not found.")
        return
    except KeyError:
        print("Error: 'patent_id' column not found in 'dados_patentes_final.csv'.")
        return

    missing_patents = promising_patent_ids - final_data_patent_ids

    if missing_patents:
        print("Promising patents not found in 'dados_patentes_final.csv':")
        for patent_id in missing_patents:
            print(patent_id)
        
        with open('missing_in_final_data_correct.txt', 'w') as f:
            for patent_id in missing_patents:
                f.write(f"{patent_id}\n")
        print("\nList of missing patents saved to 'missing_in_final_data_correct.txt'")
    else:
        print("All promising patents were found in 'dados_patentes_final.csv'.")

if __name__ == '__main__':
    find_missing_in_final_data()
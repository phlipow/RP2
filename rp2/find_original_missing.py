import csv
import re
import pandas as pd

def create_reverse_mapping(mapping_file):
    """
    Creates a reverse mapping from new patent IDs to old patent IDs.
    """
    reverse_mapping = {}
    with open(mapping_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        try:
            next(reader)  # Skip header
        except StopIteration:
            return {} # Empty file
        for row in reader:
            if len(row) < 3:
                continue
            link = row[0]
            new_id = row[2]
            # Extract the docId from the link
            match = re.search(r'docId=([A-Z0-9]+)', link)
            if match:
                old_id = match.group(1)
                reverse_mapping[new_id] = old_id
    return reverse_mapping

def find_original_missing(missing_file, reverse_mapping, final_data_file):
    """
    Finds which of the original patent IDs are present in the final data file.
    """
    with open(missing_file, 'r', encoding='utf-8') as f:
        missing_remapped_ids = {line.strip() for line in f}

    original_ids_to_check = []
    for remapped_id in missing_remapped_ids:
        original_id = reverse_mapping.get(remapped_id)
        if original_id:
            original_ids_to_check.append(original_id)
        else:
            # This case should ideally not happen if the remapping was complete
            # but as a fallback, we check the remapped_id itself if no original is found
            original_ids_to_check.append(remapped_id)

    try:
        final_data_df = pd.read_csv(final_data_file, sep=';')
        final_data_patent_ids = set(final_data_df['patent_id'])
    except FileNotFoundError:
        print(f"Error: '{final_data_file}' not found.")
        return
    except KeyError:
        print(f"Error: 'patent_id' column not found in '{final_data_file}'.")
        return

    found_originals = []
    not_found_originals = []
    for original_id in original_ids_to_check:
        if original_id in final_data_patent_ids:
            found_originals.append(original_id)
        else:
            not_found_originals.append(original_id)

    if found_originals:
        print("The following original patent IDs were found in 'dados_patentes_final.csv':")
        for patent_id in found_originals:
            print(patent_id)
    else:
        print("None of the original patent IDs for the missing remapped patents were found in 'dados_patentes_final.csv'.")

    if not_found_originals:
        print("\nThe following original patent IDs were NOT found in 'dados_patentes_final.csv':")
        for patent_id in not_found_originals:
            print(patent_id)


if __name__ == '__main__':
    reverse_mapping = create_reverse_mapping('PATENTS WIPO TO GOOGLE FINALIZADO revisado.csv')
    find_original_missing('missing_in_final_data_correct.txt', reverse_mapping, 'dados_patentes_final.csv')

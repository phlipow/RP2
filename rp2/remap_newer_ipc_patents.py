import csv
import re
import pandas as pd

def create_mapping(mapping_file):
    """
    Creates a mapping from old patent IDs to new patent IDs.
    """
    mapping = {}
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
                mapping[old_id] = new_id
    return mapping

def remap_patents(input_file, output_file, mapping):
    """
    Remaps patent IDs from the input file and saves them to the output file.
    """
    try:
        df = pd.read_csv(input_file)
    except FileNotFoundError:
        print(f"Error: '{input_file}' not found.")
        return
    
    # Get unique patent ids from the input file
    unique_patent_ids = df['patent_id'].unique()
    
    remapped_ids = []
    unmapped_ids = []
    for old_id in unique_patent_ids:
        new_id = mapping.get(str(old_id)) # Ensure old_id is a string for matching
        if new_id:
            remapped_ids.append(new_id)
        else:
            unmapped_ids.append(old_id)

    # Save the remapped IDs to a new CSV file
    if remapped_ids:
        remapped_df = pd.DataFrame({'promising_patent_id': remapped_ids})
        remapped_df.to_csv(output_file, index=False)
        print(f"Remapped {len(remapped_ids)} patent IDs and saved to {output_file}")
    else:
        print("No patent IDs could be remapped.")

    if unmapped_ids:
        print(f"\nCould not find a mapping for {len(unmapped_ids)} patent IDs:")
        #for patent_id in unmapped_ids:
            #print(patent_id)


if __name__ == '__main__':
    mapping = create_mapping('PATENTS WIPO TO GOOGLE FINALIZADO revisado.csv')
    remap_patents('patents_with_newer_ipc.csv', 'patents_with_newer_ipc_google.csv', mapping)

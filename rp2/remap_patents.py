import csv
import re

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
    Remaps patent IDs from the input file and writes them to the output file.
    """
    with open(input_file, 'r', encoding='utf-8') as f_in, \
         open(output_file, 'w', encoding='utf-8', newline='') as f_out:
        reader = csv.reader(f_in)
        writer = csv.writer(f_out)
        try:
            header = next(reader)
            writer.writerow(['promising_patent_id'])
        except StopIteration:
            return # Empty file
        
        for row in reader:
            if not row:
                continue
            old_id = row[0]
            new_id = mapping.get(old_id, old_id) # Keep old id if no mapping found
            writer.writerow([new_id])

if __name__ == '__main__':
    mapping = create_mapping('PATENTS WIPO TO GOOGLE FINALIZADO revisado.csv')
    remap_patents('promising_patents.csv', 'promising_patents_google_correct.csv', mapping)
    print("Remapping complete. Output written to promising_patents_google_correct.csv")

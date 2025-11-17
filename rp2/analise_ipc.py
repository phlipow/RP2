
import pandas as pd
import re

def normalize_wipo_ipc(ipc_code_standard):
    """
    Normalizes a standard IPC code (e.g., C12P 7/06) to the compact inventory format (e.g., C12P0007060000).
    """
    if not isinstance(ipc_code_standard, str):
        return ipc_code_standard

    match = re.match(r'([A-H][0-9]{2}[A-Z])\s*(\d{1,4})(?:\/(\d{1,6}))?', ipc_code_standard)
    if match:
        subclass = match.group(1)
        main_group = int(match.group(2))
        subgroup = match.group(3)

        main_group_padded = f"{main_group:04d}"
        
        subgroup_padded = ""
        if subgroup:
            # Pad subgroup with trailing zeros to 6 digits
            subgroup_padded = subgroup.ljust(6, '0') 
        else:
            # If no subgroup, default to 000000
            subgroup_padded = "000000" 

        return f"{subclass}{main_group_padded}{subgroup_padded}"
    return ipc_code_standard


def main():
    # Load the datasets
    patents_df = pd.read_csv('wipo_with_methanol.csv', skiprows=6)
    ipc_inventory_df = pd.read_csv('20260101_inventory_of_IPC_ever_used_symbols.csv', sep=';', names=['symbol', 'valid_from', 'extra'])

    # Rename columns for easier access
    patents_df.rename(columns={'Application Date': 'application_date', 'I P C': 'ipc'}, inplace=True)

    # Convert date columns to datetime objects
    patents_df['application_date'] = pd.to_datetime(patents_df['application_date'], format='%d.%m.%Y', errors='coerce')
    ipc_inventory_df['valid_from'] = pd.to_datetime(ipc_inventory_df['valid_from'], format='%Y%m%d', errors='coerce')

    # Create a dictionary for faster IPC date lookup directly from the inventory's 'symbol' column
    ipc_date_map = ipc_inventory_df.set_index('symbol')['valid_from'].to_dict()

    # List to store patents with newer IPC codes
    patents_with_newer_ipc = []
    
    # List to store IPCs not found in the inventory
    ipc_not_found = []

    # Regex to extract valid IPC codes from the WIPO file (standard format)
    ipc_extract_regex = re.compile(r'([A-H][0-9]{2}[A-Z]\s*\d{1,4}(?:\/\d{1,6})?)')


    # Iterate through each patent
    for _, row in patents_df.iterrows():
        application_date = row['application_date']
        ipc_string = str(row['ipc'])

        if pd.isna(application_date):
            continue

        # Extract valid IPC codes from the string using the regex
        extracted_ipc_codes = ipc_extract_regex.findall(ipc_string)
        
        for code_standard_format in extracted_ipc_codes:
            code_standard_format = code_standard_format.strip()
            
            # Normalize the extracted standard IPC code to the compact format for lookup
            normalized_code = normalize_wipo_ipc(code_standard_format)

            if normalized_code in ipc_date_map:
                ipc_date = ipc_date_map[normalized_code]
                if pd.isna(ipc_date):
                    continue
                
                if ipc_date > application_date:
                    patents_with_newer_ipc.append(row)
                    break  # Move to the next patent once one newer IPC code is found
            else:
                ipc_not_found.append({'ipc_code_standard': code_standard_format, 'ipc_code_normalized_for_lookup': normalized_code, 'original_string': ipc_string})

    if patents_with_newer_ipc:
        # Create a DataFrame from the results
        result_df = pd.DataFrame(patents_with_newer_ipc)

        # Print the results
        print("Patents with IPC codes newer than their application dates:")
        print(result_df)

        # Save the results to a CSV file
        result_df.to_csv('patents_with_newer_ipc.csv', index=False)
        print("\nResults saved to 'patents_with_newer_ipc.csv'")
    else:
        print("No patents found with IPC codes newer than their application dates.")

    if ipc_not_found:
        # Save the not found IPCs to a CSV file
        ipc_not_found_df = pd.DataFrame(ipc_not_found)
        ipc_not_found_df.to_csv('ipc_not_found.csv', index=False)
        print(f"\nFound {len(ipc_not_found)} IPC codes that were not in the inventory file. See 'ipc_not_found.csv' for the list.")
    else:
        print("\nAll IPC codes were found in the inventory file.")


if __name__ == '__main__':
    main()

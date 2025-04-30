import pdfplumber
import csv
import re
import io

def convert_date(date_str):
    """
    Converts a date string from dd.mm.yy to dd/mm/20yy.
    """
    parts = date_str.split(".")
    if len(parts) == 3:
        day, month, year = parts
        if len(year) == 2:
            year = "20" + year
        return f"{day}/{month}/{year}"
    return date_str

def is_date(date_str):
    """
    Returns True if the string is in the expected date format dd.mm.yy.
    """
    return bool(re.match(r"^\d{2}\.\d{2}\.\d{2}$", date_str.strip()))

def reformat_number(num_str):
    """
    Reformats a number string to have dot as thousand separator and comma as decimal separator.
    """
    if not num_str or num_str.strip() == "":
        return "0"
    temp = num_str.replace(".", "").replace(",", ".")
    try:
        value = float(temp)
        formatted = f"{value:,.2f}"
        formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
        return formatted
    except ValueError:
        return num_str

def is_valid_number(num_str):
    """
    Validates that the number string is in a proper format.
    """
    num_str = num_str.strip()
    pattern = r"^\d+(?:\.\d{3})*,\d{2}$"
    return bool(re.match(pattern, num_str))

def extract_table_standard(pdf_file):
    """
    Extracts table rows from the PDF using explicit vertical lines.
    """
    table_settings = {
        "vertical_strategy": "explicit",
        "horizontal_strategy": "lines",
        "explicit_vertical_lines": [25, 68, 120, 174, 180, 240, 243, 525],
        "snap_tolerance": 3,
    }
    all_rows = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            table = page.extract_table(table_settings)
            if table:
                all_rows.extend(table)
    return all_rows

def process_extracted_rows(rows):
    """
    Processes extracted rows to create a list of transaction dictionaries.
    """
    transactions = []
    current_transaction = None
    forbidden_desc = {"SALDO FINALE", "SALDO INIZIALE"}
    for row in rows:
        cleaned = [cell.strip() if cell else "" for cell in row]
        if all(cell == "" for cell in cleaned):
            continue
        if cleaned[0]:
            if current_transaction is not None:
                if current_transaction["Descrizione"].strip().upper() not in forbidden_desc:
                    transactions.append(current_transaction)
                current_transaction = None
            if not is_date(cleaned[0]):
                continue
            raw_uscite = cleaned[2]
            raw_entrate = cleaned[4]
            if raw_uscite and not is_valid_number(raw_uscite):
                continue
            if raw_entrate and not is_valid_number(raw_entrate):
                continue
            if cleaned[5].strip().upper() in forbidden_desc:
                continue
            date = convert_date(cleaned[0])
            uscite = reformat_number(raw_uscite) if raw_uscite else "0"
            entrate = reformat_number(raw_entrate) if raw_entrate else "0"
            current_transaction = {
                "Data": date,
                "Descrizione": cleaned[5],
                "Uscite": uscite,
                "Entrate": entrate,
            }
        else:
            if all(not cell for cell in cleaned[:5]) and cleaned[5]:
                if current_transaction is not None:
                    current_transaction["Descrizione"] += " " + cleaned[5]
    if current_transaction is not None:
        if current_transaction["Descrizione"].strip().upper() not in forbidden_desc:
            transactions.append(current_transaction)
    return transactions

def process_pdf(pdf_file):
    """
    Processes the uploaded PDF file-like object and returns CSV content as a string.
    """
    rows = extract_table_standard(pdf_file)
    transactions = process_extracted_rows(rows)
    
    # Clean up any newlines in Descrizione fields
    for t in transactions:
        t["Descrizione"] = t["Descrizione"].replace('\n', ' ').replace('\\n', ' ').strip()
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["Data", "Descrizione", "Uscite", "Entrate"], delimiter=";")
    writer.writeheader()
    for t in transactions:
        writer.writerow(t)
    return output.getvalue()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        with open(pdf_path, "rb") as f:
            csv_content = process_pdf(f)
        print(csv_content)
    else:
        print("Usage: python EcCreditAgricole.py <pdf_file>")

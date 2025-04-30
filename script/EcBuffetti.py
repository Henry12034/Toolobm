import re
import csv
import pdfplumber
import io

def extract_table_standard(pdf_file):
    """
    Extracts the table rows using a 'standard' horizontal strategy
    (lines-based) and explicit vertical lines.
    """
    table_settings = {
        "vertical_strategy": "explicit",
        "horizontal_strategy": "lines",
        "explicit_vertical_lines": [59, 95, 116, 273, 428, 479, 504, 553],
        "snap_tolerance": 3,
    }
    all_rows = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            table = page.extract_table(table_settings)
            if table:
                all_rows.extend(table)
    return all_rows

def parse_eu(num_str):
    """
    Converts a European style number string (e.g. "3.793,67") to a float.
    """
    num_str = num_str.strip()
    if not num_str:
        return 0.0
    num_str = num_str.replace('.', '')  # remove thousand separators
    num_str = num_str.replace(',', '.')  # replace comma with dot
    try:
        return float(num_str)
    except ValueError:
        return 0.0

def format_eu(value):
    """
    Formats a float into European number format (e.g. 3793.67 -> "3.793,67").
    """
    s = f"{value:,.2f}"
    s = s.replace(',', 'X').replace('.', ',').replace('X', '.')
    return s

def process_rows(rows):
    """
    Processes extracted rows and returns a list of dictionaries with keys:
    Data, Descrizione, Entrate, Uscite.
    """
    transactions = []
    date_regex = re.compile(r'\d{2}/\d{2}/\d{4}')
    for row in rows:
        if len(row) < 7:
            continue
        if not date_regex.match(row[0].strip()):
            continue
        data_value = row[0].strip()
        descr = row[2].strip()
        # Replace newlines with spaces
        descr = descr.replace('\n', ' ').replace('\\n', ' ').strip()
        if descr in ["SALDO INIZIALE", "SALDO FINALE"]:
            continue
        entrate_str = row[4].strip() if len(row) > 4 else ""
        uscite_str = row[6].strip() if len(row) > 6 else ""
        entrate = parse_eu(entrate_str) if entrate_str else 0.0
        uscite = parse_eu(uscite_str) if uscite_str else 0.0
        transactions.append({
            "Data": data_value,
            "Descrizione": descr,
            "Entrate": format_eu(entrate),
            "Uscite": format_eu(uscite)
        })
    return transactions

def process_pdf(pdf_file):
    """
    Processes the uploaded PDF file-like object and returns CSV content as a string.
    """
    rows = extract_table_standard(pdf_file)
    transactions = process_rows(rows)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["Data", "Descrizione", "Entrate", "Uscite"], delimiter=";")
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
        print("Usage: python EcBuffetti.py <pdf_file>")

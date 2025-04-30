import pdfplumber
import csv
import re
import io

def extract_table_explicit(pdf_file):
    table_settings = {
        "vertical_strategy": "explicit",
        "horizontal_strategy": "explicit",
        "explicit_vertical_lines": [30, 70, 110, 430, 500, 562],
        "explicit_horizontal_lines": list(range(100, 770, 10)),
        "snap_tolerance": 3,
    }
    all_rows = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            table = page.extract_table(table_settings)
            if table:
                all_rows.extend(table)
    return all_rows

def filter_valid_rows(rows):
    valid_rows = []
    date_regex = re.compile(r'^\d{2}\s\d{2}\s\d{2}$')
    for row in rows:
        if row is None or len(row) != 5:
            continue
        if row[0] and row[1] and date_regex.match(row[0].strip()) and date_regex.match(row[1].strip()):
            description = (row[2] or "").strip()
            description = description.replace('\n', ' ').replace('\\n', ' ').strip()
            if description not in ["SALDO INIZIALE A VS. CREDITO", "SALDO FINALE A VS. CREDITO"]:
                row[2] = description
                valid_rows.append(row)
    return valid_rows

def format_euro_number(num_str):
    if not num_str or not num_str.strip():
        return "0"
    num_str = num_str.strip()
    num_clean = num_str.replace('.', '').replace(',', '.')
    try:
        num = float(num_clean)
    except Exception:
        return num_str
    formatted = "{:,.2f}".format(num)
    formatted = formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
    return formatted

def process_pdf(pdf_file):
    """
    Processes the uploaded PDF file-like object and returns CSV content as a string.
    """
    rows = extract_table_explicit(pdf_file)
    valid_rows = filter_valid_rows(rows)
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    header = ['Data contabile', 'Data valuta', 'Descrizione', 'Uscite', 'Entrate']
    writer.writerow(header)
    for row in valid_rows:
        row[3] = format_euro_number(row[3])
        row[4] = format_euro_number(row[4])
        writer.writerow(row)
    return output.getvalue()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        with open(pdf_path, "rb") as f:
            csv_content = process_pdf(f)
        print(csv_content)
    else:
        print("Usage: python EcSELLA.py <pdf_file>")

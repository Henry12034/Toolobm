import pdfplumber
import csv
import re
import io

def extract_table_standard(pdf_file):
    """
    Extracts table rows using a 'standard' horizontal strategy (lines-based)
    and explicit vertical lines.
    """
    table_settings = {
        "vertical_strategy": "explicit",
        "horizontal_strategy": "lines",
        "explicit_vertical_lines": [22, 77, 158, 220, 250, 320, 340, 550],
        "snap_tolerance": 3,
    }
    all_rows = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            table = page.extract_table(table_settings)
            if table:
                all_rows.extend(table)
    return all_rows

def process_rows(rows):
    """
    Processes the extracted rows and returns a list of entries with:
    Data, Descrizione, Uscite, Entrate.
    """
    processed = []
    date_pattern = re.compile(r'\d{2}/\d{2}/\d{4}')
    for row in rows:
        if len(row) != 7:
            continue
        data = row[0]
        if not data or not date_pattern.match(data.strip()):
            continue
        descrizione = row[6]
        if descrizione:
            descrizione = descrizione.replace('\\n', ' ').replace('\n', ' ').strip()
        if descrizione in ["Saldo iniziale", "Saldo finale"]:
            continue
        uscita = row[2].strip() if row[2] and row[2].strip() != "" else "0"
        entrata = row[4].strip() if row[4] and row[4].strip() != "" else "0"
        if "%" in uscita or "%" in entrata:
            continue
        processed.append([data.strip(), descrizione, uscita, entrata])
    return processed

def process_pdf(pdf_file):
    """
    Processes the uploaded PDF file-like object and returns CSV content as a string.
    """
    rows = extract_table_standard(pdf_file)
    processed_rows = process_rows(rows)
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["Data", "Descrizione", "Uscite", "Entrate"])
    for row in processed_rows:
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
        print("Usage: python EcSONDRIO.py <pdf_file>")

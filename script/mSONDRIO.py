import pdfplumber
import csv
import re
import io

def extract_table_standard(pdf_file):
    """
    Extracts table rows from the PDF using a 'standard' horizontal (lines-based) strategy and explicit vertical lines.
    """
    table_settings = {
        "vertical_strategy": "explicit",
        "horizontal_strategy": "lines",
        "explicit_vertical_lines": [40, 80, 177, 358, 380, 455, 500, 556],
        "snap_tolerance": 3,
    }
    all_rows = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            table = page.extract_table(table_settings)
            if table:
                all_rows.extend(table)
    return all_rows

def process_pdf(pdf_file):
    """
    Processes the PDF file-like object and returns CSV content as a string.
    """
    rows = extract_table_standard(pdf_file)
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(["Data", "Descrizione", "Uscite", "Entrate"])
    
    date_pattern = re.compile(r"^\d{2}/\d{2}/\d{4}$")
    
    for row in rows:
        if len(row) < 7:
            continue
        if row[0].strip().upper() == "DATA":
            continue
        first_field = row[0].strip()
        if not date_pattern.match(first_field):
            continue
        data = first_field
        descrizione = row[2].strip()
        # Clean descrizione by replacing newlines with spaces
        descrizione = descrizione.replace('\n', ' ').replace('\\n', ' ').strip()
        uscite_raw = row[4].strip()
        entrate_raw = row[6].strip()
        def extract_numeric_value(text):
            m = re.search(r"([0-9.]+,[0-9]+)", text)
            if m:
                return m.group(1)
            return "0"
        uscite = extract_numeric_value(uscite_raw) if uscite_raw else "0"
        entrate = extract_numeric_value(entrate_raw) if entrate_raw else "0"
        writer.writerow([data, descrizione, uscite, entrate])
    return output.getvalue()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        with open(pdf_path, "rb") as f:
            csv_content = process_pdf(f)
        print(csv_content)
    else:
        print("Usage: python mSONDRIO.py <pdf_file>")

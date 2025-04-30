import pdfplumber
import re
import csv
import io

def format_currency(value):
    """
    Format a float value as a string with thousand separator '.' and decimal separator ','.
    """
    formatted = f"{value:,.2f}"
    formatted = formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
    return formatted

def extract_text_from_pdf(pdf_file):
    """
    Extract text from the PDF using pdfplumber.
    """
    full_text = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text(x_tolerance=1.5, y_tolerance=1.5)
            if text:
                full_text.append(text)
    return "\n".join(full_text)

def extract_transactions_from_text(text):
    """
    Processes the extracted text to group transaction entries.
    """
    lines = text.splitlines()
    transactions = []
    current_tx = None
    date_line_pattern = re.compile(r'^(\d{1,2}/\d{1,2})\s+(.*)')
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("Dal giorno") or line.startswith("TESA") or re.fullmatch(r'\d+/\d+', line):
            continue
        m = date_line_pattern.match(line)
        if m:
            if current_tx is not None:
                transactions.append(current_tx)
            current_tx = {
                "Data": m.group(1),
                "Descrizione": m.group(2),
                "Uscite": "0",
                "Entrate": "0"
            }
        else:
            if current_tx:
                current_tx["Descrizione"] += " " + line
    if current_tx:
        transactions.append(current_tx)
    
    amt_pattern = re.compile(r'([+-])\s*([\d.,]+)\s*EUR')
    for tx in transactions:
        amt_match = amt_pattern.search(tx["Descrizione"])
        if amt_match:
            sign = amt_match.group(1)
            amount_str = amt_match.group(2).replace(",", ".")
            try:
                amount = float(amount_str)
            except ValueError:
                amount = 0.0
            if sign == '+':
                tx["Entrate"] = format_currency(amount)
                tx["Uscite"] = format_currency(0)
            else:
                tx["Entrate"] = format_currency(0)
                tx["Uscite"] = format_currency(amount)
            tx["Descrizione"] = amt_pattern.sub("", tx["Descrizione"]).strip()
        
        # Ensure Descrizione has no newlines before writing to CSV
        tx["Descrizione"] = tx["Descrizione"].replace('\n', ' ').replace('\\n', ' ').strip()
    return transactions

def process_pdf(pdf_file):
    """
    Processes the uploaded PDF file-like object and returns CSV content as a string.
    """
    text = extract_text_from_pdf(pdf_file)
    transactions = extract_transactions_from_text(text)
    output = io.StringIO()
    fieldnames = ["Data", "Descrizione", "Uscite", "Entrate"]
    writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=";")
    writer.writeheader()
    for tx in transactions:
        writer.writerow(tx)
    return output.getvalue()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        with open(pdf_path, "rb") as f:
            csv_content = process_pdf(f)
        print(csv_content)
    else:
        print("Usage: python EcQONTO.py <pdf_file>")

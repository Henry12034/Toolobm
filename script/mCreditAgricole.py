import pdfplumber
import re
import csv
import io

def extract_text_from_pdf(pdf_file):
    """
    Extracts text from all pages of the PDF.
    """
    full_text = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text(x_tolerance=1.5, y_tolerance=1.5)
            if text:
                full_text.append(text)
    return "\n\n".join(full_text)

def format_number(amount_str):
    """
    Converts an amount string into a formatted string with Italian formatting.
    """
    normalized = amount_str.replace('.', '').replace(',', '.')
    try:
        value = float(normalized)
    except ValueError:
        return amount_str
    formatted = format(value, ",.2f")
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return formatted

def extract_transactions(text):
    """
    Extracts transactions that start with a date (dd/mm/yy) from the text.
    """
    transactions = []
    lines = text.splitlines()
    pattern = re.compile(r"^(\d{2}/\d{2}/\d{2})\s+(.+?)\s+(-?[\d\.,]+)\s*$")
    for line in lines:
        match = pattern.match(line)
        if match:
            date = match.group(1)
            description = match.group(2).strip()
            amount_str = match.group(3).strip()
            if amount_str.startswith("-"):
                formatted_amount = format_number(amount_str[1:])
                uscite = "0"
                entrate = formatted_amount
            else:
                formatted_amount = format_number(amount_str)
                uscite = formatted_amount
                entrate = "0"
            transactions.append({
                "Data": date,
                "Descrizione": description,
                "Uscite": uscite,
                "Entrate": entrate
            })
    return transactions

def extract_summary_transaction(text):
    """
    Extracts a summary transaction (if present) from the text.
    """
    transactions = []
    if "RIEPILOGO DEI SUOI MOVIMENTI" in text:
        lines = text.splitlines()
        summary_lines = []
        for i, line in enumerate(lines):
            if "RIEPILOGO DEI SUOI MOVIMENTI" in line:
                summary_lines = lines[i:i+10]
                break
        summary_date = None
        date_pattern = re.compile(r"^(\d{2}/\d{2}/\d{2})")
        for line in summary_lines:
            m = date_pattern.match(line)
            if m:
                summary_date = m.group(1)
                break
        imp_pattern = re.compile(r"^Impostadibollo\s+([\d\.,]+)")
        for line in summary_lines:
            m = imp_pattern.match(line)
            if m:
                amount_str = m.group(1)
                formatted_amount = format_number(amount_str)
                transactions.append({
                    "Data": summary_date if summary_date else "",
                    "Descrizione": "Impostadibollo",
                    "Uscite": formatted_amount,
                    "Entrate": "0"
                })
                break
    return transactions

def process_pdf(pdf_file):
    """
    Processes the Credit Agricole PDF and returns CSV content as a string.
    """
    text = extract_text_from_pdf(pdf_file)
    transactions = extract_transactions(text)
    summary_transactions = extract_summary_transaction(text)
    transactions.extend(summary_transactions)
    
    # Clean up descriptions to ensure they're on a single line
    for tx in transactions:
        tx["Descrizione"] = tx["Descrizione"].replace('\n', ' ').replace('\\n', ' ').strip()
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["Data", "Descrizione", "Uscite", "Entrate"], delimiter=";")
    writer.writeheader()
    for row in transactions:
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
        print("Usage: python mCreditAgricole.py <pdf_file>")

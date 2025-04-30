import pdfplumber
import re
import csv
import io

def extract_text_with_pdfplumber(pdf_file):
    """
    Extract text from a PDF using pdfplumber.
    """
    full_text = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text(x_tolerance=1.5, y_tolerance=1.5)
            if text:
                full_text.append(text)
    return "\n\n".join(full_text)

def format_amount(amount_float):
    """
    Format a float into the format 1.000,00.
    """
    formatted = f"{amount_float:,.2f}"
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return formatted

def parse_transactions(text):
    """
    Parse the extracted text and return a list of transaction dictionaries.
    Each transaction is expected to have fields: Data, Descrizione, and an Amount_str.
    Then, it creates two fields: Uscite and Entrate (depending on the sign).
    """
    transactions = []
    current_transaction = None
    transaction_re = re.compile(
        r'^(\d{2}/\d{2}/\d{4})\s+'      # date field 1
        r'(\d{2}/\d{2}/\d{4})\s+'       # date field 2 (ignored)
        r'([-]?[0-9\.,]+)\s+'           # amount field (with optional minus)
        r'EUR\s+'                      # literal "EUR"
        r'\S+\s+'                      # skip a field
        r'(.+)$'                       # description
    )
    lines = text.splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        match = transaction_re.match(line)
        if match:
            if current_transaction:
                transactions.append(current_transaction)
            data = match.group(1)
            amount_str = match.group(3)
            descr = match.group(4).strip()
            current_transaction = {
                "Data": data,
                "Descrizione": descr,
                "Amount_str": amount_str
            }
        else:
            if current_transaction:
                current_transaction["Descrizione"] += " " + line
    if current_transaction:
        transactions.append(current_transaction)

    parsed_transactions = []
    for tx in transactions:
        amt_str = tx["Amount_str"]
        cleaned_amt = amt_str.replace(".", "").replace(",", ".")
        try:
            amt = float(cleaned_amt)
        except ValueError:
            continue
        if amt < 0:
            uscite = format_amount(abs(amt))
            entrate = "0,00"
        else:
            entrate = format_amount(amt)
            uscite = "0,00"
        # Clean up description to ensure it's on a single line
        description = tx["Descrizione"].replace('\n', ' ').replace('\\n', ' ').strip()
        parsed_transactions.append({
            "Data": tx["Data"],
            "Descrizione": description,
            "Uscite": uscite,
            "Entrate": entrate
        })
    return parsed_transactions

def process_pdf(pdf_file):
    """
    Processes the PDF file-like object and returns a CSV string.
    """
    text = extract_text_with_pdfplumber(pdf_file)
    transactions = parse_transactions(text)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["Data", "Descrizione", "Uscite", "Entrate"], delimiter=";")
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
        print("Usage: python mBPM.py <pdf_file>")

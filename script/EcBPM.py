import re
import csv
import pdfplumber
import io

def extract_text_with_pdfplumber(pdf_file):
    """
    Extract text from all pages of the given PDF file-like object using pdfplumber.
    """
    full_text = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text(x_tolerance=1.5, y_tolerance=1.5)
            if text:
                full_text.append(text)
    return "\n".join(full_text)

def clean_description(description):
    """
    Cleans the transaction description by removing trailing or extra page-change info.
    """
    description = description.strip()
    if " pagina" in description:
        before_pagina = description.split(" pagina")[0].strip()
        after_app = ""
        if "APP *1 *2 *3" in description:
            after_app = description.split("APP *1 *2 *3")[-1].strip()
        description = (before_pagina + " " + after_app).strip()
    if " INDEX:" in description:
        description = description.split(" INDEX:")[0].strip()
    description = description.replace("30.09.2024 00393/000000009713 APP *1 *2 *3", "")
    return description.strip()

def extract_transactions_from_text(text):
    """
    Extracts transactions from the PDF text. Each transaction is expected to be in the format:
      dd/mm/yy dd/mm/yy dd/mm/yy [-] amount description
    Returns a list of dictionaries with keys: Data, Descrizione, Uscite, Entrate.
    """
    pattern = re.compile(
        r'^(\d{2}/\d{2}/\d{2})\s+'   # first date
        r'\d{2}/\d{2}/\d{2}\s+'      # second date
        r'\d{2}/\d{2}/\d{2}\s+'      # third date
        r'(-\s*)?'                  # optional minus sign
        r'([\d\.,]+)\s+'            # monetary amount
        r'(.+)$'                    # description
    )
    skip_phrases = [
        "pagina", "INDEX:", "Data di riferimento", "ATM DATA", "USCITE",
        "ENTRATE", "WEB CONTABILE", "NUMERI A DEBITO", "NUMERI A CREDITO",
        "RIASSUNTO SCALARE", "INTERESSI MATURATI", "RIEPILOGO", "DECORRENZA",
        "COMPETENZE LIQUIDATE", "TOTALE", "FONDO INTERBANCARIO",
        "30.09.2024 00393/000000009713", "APP *1 *2 *3",
    ]
    stop_phrases = [
        "SALDO FINALE", "Saldo contabile finale", "Saldo liquido finale",
        "Totale numeri del periodo",
    ]
    transactions = []
    current_record = None
    lines = text.splitlines()
    parsing = True

    for line in lines:
        if not parsing:
            break
        line = line.strip()
        if not line:
            continue
        if any(phrase in line for phrase in stop_phrases):
            if current_record:
                transactions.append(current_record)
                current_record = None
            parsing = False
            break
        match = pattern.match(line)
        if match:
            if current_record:
                transactions.append(current_record)
            data_value = match.group(1)
            is_negative = (match.group(2) is not None)
            amount = match.group(3)
            descr_line = match.group(4)
            descr_line = clean_description(descr_line)
            uscita, entrata = ("0", amount) if not is_negative else (amount, "0")
            current_record = {
                "Data": data_value,
                "Descrizione": descr_line,
                "Uscite": uscita,
                "Entrate": entrata
            }
        else:
            if current_record:
                if not any(phrase in line for phrase in skip_phrases):
                    current_record["Descrizione"] += " " + line
    if current_record:
        transactions.append(current_record)
    return transactions

def process_pdf(pdf_file):
    """
    Processes the uploaded PDF file-like object and returns CSV content as a string.
    """
    text = extract_text_with_pdfplumber(pdf_file)
    transactions = extract_transactions_from_text(text)
    
    # Ensure all descriptions are on a single line
    for transaction in transactions:
        transaction["Descrizione"] = transaction["Descrizione"].replace('\n', ' ').replace('\\n', ' ').strip()
    
    output = io.StringIO()
    fieldnames = ["Data", "Descrizione", "Uscite", "Entrate"]
    writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=";", quoting=csv.QUOTE_NONE, escapechar="\\")
    writer.writeheader()
    for transaction in transactions:
        writer.writerow(transaction)
    return output.getvalue()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        with open(pdf_path, "rb") as f:
            csv_content = process_pdf(f)
        print(csv_content)
    else:
        print("Usage: python EcBPM.py <pdf_file>")

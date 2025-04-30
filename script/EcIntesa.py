import sys
import os
import pytesseract  # Must be imported before using pytesseract
from io import BytesIO
import io
from pdf2image import convert_from_bytes
import cv2
import re
import csv
import pdfplumber
from PIL import Image
from pytesseract import Output
import shutil

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# Set up external executable paths using resource_path.
pytesseract.pytesseract.tesseract_cmd = resource_path(r"Tesseract-OCR/tesseract.exe")
poppler_path = resource_path(r"poppler-24.08.0/Library/bin")

#############################################
# OCR Extraction for Uscite and Entrate
#############################################
def extract_ocr_tokens_from_bytes(pdf_bytes):
    """
    Extract tokens from the PDF using OCR.
    Returns a list of dictionaries, each with keys "Uscite" and "Entrate".
    Instead of using a file path, this uses the PDF bytes and pdf2image.convert_from_bytes.
    """
    temp_dir = "temp_images"
    os.makedirs(temp_dir, exist_ok=True)

    # Convert PDF pages to images using pdf2image.convert_from_bytes.
    pages = convert_from_bytes(pdf_bytes, dpi=300, poppler_path=poppler_path)

    preprocessed_image_paths = []
    for i, page in enumerate(pages):
        page_path = os.path.join(temp_dir, f'page_{i+1}.png')
        page.save(page_path, 'PNG')

        # Load image in grayscale and apply Otsu's thresholding
        img_cv = cv2.imread(page_path, cv2.IMREAD_GRAYSCALE)
        _, thresh = cv2.threshold(img_cv, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        preprocessed_path = os.path.join(temp_dir, f'page_{i+1}_preprocessed.png')
        cv2.imwrite(preprocessed_path, thresh)
        preprocessed_image_paths.append(preprocessed_path)

    tokens_list = []
    for image_path in preprocessed_image_paths:
        img = cv2.imread(image_path)
        if img is None:
            continue
        # Get OCR data with bounding box information.
        data = pytesseract.image_to_data(img, config="--psm 6", output_type=Output.DICT)

        # Set horizontal boundaries based on document layout.
        addebiti_x_min, addebiti_x_max = 1650, 1790  # For "Addebiti" (Uscite)
        accrediti_x_min, accrediti_x_max = 2050, img.shape[1]  # For "Accrediti" (Entrate)

        # Pattern for a valid token (e.g. "1.234,56")
        valid_pattern = re.compile(r'^\d+(?:\.\d+)*,\d{2}$')

        tokens = []
        for i, text in enumerate(data['text']):
            token_text = text.strip()
            if token_text == "":
                continue
            left = data['left'][i]
            width = data['width'][i]
            center_x = left + width / 2
            if not any(char.isdigit() for char in token_text):
                continue
            if addebiti_x_min <= center_x <= addebiti_x_max:
                column = "Uscite"
            elif accrediti_x_min <= center_x <= accrediti_x_max:
                column = "Entrate"
            else:
                continue
            tokens.append({"order": i, "text": token_text, "column": column})
        tokens.sort(key=lambda t: t["order"])

        # Merge adjacent tokens if the next token (with the same column) starts with a comma.
        merged_tokens = []
        i = 0
        while i < len(tokens):
            token = tokens[i]
            merged_text = token["text"]
            if i + 1 < len(tokens) and tokens[i + 1]["column"] == token["column"] and tokens[i + 1]["text"].startswith(','):
                merged_text += tokens[i + 1]["text"]
                i += 2
            else:
                i += 1
            if valid_pattern.match(merged_text):
                if token["column"] == "Uscite":
                    merged_tokens.append({"Uscite": merged_text, "Entrate": "0"})
                else:
                    merged_tokens.append({"Uscite": "0", "Entrate": merged_text})
        tokens_list.extend(merged_tokens)
    shutil.rmtree(temp_dir)
    return tokens_list

#############################################
# Table Extraction for Data and Descrizione
#############################################
def extract_table_rows_from_bytes(pdf_bytes):
    """
    Uses pdfplumber to extract table rows from the PDF.
    Returns a list of dictionaries with keys "Data" and "Descrizione".
    """
    def extract_table_standard(file_bytes):
        table_settings = {
            "vertical_strategy": "explicit",
            "horizontal_strategy": "lines",
            "explicit_vertical_lines": [22, 62, 161, 350],
            "snap_tolerance": 3,
        }
        all_rows = []
        with pdfplumber.open(BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                table = page.extract_table(table_settings)
                if table:
                    all_rows.extend(table)
        return all_rows

    def is_valid_date(date_str):
        return re.match(r'^\d{2}\.\d{2}\.\d{4}$', date_str) is not None

    rows = extract_table_standard(pdf_bytes)
    extracted_rows = []
    for row in rows:
        if len(row) < 3:
            continue
        if is_valid_date(row[0]):
            # Clean descrizione by replacing newlines with spaces
            descrizione = row[2]
            if descrizione:
                descrizione = descrizione.replace('\n', ' ').replace('\\n', ' ').strip()
            extracted_rows.append({"Data": row[0], "Descrizione": descrizione})
    return extracted_rows

#############################################
# Main processing function for web usage.
#############################################
def process_pdf(pdf_file):
    """
    Processes the uploaded PDF file-like object and returns CSV content as a string.
    Combines OCR extraction (for Uscite/Entrate) and table extraction (for Data/Descrizione).
    """
    pdf_bytes = pdf_file.read()
    # Extract OCR tokens from the PDF bytes.
    ocr_tokens = extract_ocr_tokens_from_bytes(pdf_bytes)
    # Extract table rows from the PDF bytes.
    table_rows = extract_table_rows_from_bytes(pdf_bytes)
    # Combine rows by index. If counts differ, use the minimum number.
    min_rows = min(len(ocr_tokens), len(table_rows))
    combined_rows = []
    for i in range(min_rows):
        combined_rows.append({
            "Data": table_rows[i]["Data"],
            "Descrizione": table_rows[i]["Descrizione"],
            "Uscite": ocr_tokens[i]["Uscite"],
            "Entrate": ocr_tokens[i]["Entrate"]
        })
    # Write CSV data to a memory buffer.
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(["Data", "Descrizione", "Uscite", "Entrate"])
    for row in combined_rows:
        writer.writerow([row["Data"], row["Descrizione"], row["Uscite"], row["Entrate"]])
    return output.getvalue()

if __name__ == "__main__":
    # For testing via command-line: pass a PDF file path.
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        with open(pdf_path, "rb") as f:
            csv_content = process_pdf(f)
        print(csv_content)
    else:
        print("Usage: python EcIntesa.py <pdf_file>")

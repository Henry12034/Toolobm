import os
import sys
import importlib
from flask import Flask, render_template, request, jsonify, make_response
import io
import re # Import regular expressions module for sanitization

# --- A helper function for basic filename sanitization ---
def sanitize_filename(filename):
    """Removes potentially dangerous characters and ensures .csv extension."""
    # Remove characters that are problematic in filenames across OSes
    # Keep alphanumeric, underscore, hyphen, space
    sanitized = re.sub(r'[\\/*?:"<>|]', "", filename)
    # Replace multiple spaces with single space, strip leading/trailing whitespace
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    # Prevent names like '..', '.', etc.
    if not sanitized or sanitized in ('.', '..'):
        sanitized = "output" # Fallback name

    # Ensure it ends with .csv (case-insensitive check)
    if not sanitized.lower().endswith('.csv'):
        sanitized += ".csv"
    return sanitized
# -------------------------------------------------------


app = Flask(__name__)

# --- SCRIPT MAP ---
SCRIPT_MAP = {
    ("BPM", "Estratto conto"): "script.EcBPM",
    ("BPM", "Lista movimenti"): "script.mBPM",
    ("Credit Agricole", "Estratto conto"): "script.EcCreditAgricole",
    ("Credit Agricole", "Lista movimenti"): "script.mCreditAgricole",
    ("Qonto", "Estratto conto"): "script.EcQONTO",
    ("Sella", "Estratto conto"): "script.EcSELLA",
    ("Popolare di Sondrio", "Estratto conto"): "script.EcSONDRIO",
    ("Popolare di Sondrio", "Lista movimenti"): "script.mSONDRIO",
    ("Buffetti", "Estratto conto"): "script.EcBuffetti",
    ("Intesa San Paolo", "Estratto conto"): "script.EcIntesa"
}

# --- Pre-Processing Data ---
try:
    all_banche = sorted(list(set(k[0] for k in SCRIPT_MAP.keys())))
    available_docs_by_bank = {}
    for banca, tipo in SCRIPT_MAP.keys():
        available_docs_by_bank.setdefault(banca, []).append(tipo)
    for banca in available_docs_by_bank:
        available_docs_by_bank[banca].sort()
    if not all_banche:
        raise ValueError("Nessuna banca definita in SCRIPT_MAP.")
except Exception as e:
    print(f"Critical error in configuration: {e}")
    sys.exit(1)


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", all_banche=all_banche, available_docs_by_bank=available_docs_by_bank)


@app.route("/run_script", methods=["POST"])
def run_script():
    bank = request.form.get("bank")
    doc_type = request.form.get("doc_type")
    pdf_file = request.files.get("pdf_file") # Use .get for safety

    # === NEW: Get and sanitize the desired output filename ===
    output_filename_raw = request.form.get("output_filename", "output") # Default to 'output'
    safe_output_filename = sanitize_filename(output_filename_raw)
    # ========================================================

    if not bank or not doc_type or doc_type == "Nessun documento disponibile":
        return jsonify({"status": "error", "message": "Seleziona una banca e un tipo di documento valido."}), 400

    key = (bank, doc_type)
    if key not in SCRIPT_MAP:
        return jsonify({"status": "error", "message": f"La combinazione '{bank}' - '{doc_type}' non è valida."}), 400

    if not pdf_file: # Check if file exists in request.files
         return jsonify({"status": "error", "message": "Nessun file PDF inviato."}), 400
    if pdf_file.filename == "":
         return jsonify({"status": "error", "message": "Nome file PDF vuoto."}), 400 # Check filename specifically

    try:
        script_name = SCRIPT_MAP[key]
        module = importlib.import_module(script_name)

        if hasattr(module, "process_pdf") and callable(module.process_pdf):
            # Assuming process_pdf returns CSV content as string or bytes
            csv_content = module.process_pdf(pdf_file)

            response = make_response(csv_content)
            # === Use the sanitized filename in the header ===
            response.headers["Content-Disposition"] = f"attachment; filename=\"{safe_output_filename}\""
            # ===============================================
            response.headers["Content-Type"] = "text/csv"
            return response
        else:
            print(f"Script '{script_name}' non ha funzione process_pdf.") # Log server-side
            return jsonify({"status": "error", "message": f"Errore interno del server: script non configurato correttamente."}), 500

    except ModuleNotFoundError:
         print(f"Errore: Modulo '{script_name}' non trovato.") # Log server-side
         return jsonify({"status": "error", "message": f"Errore interno del server: modulo non trovato."}), 500
    except Exception as e:
        print(f"Errore esecuzione script {script_name}: {type(e).__name__}: {e}") # Log server-side detailed error
        # Consider logging traceback: import traceback; traceback.print_exc()
        # Return a more generic error message to the user
        return jsonify({"status": "error", "message": f"Errore durante l'elaborazione del file."}), 500


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)# Keep debug=True for development ONLY
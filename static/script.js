document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Elements ---
    const bankSelect = document.getElementById('bank');
    const docSelect = document.getElementById('doc_type');
    const fileInput = document.getElementById('pdf_file');
    const fileNameDisplay = document.getElementById('file-name-display');
    const outputFilenameInput = document.getElementById('output_filename');
    const fileInputButton = document.querySelector('.file-input-button');
    const uploadForm = document.getElementById('uploadForm');
    const submitButton = uploadForm.querySelector('button[type="submit"]');
    const statusDiv = document.getElementById('status');
    const loadingIndicator = document.getElementById('loading-indicator');
    // Theme Toggle Element
    const themeToggleButton = document.getElementById('theme-toggle');

    // --- Data (Passed from Flask) ---
    // const availableDocsByBank = { /* Injected by Flask via <script> tag in HTML */ };

    // --- Functions ---
    function updateDocTypes() {
        const selectedBank = bankSelect.value;
        // Ensure availableDocsByBank is accessible (defined in HTML script tag)
        const types = (typeof availableDocsByBank !== 'undefined' && availableDocsByBank[selectedBank]) ? availableDocsByBank[selectedBank] : [];

        // Clear previous options
        docSelect.innerHTML = "";

        if (types.length > 0) {
            types.forEach(type => {
                const option = document.createElement("option");
                option.value = type;
                option.text = type;
                docSelect.add(option);
            });
            docSelect.disabled = false;
        } else {
            const option = document.createElement("option");
            option.value = "";
            option.text = "Nessun documento disponibile";
            docSelect.add(option);
            docSelect.disabled = true;
        }
    }

    function showLoading(isLoading) {
        if (isLoading) {
            loadingIndicator.style.display = 'block';
            submitButton.disabled = true;
            statusDiv.textContent = ''; // Clear previous status
            statusDiv.className = 'status'; // Reset status class
        } else {
            loadingIndicator.style.display = 'none';
            submitButton.disabled = false;
        }
    }

    function showStatus(message, isError = false) {
         statusDiv.textContent = message;
         statusDiv.className = isError ? 'status error' : 'status success';
    }

    // --- Theme Handling Functions ---
    function applyTheme(theme) {
        if (theme === 'dark') {
            document.body.classList.add('dark-theme');
        } else {
            document.body.classList.remove('dark-theme');
        }
        // Icons are handled by CSS based on the body class
    }

    function toggleTheme() {
        const currentTheme = document.body.classList.contains('dark-theme') ? 'dark' : 'light';
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        applyTheme(newTheme);
        // Store preference
        try {
            localStorage.setItem('theme', newTheme);
        } catch (e) {
            console.warn("LocalStorage not available or disabled. Theme preference won't be saved.");
        }
    }

    // Load saved theme preference on page load
    function loadThemePreference() {
        try {
            const savedTheme = localStorage.getItem('theme');
            if (savedTheme) {
                applyTheme(savedTheme);
            } else {
                 // Optional: Check system preference if no local storage preference
                 // const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
                 // applyTheme(prefersDark ? 'dark' : 'light');
                applyTheme('light'); // Default to light if nothing saved or first visit
            }
        } catch (e) {
             console.warn("LocalStorage not available or disabled. Using default theme.");
             applyTheme('light'); // Default to light if localStorage fails
        }
    }

    // --- Event Listeners ---

    // Update document types when bank changes
    if (bankSelect) {
        bankSelect.addEventListener('change', updateDocTypes);
    }

    // Handle custom file input appearance AND prefill output name
    if (fileInput) {
        fileInput.addEventListener('change', () => {
            if (fileInput.files.length > 0) {
                const pdfFile = fileInput.files[0];
                const pdfFileName = pdfFile.name;
                if (fileNameDisplay) {
                    fileNameDisplay.value = pdfFileName; // Show filename in the read-only display
                    fileNameDisplay.title = pdfFileName;
                }

                // Prefill output filename input
                // Remove the .pdf extension (case-insensitive)
                const suggestedName = pdfFileName.replace(/\.pdf$/i, '');
                if (outputFilenameInput) {
                    outputFilenameInput.value = suggestedName;
                }

            } else {
                 if (fileNameDisplay) {
                    fileNameDisplay.value = '';
                    fileNameDisplay.title = '';
                 }
                // Clear output filename if no file selected
                if (outputFilenameInput) {
                    outputFilenameInput.value = '';
                }
            }
        });
    }

    // Theme toggle button listener
    if (themeToggleButton) {
        themeToggleButton.addEventListener('click', toggleTheme);
    }

    // Handle form submission with Fetch API
    if (uploadForm) {
        uploadForm.addEventListener('submit', async (event) => {
            event.preventDefault(); // Prevent traditional form submission

            const selectedBank = bankSelect ? bankSelect.value : null;
            const selectedDocType = docSelect ? docSelect.value : null;
            const pdfFile = fileInput ? fileInput.files[0] : null;
            const outputFilename = outputFilenameInput ? outputFilenameInput.value.trim() : null;

            // Basic Validation
            if (!selectedBank || !selectedDocType || selectedDocType === "Nessun documento disponibile") {
                showStatus("Per favore, seleziona una banca e un tipo di documento validi.", true);
                return;
            }
            if (!pdfFile) {
                showStatus("Per favore, seleziona un file PDF da caricare.", true);
                return;
            }
            if (!outputFilename) {
                showStatus("Per favore, inserisci un nome per il file CSV di output.", true);
                return;
            }
            // Simple check for potentially problematic characters (basic frontend check)
            if (/[\\/:*?"<>|]/.test(outputFilename)) {
                 showStatus("Il nome del file contiene caratteri non validi (\\ / : * ? \" < > |).", true);
                return;
            }

            showLoading(true);

            const formData = new FormData();
            formData.append('bank', selectedBank);
            formData.append('doc_type', selectedDocType);
            formData.append('pdf_file', pdfFile);
            formData.append('output_filename', outputFilename); // Append the output filename

            try {
                const response = await fetch('/run_script', {
                    method: 'POST',
                    body: formData
                    // No 'Content-Type' header needed, browser sets it for FormData
                });

                // Check if response indicates a file download (CSV)
                const contentType = response.headers.get("content-type");
                const contentDisposition = response.headers.get("content-disposition");

                if (response.ok && contentType && contentType.includes("text/csv")) {
                    // Extract filename from header (provided by the backend)
                    let filenameFromServer = "output.csv"; // Default fallback
                    if (contentDisposition) {
                        // Regex to handle quoted and unquoted filenames
                        const filenameMatch = contentDisposition.match(/filename\*?=['"]?([^'";]+)['"]?(?:;|$)/);
                        if (filenameMatch && filenameMatch[1]) {
                            // Decode URI component for potentially encoded filenames (e.g., UTF-8)
                            try {
                                filenameFromServer = decodeURIComponent(filenameMatch[1]);
                            } catch (e) {
                                filenameFromServer = filenameMatch[1]; // Use raw value if decoding fails
                                console.warn("Could not decode filename from Content-Disposition:", e);
                            }
                        }
                    }

                    // Create blob link to download
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.style.display = 'none';
                    a.href = url;
                    a.download = filenameFromServer; // Use filename from Content-Disposition
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    a.remove();

                    showStatus(`Elaborazione completata. Il file ${filenameFromServer} è stato scaricato.`, false);

                } else {
                    // Assume error JSON if not CSV and OK status
                    let errorData = { message: `Errore ${response.status}: ${response.statusText || 'Errore sconosciuto'}` }; // Default message
                    try {
                        // Try to parse potential JSON error from backend
                         if (contentType && contentType.includes("application/json")) {
                             errorData = await response.json();
                         } else {
                             // If not JSON, maybe read text? Handle based on expected error format
                             const errorText = await response.text();
                             if (errorText) {
                                errorData.message = errorText.substring(0, 200); // Limit length
                             }
                         }
                    } catch (parseError) {
                        console.error("Could not parse error response:", parseError);
                         // Use default error message already set
                    }
                     showStatus(`Errore durante l'elaborazione: ${errorData.message || 'Risposta non valida dal server.'}`, true);
                }

            } catch (error) {
                console.error("Fetch Error:", error);
                showStatus(`Errore di rete o connessione: ${error.message}`, true);
            } finally {
                showLoading(false);
            }
        }); // End form submit listener
    } // End if(uploadForm)

    // --- Initial Setup ---
    loadThemePreference(); // Apply theme preference ASAP
    if (bankSelect) {
        updateDocTypes(); // Populate doc types for the default selected bank on load
    }
    if (fileNameDisplay) {
        fileNameDisplay.value = "Nessun file selezionato"; // Initial placeholder text
    }
    // Placeholder for output name is set via HTML placeholder attribute

}); // End DOMContentLoaded
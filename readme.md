## RedMart Invoice Automation

This project automates the ingestion of RedMart invoice emails and logs their contents for bookkeeping.

### Workflow
1. **Gmail search** – `GetEmailAttachments` queries Gmail for the past *N* days (configurable via `EMAIL_LOOKBACK_DAYS`) looking for messages that match the RedMart invoice keyword and contain PDF attachments.
2. **Duplicate check** – For each PDF attachment, the script checks a target Google Drive folder and skips files that already exist there.
3. **Invoice extraction** – New PDFs are parsed by `ExtractInvoice`, which uses `pdfplumber` + an OpenAI model to extract line items (filename, delivery/dates, order number, quantity, unit price, totals, etc.). The script parses the JSON response and returns it as-is.
4. **Sheets logging** – Parsed rows are appended to a Google Sheet via `GoogleSheetsWriter`, one row per line item.
5. **Drive archival** – The PDF is uploaded to Google Drive for safekeeping.

### Setup
1. Create a Google Cloud OAuth client with Gmail, Drive `drive.file`, and Sheets scopes.
2. Place `credentials.json` and run `python main.py` once to generate `token.json`.
3. Define environment variables (`.env` or shell):
   - `EMAIL_LOOKBACK_DAYS`, `INVOICE_REGEX`, `PDF_MIME`
   - `DRIVE_FOLDER_ID`, `SPREADSHEET_ID`, `SHEET_NAME`
   - `OPENAI_API_KEY`, plus optional `TEST_SPREADSHEET_ID` / `TEST_SHEET_NAME`
4. Install dependencies: `pip install -r requirements.txt`

### Usage
- `python main.py` – run the full pipeline.
- `python -c "from sheets_writer import test_append_invoice_items; test_append_invoice_items()"` – sanity-check Sheets connectivity with a dummy row.

### Notes
- `token.json` caches OAuth tokens; delete it to re-authenticate with another Google account or scope set.
- The scripts assume UTF-8 PDFs where `pdfplumber` can extract text; adjust `_build_prompt` if invoice formats change.
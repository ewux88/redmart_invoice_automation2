# **Applying Data Science to Everyday Life: Building an LLM Automation to Organize My Groceries Spending**

Online grocery shopping is great — until you need to track your invoices.

Every RedMart order generates an email, a PDF invoice, and yet another tiny piece of admin work. If you're trying to manage household expenses, budget better, or keep tidy records, those PDFs matter… but manually opening and extracting them becomes tiring fast.

So I built a fully automated pipeline that takes me from **email → invoice PDF → structured rows in Google Sheets** using a combination of:

- Gmail API  
- pdfplumber  
- Google Drive  
- Google Sheets API  
- And most importantly, **an OpenAI model that converts the messy invoice text into clean JSON**  

The full code for this project is here:  
👉 https://github.com/ewux88/redmart_invoice_automation2

This article breaks down how the system works, the Python modules behind it, and why the LLM layer is the most powerful part.

---

## <span style="color:#0A5B87;font-weight:700;">Overview: What the System Does</span>

The workflow runs end-to-end with a single command:

```
python main.py
```

Under the hood, it performs five steps:

1. **Search Gmail for the last N days of RedMart invoice emails** (configurable via `EMAIL_LOOKBACK_DAYS`)  
2. **Download the invoice PDF attachments**  
3. **Use an LLM to extract structured line items from the PDF**  
4. **Append each line item as a row in Google Sheets**  
5. **Upload the original PDF into a Google Drive folder for archival**

The result?

A real-time, item-level expense log without ever opening an invoice manually.

---

## <span style="color:#0A5B87;font-weight:700;">Repository Structure</span>

```
redmart_invoice_automation2/
│
├── main.py
├── get_email_attachments.py
├── extract_invoice_data_from_pdf.py
├── sheets_writer.py
│
├── README.md
├── requirements.txt
└── .gitignore
```

---

## <span style="color:#0A5B87;font-weight:700;">1. Fetching Invoice Attachments from Gmail</span>

The `GetEmailAttachments` functionality is implemented in `get_email_attachments.py`.

This script:

- Searches Gmail for recent messages (lookback window set via `EMAIL_LOOKBACK_DAYS`)  
- Filters emails based on a keyword pattern for RedMart invoices (`INVOICE_REGEX`)  
- Pulls only messages containing PDF attachments  
- Handles Drive pagination to ensure complete duplicate detection  
- Returns the PDFs as `(filename, bytes)` tuples for downstream processing  

OAuth scopes required: Gmail read-only, Drive `drive.file`, and Sheets.

---

## <span style="color:#0A5B87;font-weight:700;">2. Extracting Raw Text from the PDF</span>

`extract_invoice_data_from_pdf.py` uses **pdfplumber** to read text from the invoice and prepare it for the LLM.

The PDF bytes are temporarily written to disk, parsed page-by-page, and the extracted text is concatenated into a single string.

---

## <span style="color:#0A5B87;font-weight:700;">3. The LLM: Converting PDF Text into Clean JSON</span>

This is the heart of the system.

A prompt is built that instructs the LLM (configured via `EXTRACT_INVOICE_MODEL`) to output structured JSON:

- filename  
- order number  
- order date and delivery date  
- order month  
- line items (description, quantity, unit price, total price)

Example output:

<div style="background:#F4F6F8; padding:16px; border-radius:8px; font-family:Menlo,Monaco,Consolas,'Courier New',monospace; color:#000; font-size:14px; line-height:1.5;">
  <div>{</div>
  <div style="margin-left:20px;"><span style="color:#003366; font-weight:700;">"items"</span>: [</div>
  <div style="margin-left:40px;">{</div>
  <div style="margin-left:60px;"><span style="color:#003366; font-weight:700;">"filename"</span>: "SG2025111501IVIS000073422673.pdf",</div>
  <div style="margin-left:60px;"><span style="color:#003366; font-weight:700;">"delivery_date"</span>: "15 Nov 2025",</div>
  <div style="margin-left:60px;"><span style="color:#003366; font-weight:700;">"order_number"</span>: "155692472517361",</div>
  <div style="margin-left:60px;"><span style="color:#003366; font-weight:700;">"order_date"</span>: "11 Nov 2025",</div>
  <div style="margin-left:60px;"><span style="color:#003366; font-weight:700;">"order_month"</span>: "Nov 2025",</div>
  <div style="margin-left:60px;"><span style="color:#003366; font-weight:700;">"description"</span>: "Singo Pears 1KG",</div>
  <div style="margin-left:60px;"><span style="color:#003366; font-weight:700;">"qty"</span>: 1,</div>
  <div style="margin-left:60px;"><span style="color:#003366; font-weight:700;">"unit_price"</span>: 6.95,</div>
  <div style="margin-left:60px;"><span style="color:#003366; font-weight:700;">"total_price"</span>: 6.95</div>
  <div style="margin-left:40px;">}</div>
  <div style="margin-left:20px;">]</div>
  <div>}</div>
</div>

The JSON is extracted from between `<json>...</json>` tags, or parsed directly if no tags are present.

**The actual prompt used:**

<div style="background:#F4F6F8; padding:16px; border-radius:8px; font-family:Menlo,Monaco,Consolas,'Courier New',monospace; color:#000; font-size:13px; line-height:1.6;">
You are a senior accountant. <br>
Given the following invoice text, extract structured data for each item.<br><br>

Invoice text:<br>
{text}<br><br>

Extract and output the following fields for the invoice and for EACH item:<br>
- filename<br>
- delivery_date (format: 15 Nov 2025)<br>
- order_number<br>
- order_date (format: 15 Nov 2025)<br>
- order_month (e.g., Nov 2025)<br>
- description<br>
- qty<br>
- unit_price (number only)<br>
- total_price (number only)<br><br>

Instructions:<br>
- Return ONLY JSON wrapped between &lt;json&gt; and &lt;/json&gt; tags.<br>
- If a field is missing, use empty string or null.<br><br>

Example output (item-centric):<br>
&lt;json&gt;<br>
{{<br>
  "items": [<br>
    {{"filename": "SG2025111501IVIS000073422673.pdf", "delivery_date": "15 Nov 2025", "order_number": "155692472517361", "order_date": "11 Nov 2025", "order_month": "Nov 2025", "description": "Singo Pears 1KG", "qty": 1, "unit_price": 6.95, "total_price": 6.95}},<br>
    {{"filename": "SG2025111501IVIS000073422673.pdf", "delivery_date": "15 Nov 2025", "order_number": "155692472517361", "order_date": "11 Nov 2025", "order_month": "Nov 2025", "description": "Alphonso Mango 200G", "qty": 1, "unit_price": 3.50, "total_price": 3.50}}<br>
  ]<br>
}}<br>
&lt;/json&gt;
</div>

The prompt is intentionally simple and role-based ("You are a senior accountant") to guide the model toward accurate extraction. The example JSON shows the exact structure expected, making it easy for the LLM to follow the format.

---

## <span style="color:#0A5B87;font-weight:700;">4. Writing Line Items to Google Sheets</span>

The JSON is sent to `GoogleSheetsWriter` (in `sheets_writer.py`) which appends each line item as a row to Google Sheets.

Each row contains: filename, delivery_date, order_number, order_date, order_month, description, qty, unit_price, total_price.

A helper exists to test the Sheet connection:

```
python -c "from sheets_writer import test_append_invoice_items; test_append_invoice_items()"
```

---

## <span style="color:#0A5B87;font-weight:700;">5. Archiving the PDF to Google Drive</span>

After writing to Sheets, the PDF is uploaded to a Drive folder (specified by `DRIVE_FOLDER_ID`). Duplicate invoices are automatically skipped on future runs by checking existing filenames in the folder.

---

## <span style="color:#0A5B87;font-weight:700;">Insight Layer: Pivoting Spend by Item and Month</span>

After the automation populated Google Sheets with clean rows, I added a lightweight analytics layer using a native pivot table:

1. Select the entire data range (including headers).
2. Click **Insert → Pivot table** (new sheet).
3. Configure the pivot table:
   - **Rows:** `description` (each grocery item).
   - **Columns:** `order_month` (e.g., "Jan 2025").
   - **Values:** 
     - `qty` → Summarize by SUM to see total quantity purchased per month.
     - `total_price` → Summarize by SUM for the dollar amount.
4. Optional: add `delivery_date` or `order_number` as filters if you want to limit to a specific time window.

The result is an at-a-glance matrix showing how many units of each item I bought each month and how much was spent. It turns the raw feed into actionable budgeting insight without any additional code.

---

## <span style="color:#0A5B87;font-weight:700;">Environment Setup</span>

1. **Create a Google Cloud OAuth client** with Gmail, Drive (`drive.file`), and Sheets scopes enabled. Download `credentials.json` and place it in the project root.

2. **Run the script once** to generate `token.json` via the OAuth flow:
   ```
   python main.py
   ```

3. **Configure `.env`** with your settings:
   ```
   EMAIL_LOOKBACK_DAYS=30
   INVOICE_REGEX=your redmart invoice
   DRIVE_FOLDER_ID=your_drive_folder_id
   SPREADSHEET_ID=your_spreadsheet_id
   SHEET_NAME=Sheet1
   OPENAI_API_KEY=sk-...
   EXTRACT_INVOICE_MODEL=gpt-4o-mini
   ```

4. **Install dependencies**:
   ```
   pip install -r requirements.txt
   ```

---

## <span style="color:#0A5B87;font-weight:700;">Why the LLM Layer Is the Most Powerful Part</span>

Traditional invoice extraction requires brittle rules and regex patterns that break when invoice formats change.

The LLM approach is:

- **more robust** — handles layout variations and edge cases  
- **easier to maintain** — update the prompt, not the code  
- **adaptable to new invoice formats** — works across vendors with minimal changes  

Once the invoice format changes, only the LLM prompt needs updating — not the entire parsing logic.

---

## <span style="color:#0A5B87;font-weight:700;">Final Thoughts</span>

This project is a blueprint for automating any document-to-dataset workflow using:

- Gmail API  
- PDF extraction  
- LLM semantic parsing  
- Google Sheets  
- Google Drive  

Start here if you want to build your own automated invoice logging system:

👉 https://github.com/ewux88/redmart_invoice_automation2

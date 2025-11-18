import os
from dotenv import load_dotenv
from get_email_attachments import GetEmailAttachments
from extract_invoice_data_from_pdf import ExtractInvoice
from sheets_writer import GoogleSheetsWriter


def main():
    load_dotenv()

    # Init
    processor = GetEmailAttachments()
    extractor = ExtractInvoice()
    sheets_writer = GoogleSheetsWriter()  

    ###### Loop through emails ######
    drive_pdfs = processor.list_drive_pdfs()
    messages = processor.search_emails()
    spreadsheet_id = os.getenv("SPREADSHEET_ID")
    sheet_name = os.getenv("SHEET_NAME", "Sheet1")
    for msg in messages:
        msg_detail = processor.get_message(msg["id"])
        pdf_files = processor.extract_pdf_attachments(msg_detail)
        
        ###### Loop through pdfs in an email ######
        for filename, file_data in pdf_files:            
            if filename in drive_pdfs:
                print(f"Skipped {filename}: already exists in Google Drive.")
                continue

            ###### Extract data from pdf ######
            invoice_data = extractor.extract_from_pdf(filename, file_data)
            print("Extracted invoice data.")

            ###### Append data to sheets ######
            if sheets_writer and spreadsheet_id:
                try:
                    resp = sheets_writer.append_invoice_items(
                        spreadsheet_id, sheet_name, invoice_data
                    )
                    print(f"Appended invoice items to sheet: {resp}")
                except Exception as exc:
                    print(f"Warning: failed to append to sheet: {exc}")

            ###### Upload to drive ######
            file_id = processor.upload_to_drive(filename, file_data)
            print(f"Uploaded {filename} to Google Drive with file ID: {file_id}")


if __name__ == "__main__":
    main()

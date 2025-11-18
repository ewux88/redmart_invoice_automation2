"""
sheets_writer.py

Provides a small helper to write invoice JSON data to a Google Sheet, one item per row.

Usage:
    from sheets_writer import GoogleSheetsWriter

    writer = GoogleSheetsWriter()
    writer.append_invoice_items(spreadsheet_id, sheet_name, invoice_dict)

Expectations:
- OAuth credentials must be available in `token.json` (user credentials) or a service
  account credentials may be used (then modify the code to load that file).
"""
from __future__ import annotations
import os
from typing import List, Dict, Any
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from dotenv import load_dotenv

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


class GoogleSheetsWriter:
    """Write invoice items to a Google Sheet.

    It expects `token.json` in the repo root (the same token used for Gmail/Drive scripts).
    Each invoice item becomes one row with columns:
        filename, delivery_date, order_number, order_date, order_month,
        description, qty, unit_price, total_price
    """

    def __init__(self, token_path: str = "token.json"):
        self.token_path = token_path
        self.creds = self._load_credentials()
        self.service = build("sheets", "v4", credentials=self.creds)

    def _load_credentials(self) -> Credentials:
        if not os.path.exists(self.token_path):
            raise FileNotFoundError(
                f"{self.token_path} not found. Run the OAuth flow to create token.json"
            )
        creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        return creds

    @staticmethod
    def _invoice_to_rows(invoice: Dict[str, Any]) -> List[List[Any]]:
        """Convert validated invoice dict into rows (one per item).

        invoice is expected to follow the InvoiceData schema produced by the extractor.
        """
        rows: List[List[Any]] = []

        items = invoice.get("items") or []
        if not isinstance(items, list):
            # unexpected shape
            return []

        for item in items:
            # each item is expected to contain its own invoice metadata and item fields
            filename = item.get("filename", "")
            delivery_date = item.get("delivery_date", "")
            order_number = item.get("order_number", "")
            order_date = item.get("order_date", "")
            order_month = item.get("order_month", "")

            description = item.get("description", "")
            qty = item.get("qty", "")
            unit_price = item.get("unit_price", "")
            total_price = item.get("total_price", "")

            rows.append([
                filename,
                delivery_date,
                order_number,
                order_date,
                order_month,
                description,
                qty,
                unit_price,
                total_price,
            ])

        return rows

    def append_invoice_items(self, spreadsheet_id: str, sheet_name: str, invoice: Dict[str, Any]) -> Dict[str, Any]:
        """Append invoice items to the given sheet.

        Returns the API response on success.
        """
        rows = self._invoice_to_rows(invoice)
        if not rows:
            return {"status": "no_items", "rows_appended": 0}

        range_name = f"{sheet_name}!A1"
        body = {"values": rows}
        result = (
            self.service.spreadsheets()
            .values()
            .append(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body=body,
            )
            .execute()
        )
        return result


def test_append_invoice_items() -> None:
    """Quick manual test for writing a sample row to Google Sheets."""
    load_dotenv()
    spreadsheet_id = os.getenv("TEST_SPREADSHEET_ID") or os.getenv("SPREADSHEET_ID")
    sheet_name = os.getenv("TEST_SHEET_NAME") or os.getenv("SHEET_NAME") or "Sheet1"

    if not spreadsheet_id:
        raise ValueError("Set TEST_SPREADSHEET_ID or SPREADSHEET_ID in your environment.")

    writer = GoogleSheetsWriter()
    sample_invoice = {
        "items": [
            {
                "filename": "test_invoice.pdf",
                "delivery_date": "01 Jan 2025",
                "order_number": "ORDER-123",
                "order_date": "31 Dec 2024",
                "order_month": "Dec 2024",
                "description": "Example Item",
                "qty": 1,
                "unit_price": 9.99,
                "total_price": 9.99,
            }
        ]
    }

    response = writer.append_invoice_items(spreadsheet_id, sheet_name, sample_invoice)
    print("Sheets append response:", response)


if __name__ == "__main__":
    test_append_invoice_items()

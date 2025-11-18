
import os
import re
import json
from typing import List, Optional
from datetime import datetime
import openai
import pdfplumber
from dotenv import load_dotenv


class ExtractInvoice:
	"""Extract invoice data from PDF bytes using an LLM and validate with Pydantic.

	Usage:
		extractor = ExtractInvoice()
		result = extractor.extract_from_pdf(filename, pdf_bytes)
	"""

	def __init__(self, model: str = "gpt-3.5-turbo"):
		load_dotenv()
		openai.api_key = os.getenv("OPENAI_API_KEY")
		self.model = os.getenv("EXTRACT_INVOICE_MODEL")

	def _pdf_bytes_to_text(self, pdf_bytes: bytes) -> str:
		tmp = "temp_invoice.pdf"
		with open(tmp, "wb") as f:
			f.write(pdf_bytes)
		try:
			with pdfplumber.open(tmp) as pdf:
				pages = [p.extract_text() or "" for p in pdf.pages]
			return "\n".join(pages).strip()
		finally:
			try:
				os.remove(tmp)
			except OSError:
				pass

	def _build_prompt(self, filename: str, text: str) -> str:
		# Example JSON braces must be doubled in f-strings so they are not treated as format placeholders
		prompt = f"""
            You are a senior accountant. 
			Given the following invoice text, extract structured data for each item.

            Invoice text:
            {text}

            Extract and output the following fields for the invoice and for EACH item:
            - filename ({filename})
            - delivery_date (format: 15 Nov 2025)
            - order_number
            - order_date (format: 15 Nov 2025)
            - order_month (e.g., Nov 2025)
            - description 
			- qty
			- unit_price (number only), 
			- total_price (number only)

            Instructions:
            - Return ONLY JSON wrapped between <json> and </json> tags.
            - If a field is missing, use empty string or null.

			Example output (item-centric):
				<json>
				{{
					"items": [
						{{"filename": "SG2025111501IVIS000073422673.pdf", "delivery_date": "15 Nov 2025", "order_number": "155692472517361", "order_date": "11 Nov 2025", "order_month": "Nov 2025", "description": "Singo Pears 1KG", "qty": 1, "unit_price": 6.95, "total_price": 6.95}},
						{{"filename": "SG2025111501IVIS000073422673.pdf", "delivery_date": "15 Nov 2025", "order_number": "155692472517361", "order_date": "11 Nov 2025", "order_month": "Nov 2025", "description": "Alphonso Mango 200G", "qty": 1, "unit_price": 3.50, "total_price": 3.50}}
					]
				}}
				</json>
				
        """
		return prompt

	def _call_llm(self, prompt: str) -> str:
		resp = openai.chat.completions.create(
			model=self.model,
			messages=[{"role": "user", "content": prompt}],
			# max_tokens=1024,
		)
		try:
			return resp.choices[0].message.content.strip()
		except Exception:
			return str(resp)

	def extract_from_pdf(self, filename: str, pdf_bytes: bytes) -> dict:
		"""Main entry: returns validated invoice dict or error payload."""
		text = self._pdf_bytes_to_text(pdf_bytes)
		prompt = self._build_prompt(filename, text)
		raw = self._call_llm(prompt)

		# extract JSON between tags or first JSON object
		m = re.search(r"<json>([\s\S]+?)</json>", raw, re.IGNORECASE)
		json_text = None
		if m:
			json_text = m.group(1).strip()
		else:
			m2 = re.search(r"(\{[\s\S]+\})", raw)
			if m2:
				json_text = m2.group(1)

		if not json_text:
			return {"error": "no_json_found", "raw": raw}

		try:
			data = json.loads(json_text)
		except Exception as e:
			return {"error": "json_parse_error", "message": str(e), "raw": json_text}

		
		return data

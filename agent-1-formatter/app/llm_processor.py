import os
import json
from groq import Groq
from .schemas import TicketCreate

# Initialize the GROQ client
# It will automatically read the GROQ_API_KEY from the environment
client = Groq()

def structure_receipt_text(raw_text: str) -> TicketCreate:
    """
    Uses GROQ function calling model to extract structured data from raw OCR text.
    """
    system_prompt = """
    You are an expert extraction system. Your ONLY job is to read noisy OCR text from a receipt and return a SINGLE valid JSON object that EXACTLY matches the schema below. 
    Do not add, remove, or rename keys. 
    Do not include comments or any text before/after the JSON. 
    If information is missing, use the specified defaults.

    ### OUTPUT SCHEMA (exact keys, exact types)
    {
    "merchant_name": "string",                 // default: "Unknown"
    "transaction_date": "YYYY-MM-DD or None",  // ISO date string or None if not found/invalid
    "total_amount": 0.0,                        // number; default: 0.0
    "category": "Groceries|Restaurant|Fuel|Transport|Shopping|Entertainment|Utilities|Other",
    "items": [
        {
        "description": "string",               // default: "Unknown"
        "price": 0.0                           // number; default: 0.0
        }
    ]
    }

    ### NORMALIZATION & TYPE RULES (strict)
    - Strings: trim whitespace; collapse multiple spaces into one; no newline characters.
    - Numbers: must be JSON numbers (not strings); dot as decimal separator; no thousands separators, no currency symbols, no scientific notation, no NaN/Infinity.
    - Dates: output must be "YYYY-MM-DD".
    - Accept inputs like DD/MM/YYYY, MM/DD/YYYY, YYYY-MM-DD, or OCR-variants (e.g., 10/2O/2O25).
    - If day/month ambiguity exists, infer from locale cues in text (Spanish month names, currency ARS, “Argentina”, etc.). If still ambiguous, prefer DD/MM/YYYY interpretation.
    - If no valid date is found, output None.
    - Currency symbols/labels (€, $, ARS, USD, IVA, TAX, SUBTOTAL, TOTAL, CHANGE) must be stripped from numeric fields.
    - Do NOT output empty keys or additional fields. If "items" are unknown, return a single default item.

    ### EXTRACTION HEURISTICS
    - merchant_name: choose the most prominent store/brand line (often at the top, uppercase, or logo-like). Exclude addresses/slogans.
    - transaction_date: pick the date closest to totals; avoid time-only values; ignore authorization codes.
    - total_amount: use the grand total line (keywords: "TOTAL", "TOTAL AMOUNT", "Amount Due"); exclude “CHANGE DUE”.
    - items:
    - Each line should include a short description and unit price.
    - If price uses comma decimals (e.g., "9,86"), convert to 9.86.
    - If items cannot be extracted reliably, return one default: {"description":"Unknown","price":0.0}.
    - category mapping (case-insensitive keywords):
    - Groceries: supermarkets, “Super”, produce, milk, bread.
    - Restaurant: bar, café, “restaurant”, “menu”, “table”, “mozo”.
    - Fuel: gas, petrol, “combustible”, YPF, Shell.
    - Transport: taxi, Uber, bus, subway, train, tolls, parking.
    - Shopping: apparel, electronics, pharmacy, retail.
    - Entertainment: cinema, theater, museum, streaming, events.
    - Utilities: electricity, water, gas service, internet, phone.
    - Default to Other if unclear.

    ### VALIDATION CHECKLIST (apply before responding)
    1) Keys must match schema exactly (order does not matter).
    2) Values must have correct types (numbers as numbers).
    3) "transaction_date" must be a valid "YYYY-MM-DD" string or None.
    4) "category" must be one of the allowed values exactly.
    5) "items" must be a non-empty array; each item has "description" (string) and "price" (number).
    6) No extra fields, no comments, no trailing commas.

    ### RETURN FORMAT
    Return ONLY the JSON object. No markdown, no prose, no code fences.
    """
    
    prompt = f"""
    Extract the structured data from the following receipt text:
    ---
    {raw_text}
    ---
    """

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        )
        
        response_json = json.loads(response.choices[0].message.content)
        
        # Validate the response with our Pydantic model
        validated_data = TicketCreate(**response_json)
        return validated_data

    except Exception as e:
        print(f"An error occurred with the LLM: {e}")
        print(f"Response: {response.choices[0].message.content}")
        raise

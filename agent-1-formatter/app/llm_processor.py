import os
import json
from openai import OpenAI
from .schemas import TicketCreate

# Initialize the OpenAI client
# It will automatically read the OPENAI_API_KEY from the environment
client = OpenAI()

def structure_receipt_text(raw_text: str) -> TicketCreate:
    """
    Uses OpenAI's function calling model to extract structured data from raw OCR text.
    """
    system_prompt = """
    You are an expert system designed to extract structured data from OCR text of receipts.
    Analyze the user's text and extract the required information, adhering strictly to the JSON schema provided below.
    Do not invent new field names. If a value for a field is not found, use a reasonable default like "Unknown" for strings or 0.0 for numbers.

    Your response MUST be a valid JSON object that matches this exact structure:

    {
      "merchant_name": "string",
      "transaction_date": "YYYY-MM-DD",
      "total_amount": 0.0,
      "category": "One of: Groceries, Restaurant, Fuel, Transport, Shopping, Entertainment, Utilities, Other",
      "items": [
        {
          "description": "string",
          "price": 0.0
        }
      ]
    }

    RETURN ONLY THE JSON OBJECT, DO NOT INCLUDE ANY OTHER TEXT.
    """
    
    prompt = f"""
    Extract the structured data from the following receipt text:
    ---
    {raw_text}
    ---
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
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
        raise

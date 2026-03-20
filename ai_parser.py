import os
import json
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

# ─────────────────────────────────────────────
# CONCEPT: LLM Invoice Parser using Groq
# Groq runs open source models (Llama, Mixtral)
# at extremely fast speeds — free tier is generous.
# We use llama-3.3-70b — powerful and free.
# ─────────────────────────────────────────────

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def parse_invoice_from_text(text: str, available_products: list) -> dict:
    products_info = "\n".join([
        f"- ID: {p['id']}, Name: {p['name']}, Price: Rs.{p['current_price']}, Stock: {p['stock_quantity']}"
        for p in available_products
    ])

    prompt = f"""
You are an invoice parser. Extract invoice details from the user's text and return ONLY valid JSON.

Available products in our system:
{products_info}

User's text:
"{text}"

Instructions:
1. Extract the customer name if mentioned, otherwise use "Walk-in Customer"
2. Match mentioned items to the closest available product by name
3. Extract quantities — default to 1 if not specified
4. Use the product ID from the available products list
5. If a product is not in the available list, skip it
6. Return ONLY JSON, no explanation, no markdown, no backticks

Return this exact JSON format:
{{
    "customer_name": "extracted or default name",
    "items": [
        {{"product_id": 1, "quantity": 2}},
        {{"product_id": 2, "quantity": 1}}
    ],
    "notes": "any important notes or warnings"
}}
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are an invoice parser that returns only valid JSON. Never include markdown or explanations."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
        )

        raw = response.choices[0].message.content.strip()

        # Clean up response
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        parsed = json.loads(raw)

        if "items" not in parsed or not parsed["items"]:
            return {
                "error": "Could not extract any items from the text",
                "raw_response": raw
            }

        return parsed

    except json.JSONDecodeError as e:
        return {
            "error": f"LLM returned invalid JSON: {str(e)}",
            "raw_response": raw
        }
    except Exception as e:
        return {
            "error": f"AI parsing failed: {str(e)}"
        }
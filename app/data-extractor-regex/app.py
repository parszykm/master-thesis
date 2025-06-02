import re
import json
import psycopg2
from flask import Flask, request, jsonify
from psycopg2.extras import RealDictCursor
from datetime import datetime
import os

app = Flask(__name__)

DB_HOST =  os.getenv("DB_HOST", "postgres-service")
DB_NAME = os.getenv("DB_NAME", "invoices")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_PORT = os.getenv("DB_PORT", "5432")

def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def parse_invoice(invoice_text):
    # Initialize the output dictionary
    result = {
        "client": "",
        "client_address": "",
        "client_tax_id": "",
        "gross_total": "",
        "iban": "",
        "invoice_number": "",
        "issue_date": "",
        "items": [],
        "net_total": "",
        "seller": "",
        "seller_address": "",
        "seller_tax_id": "",
        "vat_amount": "",
        "vat_rate": ""
    }

    # Helper function to clean and normalize text
    def clean_text(text):
        return ' '.join(text.strip().split())

    # Extract invoice number
    invoice_no_match = re.search(r'Invoice no: (\d+)', invoice_text)
    if invoice_no_match:
        result["invoice_number"] = invoice_no_match.group(1)

    # Extract issue date
    date_match = re.search(r'Date of issue:.*?(\d{2}/\d{2}/\d{4})', invoice_text, re.DOTALL)
    if date_match:
        result["issue_date"] = date_match.group(1)

    # Extract seller details
    seller_match = re.search(r'Seller:\s*(.*?)\s*Tax Id: (\d{3}-\d{2}-\d{4})\s*IBAN: ([\w\d]+)', invoice_text, re.DOTALL)
    if seller_match:
        seller_info = seller_match.group(1).split('\n')
        result["seller"] = clean_text(seller_info[0])
        result["seller_address"] = clean_text(' '.join(seller_info[1:]))
        result["seller_tax_id"] = seller_match.group(2)
        result["iban"] = seller_match.group(3)

    # Extract client details
    client_match = re.search(r'Client:\s*(.*?)\s*Tax Id: (\d{3}-\d{2}-\d{4})', invoice_text, re.DOTALL)
    if client_match:
        client_info = client_match.group(1).split('\n')
        result["client"] = clean_text(client_info[0])
        result["client_address"] = clean_text(' '.join(client_info[1:]))
        result["client_tax_id"] = client_match.group(2)

    # Extract items
    items_section = re.search(r'ITEMS\s*No\.\s*Description\s*Qty\s*(.*?)\s*SUMMARY', invoice_text, re.DOTALL)
    if items_section:
        items_text = items_section.group(1).strip().split('\n')
        current_item = {}
        for line in items_text:
            item_match = re.match(r'(\d+)\.\s*(.*?)\s*(\d+,\d{2})\s*(each)?$', line)
            if item_match:
                if current_item:
                    result["items"].append(current_item)
                current_item = {
                    "description": clean_text(item_match.group(2)),
                    "quantity": item_match.group(3),
                    "unit": item_match.group(4) or ""
                }
            else:
                if current_item:
                    current_item["description"] += " " + clean_text(line)
        if current_item:
            result["items"].append(current_item)

    # Extract totals and VAT
    totals_match = re.search(r'Gross worth\s*\$?\s*(\d+,\d{2})\s*\$?\s*(\d+,\d{2})', invoice_text)
    if totals_match:
        result["net_total"] = f"$ {totals_match.group(1)}"
        result["gross_total"] = f"$ {totals_match.group(2)}"

    vat_match = re.search(r'VAT \[%]\s*(\d+%)\s*.*?Net worth VAT\s*\$?\s*(\d+,\d{2})', invoice_text, re.DOTALL)
    if vat_match:
        result["vat_rate"] = vat_match.group(1)
        result["vat_amount"] = f"$ {vat_match.group(2)}"

    return result

def save_to_database(parsed_data):
    conn = get_db_connection()
    if not conn:
        return False, "Database connection failed", 500

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Insert or get seller
        cur.execute("""
            INSERT INTO sellers (name, address, tax_id, iban)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (tax_id) DO UPDATE SET name = EXCLUDED.name
            RETURNING id
        """, (parsed_data["seller"], parsed_data["seller_address"], parsed_data["seller_tax_id"], parsed_data["iban"]))
        seller_id = cur.fetchone()["id"]

        # Insert or get client
        cur.execute("""
            INSERT INTO clients (name, address, tax_id)
            VALUES (%s, %s, %s)
            ON CONFLICT (tax_id) DO UPDATE SET name = EXCLUDED.name
            RETURNING id
        """, (parsed_data["client"], parsed_data["client_address"], parsed_data["client_tax_id"]))
        client_id = cur.fetchone()["id"]

        issue_date = None
        if parsed_data["issue_date"]:
            try:
                issue_date = datetime.strptime(parsed_data["issue_date"], "%d/%m/%Y").date()
            except ValueError:
                issue_date = None

        # Insert invoice
        cur.execute("""
            INSERT INTO invoices (invoice_number, issue_date, seller_id, client_id, net_total, gross_total, vat_rate, vat_amount)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (invoice_number) DO NOTHING
            RETURNING id
        """, (
            parsed_data["invoice_number"],
            issue_date,
            seller_id,
            client_id,
            parsed_data["net_total"],
            parsed_data["gross_total"],
            parsed_data["vat_rate"],
            parsed_data["vat_amount"]
        ))
        invoice_result = cur.fetchone()
        if not invoice_result:
            conn.rollback()
            return False, "Invoice already exists", 409

        invoice_id = invoice_result["id"]

        # Insert items
        for item in parsed_data["items"]:
            cur.execute("""
                INSERT INTO items (invoice_id, description, quantity, unit)
                VALUES (%s, %s, %s, %s)
            """, (invoice_id, item["description"], item["quantity"], item["unit"]))

        conn.commit()
        return True, "Data saved successfully", 200

    except Exception as e:
        conn.rollback()
        return False, f"Error saving to database: {str(e)}", 500
    finally:
        cur.close()
        conn.close()

@app.route('/parse-invoice', methods=['POST'])
def parse_invoice_endpoint():
    try:
        if not request.is_json:
            return jsonify({"error": "Request must contain JSON data"}), 400

        data = request.get_json()
        invoice_text = data.get('invoice_text')

        if not invoice_text or not isinstance(invoice_text, str):
            return jsonify({"error": "Invalid or missing 'invoice_text' in request body"}), 400

        parsed_data = parse_invoice(invoice_text)
        success, message, status_code = save_to_database(parsed_data)

        if not success and status_code != 409:
            return jsonify({"error": message}), status_code
        elif not success and success == 409:
            return jsonify({"error": message, "invoice": parsed_data}), status_code
        return jsonify(parsed_data), 200

    except Exception as e:
        return jsonify({"error": f"Error processing request: {str(e)}"}), 500

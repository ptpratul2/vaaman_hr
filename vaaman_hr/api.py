import frappe
import json
import google.generativeai as genai
import difflib
import re

from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice

@frappe.whitelist(allow_guest=False)
def extract_invoice_data():
    """
    Receives an image via multipart/form-data, sends it to Gemini 2.5 Flash,
    and returns a structured JSON object matching the frontend React Native interface.
    """
    
    api_key = frappe.conf.get("gemini_api_key")
    if not api_key:
        frappe.throw("Gemini API key not configured in site_config.json")

    genai.configure(api_key=api_key)

    if 'file' not in frappe.request.files:
        frappe.throw("No image file received from the app.")

    uploaded_file = frappe.request.files.get('file')
    file_bytes = uploaded_file.read()
    mime_type = uploaded_file.content_type or 'image/jpeg'

   
    prompt = """
    You are a precision data extraction engine. Analyze the provided image of a receipt/invoice.
    Extract the following information and return it. 
    If a field is unreadable or not found in the image, return null for that field.

    Return ONLY JSON matching this exact schema:
    {
        "poNumber": "string",
        "invoiceNumber": "string",
        "invoiceDate": "string (YYYY-MM-DD format)",
        "totalTaxableAmount": "string",
        "cgstTotal": "string",
        "sgstTotal": "string",
        "grandTotal": "string",
        "items": [
            {
                "slNo": "string",
                "description": "string",
                "hsn": "string",
                "gstRate": "string",
                "quantity": "string",
                "rate": "string",
                "amount": "string",
                "per": "string"
            }
        ]
    }
    """

    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        response = model.generate_content(
            contents=[
                prompt, 
                {"mime_type": mime_type, "data": file_bytes}
            ],
            generation_config={"response_mime_type": "application/json"}
        )
        
        extracted_data = json.loads(response.text)
        return extracted_data

    except json.JSONDecodeError:
        frappe.log_error(title="Gemini JSON Error", message=response.text)
        frappe.throw("The AI returned an invalid format. Please try again.")
    except Exception as e:
        frappe.log_error(title="Gemini API Error", message=str(e))
        frappe.throw(f"Extraction failed: {str(e)}")


@frappe.whitelist(allow_guest=False)
def create_pr_from_extracted_data(payload):
    """
    Uses ERPNext's native mapping to bring over PO items, taxes, and terms.
    Filters the items against AI-extracted data, updates quantities, 
    and recalculates the totals.
    """
    if isinstance(payload, str):
        data = json.loads(payload)
    else:
        data = payload

    po_number = data.get("poNumber")
    if not po_number:
        frappe.throw("Cannot create a receipt without a Purchase Order Number.")

    if not frappe.db.exists("Purchase Order", po_number):
        frappe.throw(f"Purchase Order '{po_number}' not found in the system.")
    
    po_doc = frappe.get_doc("Purchase Order", po_number)
    
    if po_doc.docstatus != 1:
        frappe.throw(f"Purchase Order '{po_number}' must be Submitted before creating a receipt.")

    pr_doc = make_purchase_receipt(po_number)

    if data.get("invoiceNumber"):
        pr_doc.supplier_delivery_note = data.get("invoiceNumber")
        
    if data.get("invoiceDate"):
        pr_doc.supplier_delivery_note_date = data.get("invoiceDate")

    extracted_items = data.get("items", [])
    matched_count = 0
    
    items_to_keep = []

    for pr_item in pr_doc.items:
        matched_ai_item = None
        po_desc = pr_item.item_name.lower()
        
        for ai_item in extracted_items:
            ext_desc = ai_item.get("description", "").lower()
            ext_hsn = ai_item.get("hsn", "")
            
            if ext_hsn and ext_hsn in pr_item.item_code:
                matched_ai_item = ai_item
                break

            if ext_desc in po_desc or po_desc in ext_desc:
                matched_ai_item = ai_item
                break
            
            similarity = difflib.SequenceMatcher(None, po_desc, ext_desc).ratio()
            if similarity > 0.60:
                matched_ai_item = ai_item
                break
        
        if matched_ai_item:

            raw_qty = matched_ai_item.get("quantity", str(pr_item.qty))
            clean_qty = re.sub(r'[^\d.]+', '', raw_qty)
            if clean_qty:
                pr_item.qty = float(clean_qty)
            
            # NEW: Assign the uploaded image URL to the field
            item_proof_url = matched_ai_item.get("custom_item_proof")
            if item_proof_url:
                pr_item.item_proof = item_proof_url
            
            items_to_keep.append(pr_item)
            matched_count += 1

    if matched_count == 0:
        frappe.log_error(title="OCR Match Debug", message=f"PO Items: {[i.item_name for i in po_doc.items]} | AI Items: {[i.get('description') for i in extracted_items]}")
        frappe.throw("Could not match any items from the invoice to this Purchase Order.")

    pr_doc.set("items", items_to_keep)

    pr_doc.set_missing_values()
    pr_doc.calculate_taxes_and_totals()

    pr_doc.insert() 

    return {
        "status": "success",
        "message": f"Successfully created Draft Purchase Receipt: {pr_doc.name} with {matched_count} items and applied taxes.",
        "pr_name": pr_doc.name
    }
    
    
def auto_create_purchase_invoice(doc, method):
    """
    Triggered when a Purchase Receipt is Submitted.
    """
    try:
        pi_doc = make_purchase_invoice(doc.name)
        
        pi_doc.set_missing_values()
        

        if doc.supplier_delivery_note:
            pi_doc.bill_no = doc.supplier_delivery_note

            pi_doc.bill_date = doc.supplier_delivery_note_date or doc.posting_date
            
        pi_doc.flags.ignore_mandatory = True 

        pi_doc.insert(ignore_permissions=True) 

    except Exception as e:
        frappe.log_error(title=f"Auto-PI Error for {doc.name}", message=str(e))
        frappe.throw(f"Could not auto-generate the Draft Purchase Invoice: {str(e)}")

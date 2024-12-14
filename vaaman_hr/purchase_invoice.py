import frappe
from frappe.utils import nowdate, add_days
from datetime import datetime

@frappe.whitelist()
def create_payment_request():
    # Define the target date range
    target_date = add_days(nowdate(), 7)  # 7 days from now
    today = nowdate()  # Today's date

    # Fetch all Purchase Invoices with outstanding amounts and due dates
    purchase_invoices = frappe.get_all(
        "Purchase Invoice",
        filters={
            "outstanding_amount": (">", 0),  # Outstanding amount must be greater than 0
            "docstatus": 1,  # Only submitted invoices
            "due_date": ["<=", target_date],  # Due today or in the next 7 days
            # "custom_creation_date": [">=", "2024-12-01"]  # Created after a specific date
        },
        fields=[
            "name", "supplier", "grand_total", "outstanding_amount", "due_date", 
            "cost_center", "naming_series", "bill_no", "bill_date", "custom_creation_date"
        ]
    )

    for invoice in purchase_invoices:
        try:
            # Check if Payment Request already exists for the invoice
            existing_request = frappe.get_all(
                "Payment Request",
                filters={
                    "reference_name": invoice["name"], 
                    "docstatus": ("<", 2)  # Draft or submitted requests
                }
            )
            due_date = datetime.strptime(invoice["due_date"], "%Y-%m-%d").date()
            if not existing_request and invoice["naming_series"] != "CS/PINV-.YY.-" and due_date >= datetime(2024, 12, 1).date():
       
            # if not existing_request and invoice["naming_series"] != "CS/PINV-.YY.-" and  invoice["due_date"] >= "2024-12-01":
                # Create a Payment Request
                payment_request = frappe.get_doc({
                    "doctype": "Payment Request",
                    "payment_request_type": "Outward",
                    "party_type": "Supplier",
                    "party": invoice["supplier"],
                    "reference_doctype": "Purchase Invoice",
                    "reference_name": invoice["name"],
                    "grand_total": invoice["outstanding_amount"],
                    "due_date": invoice["due_date"],
                    "custom_supplier_invoice_no": invoice["bill_no"],
                    "custom_supplier_invoice_date": invoice["bill_date"],
                    "transaction_date": today,
                    "cost_center": invoice["cost_center"],
                    "mode_of_payment": "NEFT"
                })
                payment_request.insert()
                frappe.db.commit()  # Commit changes to the database
                
                # Update Workflow State based on Cost Center
                cost_center = invoice.get("cost_center", "").strip()  # Clean up the cost center value
                
                if payment_request.cost_center in ["Head Office - VEIL", "Head Office - VEL", "HO Aurangabad - VEIL"]:
                    payment_request.workflow_state = "HO Accounts Manager Payment"
                    print(f"Processed Invoice: {invoice['name']} with Cost Center: {cost_center}")
                
                else:
                    payment_request.workflow_state = "Pending at Site Head"
                    print(f"Processed Invoice: {invoice['name']} with Cost Center: {cost_center}")
                
                
                payment_request.save()  # Save after setting the workflow state
                print(f"Workflow state updated for Cost Center: {cost_center}")
        
        except Exception as e:
            frappe.log_error(
                f"Error processing invoice {invoice['name']}: {str(e)}",
                "Payment Request Creation Error"
            )

@frappe.whitelist()
def update_payment_request_status(doc, method):
    """
    Update Payment Request status when the workflow state changes to "Approved".
    Trigger this function using a Server Script on the 'Payment Request' DocType.
    """
    if doc.workflow_state == "Approved":  # Match with your workflow's "Approved" state
        doc.status = "Ready to Pay"
        doc.save()

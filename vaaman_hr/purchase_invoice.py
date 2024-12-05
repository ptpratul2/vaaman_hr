import frappe
from frappe.utils import nowdate, add_days

@frappe.whitelist()
def create_payment_request():
    # Define the target date range for both upcoming and past invoices
    target_date = add_days(nowdate(), 7)  # 7 days from now
    start_date = add_days(nowdate(), -7)  # 7 days ago
    end_date = nowdate()  # Today's date

    # Fetch all Purchase Invoices with outstanding amounts and due dates in the defined ranges
    purchase_invoices = frappe.get_all(
        "Purchase Invoice",
        filters={
            "outstanding_amount": (">", 0),
            "docstatus": 1,  # Only submitted invoices
            # Match invoices either due 7 days from now or in the past 7 days
            "due_date": ["in", [target_date, start_date]],
        },
        fields=["name", "supplier", "grand_total", "outstanding_amount", "due_date", "cost_center", "naming_series", "bill_no", "bill_date"]
    )

    for invoice in purchase_invoices:
        try:
            # Check if Payment Request already exists for the invoice
            existing_request = frappe.get_all(
                "Payment Request",
                filters={"reference_name": invoice["name"], "docstatus": ("<", 2)},
            )
            if not existing_request and invoice["naming_series"] != "CS/PINV-.YY.-":
                # Create a Payment Request with the desired workflow state
                payment_request = frappe.get_doc({
                    "doctype": "Payment Request",
                    "payment_request_type": "Outward",
                    "party_type": "Supplier",
                    "party": invoice["supplier"],
                    "reference_doctype": "Purchase Invoice",
                    "reference_name": invoice["name"],
                    "grand_total": invoice["grand_total"],
                    "due_date": invoice["due_date"],
                    "custom_supplier_invoice_no": invoice["bill_no"],
                    "custom_supplier_invoice_date": invoice["bill_date"],
                    "transaction_date": nowdate(),
                    "cost_center": invoice["cost_center"],
                    "mode_of_payment": "NEFT"
                })
                payment_request.insert()
                frappe.db.commit()  # Commit changes to the database
                payment_request.workflow_state = "Pending at Site Head"
                payment_request.save()

        except Exception as e:
            frappe.log_error(f"Failed to create Payment Request for {invoice['name']}: {str(e)}")

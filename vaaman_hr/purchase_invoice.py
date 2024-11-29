import frappe
from frappe.utils import nowdate, add_days

@frappe.whitelist()
def create_payment_request():
    # Calculate the date 7 days from today
    target_date = add_days(nowdate(), 7)

    # Fetch all Purchase Invoices with a due date matching the target date and outstanding amount
    purchase_invoices = frappe.get_all(
        "Purchase Invoice",
        filters={
            "due_date": target_date,  # Match invoices due 7 days from now
            "outstanding_amount": (">", 0),
            "docstatus": 1,  # Only submitted invoices
        },
        fields=["name", "supplier", "grand_total", "outstanding_amount", "due_date", "cost_center"]
    )

    for invoice in purchase_invoices:
        try:
            # Check if Payment Request already exists for the invoice
            existing_request = frappe.get_all(
                "Payment Request",
                filters={"reference_name": invoice["name"], "docstatus": ("<", 2)},
            )
            if not existing_request:
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
                    # "workflow_state": "Pending at Site Head",  # Set workflow state
                    "cost_center": invoice["cost_center"],
                    "mode_of_payment": "NEFT"
                })
                payment_request.insert()
                frappe.db.commit()  # Commit changes to the database
                payment_request.workflow_state = "Pending at Site Head"
                payment_request.save()

        except Exception as e:
            frappe.log_error(f"Failed to create Payment Request for {invoice['name']}: {str(e)}")

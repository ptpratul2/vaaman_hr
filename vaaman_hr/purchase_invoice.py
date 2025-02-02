import frappe
from frappe import ValidationError, _, qb, scrub, throw
from frappe.utils import nowdate, add_days, getdate
from frappe.utils.data import comma_and
import traceback


def is_auto_payment_request_enabled():
    value = frappe.db.get_single_value('Vaaman Settings', 'enable_auto_payment_request')
    if not value:
        frappe.log_error("Auto Payment Request is disabled.", "Configuration Warning")
    return value == 1


@frappe.whitelist()
def create_payment_request():
    if is_auto_payment_request_enabled:
        # Define the target date range
        target_date = add_days(nowdate(), 7)  # 7 days from now
        today = getdate()  # Today's date

        # Fetch all Purchase Invoices with outstanding amounts and due dates
        purchase_invoices = frappe.get_all(
            "Purchase Invoice",
            filters={
                "outstanding_amount": (">", 0),  # Outstanding amount must be greater than 0
                "docstatus": 1,  # Only submitted invoices
                "due_date": ["<=", target_date],  # Due today or in the next 7 days
                "due_date": [">=", "2024-12-01"],  # Not older than 2024-12-01
                "naming_series": ("!=", "CS/PINV-.YY.-")  # Exclude specific naming series
            },
            fields=[
                "name", "supplier", "grand_total", "outstanding_amount", "due_date", 
                "cost_center", "naming_series", "bill_no", "bill_date", "custom_creation_date"
            ]
        )

        # Workflow mapping for cost centers
        cost_center_mapping = {
            "Head Office - VEIL": "HO Accounts Manager Payment",
            "Head Office - VEL": "HO Accounts Manager Payment",
            "HO Aurangabad - VEIL": "HO Accounts Manager Payment"
        }

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

                if not existing_request:
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
                    print(payment_request.cost_center)
                    cost_center_list = {
                                            "Head Office - VEIL",
                                            "Head Office - VEL",
                                            "HO Aurangabad - VEIL"
                                        }
                    
                    

                    cost_center = invoice.get("cost_center", "").strip()  # Clean up the cost center value
                    
                    if payment_request.cost_center in cost_center_list:
                        payment_request.workflow_state = "Pending at HO Admin Manager"
                        print(f"Processed Invoice: {invoice['name']} with Cost Center: {cost_center}")
                    
                    if payment_request.cost_center not in cost_center_list:
                        payment_request.workflow_state = "Pending at Site Head"
                        print(f"Processed Invoice: {invoice['name']} with Cost Center: {cost_center}")
                    
                    
                    payment_request.save()  # Save after setting the workflow state

            except Exception as e:
                error_message = f"Error processing invoice {invoice['name']}: {str(e)}"
                frappe.log_error(f"{error_message}\n{traceback.format_exc()}", "Payment Request Creation Error")
                print(error_message)

        frappe.db.commit()  # Commit changes after processing all invoices
        print("All eligible invoices have been processed.")

@frappe.whitelist()
def update_payment_request_status(doc, method):
    """
    Update Payment Request status when the workflow state changes to "Approved".
    Trigger this function using a Server Script on the 'Payment Request' DocType.
    """
    if doc.workflow_state == "Approved":  # Match with your workflow's "Approved" state
        doc.status = "Ready to Pay"
        doc.save()

@frappe.whitelist()
def validate_invoice_outstanding(doc, method):
    """
    Validate outstanding amounts for invoices linked to a Payment Request before submission.
    """
    no_outstanding_refs = {}

    # Ensure it's linked to invoices
    if doc.reference_doctype in ("Sales Invoice", "Purchase Invoice"):
        # Get details from the referenced invoice
        outstanding_amount, is_return = frappe.get_cached_value(
            doc.reference_doctype,
            doc.reference_name,
            ["outstanding_amount", "is_return"]
        )

        # Check if outstanding amount is zero or negative
        if outstanding_amount <= 0 and not is_return:
            no_outstanding_refs.setdefault(doc.reference_doctype, []).append(doc)

    # Display a warning message for invoices with no outstanding amount
    for reference_doctype, references in no_outstanding_refs.items():
        frappe.throw(
            _(
                "References {0} of type {1} have no outstanding amount left and cannot proceed."
            ).format(
                frappe.bold(comma_and([d.reference_name for d in references])),
                _(reference_doctype),
            ),
            title=_("Validation Error"),
        )

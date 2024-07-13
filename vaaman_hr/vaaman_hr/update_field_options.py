import frappe

def update_earned_leave_frequency_options():
    # Load the Leave Type DocType
    doctype = frappe.get_doc("DocType", "Leave Type")
    
    # Find the earned_leave_frequency field
    for field in doctype.fields:
        if field.fieldname == "earned_leave_frequency":
            # Update the options
            field.options = "Monthly\nQuarterly\nHalf-Yearly\nYearly\n20 Days"
            break
    
    # Save the changes to the DocType
    doctype.save()
    
    # Ensure the changes are committed
    frappe.db.commit()

import frappe
from frappe.model.document import Document
from frappe import _, throw
@frappe.whitelist()
def create_quality_inspection(purchase_order):
	po = frappe.get_doc('Purchase Order', purchase_order)    
	if po.docstatus != 0:
		frappe.throw(_('Quality Inspection can only be created from a draft Purchase Order.'))
	
	qi = frappe.new_doc('Quality Inspection')
	qi.reference_type = 'Purchase Order'
	qi.reference_name = po.name
	qi.supplier = po.supplier
	qi.inspection_type = 'Incoming'
	qi.inspected_by='pratul@ossolutions.in'
	qi.item_code=po.owner
	qi.sample_size=po.owner
	# Add any other fields that need to be copied from PO to QI
	
	for item in po.items:
		qi.append('custom_items', {
			'item_code': item.item_code,
			'item_name': item.item_name,
			'qty': item.qty,
			# Add any other item fields that need to be copied
		})
	
	qi.insert()
	return qi.name

# @frappe.whitelist()
# def validate_items_quality_inspection(purchase_order):
# 		self=purchase_order
# 		for item in self.get("items"):
# 			if item.quality_inspection:
# 				qi = frappe.db.get_value(
# 					"Quality Inspection",
# 					item.quality_inspection,
# 					["reference_type", "reference_name", "item_code"],
# 					as_dict=True,
# 				)

# 				if qi.reference_type != self.doctype or qi.reference_name != self.name:
# 					msg = f"""Row #{item.idx}: Please select a valid Quality Inspection with Reference Type
# 						{frappe.bold(self.doctype)} and Reference Name {frappe.bold(self.name)}."""
# 					frappe.throw(_(msg))

# 				if qi.item_code != item.item_code:
# 					msg = f"""Row #{item.idx}: Please select a valid Quality Inspection with Item Code
# 						{frappe.bold(item.item_code)}."""
# 					frappe.throw(_(msg))

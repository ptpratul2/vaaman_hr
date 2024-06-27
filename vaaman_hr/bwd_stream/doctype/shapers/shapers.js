frappe.ui.form.on('Purchase Order', {
    refresh: function(frm) {
        if (frm.doc.docstatus == 0) { // Ensure it is a Draft PO
            frm.add_custom_button(__('Create Quality Inspection'), function() {
                frappe.call({
                    method: "your_app.api.create_quality_inspection",
                    args: {
                        purchase_order: frm.doc.name
                    },
                    callback: function(r) {
                        if (r.message) {
                            frappe.msgprint(__('Quality Inspection {0} created', [r.message]));
                            frm.reload_doc();
                        }
                    }
                });
            });
        }
    }
});

make_quality_inspection() {
    let data = [];
    const fields = [
        {
            label: "Items",
            fieldtype: "Table",
            fieldname: "items",
            cannot_add_rows: true,
            in_place_edit: true,
            data: data,
            get_data: () => {
                return data;
            },
            fields: [
                {
                    fieldtype: "Data",
                    fieldname: "docname",
                    hidden: true
                },
                {
                    fieldtype: "Read Only",
                    fieldname: "item_code",
                    label: __("Item Code"),
                    in_list_view: true
                },
                {
                    fieldtype: "Read Only",
                    fieldname: "item_name",
                    label: __("Item Name"),
                    in_list_view: true
                },
                {
                    fieldtype: "Float",
                    fieldname: "qty",
                    label: __("Accepted Quantity"),
                    in_list_view: true,
                    read_only: true
                },
                {
                    fieldtype: "Float",
                    fieldname: "sample_size",
                    label: __("Sample Size"),
                    reqd: true,
                    in_list_view: true
                },
                {
                    fieldtype: "Data",
                    fieldname: "description",
                    label: __("Description"),
                    hidden: true
                },
                {
                    fieldtype: "Data",
                    fieldname: "serial_no",
                    label: __("Serial No"),
                    hidden: true
                },
                {
                    fieldtype: "Data",
                    fieldname: "batch_no",
                    label: __("Batch No"),
                    hidden: true
                }
            ]
        }
    ];

    const me = this;
    const dialog = new frappe.ui.Dialog({
        title: __("Select Items for Quality Inspection"),
        size: "extra-large",
        fields: fields,
        primary_action: function () {
            const data = dialog.get_values();
            frappe.call({
                method: "erpnext.controllers.stock_controller.make_quality_inspections",
                args: {
                    doctype: me.frm.doc.doctype,
                    docname: me.frm.doc.name,
                    items: data.items
                },
                freeze: true,
                callback: function (r) {
                    if (r.message.length > 0) {
                        if (r.message.length === 1) {
                            frappe.set_route("Form", "Quality Inspection", r.message[0]);
                        } else {
                            frappe.route_options = {
                                "reference_type": me.frm.doc.doctype,
                                "reference_name": me.frm.doc.name
                            };
                            frappe.set_route("List", "Quality Inspection");
                        }
                    }
                    dialog.hide();
                }
            });
        },
        primary_action_label: __("Create")
    });

    this.frm.doc.items.forEach(item => {
        if (this.has_inspection_required(item)) {
            let dialog_items = dialog.fields_dict.items;
            dialog_items.df.data.push({
                "docname": item.name,
                "item_code": item.item_code,
                "item_name": item.item_name,
                "qty": item.qty,
                "description": item.description,
                "serial_no": item.serial_no,
                "batch_no": item.batch_no,
                "sample_size": item.sample_quantity
            });
            dialog_items.grid.refresh();
        }
    });

    data = dialog.fields_dict.items.df.data;
    if (!data.length) {
        frappe.msgprint(__("All items in this document already have a linked Quality Inspection."));
    } else {
        dialog.show();
    }
}

has_inspection_required(item) {
    if (this.frm.doc.doctype === "Stock Entry" && this.frm.doc.purpose == "Manufacture" ) {
        if (item.is_finished_item && !item.quality_inspection) {
            return true;
        }
    } else if (!item.quality_inspection) {
        return true;
    }
}
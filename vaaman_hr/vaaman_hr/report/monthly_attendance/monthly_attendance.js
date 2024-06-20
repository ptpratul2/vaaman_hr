frappe.query_reports["Monthly Attendance"] = {
    "filters": [
        {
            "fieldname": "employee",
            "label": __("Employee"),
            "fieldtype": "Link",
            "options": "Employee",
            "default": frappe.defaults.get_user_default("Employee")
        },
        {
            "fieldname": "month",
            "label": __("Month"),
            "fieldtype": "Select",
            "options": [
                { "label": __("January"), "value": "1" },
                { "label": __("February"), "value": "2" },
                { "label": __("March"), "value": "3" },
                { "label": __("April"), "value": "4" },
                { "label": __("May"), "value": "5" },
                { "label": __("June"), "value": "6" },
                { "label": __("July"), "value": "7" },
                { "label": __("August"), "value": "8" },
                { "label": __("September"), "value": "9" },
                { "label": __("October"), "value": "10" },
                { "label": __("November"), "value": "11" },
                { "label": __("December"), "value": "12" }
            ],
            "default": (new Date()).getMonth() + 1
        },
        {
            "fieldname": "year",
            "label": __("Year"),
            "fieldtype": "Int",
            "default": (new Date()).getFullYear()
        },
		{
            "fieldname": "employee_group",
            "label": __("Employee Group"),
            "fieldtype": "Link",
            "options": "Employee Group"
        },
        {
            "fieldname": "department",
            "label": __("Department"),
            "fieldtype": "Link",
            "options": "Department"
        },
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("Company")
        },
    ]
}


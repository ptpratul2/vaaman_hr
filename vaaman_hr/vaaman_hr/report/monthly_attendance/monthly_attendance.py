import frappe
from frappe import _
from datetime import datetime, timedelta
from frappe.query_builder.functions import Count, Extract, Sum

def execute(filters=None):
    columns, data = [], []
    
    # Calculate date range based on selected month and year
    month = int(filters.get("month"))
    year = int(filters.get("year"))
    start_date, end_date = get_date_range(month, year)
    dates = get_dates_in_range(start_date, end_date)
    columns = get_columns(dates)
    data = get_data(filters, dates, start_date, end_date)
    
    return columns, data

def get_date_range(month, year):
    # Calculate the first and last date of the given month and year
    start_date = datetime(year, month, 1)
    next_month = start_date.replace(day=28) + timedelta(days=4)  # This will never fail
    end_date = next_month - timedelta(days=next_month.day)
    
    return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")

def get_dates_in_range(start_date, end_date):
    date_format = "%Y-%m-%d"
    start_date = datetime.strptime(start_date, date_format)
    end_date = datetime.strptime(end_date, date_format)
    
    delta = end_date - start_date
    
    dates = []
    for i in range(delta.days + 1):
        date = start_date + timedelta(days=i)
        dates.append({
            "date": date.strftime("%Y-%m-%d"),
            "label": "%d %s" % (date.day, date.strftime("%a"))
        })
    
    return dates

def get_columns(dates):
    columns = [
        {
            "label": _("Employee"),
            "fieldname": "employee",
            "fieldtype": "Link",
            "options": "Employee",
            "width": 150
        },
        {
            "label": _("Employee Name"),
            "fieldname": "employee_name",
            "fieldtype": "Data",
            "width": 150
        }
    ]
    
    # Add a column for each date
    for date in dates:
        columns.append({
            "label": _(date["label"]),
            "fieldname": date["date"],
            "fieldtype": "Data",
            "width": 65
        })
    
    return columns

def get_data(filters, dates, start_date, end_date):
    conditions = get_conditions(filters, start_date, end_date)
    raw_data = frappe.db.sql("""
        SELECT
            employee, employee_name, attendance_date, status
        FROM
            `tabAttendance`
        WHERE
            %s
    """ % conditions, filters, as_dict=1)
    
    # Get holiday map for weekly_off status
    holiday_map = get_holiday_map(filters)
    
    # Transform raw data to calendar format
    data = transform_to_calendar_format(raw_data, dates, holiday_map)
    return data

def get_conditions(filters, start_date, end_date):
    conditions = "1=1"
    if filters.get("employee"):
        conditions += " AND employee = %(employee)s"
    if filters.get("employee_group"):
        conditions += " AND employee_group = %(employee_group)s"
    if filters.get("department"):
        conditions += " AND department = %(department)s"
    if start_date:
        conditions += " AND attendance_date >= '%s'" % start_date
    if end_date:
        conditions += " AND attendance_date <= '%s'" % end_date
    if filters.get("company"):
        conditions += " AND company = %(company)s"
    
    return conditions

def get_holiday_map(filters):
    # Add default holiday list too
    holiday_lists = frappe.db.get_all("Holiday List", pluck="name")
    default_holiday_list = frappe.get_cached_value("Company", filters.get("company"), "default_holiday_list")
    if default_holiday_list:
        holiday_lists.append(default_holiday_list)

    holiday_map = []  
    Holiday = frappe.qb.DocType("Holiday")  

    for holiday_list_name in holiday_lists:
        if not holiday_list_name:
            continue
        holidays = (
			frappe.qb.from_(Holiday)
			.select(Extract("day", Holiday.holiday_date).as_("day_of_month"), Holiday.weekly_off)
			.where(
				(Holiday.parent == holiday_list_name)
				& (Extract("month", Holiday.holiday_date) == filters.month)
				& (Extract("year", Holiday.holiday_date) == filters.year)
			)
		).run(as_dict=True)

        if holidays:
            holiday_map.append({"name": holiday_list_name, "holidays": holidays})

    return {"holiday_list": holiday_map}

def transform_to_calendar_format(raw_data, dates, holiday_map):
    status_map = {
        "Present": {"abbr": "P", "color": "green"},
        "Absent": {"abbr": "A", "color": "red"},
        "Half Day": {"abbr": "HD", "color": "orange"},
        "Work From Home": {"abbr": "WFH", "color": "green"},
        "On Leave": {"abbr": "L", "color": "#318AD8"},
        "Holiday": {"abbr": "H", "color": ""},
        "Weekly Off": {"abbr": "WO", "color": ""}
    }
    
    data_dict = {}
    
    # Initialize data dictionary with employees and dates
    for entry in raw_data:
        employee = entry["employee"]
        if employee not in data_dict:
            data_dict[employee] = {
                "employee": employee,
                "employee_name": entry["employee_name"]
            }
            for date in dates:
                data_dict[employee][date["date"]] = {
                    "status": "",
                    "color": ""
                }
    
    # Fill in attendance status using status_map
    for entry in raw_data:
        employee = entry["employee"]
        attendance_date = entry["attendance_date"].strftime("%Y-%m-%d")
        status = entry["status"]
        data_dict[employee][attendance_date]["status"] = status_map.get(status, {}).get("abbr", status)
        data_dict[employee][attendance_date]["color"] = status_map.get(status, {}).get("color", "")
    
    # Fill in weekly off using holiday_map
    for employee_data in data_dict.values():
        for date in dates:
            for holiday_list in holiday_map.get("holiday_list", []):
                holidays = holiday_list.get("holidays", [])
                for holiday in holidays:
                    day_of_month = holiday.get("day_of_month")
                    weekly_off = holiday.get("weekly_off")
                    if day_of_month == date["date"].split("-")[2]:  # Match day of month with date
                        if weekly_off:
                            employee_data[date["date"]]["status"] = "WO"
                            employee_data[date["date"]]["color"] = status_map["Weekly Off"]["color"]
    
    # Convert data dictionary to list
    data = []
    for employee_data in data_dict.values():
        row = {
            "employee": employee_data["employee"],
            "employee_name": employee_data["employee_name"]
        }
        for date in dates:
            row[date["date"]] = f"<span style='color: {employee_data[date['date']]['color']}'>{employee_data[date['date']]['status']}</span>"
        data.append(row)
    
    return data

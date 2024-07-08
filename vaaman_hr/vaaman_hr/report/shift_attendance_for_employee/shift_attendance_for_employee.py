# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import cint, flt, format_datetime, format_duration


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart_data(data)
	report_summary = get_report_summary(data)
	return columns, data, None, chart, report_summary


def get_columns():
	return [
		{
			"label": _("Employee"),
			"fieldname": "employee",
			"fieldtype": "Link",
			"options": "Employee",
			"width": 100,
		},
		{
			"fieldname": "employee_name",
			"fieldtype": "Data",
			"label": _("Employee Name"),
			"width": 100,
			"hidden": 1,
		},
		{
			"label": _("Shift"),
			"fieldname": "shift",
			"fieldtype": "Link",
			"options": "Shift Type",
			"width": 50,
		},
		{
			"label": _("Attendance Date"),
			"fieldname": "attendance_date",
			"fieldtype": "Date",
			"width": 100,
		},
		{
			"label": _("Status"),
			"fieldname": "status",
			"fieldtype": "Data",
			"width": 80,
		},
		{
			"label": _("Shift Start Time"),
			"fieldname": "start_time",
			"fieldtype": "Time",
			"width": 125,
		},
		{
			"label": _("Shift End Time"),
			"fieldname": "end_time",
			"fieldtype": "Time",
			"width": 125,
		},
		{
			"label": _("In Time"),
			"fieldname": "in_time",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Out Time"),
			"fieldname": "out_time",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Total Working Hours"),
			"fieldname": "working_hours",
			"fieldtype": "Data",
			"width": 50,
		},
		{
			"label": _("Over Time"),
			"fieldname": "custom_over_time",
			"fieldtype": "Data",
			"width": 50,
		},
	
		{
			"label": _("Branch"),
			"fieldname": "branch",
			"fieldtype": "Link",
			"options": "Branch",
			"width": 150,
		},
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 150,
		},

		{
			"label": _("Attendance ID"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Attendance",
			"width": 150,
		},
	]


def get_data(filters):
	query = get_query(filters)
	data = query.run(as_dict=True)
	data = update_data(data, filters)
	return data


def get_report_summary(data):
	if not data:
		return None

	present_records = half_day_records = absent_records = late_entries = early_exits = 0

	for entry in data:
		if entry.status == "Present":
			present_records += 1
		elif entry.status == "Half Day":
			half_day_records += 1
		else:
			absent_records += 1
		

	return [
		{
			"value": present_records,
			"indicator": "Green",
			"label": _("Present Records"),
			"datatype": "Int",
		},
		{
			"value": half_day_records,
			"indicator": "Blue",
			"label": _("Half Day Records"),
			"datatype": "Int",
		},
		{
			"value": absent_records,
			"indicator": "Red",
			"label": _("Absent Records"),
			"datatype": "Int",
		},
	
	]


def get_chart_data(data):
	if not data:
		return None

	total_shift_records = {}
	for entry in data:
		total_shift_records.setdefault(entry.shift, 0)
		total_shift_records[entry.shift] += 1

	labels = [_(d) for d in list(total_shift_records)]
	chart = {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Shift"), "values": list(total_shift_records.values())}],
		},
		"type": "percentage",
	}
	return chart


def get_query(filters):
	attendance = frappe.qb.DocType("Attendance")	
	shift_type = frappe.qb.DocType("Shift Type")

	query = (
		frappe.qb.from_(attendance)
		# .inner_join(checkin)
		# .on(checkin.attendance == attendance.name)
		.inner_join(shift_type)
		.on(attendance.shift == shift_type.name)
		.select(
			attendance.name,
			attendance.employee,
			attendance.employee_name,
			attendance.shift,
			attendance.attendance_date,
			attendance.status,
			shift_type.start_time,
    		shift_type.end_time,
			attendance.in_time,
			attendance.out_time,
			attendance.working_hours,
			attendance.custom_over_time,			
			attendance.custom_branch,			
			attendance.company,
						
		)
		.where(attendance.docstatus == 1)
		.groupby(attendance.name)
	)

	for filter in filters:
		if filter == "from_date":
			query = query.where(attendance.attendance_date >= filters.from_date)
		elif filter == "to_date":
			query = query.where(attendance.attendance_date <= filters.to_date)
		elif filter == "consider_grace_period":
			continue	
		else:
			query = query.where(attendance[filter] == filters[filter])

	return query


def update_data(data, filters):
	for d in data:
		d.working_hours = format_float_precision(d.working_hours)
		d.custom_over_time = format_float_precision(d.custom_over_time)
		d.in_time, d.out_time = format_in_out_time(d.in_time, d.out_time, d.attendance_date)
	return data



def format_float_precision(value):
	precision = cint(frappe.db.get_default("float_precision")) or 2
	return flt(value, precision)


def format_in_out_time(in_time, out_time, attendance_date):
	if in_time and not out_time and in_time.date() == attendance_date:
		in_time = in_time.time()
	elif out_time and not in_time and out_time.date() == attendance_date:
		out_time = out_time.time()
	else:
		in_time, out_time = convert_datetime_to_time_for_same_date(in_time, out_time)
	return in_time, out_time


def convert_datetime_to_time_for_same_date(start, end):
	if start and end and start.date() == end.date():
		start = start.time()
		end = end.time()
	else:
		start = format_datetime(start)
		end = format_datetime(end)
	return start, end

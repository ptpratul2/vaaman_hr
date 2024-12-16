import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, cint, date_diff, format_date, get_url_to_list, getdate
from hrms.hr.doctype.compensatory_leave_request.compensatory_leave_request import CompensatoryLeaveRequest

from hrms.hr.utils import (
    create_additional_leave_ledger_entry,
    get_holiday_dates_for_employee,
    get_leave_period,
    validate_active_employee,
    validate_dates,
    validate_overlap,
)

class CompOff(CompensatoryLeaveRequest):
    def validate_attendance(self):
        frappe.logger().info("Validating attendance records...")
        try:
            attendance_records = frappe.get_all(
                "Attendance",
                filters={
                    "attendance_date": ["between", (self.work_from_date, self.work_end_date)],
                    "status": ("in", ["Present", "Work From Home", "Half Day", "Weekly Off"]),
                    "docstatus": 1,
                    "employee": self.employee,
                },
                fields=["attendance_date", "status"],
            )
            frappe.logger().debug(f"Attendance records fetched: {attendance_records}")

            half_days = [entry.attendance_date for entry in attendance_records if entry.status == "Half Day"]

            if half_days and (not self.half_day or getdate(self.half_day_date) not in half_days):
                frappe.throw(
                    _(
                        "You were only present for Half Day on {}. Cannot apply for a full day compensatory leave"
                    ).format(", ".join([frappe.bold(format_date(half_day)) for half_day in half_days]))
                )

            if len(attendance_records) < date_diff(self.work_end_date, self.work_from_date) + 1:
                frappe.throw(_("You are not present all day(s) between compensatory leave request days"))
        except Exception as e:
            frappe.logger().error(f"Error in validate_attendance: {str(e)}")
            # frappe.throw(_("An error occurred during attendance validation. Please check the logs."))

    def validate_holidays(self):
        frappe.logger().info("Validating holidays...")
        try:
            holidays = get_holiday_dates_for_employee(self.employee, self.work_from_date, self.work_end_date)
            frappe.logger().debug(f"Holidays fetched: {holidays}")

            attendance_records = frappe.get_all(
                "Attendance",
                filters={
                    "attendance_date": ["between", (self.work_from_date, self.work_end_date)],
                    "status": "Weekly Off",
                    "docstatus": 1,
                    "employee": self.employee,
                },
                fields=["attendance_date", "status", "custom_over_time"],
            )
            frappe.logger().debug(f"Attendance records for Weekly Off: {attendance_records}")

            overtime_days = [entry.attendance_date for entry in attendance_records if entry.custom_over_time > 0]
            frappe.logger().debug(f"Overtime days identified: {overtime_days}")

            if holidays or overtime_days:
                frappe.msgprint(
                    _("Compensatory leave will be added for the following dates: {}").format(
                        ", ".join([frappe.bold(format_date(day)) for day in overtime_days or holidays])
                    )
                )
            elif not holidays and not overtime_days:
                if date_diff(self.work_end_date, self.work_from_date):
                    msg = _("The days between {0} to {1} are not valid holidays,weekly off or weekly offs with overtime.").format(
                        frappe.bold(format_date(self.work_from_date)),
                        frappe.bold(format_date(self.work_end_date)),
                    )
                else:
                    msg = _("{0} is not a holiday,weekly off or a weekly off with overtime.").format(
                        frappe.bold(format_date(self.work_from_date))
                    )
                frappe.throw(msg)
        except Exception as e:
            frappe.logger().error(f"Error in validate_holidays: {str(e)}")
            # frappe.throw(_("An error occurred during holiday validation. Please check the logs."))

    def calculate_overtime_leave(self):
        frappe.logger().info("Calculating overtime leave...")
        try:
            attendance_records = frappe.get_all(
                "Attendance",
                filters={
                    "attendance_date": ["between", (self.work_from_date, self.work_end_date)],
                    "status": "Weekly Off",
                    "docstatus": 1,
                    "employee": self.employee,
                },
                fields=["attendance_date", "custom_over_time"],
            )
            frappe.logger().debug(f"Attendance records for overtime calculation: {attendance_records}")

            overtime_leave_days = 0
            for record in attendance_records:
                overtime_hours = record.custom_over_time
                if not overtime_hours:
                    frappe.logger().warning(f"No custom_over_time for record: {record}")
                    continue
                overtime_leave_days += overtime_hours / 8  # Assuming 8 hours equals 1 day of leave

            frappe.logger().info(f"Overtime leave days calculated: {overtime_leave_days}")
            return overtime_leave_days
        except Exception as e:
            frappe.logger().error(f"Error in calculate_overtime_leave: {str(e)}")
            # frappe.throw(_("An error occurred while calculating overtime leave. Please check the logs."))



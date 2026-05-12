
import frappe
from frappe.utils import getdate, get_time, flt, time_diff_in_hours

def validate_half_day_attendance(doc, method=None):

    logs = frappe.get_all("Employee Checkin", filters={
        "employee": doc.employee,
        "time": ["between", [str(doc.attendance_date) + " 00:00:00", str(doc.attendance_date) + " 23:59:59"]]
    }, fields=["time", "log_type"], order_by="time asc")

    if not logs:
        return

    # 2. Calculation of Working Hours
    working_hours = 0
    last_in = None
    for log in logs:
        if log.log_type == "IN":
            last_in = log.time
        elif log.log_type == "OUT" and last_in:
            working_hours += time_diff_in_hours(log.time, last_in)
            last_in = None

    
    in_time = get_time(logs[0].time)
    out_time = get_time(logs[-1].time)
    attendance_date = getdate(doc.attendance_date)
    is_saturday = attendance_date.weekday() == 5
    
    min_hd_hours = 4.0 if is_saturday else 4.5
    full_day_hours = 8.5
    
    final_status = "Absent"
    final_half_day_status = ""

  
    # CASE A: Full Day Present
    if working_hours >= full_day_hours:
        final_status = "Present"
        final_half_day_status = ""

    # CASE B: Half Day Eligibility (Hours + Timing Check)
    elif working_hours >= min_hd_hours:
        is_timing_ok = False
        
        # 1st Half: In <= 10:00 AM & Out >= 02:30 PM
        if in_time <= get_time("10:05:00") and out_time >= get_time("14:30:00"):
            is_timing_ok = True
            
        # 2nd Half: In <= 01:30 PM & Out >= 06:30 PM (Sat: 05:00 PM)
        elif in_time <= get_time("13:35:00"):
            target_out = "17:00:00" if is_saturday else "18:30:00"
            if out_time >= get_time(target_out):
                is_timing_ok = True

        if is_timing_ok:
            final_status = "Half Day"
            final_half_day_status = "Present"
        else:
           
            final_status = "Absent"
            final_half_day_status = ""

    # CASE C: Less than 4.5 Hours
    else:
        if doc.leave_application:
            final_status = "Half Day"
            final_half_day_status = "Absent"
        else:
            final_status = "Absent"
            final_half_day_status = ""

    frappe.db.set_value("Attendance", doc.name, {
        "working_hours": flt(working_hours),
        "status": final_status,
        "half_day_status": final_half_day_status
    }, update_modified=False)

   
    doc.working_hours = flt(working_hours)
    doc.status = final_status
    doc.half_day_status = final_half_day_status
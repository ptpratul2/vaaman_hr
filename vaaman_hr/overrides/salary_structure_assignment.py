"""Overrides for HRMS Salary Structure Assignment formula pre-evaluation.

HRMS v16+ pre-evaluates every Salary Structure formula when a Salary Structure
Assignment is saved (to compute annual_gross_earning / ctc), using a
synthetic context built from the SSA + Employee + a fixed list of
pseudo Salary Slip fields (start_date, payment_days, ...). Any *custom*
field added on Salary Slip (e.g. total_weekly_off) that a formula
references isn't in that fixed list, so this pre-check raises a
NameError even though the real Salary Slip evaluation works fine
(get_data_for_eval() there merges the full slip via self.as_dict()).

HRMS v15 has no _get_component_eval_context, so this patch is a no-op there.
"""

import frappe

from hrms.payroll.doctype.salary_structure_assignment.salary_structure_assignment import (
	SalaryStructureAssignment,
)


def apply_salary_structure_assignment_patch():
	"""Monkeypatch SSA's formula pre-check to tolerate custom Salary Slip fields."""
	if getattr(SalaryStructureAssignment, "_vaaman_eval_context_patched", False):
		return

	original = getattr(SalaryStructureAssignment, "_get_component_eval_context", None)
	if not callable(original):
		return

	def _patched_get_component_eval_context(self):
		data = original(self)

		# Seed a 0 default for any Salary Slip field missing from the synthetic
		# context, so the SSA-time pre-check doesn't NameError on custom fields.
		# The real Salary Slip evaluation later still computes the actual value.
		for df in frappe.get_meta("Salary Slip").get("fields"):
			if df.fieldname not in data:
				data[df.fieldname] = 0

		return data

	SalaryStructureAssignment._get_component_eval_context = _patched_get_component_eval_context
	SalaryStructureAssignment._vaaman_eval_context_patched = True

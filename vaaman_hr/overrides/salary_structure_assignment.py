"""Overrides for HRMS Salary Structure Assignment formula pre-evaluation.

HRMS pre-evaluates every Salary Structure formula when a Salary Structure
Assignment is saved (to compute annual_gross_earning / ctc), using a
synthetic context built from the SSA + Employee + a fixed list of
pseudo Salary Slip fields (start_date, payment_days, ...). Any *custom*
field added on Salary Slip (e.g. total_weekly_off) that a formula
references isn't in that fixed list, so this pre-check raises a
NameError even though the real Salary Slip evaluation works fine
(get_data_for_eval() there merges the full slip via self.as_dict()).

get_evaluated_components() (called by both SSA save AND real Salary Slip
creation, via SalarySlip.set_salary_structure_doc()) shares this same
pre-check, so the gap blocks real payroll too, not just the SSA screen.
"""

import frappe

from hrms.payroll.doctype.salary_structure_assignment.salary_structure_assignment import (
	SalaryStructureAssignment,
)

_original_get_component_eval_context = SalaryStructureAssignment._get_component_eval_context


def _patched_get_component_eval_context(self):
	data = _original_get_component_eval_context(self)

	# Seed a 0 default for any Salary Slip field missing from the synthetic
	# context, so the SSA-time pre-check doesn't NameError on custom fields.
	# The real Salary Slip evaluation later still computes the actual value.
	for df in frappe.get_meta("Salary Slip").get("fields"):
		if df.fieldname not in data:
			data[df.fieldname] = 0

	return data


def apply_salary_structure_assignment_patch():
	"""Monkeypatch SSA's formula pre-check to tolerate custom Salary Slip fields."""
	if getattr(SalaryStructureAssignment, "_vaaman_eval_context_patched", False):
		return

	SalaryStructureAssignment._get_component_eval_context = _patched_get_component_eval_context
	SalaryStructureAssignment._vaaman_eval_context_patched = True

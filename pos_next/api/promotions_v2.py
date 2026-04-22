# -*- coding: utf-8 -*-
# Copyright (c) 2025, POS Next and contributors
# For license information, please see license.txt

"""
Promotions V2 API — CRUD operations for POS Promotion DocType.
Works alongside the existing promotions.py which handles ERPNext Promotional Schemes.
"""

import frappe
from frappe import _
from frappe.utils import flt, nowdate, getdate, cint, now_datetime
import json


def _check_permissions(action="read"):
	"""Check promotion management permissions."""
	if action in ("write", "delete"):
		if not (frappe.has_permission("POS Promotion", action) or
				"System Manager" in frappe.get_roles(frappe.session.user) or
				"Sales Manager" in frappe.get_roles(frappe.session.user)):
			frappe.throw(_("You don't have permission to manage promotions"), frappe.PermissionError)


@frappe.whitelist()
def get_all_promotions(branch=None, promotion_type=None, status=None, include_disabled=False):
	"""
	Get all POS Promotions with filters.

	Args:
		branch: Filter by branch
		promotion_type: Filter by type
		status: Filter by status (Active/Inactive/Expired/Scheduled)
		include_disabled: Include disabled promotions

	Returns:
		List of promotion summaries
	"""
	_check_permissions("read")

	if not frappe.db.table_exists("POS Promotion"):
		return []

	filters = {}

	if not cint(include_disabled):
		filters["enabled"] = 1

	if branch:
		filters["branch"] = branch

	if promotion_type:
		filters["promotion_type"] = promotion_type

	promotions = frappe.get_all(
		"POS Promotion",
		filters=filters,
		fields=[
			"name", "promotion_name", "promotion_type",
			"branch", "start_date", "end_date",
			"start_time", "end_time",
			"stackable", "priority", "enabled",
			"creation", "modified", "modified_by"
		],
		order_by="priority asc, modified desc"
	)

	today = getdate(nowdate())

	for p in promotions:
		# Compute status
		if not p.enabled:
			p["status"] = "Disabled"
		elif p.start_date and getdate(p.start_date) > today:
			p["status"] = "Scheduled"
		elif p.end_date and getdate(p.end_date) < today:
			p["status"] = "Expired"
		else:
			p["status"] = "Active"

		# Get usage count from logs
		if frappe.db.table_exists("POS Promotion Log"):
			p["usage_count"] = frappe.db.count(
				"POS Promotion Log",
				{"promotion": p.name}
			)
		else:
			p["usage_count"] = 0

	# Filter by status if requested
	if status:
		promotions = [p for p in promotions if p["status"] == status]

	return promotions


@frappe.whitelist()
def get_promotion(name):
	"""Get full details of a single promotion."""
	_check_permissions("read")

	if not frappe.db.exists("POS Promotion", name):
		frappe.throw(_("Promotion {0} not found").format(name))

	doc = frappe.get_doc("POS Promotion", name)
	data = doc.as_dict()

	# Add computed status
	today = getdate(nowdate())
	if not doc.enabled:
		data["status"] = "Disabled"
	elif doc.start_date and getdate(doc.start_date) > today:
		data["status"] = "Scheduled"
	elif doc.end_date and getdate(doc.end_date) < today:
		data["status"] = "Expired"
	else:
		data["status"] = "Active"

	return data


@frappe.whitelist()
def create_promotion(data):
	"""
	Create a new POS Promotion.

	Args:
		data: dict or JSON string with promotion fields

	Returns:
		Success response with promotion name
	"""
	_check_permissions("write")

	if isinstance(data, str):
		data = json.loads(data)

	# Validate required fields
	if not data.get("promotion_name"):
		frappe.throw(_("Promotion Name is required"))
	if not data.get("promotion_type"):
		frappe.throw(_("Promotion Type is required"))

	try:
		doc = frappe.new_doc("POS Promotion")
		doc.promotion_name = data["promotion_name"]
		doc.promotion_type = data["promotion_type"]
		doc.branch = data.get("branch")
		doc.enabled = cint(data.get("enabled", 1))
		doc.stackable = cint(data.get("stackable", 1))
		doc.priority = cint(data.get("priority", 10))
		doc.start_date = data.get("start_date")
		doc.end_date = data.get("end_date")
		doc.start_time = data.get("start_time")
		doc.end_time = data.get("end_time")

		# Add rule configuration
		rule_data = data.get("config", {})
		rule = doc.append("rules", {})
		rule.buy_qty = cint(rule_data.get("buy_qty", 0))
		rule.free_qty = cint(rule_data.get("free_qty", 0))
		rule.discount_percentage = flt(rule_data.get("discount_percentage", 0))
		rule.cashback_threshold = flt(rule_data.get("cashback_threshold", 0))
		rule.cashback_percentage = flt(rule_data.get("cashback_percentage", 0))
		rule.cashback_max_cap = flt(rule_data.get("cashback_max_cap", 0))
		rule.bundle_qty = cint(rule_data.get("bundle_qty", 0))
		rule.bundle_fixed_price = flt(rule_data.get("bundle_fixed_price", 0))
		rule.max_categories = cint(rule_data.get("max_categories", 3))

		# Add eligible items
		for item in data.get("items", []):
			doc.append("promotion_items", {
				"item_code": item.get("item_code"),
				"item_group": item.get("item_group"),
				"brand": item.get("brand"),
			})

		doc.insert()

		return {
			"success": True,
			"message": _("Promotion '{0}' created successfully").format(doc.promotion_name),
			"name": doc.name,
		}

	except Exception as e:
		frappe.db.rollback()
		frappe.log_error(title=_("Promotion Creation Failed"), message=frappe.get_traceback())
		frappe.throw(_("Failed to create promotion: {0}").format(str(e)))


@frappe.whitelist()
def update_promotion(name, data):
	"""Update an existing POS Promotion."""
	_check_permissions("write")

	if isinstance(data, str):
		data = json.loads(data)

	if not frappe.db.exists("POS Promotion", name):
		frappe.throw(_("Promotion {0} not found").format(name))

	try:
		doc = frappe.get_doc("POS Promotion", name)

		# Update basic fields
		for field in ["promotion_name", "promotion_type", "branch",
					   "enabled", "stackable", "priority",
					   "start_date", "end_date", "start_time", "end_time"]:
			if field in data:
				setattr(doc, field, data[field])

		# Update rule configuration
		if "config" in data:
			rule_data = data["config"]
			if doc.rules and len(doc.rules) > 0:
				rule = doc.rules[0]
			else:
				rule = doc.append("rules", {})

			for field in ["buy_qty", "free_qty", "discount_percentage",
						   "cashback_threshold", "cashback_percentage", "cashback_max_cap",
						   "bundle_qty", "bundle_fixed_price", "max_categories"]:
				if field in rule_data:
					setattr(rule, field, rule_data[field])

		# Update items
		if "items" in data:
			doc.promotion_items = []
			for item in data["items"]:
				doc.append("promotion_items", {
					"item_code": item.get("item_code"),
					"item_group": item.get("item_group"),
					"brand": item.get("brand"),
				})

		doc.save()

		return {
			"success": True,
			"message": _("Promotion '{0}' updated successfully").format(doc.promotion_name),
		}

	except Exception as e:
		frappe.db.rollback()
		frappe.log_error(title=_("Promotion Update Failed"), message=frappe.get_traceback())
		frappe.throw(_("Failed to update promotion: {0}").format(str(e)))


@frappe.whitelist()
def toggle_promotion(name, enabled=None):
	"""Toggle a promotion on/off."""
	_check_permissions("write")

	if not frappe.db.exists("POS Promotion", name):
		frappe.throw(_("Promotion {0} not found").format(name))

	doc = frappe.get_doc("POS Promotion", name)

	if enabled is not None:
		doc.enabled = cint(enabled)
	else:
		doc.enabled = 0 if doc.enabled else 1

	doc.save()

	status = "enabled" if doc.enabled else "disabled"
	return {
		"success": True,
		"message": _("Promotion '{0}' {1}").format(doc.promotion_name, status),
		"enabled": doc.enabled,
	}


@frappe.whitelist()
def delete_promotion(name):
	"""Delete a POS Promotion."""
	_check_permissions("delete")

	if not frappe.db.exists("POS Promotion", name):
		frappe.throw(_("Promotion {0} not found").format(name))

	try:
		frappe.delete_doc("POS Promotion", name)
		return {
			"success": True,
			"message": _("Promotion deleted successfully"),
		}
	except Exception as e:
		frappe.db.rollback()
		frappe.throw(_("Failed to delete promotion: {0}").format(str(e)))


@frappe.whitelist()
def get_promotion_report(name=None, branch=None, from_date=None, to_date=None):
	"""
	Get promotion usage report.

	Args:
		name: specific promotion name
		branch: filter by branch
		from_date: start date
		to_date: end date

	Returns:
		Usage statistics per promotion
	"""
	_check_permissions("read")

	if not frappe.db.table_exists("POS Promotion"):
		return []

	filters = {"enabled": ["in", [0, 1]]}
	if name:
		filters["name"] = name
	if branch:
		filters["branch"] = branch

	promotions = frappe.get_all(
		"POS Promotion",
		filters=filters,
		fields=["name", "promotion_name", "promotion_type", "branch", "enabled"]
	)

	result = []
	for p in promotions:
		log_filters = {"promotion": p.name}
		if from_date:
			log_filters["applied_at"] = [">=", from_date]
		if to_date:
			log_filters["applied_at"] = ["<=", to_date]

		if frappe.db.table_exists("POS Promotion Log"):
			logs = frappe.get_all(
				"POS Promotion Log",
				filters=log_filters,
				fields=["discount_amount", "cashback_amount", "applied_at"]
			)
		else:
			logs = []

		p["total_uses"] = len(logs)
		p["total_discount"] = sum(flt(l.get("discount_amount", 0)) for l in logs)
		p["total_cashback"] = sum(flt(l.get("cashback_amount", 0)) for l in logs)
		result.append(p)

	return result

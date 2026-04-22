# Copyright (c) 2025, BrainWise and contributors
# Promotion demo data generator for testing purposes

import frappe
from frappe import _
from frappe.utils import today, add_days


@frappe.whitelist()
def create_demo_promotions():
	"""
	Create sample POS Promotions for testing all 6 promotion types.
	Returns the list of created promotion names.

	Requires System Manager or Sales Manager role.
	"""
	if not frappe.has_permission("POS Promotion", "create"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	created = []
	start = today()
	end = add_days(start, 90)

	demos = [
		{
			"promotion_name": "🎁 Buy 2 Get 1 Free — All Items",
			"promotion_type": "buy_x_get_y",
			"enabled": 1,
			"stackable": 1,
			"priority": 1,
			"start_date": start,
			"end_date": end,
			"rules": [
				{"buy_qty": 2, "get_qty": 1}
			],
			"promotion_items": []
		},
		{
			"promotion_name": "💰 10% Invoice Discount",
			"promotion_type": "invoice_discount",
			"enabled": 1,
			"stackable": 1,
			"priority": 20,
			"start_date": start,
			"end_date": end,
			"rules": [
				{"discount_percentage": 10}
			],
			"promotion_items": []
		},
		{
			"promotion_name": "💵 Cashback — Spend 500 Get 5%",
			"promotion_type": "cashback",
			"enabled": 1,
			"stackable": 1,
			"priority": 30,
			"start_date": start,
			"end_date": end,
			"rules": [
				{
					"min_spend_threshold": 500,
					"cashback_percentage": 5,
					"cashback_max_cap": 100
				}
			],
			"promotion_items": []
		},
		{
			"promotion_name": "⏰ Happy Hour — 15% Off (12-2 PM)",
			"promotion_type": "time_based",
			"enabled": 1,
			"stackable": 0,
			"priority": 5,
			"start_date": start,
			"end_date": end,
			"start_time": "12:00:00",
			"end_time": "14:00:00",
			"rules": [
				{"discount_percentage": 15}
			],
			"promotion_items": []
		},
		{
			"promotion_name": "📦 Bundle Deal — Any 3 for 20% Off",
			"promotion_type": "fixed_bundle",
			"enabled": 1,
			"stackable": 0,
			"priority": 3,
			"start_date": start,
			"end_date": end,
			"rules": [
				{"bundle_qty": 3, "discount_percentage": 20}
			],
			"promotion_items": []
		},
		{
			"promotion_name": "🏷️ Category Discount — 25% Max per Category",
			"promotion_type": "category_discount",
			"enabled": 1,
			"stackable": 1,
			"priority": 15,
			"start_date": start,
			"end_date": end,
			"rules": [
				{"discount_percentage": 25, "max_category_discount": 25}
			],
			"promotion_items": []
		}
	]

	for demo in demos:
		# Skip if already exists
		if frappe.db.exists("POS Promotion", {"promotion_name": demo["promotion_name"]}):
			existing = frappe.db.get_value("POS Promotion", {"promotion_name": demo["promotion_name"]}, "name")
			created.append(existing)
			continue

		rules = demo.pop("rules", [])
		items = demo.pop("promotion_items", [])

		doc = frappe.new_doc("POS Promotion")
		doc.update(demo)

		for rule in rules:
			doc.append("rules", rule)

		for item in items:
			doc.append("promotion_items", item)

		doc.insert(ignore_permissions=True)
		created.append(doc.name)

	frappe.db.commit()

	frappe.msgprint(
		_("Created {0} demo promotions successfully.").format(len(created)),
		indicator="green",
		alert=True
	)

	return created


@frappe.whitelist()
def clear_demo_promotions():
	"""
	Delete all POS Promotions whose names start with demo emoji markers.
	Returns count of deleted records.

	Requires System Manager or Sales Manager role.
	"""
	if not frappe.has_permission("POS Promotion", "delete"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	demo_markers = ["🎁", "💰", "💵", "⏰", "📦", "🏷️"]

	all_promos = frappe.get_all(
		"POS Promotion",
		fields=["name", "promotion_name"],
		order_by="creation asc"
	)

	deleted = 0
	for promo in all_promos:
		is_demo = any(promo["promotion_name"].startswith(marker) for marker in demo_markers)
		if is_demo:
			frappe.delete_doc("POS Promotion", promo["name"], force=True)
			deleted += 1

	frappe.db.commit()

	frappe.msgprint(
		_("Deleted {0} demo promotions.").format(deleted),
		indicator="orange",
		alert=True
	)

	return deleted

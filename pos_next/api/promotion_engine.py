# -*- coding: utf-8 -*-
# Copyright (c) 2025, POS Next and contributors
# For license information, please see license.txt

"""
Promotion Engine — Phase-based pipeline for applying promotions to POS invoices.

Execution Order (3 phases):
  Phase 1 (Item-level):  Fixed Bundle → Buy X Get Y → Category Discount → Time-Based
  Phase 2 (Invoice-level): Total Invoice Discount (%)
  Phase 3 (Post-invoice):  Cashback

Each handler implements is_eligible() and apply().
Stacking rules and conflict resolution are enforced centrally.
"""

import frappe
from frappe import _
from frappe.utils import flt, nowdate, now_datetime, getdate, get_datetime, cint
from datetime import timedelta
import json
import copy


# =============================================================================
# Constants
# =============================================================================

PROMOTION_TYPES = [
	"buy_x_get_y",
	"invoice_discount",
	"cashback",
	"time_based",
	"fixed_bundle",
	"category_discount",
]

# Phase assignment — determines execution order
PHASE_MAP = {
	"fixed_bundle": 1,
	"buy_x_get_y": 1,
	"category_discount": 1,
	"time_based": 1,
	"invoice_discount": 2,
	"cashback": 3,
}

# Default priority within phase (lower = runs first)
DEFAULT_PRIORITY_MAP = {
	"fixed_bundle": 1,
	"buy_x_get_y": 2,
	"category_discount": 3,
	"time_based": 4,
	"invoice_discount": 5,
	"cashback": 6,
}

# Stacking compatibility matrix — (type_a, type_b) pairs that CAN stack
STACKABLE_PAIRS = {
	("buy_x_get_y", "category_discount"),
	("buy_x_get_y", "time_based"),
	("buy_x_get_y", "invoice_discount"),
	("buy_x_get_y", "cashback"),
	("category_discount", "time_based"),
	("category_discount", "invoice_discount"),
	("category_discount", "cashback"),
	("time_based", "invoice_discount"),
	("time_based", "cashback"),
	("invoice_discount", "cashback"),
	("fixed_bundle", "invoice_discount"),
	("fixed_bundle", "cashback"),
}


# =============================================================================
# Data structures
# =============================================================================

class PromotionResult:
	"""Result of applying a single promotion."""

	def __init__(self, promotion, success=False, discount_amount=0,
				 cashback_amount=0, affected_items=None, message=""):
		self.promotion = promotion
		self.success = success
		self.discount_amount = flt(discount_amount, 2)
		self.cashback_amount = flt(cashback_amount, 2)
		self.affected_items = affected_items or []
		self.message = message

	def to_dict(self):
		return {
			"promotion_id": self.promotion.get("name", ""),
			"promotion_name": self.promotion.get("promotion_name", ""),
			"promotion_type": self.promotion.get("promotion_type", ""),
			"success": self.success,
			"discount_amount": self.discount_amount,
			"cashback_amount": self.cashback_amount,
			"affected_items": self.affected_items,
			"message": self.message,
		}


# =============================================================================
# Handler Base
# =============================================================================

class BasePromotionHandler:
	"""Base class for all promotion type handlers."""

	def is_eligible(self, invoice, promo):
		"""Check if the invoice is eligible for this promotion."""
		raise NotImplementedError

	def apply(self, invoice, promo):
		"""Apply the promotion to the invoice. Returns PromotionResult."""
		raise NotImplementedError

	def _get_eligible_items(self, invoice, promo):
		"""Get items matching the promotion's item/group/brand filters."""
		rules = promo.get("rules", [])
		if not rules:
			return invoice.get("items", [])

		eligible = []
		for item in invoice.get("items", []):
			for rule in rules:
				if rule.get("item_code") and rule["item_code"] == item.get("item_code"):
					eligible.append(item)
					break
				elif rule.get("item_group") and rule["item_group"] == item.get("item_group"):
					eligible.append(item)
					break
				elif rule.get("brand") and rule["brand"] == item.get("brand"):
					eligible.append(item)
					break
		return eligible


# =============================================================================
# Phase 1 Handlers
# =============================================================================

class FixedBundleHandler(BasePromotionHandler):
	"""
	Fixed Price Bundle:
	- Exact quantity required (no more, no less)
	- Discount distributed equally across items
	- Not repeatable — only one bundle per invoice
	"""

	def is_eligible(self, invoice, promo):
		config = promo.get("config", {})
		bundle_qty = cint(config.get("bundle_qty", 0))
		if bundle_qty < 2:
			return False

		eligible_items = self._get_eligible_items(invoice, promo)
		total_qty = sum(flt(item.get("qty", 0)) for item in eligible_items)
		return total_qty == bundle_qty

	def apply(self, invoice, promo):
		config = promo.get("config", {})
		bundle_qty = cint(config.get("bundle_qty", 0))
		fixed_price = flt(config.get("bundle_fixed_price", 0))

		eligible_items = self._get_eligible_items(invoice, promo)
		if not eligible_items:
			return PromotionResult(promo, success=False, message=_("No eligible items"))

		# Calculate original total of eligible items
		original_total = sum(
			flt(item.get("rate", 0)) * flt(item.get("qty", 0))
			for item in eligible_items
		)

		if fixed_price >= original_total:
			return PromotionResult(promo, success=False,
								   message=_("Bundle price is not less than item total"))

		# Distribute discount equally across items
		total_discount = original_total - fixed_price
		per_item_discount = flt(total_discount / bundle_qty, 2)
		affected = []

		for item in eligible_items:
			qty = flt(item.get("qty", 0))
			for _ in range(int(qty)):
				item_discount = per_item_discount
				item.setdefault("promotion_discounts", []).append({
					"promotion_id": promo.get("name"),
					"promotion_type": "fixed_bundle",
					"discount_amount": item_discount,
				})
			affected.append(item.get("item_code"))

		return PromotionResult(
			promo, success=True,
			discount_amount=total_discount,
			affected_items=affected,
			message=_("Bundle applied: {0} items for {1}").format(bundle_qty, fixed_price)
		)


class BuyXGetYHandler(BasePromotionHandler):
	"""
	Buy X Get Y Free:
	- Customer pays for highest-priced items only
	- Repeatable and scales with quantity
	- No minimum order required
	"""

	def is_eligible(self, invoice, promo):
		config = promo.get("config", {})
		buy_qty = cint(config.get("buy_qty", 0))
		free_qty = cint(config.get("free_qty", 0))
		if buy_qty < 1 or free_qty < 1:
			return False

		eligible_items = self._get_eligible_items(invoice, promo)
		total_qty = sum(flt(item.get("qty", 0)) for item in eligible_items)
		group_size = buy_qty + free_qty
		return total_qty >= group_size

	def apply(self, invoice, promo):
		config = promo.get("config", {})
		buy_qty = cint(config.get("buy_qty", 0))
		free_qty = cint(config.get("free_qty", 0))
		group_size = buy_qty + free_qty

		eligible_items = self._get_eligible_items(invoice, promo)

		# Expand items by qty into individual units with their price
		units = []
		for item in eligible_items:
			rate = flt(item.get("rate", 0))
			qty = int(flt(item.get("qty", 0)))
			for _ in range(qty):
				units.append({"item_code": item.get("item_code"), "rate": rate, "item_ref": item})

		total_units = len(units)
		sets = total_units // group_size
		free_count = sets * free_qty

		if free_count == 0:
			return PromotionResult(promo, success=False, message=_("Not enough items for promotion"))

		# Sort descending by price — free items are the cheapest
		units.sort(key=lambda u: u["rate"], reverse=True)

		# The last `free_count` units become free
		free_units = units[-free_count:]
		total_discount = sum(u["rate"] for u in free_units)

		# Track discounts per item_code
		discount_per_item = {}
		for u in free_units:
			code = u["item_code"]
			discount_per_item.setdefault(code, 0)
			discount_per_item[code] += u["rate"]

		# Apply to original items
		affected = []
		for item in eligible_items:
			code = item.get("item_code")
			if code in discount_per_item:
				item.setdefault("promotion_discounts", []).append({
					"promotion_id": promo.get("name"),
					"promotion_type": "buy_x_get_y",
					"discount_amount": discount_per_item[code],
				})
				affected.append(code)

		return PromotionResult(
			promo, success=True,
			discount_amount=total_discount,
			affected_items=affected,
			message=_("Buy {0} Get {1} Free applied ({2} sets)").format(buy_qty, free_qty, sets)
		)


class CategoryDiscountHandler(BasePromotionHandler):
	"""
	Category-Based Discount:
	- Applies only if items are from ≤ 3 categories
	- Fails if more than 3 categories are included
	"""

	def is_eligible(self, invoice, promo):
		config = promo.get("config", {})
		max_categories = cint(config.get("max_categories", 3))
		discount_pct = flt(config.get("discount_percentage", 0))
		if discount_pct <= 0:
			return False

		# Count distinct categories in the entire invoice
		categories = set()
		for item in invoice.get("items", []):
			if item.get("item_group"):
				categories.add(item["item_group"])

		return len(categories) <= max_categories

	def apply(self, invoice, promo):
		config = promo.get("config", {})
		discount_pct = flt(config.get("discount_percentage", 0))

		eligible_items = self._get_eligible_items(invoice, promo)
		if not eligible_items:
			eligible_items = invoice.get("items", [])

		total_discount = 0
		affected = []

		for item in eligible_items:
			rate = flt(item.get("rate", 0))
			qty = flt(item.get("qty", 0))
			item_discount = flt(rate * qty * discount_pct / 100, 2)
			total_discount += item_discount

			item.setdefault("promotion_discounts", []).append({
				"promotion_id": promo.get("name"),
				"promotion_type": "category_discount",
				"discount_percentage": discount_pct,
				"discount_amount": item_discount,
			})
			affected.append(item.get("item_code"))

		return PromotionResult(
			promo, success=True,
			discount_amount=total_discount,
			affected_items=affected,
			message=_("Category discount {0}% applied").format(discount_pct)
		)


class TimeBasedHandler(BasePromotionHandler):
	"""
	Time-Based Discount:
	- Active only within defined server-based time range
	- Can be overridden ±10 minutes by authorized roles
	"""

	def is_eligible(self, invoice, promo):
		config = promo.get("config", {})
		discount_pct = flt(config.get("discount_percentage", 0))
		if discount_pct <= 0:
			return False

		start_time = config.get("start_time")
		end_time = config.get("end_time")

		if not start_time or not end_time:
			return True  # No time restriction = always active

		now = now_datetime()
		current_time = now.time()

		from datetime import time as dt_time
		if isinstance(start_time, str):
			parts = start_time.split(":")
			start_time = dt_time(int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)
		if isinstance(end_time, str):
			parts = end_time.split(":")
			end_time = dt_time(int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)

		# Check if within window
		if start_time <= current_time <= end_time:
			return True

		# Check ±10 minute override tolerance
		tolerance = timedelta(minutes=10)
		from datetime import datetime, date
		start_dt = datetime.combine(date.today(), start_time)
		end_dt = datetime.combine(date.today(), end_time)
		now_dt = datetime.combine(date.today(), current_time)

		if (start_dt - tolerance) <= now_dt <= (end_dt + tolerance):
			# Within tolerance — check role permission
			user_roles = frappe.get_roles(frappe.session.user)
			if "System Manager" in user_roles or "Sales Manager" in user_roles:
				# Log the override
				frappe.log_error(
					title=_("Time-Based Promotion Override"),
					message=_("User {0} applied time-based promotion {1} outside window (±10 min tolerance)").format(
						frappe.session.user, promo.get("name")
					)
				)
				return True

		return False

	def apply(self, invoice, promo):
		config = promo.get("config", {})
		discount_pct = flt(config.get("discount_percentage", 0))

		eligible_items = self._get_eligible_items(invoice, promo)
		if not eligible_items:
			eligible_items = invoice.get("items", [])

		total_discount = 0
		affected = []

		for item in eligible_items:
			rate = flt(item.get("rate", 0))
			qty = flt(item.get("qty", 0))
			item_discount = flt(rate * qty * discount_pct / 100, 2)
			total_discount += item_discount

			item.setdefault("promotion_discounts", []).append({
				"promotion_id": promo.get("name"),
				"promotion_type": "time_based",
				"discount_percentage": discount_pct,
				"discount_amount": item_discount,
			})
			affected.append(item.get("item_code"))

		return PromotionResult(
			promo, success=True,
			discount_amount=total_discount,
			affected_items=affected,
			message=_("Time-based discount {0}% applied").format(discount_pct)
		)


# =============================================================================
# Phase 2 Handler
# =============================================================================

class InvoiceDiscountHandler(BasePromotionHandler):
	"""
	Total Invoice Discount (%):
	- Applied to final invoice total after all item-level promotions
	- No exclusions — applies to all items
	- Stackable with all promotions
	"""

	def is_eligible(self, invoice, promo):
		config = promo.get("config", {})
		discount_pct = flt(config.get("discount_percentage", 0))
		return discount_pct > 0

	def apply(self, invoice, promo):
		config = promo.get("config", {})
		discount_pct = flt(config.get("discount_percentage", 0))

		# Calculate subtotal after Phase 1 discounts
		subtotal = 0
		for item in invoice.get("items", []):
			rate = flt(item.get("rate", 0))
			qty = flt(item.get("qty", 0))
			item_total = rate * qty

			# Subtract any already-applied promotion discounts
			for pd in item.get("promotion_discounts", []):
				item_total -= flt(pd.get("discount_amount", 0))

			subtotal += max(item_total, 0)

		discount_amount = flt(subtotal * discount_pct / 100, 2)

		# Distribute proportionally across items
		affected = []
		for item in invoice.get("items", []):
			rate = flt(item.get("rate", 0))
			qty = flt(item.get("qty", 0))
			item_total = rate * qty

			for pd in item.get("promotion_discounts", []):
				item_total -= flt(pd.get("discount_amount", 0))

			item_total = max(item_total, 0)

			if subtotal > 0:
				item_share = flt(item_total / subtotal * discount_amount, 2)
			else:
				item_share = 0

			if item_share > 0:
				item.setdefault("promotion_discounts", []).append({
					"promotion_id": promo.get("name"),
					"promotion_type": "invoice_discount",
					"discount_percentage": discount_pct,
					"discount_amount": item_share,
				})
				affected.append(item.get("item_code"))

		return PromotionResult(
			promo, success=True,
			discount_amount=discount_amount,
			affected_items=affected,
			message=_("Invoice discount {0}% applied (saved {1})").format(discount_pct, discount_amount)
		)


# =============================================================================
# Phase 3 Handler
# =============================================================================

class CashbackHandler(BasePromotionHandler):
	"""
	Cashback (Spend X → Get Y%):
	- Instant cash return (does NOT reduce invoice total)
	- Triggered when invoice reaches threshold
	- Has optional maximum cap
	"""

	def is_eligible(self, invoice, promo):
		config = promo.get("config", {})
		threshold = flt(config.get("cashback_threshold", 0))
		pct = flt(config.get("cashback_percentage", 0))
		if threshold <= 0 or pct <= 0:
			return False

		# Calculate final total after all discounts
		final_total = self._get_final_total(invoice)
		return final_total >= threshold

	def apply(self, invoice, promo):
		config = promo.get("config", {})
		threshold = flt(config.get("cashback_threshold", 0))
		pct = flt(config.get("cashback_percentage", 0))
		max_cap = flt(config.get("cashback_max_cap", 0))

		final_total = self._get_final_total(invoice)
		cashback = flt(final_total * pct / 100, 2)

		if max_cap > 0 and cashback > max_cap:
			cashback = max_cap

		return PromotionResult(
			promo, success=True,
			cashback_amount=cashback,
			message=_("Cashback {0}% = {1} (threshold: {2})").format(pct, cashback, threshold)
		)

	def _get_final_total(self, invoice):
		"""Calculate invoice total after all applied discounts."""
		total = 0
		for item in invoice.get("items", []):
			rate = flt(item.get("rate", 0))
			qty = flt(item.get("qty", 0))
			item_total = rate * qty

			for pd in item.get("promotion_discounts", []):
				item_total -= flt(pd.get("discount_amount", 0))

			total += max(item_total, 0)
		return total


# =============================================================================
# Stacking & Conflict Resolution
# =============================================================================

def can_stack(new_promo, applied_results):
	"""
	Check if a new promotion can stack with already-applied promotions.

	Rules:
	1. If new_promo.stackable is False, it can only run alone.
	2. If any applied promo has stackable=False, nothing else can stack.
	3. Check the STACKABLE_PAIRS matrix for type compatibility.
	"""
	new_type = new_promo.get("promotion_type", "")
	new_stackable = cint(new_promo.get("stackable", 1))

	if not new_stackable and len(applied_results) > 0:
		return False

	for result in applied_results:
		if not result.success:
			continue

		applied_promo = result.promotion
		applied_stackable = cint(applied_promo.get("stackable", 1))

		if not applied_stackable:
			return False

		applied_type = applied_promo.get("promotion_type", "")

		# Check compatibility (order-independent lookup)
		pair = tuple(sorted([new_type, applied_type]))
		if pair[0] == pair[1]:
			# Same type — generally not stackable unless different item sets
			if new_type == "buy_x_get_y":
				# BuyXGetY can stack if targeting different items
				new_items = set(r.get("item_code") for r in new_promo.get("rules", []) if r.get("item_code"))
				applied_items = set(result.affected_items or [])
				if new_items and applied_items and not new_items.intersection(applied_items):
					continue
			return False

		if pair not in STACKABLE_PAIRS:
			return False

	return True


# =============================================================================
# Main Engine
# =============================================================================

class PromotionEngine:
	"""Central promotion processor — evaluates and applies promotions."""

	HANDLERS = {
		"buy_x_get_y": BuyXGetYHandler(),
		"invoice_discount": InvoiceDiscountHandler(),
		"cashback": CashbackHandler(),
		"time_based": TimeBasedHandler(),
		"fixed_bundle": FixedBundleHandler(),
		"category_discount": CategoryDiscountHandler(),
	}

	def evaluate(self, invoice_data, branch=None, preview=False):
		"""
		Main entry point: evaluate all active promotions against an invoice.

		Args:
			invoice_data: dict with 'items' list, each item having
						  item_code, rate, qty, item_group, brand
			branch: optional branch filter
			preview: if True, don't persist any changes

		Returns:
			dict with 'invoice', 'applied', 'total_discount', 'total_cashback'
		"""
		# Deep copy to avoid mutating original
		invoice = copy.deepcopy(invoice_data)

		# Fetch active promotions
		promotions = self._get_active_promotions(branch)

		# Sort by phase then priority
		promotions.sort(key=lambda p: (
			PHASE_MAP.get(p.get("promotion_type", ""), 99),
			p.get("priority", DEFAULT_PRIORITY_MAP.get(p.get("promotion_type", ""), 99))
		))

		applied_results = []

		for promo in promotions:
			promo_type = promo.get("promotion_type", "")
			handler = self.HANDLERS.get(promo_type)

			if not handler:
				continue

			# Check eligibility
			if not handler.is_eligible(invoice, promo):
				continue

			# Check stacking compatibility
			if not can_stack(promo, applied_results):
				continue

			# Apply
			result = handler.apply(invoice, promo)
			if result.success:
				applied_results.append(result)

		# Calculate totals
		total_discount = sum(r.discount_amount for r in applied_results)
		total_cashback = sum(r.cashback_amount for r in applied_results)

		return {
			"invoice": invoice,
			"applied": [r.to_dict() for r in applied_results],
			"total_discount": flt(total_discount, 2),
			"total_cashback": flt(total_cashback, 2),
			"promotions_count": len(applied_results),
		}

	def _get_active_promotions(self, branch=None):
		"""Fetch all active POS Promotions from database."""
		if not frappe.db.table_exists("POS Promotion"):
			return []

		filters = {
			"enabled": 1,
		}

		today = nowdate()

		promotions_raw = frappe.get_all(
			"POS Promotion",
			filters=filters,
			fields=[
				"name", "promotion_name", "promotion_type",
				"branch", "start_date", "end_date",
				"start_time", "end_time",
				"stackable", "priority", "enabled"
			],
			order_by="priority asc"
		)

		promotions = []
		for p in promotions_raw:
			# Date filter
			if p.start_date and getdate(p.start_date) > getdate(today):
				continue
			if p.end_date and getdate(p.end_date) < getdate(today):
				continue

			# Branch filter
			if branch and p.branch and p.branch != branch and p.branch != "All":
				continue

			# Enrich with config and rules
			promo = dict(p)
			promo["config"] = self._get_promotion_config(p.name)
			promo["rules"] = self._get_promotion_items(p.name)
			promotions.append(promo)

		return promotions

	def _get_promotion_config(self, promo_name):
		"""Fetch promotion-specific configuration from child table."""
		if not frappe.db.table_exists("POS Promotion Rule"):
			return {}

		rules = frappe.get_all(
			"POS Promotion Rule",
			filters={"parent": promo_name},
			fields=["*"],
			limit=1
		)
		return rules[0] if rules else {}

	def _get_promotion_items(self, promo_name):
		"""Fetch eligible items/groups/brands from child table."""
		if not frappe.db.table_exists("POS Promotion Item"):
			return []

		return frappe.get_all(
			"POS Promotion Item",
			filters={"parent": promo_name},
			fields=["item_code", "item_group", "brand"]
		)


# =============================================================================
# API Endpoints (Whitelisted)
# =============================================================================

@frappe.whitelist()
def evaluate_promotions(invoice_data, branch=None):
	"""
	Evaluate all active promotions for an invoice.

	Args:
		invoice_data: JSON string or dict with invoice items
		branch: optional branch name

	Returns:
		dict with applied promotions and calculated discounts
	"""
	if isinstance(invoice_data, str):
		invoice_data = json.loads(invoice_data)

	engine = PromotionEngine()
	return engine.evaluate(invoice_data, branch=branch)


@frappe.whitelist()
def preview_promotions(invoice_data, branch=None):
	"""
	Preview promotion effects without persisting.
	Same as evaluate but explicitly marked as preview.
	"""
	if isinstance(invoice_data, str):
		invoice_data = json.loads(invoice_data)

	engine = PromotionEngine()
	return engine.evaluate(invoice_data, branch=branch, preview=True)


@frappe.whitelist()
def get_active_promotion_summary(branch=None):
	"""Get a summary of all active promotions for a branch."""
	if not frappe.db.table_exists("POS Promotion"):
		return []

	filters = {"enabled": 1}
	today = nowdate()

	promotions = frappe.get_all(
		"POS Promotion",
		filters=filters,
		fields=[
			"name", "promotion_name", "promotion_type",
			"branch", "start_date", "end_date",
			"stackable", "priority"
		],
		order_by="priority asc"
	)

	result = []
	for p in promotions:
		if p.start_date and getdate(p.start_date) > getdate(today):
			continue
		if p.end_date and getdate(p.end_date) < getdate(today):
			continue
		if branch and p.branch and p.branch != branch and p.branch != "All":
			continue
		result.append(p)

	return result

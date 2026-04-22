# Copyright (c) 2025, POS Next and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, cint, getdate


class POSPromotion(Document):
	def validate(self):
		self.validate_dates()
		self.validate_type_config()

	def validate_dates(self):
		"""Ensure start_date is before end_date."""
		if self.start_date and self.end_date:
			if getdate(self.start_date) > getdate(self.end_date):
				frappe.throw(_("Start Date cannot be after End Date"))

		if self.promotion_type == "time_based":
			if self.start_time and self.end_time:
				if str(self.start_time) >= str(self.end_time):
					frappe.throw(_("Start Time must be before End Time"))

	def validate_type_config(self):
		"""Validate promotion-specific configuration."""
		if not self.rules or len(self.rules) == 0:
			frappe.throw(_("At least one promotion rule configuration is required"))

		rule = self.rules[0]

		if self.promotion_type == "buy_x_get_y":
			if cint(rule.buy_qty) < 1:
				frappe.throw(_("Buy Quantity must be at least 1"))
			if cint(rule.free_qty) < 1:
				frappe.throw(_("Free Quantity must be at least 1"))
			if cint(rule.free_qty) >= cint(rule.buy_qty):
				frappe.throw(_("Free Quantity must be less than Buy Quantity"))

		elif self.promotion_type == "invoice_discount":
			if flt(rule.discount_percentage) <= 0 or flt(rule.discount_percentage) > 100:
				frappe.throw(_("Discount Percentage must be between 0 and 100"))

		elif self.promotion_type == "cashback":
			if flt(rule.cashback_threshold) <= 0:
				frappe.throw(_("Cashback Threshold must be greater than 0"))
			if flt(rule.cashback_percentage) <= 0 or flt(rule.cashback_percentage) > 100:
				frappe.throw(_("Cashback Percentage must be between 0 and 100"))

		elif self.promotion_type == "time_based":
			if flt(rule.discount_percentage) <= 0 or flt(rule.discount_percentage) > 100:
				frappe.throw(_("Discount Percentage must be between 0 and 100"))

		elif self.promotion_type == "fixed_bundle":
			if cint(rule.bundle_qty) < 2:
				frappe.throw(_("Bundle Quantity must be at least 2"))
			if flt(rule.bundle_fixed_price) <= 0:
				frappe.throw(_("Bundle Fixed Price must be greater than 0"))

		elif self.promotion_type == "category_discount":
			if flt(rule.discount_percentage) <= 0 or flt(rule.discount_percentage) > 100:
				frappe.throw(_("Discount Percentage must be between 0 and 100"))
			if cint(rule.max_categories) < 1:
				frappe.throw(_("Max Categories must be at least 1"))
			if cint(rule.max_categories) > 3:
				frappe.throw(_("Max Categories cannot exceed 3"))

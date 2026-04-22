// Copyright (c) 2024, BrainWise and contributors
// For license information, please see license.txt

frappe.ui.form.on("POS Settings", {
	refresh(frm) {
		// Set query for loyalty program filtered by POS Profile company
		frm.set_query("default_loyalty_program", function () {
			if (!frm.doc.__company) {
				return { filters: {} };
			}
			return {
				filters: {
					company: frm.doc.__company,
				},
			};
		});

		// Fetch company when form loads
		if (frm.doc.pos_profile) {
			fetch_pos_profile_company(frm);
		}

		// === Promotion Demo Buttons ===
		if (!frm.is_new()) {
			frm.add_custom_button(
				__("Create Demo Promotions"),
				function () {
					frappe.confirm(
						__("This will create 6 sample promotions (Buy X Get Y, Invoice Discount, Cashback, Time-Based, Bundle, Category). Continue?"),
						function () {
							frappe.call({
								method: "pos_next.api.promotion_demo.create_demo_promotions",
								freeze: true,
								freeze_message: __("Creating demo promotions..."),
								callback: function (r) {
									if (r.message) {
										frm.reload_doc();
									}
								},
							});
						}
					);
				},
				__("Promotions")
			);

			frm.add_custom_button(
				__("Clear Demo Promotions"),
				function () {
					frappe.confirm(
						__("This will permanently delete all demo promotions (identified by emoji markers). Continue?"),
						function () {
							frappe.call({
								method: "pos_next.api.promotion_demo.clear_demo_promotions",
								freeze: true,
								freeze_message: __("Clearing demo promotions..."),
								callback: function (r) {
									if (r.message !== undefined) {
										frm.reload_doc();
									}
								},
							});
						}
					);
				},
				__("Promotions")
			);
		}
	},

	pos_profile(frm) {
		// Clear loyalty program when POS Profile changes
		frm.set_value("default_loyalty_program", "");
		frm.doc.__company = null;

		if (frm.doc.pos_profile) {
			fetch_pos_profile_company(frm);
		}
	},
});

function fetch_pos_profile_company(frm) {
	frappe.db.get_value("POS Profile", frm.doc.pos_profile, "company", (r) => {
		if (r && r.company) {
			frm.doc.__company = r.company;
		}
	});
}

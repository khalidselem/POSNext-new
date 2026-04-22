# POS Promotion Engine — User Guide

> **Version:** 1.0  
> **Module:** POS Next  
> **Last Updated:** April 2026

---

## Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Accessing Promotion Settings](#accessing-promotion-settings)
4. [Creating Promotions](#creating-promotions)
5. [Promotion Types](#promotion-types)
   - [Buy X Get Y](#1-buy-x-get-y)
   - [Invoice Discount](#2-invoice-discount)
   - [Cashback](#3-cashback)
   - [Time-Based Discount](#4-time-based-discount)
   - [Fixed Bundle](#5-fixed-bundle)
   - [Category Discount](#6-category-discount)
6. [Stacking Rules](#stacking-rules)
7. [How the Engine Works](#how-the-engine-works)
8. [POS Checkout Experience](#pos-checkout-experience)
9. [Demo Data](#demo-data)
10. [Audit & Reporting](#audit--reporting)
11. [Troubleshooting](#troubleshooting)
12. [API Reference](#api-reference)

---

## Overview

The POS Promotion Engine is a powerful, enterprise-grade system for managing discounts, offers, and incentives across your retail branches. It supports **6 promotion types**, handles **automatic stacking and conflict resolution**, and provides a complete **audit trail** of every promotion applied.

### Key Features

- ✅ 6 distinct promotion types covering all common retail scenarios
- ✅ Automatic evaluation during checkout — no cashier action required
- ✅ Stacking rules prevent conflicting promotions
- ✅ Branch-specific promotions
- ✅ Date/time validity windows
- ✅ Priority-based execution order
- ✅ Full audit log for accounting reconciliation
- ✅ Works alongside existing ERPNext Pricing Rules (additive, not replacing)

---

## Getting Started

### Prerequisites

1. **ERPNext v15** with POS Next app installed
2. **System Manager** or **Sales Manager** role
3. At least one **POS Profile** configured

### Installation

After updating to the latest POS Next version:

```bash
cd frappe-bench
bench migrate
bench build --app pos_next
bench restart
```

This creates the required database tables:
- `POS Promotion` (main)
- `POS Promotion Rule` (configuration)
- `POS Promotion Item` (eligibility)
- `POS Promotion Log` (audit)
- `POS Promotion Detail` (settings link)

---

## Accessing Promotion Settings

Promotions are managed from the **ERPNext Desk**, not the POS frontend.

### Step-by-step

1. Go to the URL bar and type: **POS Settings**
2. Open the settings record for your POS Profile (e.g., `0nss1lrsm3`)
3. Click the **"Promotions"** tab (alongside "Details" and "Barcode")

### Promotions Tab Fields

| Field | Description |
|-------|-------------|
| **Enable Promotion Engine** | Master toggle — must be ON for promotions to work |
| **Promotion Stacking Rule** | `Best Price` (only highest-value promotion) or `Stack All` (all non-conflicting) |
| **Promotions Table** | Link POS Promotion records to this profile |

### Quick Access to POS Promotion List

You can also manage promotions directly from the **POS Promotion** list view:

```
/app/pos-promotion
```

---

## Creating Promotions

### From POS Settings

1. Open POS Settings → Promotions tab
2. Click **"Add Row"** in the Promotions table
3. In the **Promotion** field, click the link icon to create a new POS Promotion
4. Fill in the details and save

### From POS Promotion List

1. Navigate to `/app/pos-promotion`
2. Click **"+ Add POS Promotion"**
3. Fill in the form and save

### Promotion Form Fields

| Field | Required | Description |
|-------|----------|-------------|
| **Promotion Name** | ✅ | Display name (e.g., "Summer Sale 20% Off") |
| **Promotion Type** | ✅ | One of the 6 types (see below) |
| **Branch** | ❌ | Leave blank for all branches, or select specific |
| **Enabled** | ✅ | Toggle on/off without deleting |
| **Stackable** | ❌ | Allow this to combine with other promotions |
| **Priority** | ❌ | Lower number = executed first (default: 10) |
| **Start Date** | ❌ | When the promotion becomes active |
| **End Date** | ❌ | When the promotion expires |
| **Start Time / End Time** | ❌ | For time-based promotions only |

---

## Promotion Types

### 1. Buy X Get Y

> **Type code:** `buy_x_get_y`  
> **Phase:** Item-level (Phase 1)

**Business Rule:** Customer buys X items and gets Y items free. The system charges for the highest-priced items only.

#### Configuration

| Rule Field | Example | Description |
|------------|---------|-------------|
| **Buy Qty** | `2` | Number of items customer must buy |
| **Get Qty** | `1` | Number of free items |

#### How It Works

1. Customer adds 3 units of an item (or mix of eligible items)
2. Engine detects "Buy 2 Get 1" is active
3. The cheapest item becomes free
4. **Repeatable:** Buy 6 → Get 2 free, Buy 9 → Get 3 free

#### Example

```
Cart: 3x Shampoo @ SAR 25 each
Rule: Buy 2 Get 1 Free

Before: SAR 75.00
After:  SAR 50.00  (cheapest item free)
Saving: SAR 25.00
```

#### Eligible Items

Add items to the **Eligible Items** table to restrict which items qualify. Leave empty for all items.

---

### 2. Invoice Discount

> **Type code:** `invoice_discount`  
> **Phase:** Invoice-level (Phase 2)

**Business Rule:** A flat percentage discount on the entire invoice total, applied after all item-level promotions.

#### Configuration

| Rule Field | Example | Description |
|------------|---------|-------------|
| **Discount Percentage** | `10` | Percentage off the invoice total |

#### How It Works

1. All item-level promotions are applied first
2. The invoice subtotal is calculated
3. The discount percentage is applied to the remaining total
4. Tax is recalculated on the discounted amount

#### Example

```
Invoice subtotal: SAR 500.00
Rule: 10% Invoice Discount

Discount: SAR 50.00
After:    SAR 450.00 (+ tax)
```

#### Notes

- ✅ Stackable with all item-level promotions
- ✅ No item exclusions — applies to everything
- ⚠️ Only one invoice discount can be active at a time

---

### 3. Cashback

> **Type code:** `cashback`  
> **Phase:** Post-invoice (Phase 3)

**Business Rule:** When the invoice reaches a minimum spend threshold, the customer receives instant cashback as a percentage of the total.

#### Configuration

| Rule Field | Example | Description |
|------------|---------|-------------|
| **Minimum Spend Threshold** | `500` | Invoice must reach this amount |
| **Cashback Percentage** | `5` | Percentage returned as cashback |
| **Maximum Cashback Cap** | `100` | Maximum cashback amount (0 = no cap) |

#### How It Works

1. Invoice is finalized (all discounts applied)
2. Engine checks if total ≥ threshold
3. Cashback amount = total × percentage
4. If cashback > cap, it's capped
5. Cashback is recorded separately — **does NOT reduce the invoice total**

#### Example

```
Invoice total: SAR 800.00
Rule: Spend 500 → Get 5% (max SAR 100)

Cashback: 800 × 5% = SAR 40.00
Customer pays: SAR 800.00
Customer receives: SAR 40.00 cashback
```

#### Important

- Cashback is a **separate ledger entry** — the invoice amount stays the same
- This ensures tax calculations remain correct
- Cashback can be applied to wallet, store credit, or cash return

---

### 4. Time-Based Discount

> **Type code:** `time_based`  
> **Phase:** Item-level (Phase 1)

**Business Rule:** A percentage discount that is only active during specific hours of the day (e.g., Happy Hour).

#### Configuration

| Rule Field | Example | Description |
|------------|---------|-------------|
| **Discount Percentage** | `15` | Percentage off during the time window |
| **Start Time** | `12:00` | Window opens (server time) |
| **End Time** | `14:00` | Window closes (server time) |

#### How It Works

1. Engine checks current server time against the promotion window
2. If within window → discount is applied to all eligible items
3. If outside window → promotion is skipped entirely
4. A ±10 minute tolerance is allowed with manager permission

#### Example

```
Time: 12:30 PM (within 12:00-14:00 window)
Cart: 2x Coffee @ SAR 20 each
Rule: 15% Happy Hour Discount

Before: SAR 40.00
After:  SAR 34.00
Saving: SAR 6.00
```

#### Notes

- ⚠️ Uses **server time**, not client time (prevents manipulation)
- The ±10 minute tolerance requires `Sales Manager` role

---

### 5. Fixed Bundle

> **Type code:** `fixed_bundle`  
> **Phase:** Item-level (Phase 1)

**Business Rule:** Buy an exact quantity of items together and get a percentage discount on the bundle.

#### Configuration

| Rule Field | Example | Description |
|------------|---------|-------------|
| **Bundle Qty** | `3` | Exact number of items required |
| **Discount Percentage** | `20` | Percentage off the bundle |

#### How It Works

1. Customer must have **exactly** the required quantity of eligible items
2. If qty matches → discount applied to all bundle items
3. If qty doesn't match → promotion not triggered

#### Example

```
Cart: 3x items (matching bundle requirement)
  - Item A: SAR 50
  - Item B: SAR 30
  - Item C: SAR 20
Rule: Any 3 items for 20% off

Before: SAR 100.00
After:  SAR 80.00
Saving: SAR 20.00
```

#### Notes

- Must have **at least** the bundle quantity to trigger
- Multiples of bundle qty are supported (6 items = 2 bundles)

---

### 6. Category Discount

> **Type code:** `category_discount`  
> **Phase:** Item-level (Phase 1)

**Business Rule:** Apply a percentage discount to items within specific categories (item groups), with an optional maximum discount cap per category.

#### Configuration

| Rule Field | Example | Description |
|------------|---------|-------------|
| **Discount Percentage** | `25` | Percentage off items in the category |
| **Max Category Discount** | `25` | Maximum discount percentage allowed |

#### How It Works

1. Engine identifies items that belong to eligible item groups
2. Discount is applied to each qualifying item
3. If the calculated discount exceeds the max cap, it's capped

#### Example

```
Cart: 2x Electronics items
  - Headphones: SAR 200
  - USB Cable: SAR 50
Rule: 25% off Electronics (max 25%)

Before: SAR 250.00
After:  SAR 187.50
Saving: SAR 62.50
```

#### Eligible Items Setup

For category discounts, add **Item Groups** to the Eligible Items table:

| Item Group | Type |
|------------|------|
| Electronics | Item Group |
| Accessories | Item Group |

---

## Stacking Rules

### What is Stacking?

When multiple promotions are active, the engine needs to decide which ones can be applied together. The **Promotion Stacking Rule** in POS Settings controls this.

### Stacking Modes

| Mode | Behavior |
|------|----------|
| **Best Price** | Only the promotion that gives the customer the highest savings is applied |
| **Stack All** | All non-conflicting promotions are applied in priority order |

### Stacking Compatibility Matrix

| Promotion A | Promotion B | Can Stack? |
|-------------|-------------|:----------:|
| Buy X Get Y | Invoice Discount | ✅ |
| Buy X Get Y | Cashback | ✅ |
| Buy X Get Y | Time-Based | ❌ |
| Buy X Get Y | Fixed Bundle | ❌ |
| Invoice Discount | Cashback | ✅ |
| Invoice Discount | Time-Based | ✅ |
| Fixed Bundle | Category Discount | ❌ |
| Time-Based | Category Discount | ❌ |

### Priority

Promotions with **lower priority numbers** are executed first.

```
Priority 1:  Fixed Bundle (executed first)
Priority 5:  Buy X Get Y
Priority 10: Category Discount
Priority 15: Time-Based
Priority 20: Invoice Discount (after all item-level)
Priority 30: Cashback (after invoice total)
```

---

## How the Engine Works

### 3-Phase Execution Pipeline

The engine processes promotions in a strict 3-phase order to prevent calculation conflicts:

```
┌─────────────────────────────────────────────────┐
│ PHASE 1: Item-Level Promotions                  │
│                                                 │
│  1. Fixed Bundle    → exact qty match           │
│  2. Buy X Get Y     → free items                │
│  3. Category         → group-based discounts    │
│  4. Time-Based       → time-window discounts    │
│                                                 │
│  ➜ Item prices are adjusted                     │
├─────────────────────────────────────────────────┤
│ PHASE 2: Invoice-Level Promotions               │
│                                                 │
│  5. Invoice Discount → % off final subtotal     │
│                                                 │
│  ➜ Invoice total is reduced                     │
├─────────────────────────────────────────────────┤
│ PHASE 3: Post-Invoice Promotions                │
│                                                 │
│  6. Cashback        → % returned as cash        │
│                                                 │
│  ➜ Separate ledger entry (not on invoice)       │
└─────────────────────────────────────────────────┘
```

### Why This Order Matters

- **Item-level first:** Ensures correct line-item pricing before totaling
- **Invoice discount second:** Applies to the already-adjusted subtotal
- **Cashback last:** Calculated on the final invoice amount, kept separate so tax isn't affected

---

## POS Checkout Experience

### What the Cashier Sees

When promotions are active, a **Promotion Banner** appears above the cart:

#### Before Purchase
```
┌──────────────────────────────────────┐
│ 🎁  3 promotions available      ▼   │
└──────────────────────────────────────┘
```

Click to expand and see which promotions are available.

#### After Promotions Apply
```
┌──────────────────────────────────────┐
│ ✅  2 promotion(s) applied           │
│     Save SAR 45.00  Cashback SAR 40  │
│                                      │
│  [Buy 2 Get 1] [10% Discount]        │
└──────────────────────────────────────┘
```

### Automatic Application

- Promotions are **automatically evaluated** every time the cart changes
- No cashier action is required
- The banner updates in real-time

### Important Notes for Cashiers

- 🔒 Promotions cannot be manually overridden by cashiers
- ⚙️ Only managers can enable/disable promotions from POS Settings
- 📋 The promotion engine runs **after** ERPNext Pricing Rules, so both systems work together
- 🔌 If the promotion engine encounters an error, the sale **still works** — promotions are non-blocking

---

## Demo Data

### Creating Demo Promotions

For testing, you can quickly create 6 sample promotions:

1. Open **POS Settings** for any profile
2. Click the **"Promotions"** button in the toolbar
3. Select **"Create Demo Promotions"**
4. Confirm the dialog

This creates:

| Promotion | Type | Details |
|-----------|------|---------|
| 🎁 Buy 2 Get 1 Free — All Items | Buy X Get Y | Buy 2, get 1 free |
| 💰 10% Invoice Discount | Invoice Discount | 10% off total |
| 💵 Cashback — Spend 500 Get 5% | Cashback | Spend 500, get 5% back (max 100) |
| ⏰ Happy Hour — 15% Off (12-2 PM) | Time-Based | 15% off during 12:00-14:00 |
| 📦 Bundle Deal — Any 3 for 20% Off | Fixed Bundle | 3 items for 20% off |
| 🏷️ Category Discount — 25% Max | Category Discount | 25% off per category |

All demo promotions are valid for **90 days** from creation.

### Clearing Demo Promotions

1. Click **"Promotions" → "Clear Demo Promotions"**
2. Confirm the dialog
3. All promotions with emoji markers (🎁💰💵⏰📦🏷️) are deleted
4. Your real promotions are **not affected**

---

## Audit & Reporting

### Promotion Application Log

Every time a promotion is applied to an invoice, a record is created in the **POS Promotion Log** child table:

| Field | Description |
|-------|-------------|
| **Invoice** | Sales Invoice name |
| **Applied Date** | When the promotion was applied |
| **Discount Amount** | Total discount given |
| **Cashback Amount** | Cashback amount (if applicable) |

### Viewing Logs

1. Open any **POS Promotion** record
2. Scroll to the **Application Log** section
3. See all invoices where this promotion was applied

### API Reporting

```python
# Get promotion report via API
from pos_next.api.promotions_v2 import get_promotion_report

report = get_promotion_report(
    branch="Main Branch",
    start_date="2026-01-01",
    end_date="2026-12-31"
)
```

---

## Troubleshooting

### Promotions Not Appearing

| Check | Solution |
|-------|----------|
| Engine not enabled | POS Settings → Promotions tab → ✅ Enable Promotion Engine |
| Promotion disabled | Open POS Promotion → ✅ Enabled |
| Date expired | Check Start Date / End Date are valid |
| Wrong branch | Ensure Branch field matches or is blank (all branches) |
| No eligible items | Check the Eligible Items table has matching items/groups |

### Promotion Not Stacking

| Check | Solution |
|-------|----------|
| Stackable unchecked | Open POS Promotion → ✅ Stackable |
| Conflicting types | See stacking matrix — some types cannot stack |
| Best Price mode | Switch to "Stack All" in POS Settings if you want multiple |

### Cashback Not Showing

| Check | Solution |
|-------|----------|
| Below threshold | Invoice total must reach Minimum Spend Threshold |
| Cap reached | Check Maximum Cashback Cap setting |
| Different phase | Cashback appears separately, not as invoice discount |

### Time-Based Not Working

| Check | Solution |
|-------|----------|
| Wrong timezone | Engine uses **server time**, not browser time |
| Outside window | Check Start Time / End Time match current server time |
| ±10 min tolerance | Only available with Sales Manager permission |

### General Issues

```bash
# Check if DocTypes exist
bench console
> frappe.get_doc("DocType", "POS Promotion")

# Re-run migration if tables are missing
bench migrate

# Rebuild frontend if banner not showing
cd apps/pos_next/POS
npm run build
bench restart
```

---

## API Reference

### Engine Evaluation

```python
# Evaluate promotions for an invoice
frappe.call({
    method: "pos_next.api.promotion_engine.evaluate_promotions",
    args: {
        invoice_data: JSON.stringify({
            items: [
                { item_code: "ITEM-001", qty: 3, rate: 100 }
            ]
        }),
        branch: "Main Branch"  // optional
    }
})
```

### Preview (without persisting)

```python
frappe.call({
    method: "pos_next.api.promotion_engine.preview_promotions",
    args: {
        invoice_data: JSON.stringify({ items: [...] }),
        branch: null
    }
})
```

### CRUD Operations

| Endpoint | Method |
|----------|--------|
| `pos_next.api.promotions_v2.get_all_promotions` | List all promotions |
| `pos_next.api.promotions_v2.create_promotion` | Create new promotion |
| `pos_next.api.promotions_v2.update_promotion` | Update existing |
| `pos_next.api.promotions_v2.toggle_promotion` | Enable/disable |
| `pos_next.api.promotions_v2.delete_promotion` | Delete |
| `pos_next.api.promotions_v2.get_promotion_report` | Usage report |

### Demo Data

| Endpoint | Description |
|----------|-------------|
| `pos_next.api.promotion_demo.create_demo_promotions` | Create 6 sample promotions |
| `pos_next.api.promotion_demo.clear_demo_promotions` | Delete all demo promotions |

---

## File Reference

| File | Purpose |
|------|---------|
| `pos_next/api/promotion_engine.py` | Core engine with 3-phase pipeline |
| `pos_next/api/promotions_v2.py` | CRUD API with permissions |
| `pos_next/api/promotion_demo.py` | Demo data generator |
| `pos_next/pos_next/doctype/pos_promotion/` | Main DocType |
| `pos_next/pos_next/doctype/pos_promotion_rule/` | Rule child table |
| `pos_next/pos_next/doctype/pos_promotion_item/` | Eligibility child table |
| `pos_next/pos_next/doctype/pos_promotion_log/` | Audit child table |
| `pos_next/pos_next/doctype/pos_promotion_detail/` | Settings link child table |
| `pos_next/pos_next/doctype/pos_settings/` | POS Settings with Promotions tab |
| `POS/src/stores/posPromotions.js` | Frontend Pinia store |
| `POS/src/components/pos/PromotionBanner.vue` | Real-time banner component |

---

*© 2026 BrainWise — POS Next*

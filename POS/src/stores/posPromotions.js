import { defineStore } from "pinia"
import { computed, ref } from "vue"
import { call } from "@/utils/apiWrapper"
import { logger } from "@/utils/logger"

const log = logger.create("PosPromotions")

/**
 * Store for managing POS Promotion Engine integration.
 *
 * This store bridges the new Promotion Engine (v2) with the POS cart.
 * It handles:
 *   - Evaluating promotions against the current cart
 *   - Caching active promotions for offline use
 *   - Providing promotion preview/summary for UI display
 *
 * Works alongside posOffers.js which handles ERPNext Pricing Rules.
 * The two systems are additive — Pricing Rules are applied first,
 * then POS Promotions are layered on top.
 */
export const usePOSPromotionsStore = defineStore("posPromotions", () => {
	// ==========================================================================
	// State
	// ==========================================================================
	const activePromotions = ref([])      // All active POS Promotions for this branch
	const appliedPromotions = ref([])     // Currently applied promotion results
	const lastEvaluation = ref(null)      // Full result of last engine evaluation
	const isEvaluating = ref(false)       // True while engine is processing
	const hasFetched = ref(false)
	const totalDiscount = ref(0)
	const totalCashback = ref(0)

	// ==========================================================================
	// Computed
	// ==========================================================================
	const appliedCount = computed(() => appliedPromotions.value.length)
	const hasAppliedPromotions = computed(() => appliedPromotions.value.length > 0)
	const hasActivePromotions = computed(() => activePromotions.value.length > 0)

	const promotionSummary = computed(() => ({
		activeCount: activePromotions.value.length,
		appliedCount: appliedPromotions.value.length,
		totalDiscount: totalDiscount.value,
		totalCashback: totalCashback.value,
	}))

	// ==========================================================================
	// Actions
	// ==========================================================================

	/**
	 * Fetch active promotions summary for the current branch.
	 * Used to populate promotion indicators in the UI.
	 */
	async function fetchActivePromotions(branch = null) {
		try {
			const data = await call("pos_next.api.promotion_engine.get_active_promotion_summary", {
				branch,
			})
			activePromotions.value = data?.message || data || []
			hasFetched.value = true
			log.info(`Fetched ${activePromotions.value.length} active promotions`)
		} catch (error) {
			log.error("Failed to fetch active promotions:", error)
			activePromotions.value = []
			hasFetched.value = true
		}
	}

	/**
	 * Evaluate all active promotions against the current cart.
	 *
	 * @param {Object} cartData - Invoice data with items array
	 * @param {string} branch - Optional branch filter
	 * @returns {Object|null} Evaluation result or null on failure
	 */
	async function evaluatePromotions(cartData, branch = null) {
		if (!cartData || !cartData.items || cartData.items.length === 0) {
			clearPromotions()
			return null
		}

		isEvaluating.value = true

		try {
			const result = await call("pos_next.api.promotion_engine.evaluate_promotions", {
				invoice_data: JSON.stringify(cartData),
				branch,
			})

			const evaluation = result?.message || result || {}

			lastEvaluation.value = evaluation
			appliedPromotions.value = evaluation.applied || []
			totalDiscount.value = evaluation.total_discount || 0
			totalCashback.value = evaluation.total_cashback || 0

			log.info(
				`Promotion evaluation: ${evaluation.promotions_count || 0} applied,` +
				` discount=${totalDiscount.value}, cashback=${totalCashback.value}`
			)

			return evaluation
		} catch (error) {
			log.error("Promotion evaluation failed:", error)
			return null
		} finally {
			isEvaluating.value = false
		}
	}

	/**
	 * Preview promotions without persisting.
	 * Used for showing "you could save X" indicators.
	 */
	async function previewPromotions(cartData, branch = null) {
		if (!cartData || !cartData.items || cartData.items.length === 0) {
			return null
		}

		try {
			const result = await call("pos_next.api.promotion_engine.preview_promotions", {
				invoice_data: JSON.stringify(cartData),
				branch,
			})
			return result?.message || result || {}
		} catch (error) {
			log.warn("Promotion preview failed:", error)
			return null
		}
	}

	/**
	 * Build invoice data from cart items for engine evaluation.
	 *
	 * @param {Array} cartItems - Raw cart items from useInvoice
	 * @returns {Object} Invoice data formatted for the promotion engine
	 */
	function buildInvoiceData(cartItems) {
		return {
			items: cartItems.map(item => ({
				item_code: item.item_code,
				item_name: item.item_name,
				rate: item.price_list_rate || item.rate || 0,
				qty: item.quantity || item.qty || 1,
				item_group: item.item_group || "",
				brand: item.brand || "",
				uom: item.uom,
				warehouse: item.warehouse,
			})),
		}
	}

	/**
	 * Clear all applied promotions.
	 */
	function clearPromotions() {
		appliedPromotions.value = []
		lastEvaluation.value = null
		totalDiscount.value = 0
		totalCashback.value = 0
	}

	/**
	 * Reset the entire store (on shift close, etc.)
	 */
	function reset() {
		activePromotions.value = []
		clearPromotions()
		hasFetched.value = false
	}

	return {
		// State
		activePromotions,
		appliedPromotions,
		lastEvaluation,
		isEvaluating,
		hasFetched,
		totalDiscount,
		totalCashback,

		// Computed
		appliedCount,
		hasAppliedPromotions,
		hasActivePromotions,
		promotionSummary,

		// Actions
		fetchActivePromotions,
		evaluatePromotions,
		previewPromotions,
		buildInvoiceData,
		clearPromotions,
		reset,
	}
})

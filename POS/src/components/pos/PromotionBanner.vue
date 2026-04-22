<template>
	<!-- Promotion Banner — shows active promotions and applied savings -->
	<Transition name="slide-down">
		<div v-if="showBanner" class="promotion-banner">
			<!-- Active Promotions Summary -->
			<div v-if="!hasApplied && activeCount > 0" class="banner-info" @click="expanded = !expanded">
				<div class="banner-icon">
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v13m0-13V6a2 2 0 112 2h-2zm0 0V5.5A2.5 2.5 0 109.5 8H12zm-7 4h14M5 12a2 2 0 110-4h14a2 2 0 110 4M5 12v7a2 2 0 002 2h10a2 2 0 002-2v-7"/>
					</svg>
				</div>
				<span class="banner-text">
					{{ __("{0} promotions available", [activeCount]) }}
				</span>
				<svg class="w-3.5 h-3.5 text-amber-500 transition-transform" :class="{ 'rotate-180': expanded }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
				</svg>
			</div>

			<!-- Applied Promotions with Savings -->
			<div v-if="hasApplied" class="banner-applied">
				<div class="banner-icon applied">
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
					</svg>
				</div>
				<div class="flex-1 min-w-0">
					<div class="flex items-center justify-between">
						<span class="banner-text-applied">
							{{ __("{0} promotion(s) applied", [appliedCount]) }}
						</span>
						<div class="flex items-center gap-2">
							<span v-if="totalDiscount > 0" class="savings-badge">
								{{ __("Save {0}", [formatCurrency(totalDiscount)]) }}
							</span>
							<span v-if="totalCashback > 0" class="cashback-badge">
								{{ __("Cashback {0}", [formatCurrency(totalCashback)]) }}
							</span>
						</div>
					</div>
					<!-- Applied promotion names -->
					<div class="applied-names">
						<span v-for="promo in appliedPromotions" :key="promo.promotion_name" class="promo-pill">
							{{ promo.promotion_name }}
						</span>
					</div>
				</div>
			</div>

			<!-- Expanded List of Active Promotions -->
			<Transition name="expand">
				<div v-if="expanded && activePromotions.length > 0" class="banner-details">
					<div v-for="promo in activePromotions" :key="promo.name" class="detail-row">
						<span class="detail-type" :class="typeColor(promo.promotion_type)">
							{{ typeLabel(promo.promotion_type) }}
						</span>
						<span class="detail-name">{{ promo.promotion_name }}</span>
					</div>
				</div>
			</Transition>

			<!-- Evaluating Indicator -->
			<div v-if="isEvaluating" class="evaluating-indicator">
				<div class="animate-spin rounded-full h-3 w-3 border-b-2 border-amber-500"></div>
				<span class="text-[10px] text-amber-600 font-medium">{{ __('Checking promotions...') }}</span>
			</div>
		</div>
	</Transition>
</template>

<script setup>
import { computed, ref } from 'vue'
import { usePOSPromotionsStore } from '@/stores/posPromotions'
import { useBootstrapStore } from '@/stores/bootstrap'

const promotionsStore = usePOSPromotionsStore()
const expanded = ref(false)

const activePromotions = computed(() => promotionsStore.activePromotions)
const appliedPromotions = computed(() => promotionsStore.appliedPromotions)
const activeCount = computed(() => promotionsStore.activePromotions.length)
const appliedCount = computed(() => promotionsStore.appliedPromotions.length)
const hasApplied = computed(() => promotionsStore.hasAppliedPromotions)
const isEvaluating = computed(() => promotionsStore.isEvaluating)
const totalDiscount = computed(() => promotionsStore.totalDiscount)
const totalCashback = computed(() => promotionsStore.totalCashback)

const showBanner = computed(() => activeCount.value > 0 || hasApplied.value || isEvaluating.value)

function formatCurrency(value) {
	// Dynamically get currency from bootstrap store or default to SAR
	const bootstrapStore = useBootstrapStore()
	const currency = bootstrapStore.getPreloadedPOSProfile()?.currency || 'SAR'
	
	return new Intl.NumberFormat(undefined, {
		style: 'currency',
		currency: currency,
		minimumFractionDigits: 2,
	}).format(value)
}

function typeLabel(type) {
	const labels = {
		buy_x_get_y: __('Buy X Get Y'),
		invoice_discount: __('Invoice Discount'),
		cashback: __('Cashback'),
		time_based: __('Time-Based'),
		fixed_bundle: __('Bundle'),
		category_discount: __('Category'),
	}
	return labels[type] || type
}

function typeColor(type) {
	const colors = {
		buy_x_get_y: 'type-purple',
		invoice_discount: 'type-blue',
		cashback: 'type-green',
		time_based: 'type-orange',
		fixed_bundle: 'type-pink',
		category_discount: 'type-teal',
	}
	return colors[type] || ''
}
</script>

<style scoped>
.promotion-banner {
	background: linear-gradient(135deg, #fefce8, #fef3c7);
	border: 1px solid #fde68a;
	border-radius: 0.75rem;
	padding: 0.625rem 0.875rem;
	margin-bottom: 0.5rem;
}

.banner-info, .banner-applied {
	display: flex;
	align-items: center;
	gap: 0.5rem;
	cursor: pointer;
}

.banner-icon {
	display: flex;
	align-items: center;
	justify-content: center;
	width: 1.75rem;
	height: 1.75rem;
	background: #fef3c7;
	border: 1px solid #fde68a;
	border-radius: 0.5rem;
	color: #d97706;
	flex-shrink: 0;
}

.banner-icon.applied {
	background: #d1fae5;
	border-color: #a7f3d0;
	color: #059669;
}

.banner-text {
	font-size: 0.8125rem;
	font-weight: 600;
	color: #92400e;
	flex: 1;
}

.banner-text-applied {
	font-size: 0.8125rem;
	font-weight: 600;
	color: #065f46;
}

.savings-badge {
	display: inline-flex;
	align-items: center;
	padding: 0.125rem 0.5rem;
	background: #d1fae5;
	border: 1px solid #6ee7b7;
	border-radius: 9999px;
	font-size: 0.6875rem;
	font-weight: 700;
	color: #047857;
}

.cashback-badge {
	display: inline-flex;
	align-items: center;
	padding: 0.125rem 0.5rem;
	background: #dbeafe;
	border: 1px solid #93c5fd;
	border-radius: 9999px;
	font-size: 0.6875rem;
	font-weight: 700;
	color: #1d4ed8;
}

.applied-names {
	display: flex;
	flex-wrap: wrap;
	gap: 0.25rem;
	margin-top: 0.375rem;
}

.promo-pill {
	display: inline-flex;
	padding: 0.0625rem 0.375rem;
	background: rgba(5, 150, 105, 0.1);
	border-radius: 0.25rem;
	font-size: 0.625rem;
	color: #065f46;
	font-weight: 500;
}

.banner-details {
	margin-top: 0.5rem;
	padding-top: 0.5rem;
	border-top: 1px solid #fde68a;
	display: flex;
	flex-direction: column;
	gap: 0.375rem;
}

.detail-row {
	display: flex;
	align-items: center;
	gap: 0.5rem;
}

.detail-type {
	display: inline-flex;
	padding: 0.0625rem 0.375rem;
	border-radius: 0.25rem;
	font-size: 0.625rem;
	font-weight: 600;
	flex-shrink: 0;
}

.type-purple { background: #ede9fe; color: #6d28d9; }
.type-blue   { background: #dbeafe; color: #1d4ed8; }
.type-green  { background: #d1fae5; color: #047857; }
.type-orange { background: #ffedd5; color: #c2410c; }
.type-pink   { background: #fce7f3; color: #be185d; }
.type-teal   { background: #ccfbf1; color: #0f766e; }

.detail-name {
	font-size: 0.75rem;
	color: #78350f;
	font-weight: 500;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.evaluating-indicator {
	display: flex;
	align-items: center;
	gap: 0.375rem;
	margin-top: 0.375rem;
	padding-top: 0.375rem;
	border-top: 1px solid #fde68a;
}

/* Transitions */
.slide-down-enter-active, .slide-down-leave-active {
	transition: all 0.3s ease;
}
.slide-down-enter-from, .slide-down-leave-to {
	opacity: 0;
	transform: translateY(-0.5rem);
}

.expand-enter-active, .expand-leave-active {
	transition: all 0.25s ease;
	overflow: hidden;
}
.expand-enter-from, .expand-leave-to {
	opacity: 0;
	max-height: 0;
}
.expand-enter-to, .expand-leave-from {
	max-height: 200px;
}
</style>

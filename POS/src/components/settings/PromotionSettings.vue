<template>
	<!-- Promotion Settings Tab Content -->
	<div class="flex flex-col gap-6">
		<!-- Section Header -->
		<div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
			<div class="px-6 py-4 bg-gradient-to-r from-amber-50 to-orange-50 border-b border-amber-100">
				<div class="flex items-center justify-between">
					<div class="flex items-center gap-3">
						<div class="p-2 bg-amber-100 rounded-lg">
							<svg class="w-5 h-5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v13m0-13V6a2 2 0 112 2h-2zm0 0V5.5A2.5 2.5 0 109.5 8H12zm-7 4h14M5 12a2 2 0 110-4h14a2 2 0 110 4M5 12v7a2 2 0 002 2h10a2 2 0 002-2v-7"/>
							</svg>
						</div>
						<div>
							<h3 class="text-lg font-bold text-gray-900">{{ __('Promotion Settings') }}</h3>
							<p class="text-xs text-gray-600 mt-0.5">{{ __('Manage promotions, discounts, and cashback offers') }}</p>
						</div>
					</div>
					<button
						@click="showCreateForm = true"
						class="inline-flex items-center gap-2 px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white text-sm font-medium rounded-lg transition-colors shadow-sm"
					>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
						</svg>
						{{ __('New Promotion') }}
					</button>
				</div>
			</div>

			<!-- Filters Bar -->
			<div class="px-6 py-3 border-b bg-gray-50 flex flex-wrap gap-3 items-center">
				<select v-model="filterType" class="text-sm border border-gray-300 rounded-md px-3 py-1.5 bg-white focus:ring-2 focus:ring-amber-300 focus:border-amber-400">
					<option value="">{{ __('All Types') }}</option>
					<option value="buy_x_get_y">{{ __('Buy X Get Y') }}</option>
					<option value="invoice_discount">{{ __('Invoice Discount') }}</option>
					<option value="cashback">{{ __('Cashback') }}</option>
					<option value="time_based">{{ __('Time-Based') }}</option>
					<option value="fixed_bundle">{{ __('Fixed Bundle') }}</option>
					<option value="category_discount">{{ __('Category Discount') }}</option>
				</select>
				<select v-model="filterStatus" class="text-sm border border-gray-300 rounded-md px-3 py-1.5 bg-white focus:ring-2 focus:ring-amber-300 focus:border-amber-400">
					<option value="">{{ __('All Status') }}</option>
					<option value="Active">{{ __('Active') }}</option>
					<option value="Disabled">{{ __('Disabled') }}</option>
					<option value="Scheduled">{{ __('Scheduled') }}</option>
					<option value="Expired">{{ __('Expired') }}</option>
				</select>
				<div class="ms-auto text-xs text-gray-500">
					{{ filteredPromotions.length }} {{ __('promotions') }}
				</div>
			</div>

			<!-- Promotions List -->
			<div class="divide-y divide-gray-100">
				<!-- Loading -->
				<div v-if="loading" class="flex items-center justify-center py-12">
					<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-amber-500"></div>
				</div>

				<!-- Empty State -->
				<div v-else-if="filteredPromotions.length === 0" class="flex flex-col items-center justify-center py-12 text-center">
					<svg class="w-12 h-12 text-gray-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v13m0-13V6a2 2 0 112 2h-2zm0 0V5.5A2.5 2.5 0 109.5 8H12zm-7 4h14M5 12a2 2 0 110-4h14a2 2 0 110 4M5 12v7a2 2 0 002 2h10a2 2 0 002-2v-7"/>
					</svg>
					<p class="text-sm text-gray-500 font-medium">{{ __('No promotions found') }}</p>
					<p class="text-xs text-gray-400 mt-1">{{ __('Create a new promotion to get started') }}</p>
				</div>

				<!-- Promotion Cards -->
				<div
					v-for="promo in filteredPromotions"
					:key="promo.name"
					class="px-6 py-4 hover:bg-gray-50 transition-colors cursor-pointer"
					@click="editPromotion(promo)"
				>
					<div class="flex items-center justify-between">
						<div class="flex items-center gap-3 min-w-0">
							<!-- Status Indicator -->
							<div
								class="w-2.5 h-2.5 rounded-full flex-shrink-0"
								:class="{
									'bg-green-500': promo.status === 'Active',
									'bg-gray-400': promo.status === 'Disabled',
									'bg-blue-500': promo.status === 'Scheduled',
									'bg-red-400': promo.status === 'Expired',
								}"
							></div>
							<div class="min-w-0">
								<div class="flex items-center gap-2">
									<span class="text-sm font-semibold text-gray-900 truncate">{{ promo.promotion_name }}</span>
									<span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium"
										:class="typeClasses[promo.promotion_type]">
										{{ typeLabels[promo.promotion_type] }}
									</span>
								</div>
								<div class="flex items-center gap-3 mt-1 text-xs text-gray-500">
									<span v-if="promo.branch">🏪 {{ promo.branch }}</span>
									<span v-else>🌐 {{ __('All Branches') }}</span>
									<span v-if="promo.start_date">📅 {{ promo.start_date }} – {{ promo.end_date || '∞' }}</span>
									<span>⚡ P{{ promo.priority }}</span>
									<span v-if="promo.stackable">🔗 {{ __('Stackable') }}</span>
								</div>
							</div>
						</div>
						<div class="flex items-center gap-2 flex-shrink-0">
							<span class="text-xs text-gray-400">{{ promo.usage_count || 0 }} {{ __('uses') }}</span>
							<!-- Toggle Button -->
							<button
								@click.stop="togglePromo(promo)"
								class="p-1.5 rounded-lg transition-colors"
								:class="promo.enabled ? 'text-green-600 hover:bg-green-50' : 'text-gray-400 hover:bg-gray-100'"
								:title="promo.enabled ? __('Disable') : __('Enable')"
							>
								<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path v-if="promo.enabled" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
									<path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"/>
								</svg>
							</button>
						</div>
					</div>
				</div>
			</div>
		</div>

		<!-- Create/Edit Form Modal -->
		<Transition name="fade">
			<div v-if="showCreateForm" class="fixed inset-0 bg-black bg-opacity-50 z-[400] flex items-center justify-center p-4" @click.self="closeForm">
				<div class="w-full max-w-2xl max-h-[85vh] bg-white rounded-xl shadow-2xl overflow-hidden flex flex-col">
					<!-- Form Header -->
					<div class="flex items-center justify-between px-6 py-4 border-b bg-gradient-to-r from-amber-50 to-orange-50">
						<h3 class="text-lg font-bold text-gray-900">
							{{ editingPromo ? __('Edit Promotion') : __('New Promotion') }}
						</h3>
						<button @click="closeForm" class="p-2 hover:bg-white/50 rounded-lg transition-colors">
							<svg class="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
							</svg>
						</button>
					</div>

					<!-- Form Body -->
					<div class="flex-1 overflow-y-auto p-6">
						<div class="flex flex-col gap-5">
							<!-- Name & Type -->
							<div class="grid grid-cols-2 gap-4">
								<div>
									<label class="block text-sm font-medium text-gray-700 mb-1">{{ __('Promotion Name') }} *</label>
									<input v-model="form.promotion_name" type="text" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-amber-300 focus:border-amber-400" :placeholder="__('e.g., Summer Sale 2025')">
								</div>
								<div>
									<label class="block text-sm font-medium text-gray-700 mb-1">{{ __('Type') }} *</label>
									<select v-model="form.promotion_type" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-amber-300 focus:border-amber-400">
										<option value="">{{ __('Select type...') }}</option>
										<option v-for="(label, key) in typeLabels" :key="key" :value="key">{{ label }}</option>
									</select>
								</div>
							</div>

							<!-- Branch, Priority, Stackable -->
							<div class="grid grid-cols-3 gap-4">
								<div>
									<label class="block text-sm font-medium text-gray-700 mb-1">{{ __('Branch') }}</label>
									<input v-model="form.branch" type="text" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" :placeholder="__('All branches')">
								</div>
								<div>
									<label class="block text-sm font-medium text-gray-700 mb-1">{{ __('Priority') }}</label>
									<input v-model.number="form.priority" type="number" min="1" max="100" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
								</div>
								<div class="flex items-end pb-1">
									<label class="flex items-center gap-2 cursor-pointer">
										<input v-model="form.stackable" type="checkbox" class="w-4 h-4 text-amber-600 border-gray-300 rounded focus:ring-amber-500">
										<span class="text-sm text-gray-700">{{ __('Stackable') }}</span>
									</label>
								</div>
							</div>

							<!-- Dates -->
							<div class="grid grid-cols-2 gap-4">
								<div>
									<label class="block text-sm font-medium text-gray-700 mb-1">{{ __('Start Date') }}</label>
									<input v-model="form.start_date" type="date" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
								</div>
								<div>
									<label class="block text-sm font-medium text-gray-700 mb-1">{{ __('End Date') }}</label>
									<input v-model="form.end_date" type="date" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
								</div>
							</div>

							<!-- Time (for time-based) -->
							<div v-if="form.promotion_type === 'time_based'" class="grid grid-cols-2 gap-4">
								<div>
									<label class="block text-sm font-medium text-gray-700 mb-1">{{ __('Start Time') }}</label>
									<input v-model="form.start_time" type="time" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
								</div>
								<div>
									<label class="block text-sm font-medium text-gray-700 mb-1">{{ __('End Time') }}</label>
									<input v-model="form.end_time" type="time" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
								</div>
							</div>

							<!-- Dynamic Config Fields -->
							<div class="border-t pt-5">
								<h4 class="text-sm font-semibold text-gray-900 mb-3">{{ __('Configuration') }}</h4>

								<!-- Buy X Get Y -->
								<div v-if="form.promotion_type === 'buy_x_get_y'" class="grid grid-cols-2 gap-4">
									<div>
										<label class="block text-sm font-medium text-gray-700 mb-1">{{ __('Buy Quantity (X)') }} *</label>
										<input v-model.number="form.config.buy_qty" type="number" min="1" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
									</div>
									<div>
										<label class="block text-sm font-medium text-gray-700 mb-1">{{ __('Free Quantity (Y)') }} *</label>
										<input v-model.number="form.config.free_qty" type="number" min="1" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
									</div>
								</div>

								<!-- Invoice Discount / Time / Category -->
								<div v-if="['invoice_discount', 'time_based', 'category_discount'].includes(form.promotion_type)" class="grid grid-cols-2 gap-4">
									<div>
										<label class="block text-sm font-medium text-gray-700 mb-1">{{ __('Discount Percentage') }} *</label>
										<input v-model.number="form.config.discount_percentage" type="number" min="0.1" max="100" step="0.1" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
									</div>
									<div v-if="form.promotion_type === 'category_discount'">
										<label class="block text-sm font-medium text-gray-700 mb-1">{{ __('Max Categories') }}</label>
										<input v-model.number="form.config.max_categories" type="number" min="1" max="3" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
										<p class="text-xs text-gray-400 mt-1">{{ __('Maximum 3 categories allowed') }}</p>
									</div>
								</div>

								<!-- Cashback -->
								<div v-if="form.promotion_type === 'cashback'" class="grid grid-cols-3 gap-4">
									<div>
										<label class="block text-sm font-medium text-gray-700 mb-1">{{ __('Threshold') }} *</label>
										<input v-model.number="form.config.cashback_threshold" type="number" min="0" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
									</div>
									<div>
										<label class="block text-sm font-medium text-gray-700 mb-1">{{ __('Cashback %') }} *</label>
										<input v-model.number="form.config.cashback_percentage" type="number" min="0.1" max="100" step="0.1" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
									</div>
									<div>
										<label class="block text-sm font-medium text-gray-700 mb-1">{{ __('Max Cap') }}</label>
										<input v-model.number="form.config.cashback_max_cap" type="number" min="0" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
										<p class="text-xs text-gray-400 mt-1">{{ __('0 = no cap') }}</p>
									</div>
								</div>

								<!-- Fixed Bundle -->
								<div v-if="form.promotion_type === 'fixed_bundle'" class="grid grid-cols-2 gap-4">
									<div>
										<label class="block text-sm font-medium text-gray-700 mb-1">{{ __('Bundle Quantity') }} *</label>
										<input v-model.number="form.config.bundle_qty" type="number" min="2" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
									</div>
									<div>
										<label class="block text-sm font-medium text-gray-700 mb-1">{{ __('Fixed Price') }} *</label>
										<input v-model.number="form.config.bundle_fixed_price" type="number" min="0.01" step="0.01" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
									</div>
								</div>

								<!-- No type selected -->
								<div v-if="!form.promotion_type" class="p-4 bg-gray-50 rounded-lg text-center">
									<p class="text-sm text-gray-500">{{ __('Select a promotion type to see configuration options') }}</p>
								</div>
							</div>

							<!-- Validation Error -->
							<div v-if="formError" class="p-3 bg-red-50 border border-red-200 rounded-lg">
								<p class="text-sm text-red-700">{{ formError }}</p>
							</div>
						</div>
					</div>

					<!-- Form Footer -->
					<div class="flex items-center justify-between px-6 py-4 border-t bg-gray-50">
						<button v-if="editingPromo" @click="deletePromo" class="text-sm text-red-600 hover:text-red-700 font-medium">
							{{ __('Delete') }}
						</button>
						<div v-else></div>
						<div class="flex items-center gap-3">
							<button @click="closeForm" class="px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-lg transition-colors">
								{{ __('Cancel') }}
							</button>
							<button @click="savePromotion" :disabled="saving" class="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50">
								{{ saving ? __('Saving...') : (editingPromo ? __('Update') : __('Create')) }}
							</button>
						</div>
					</div>
				</div>
			</div>
		</Transition>
	</div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { call } from 'frappe-ui'

const props = defineProps({
	posProfile: String,
	company: String,
})

// State
const loading = ref(false)
const saving = ref(false)
const promotions = ref([])
const showCreateForm = ref(false)
const editingPromo = ref(null)
const formError = ref('')
const filterType = ref('')
const filterStatus = ref('')

// Type labels & colors
const typeLabels = {
	buy_x_get_y: __('Buy X Get Y'),
	invoice_discount: __('Invoice Discount'),
	cashback: __('Cashback'),
	time_based: __('Time-Based'),
	fixed_bundle: __('Fixed Bundle'),
	category_discount: __('Category Discount'),
}

const typeClasses = {
	buy_x_get_y: 'bg-purple-100 text-purple-700',
	invoice_discount: 'bg-blue-100 text-blue-700',
	cashback: 'bg-green-100 text-green-700',
	time_based: 'bg-orange-100 text-orange-700',
	fixed_bundle: 'bg-pink-100 text-pink-700',
	category_discount: 'bg-teal-100 text-teal-700',
}

// Form
const defaultForm = () => ({
	promotion_name: '',
	promotion_type: '',
	branch: '',
	priority: 10,
	stackable: true,
	start_date: '',
	end_date: '',
	start_time: '',
	end_time: '',
	config: {
		buy_qty: 2,
		free_qty: 1,
		discount_percentage: 10,
		cashback_threshold: 100,
		cashback_percentage: 5,
		cashback_max_cap: 0,
		bundle_qty: 3,
		bundle_fixed_price: 0,
		max_categories: 3,
	},
	items: [],
})

const form = ref(defaultForm())

// Computed
const filteredPromotions = computed(() => {
	let result = promotions.value
	if (filterType.value) {
		result = result.filter(p => p.promotion_type === filterType.value)
	}
	if (filterStatus.value) {
		result = result.filter(p => p.status === filterStatus.value)
	}
	return result
})

// Methods
async function loadPromotions() {
	loading.value = true
	try {
		const data = await call('pos_next.api.promotions_v2.get_all_promotions', {
			include_disabled: 1,
		})
		promotions.value = data || []
	} catch (err) {
		console.error('Failed to load promotions:', err)
		promotions.value = []
	}
	loading.value = false
}

function editPromotion(promo) {
	editingPromo.value = promo
	form.value = {
		promotion_name: promo.promotion_name,
		promotion_type: promo.promotion_type,
		branch: promo.branch || '',
		priority: promo.priority || 10,
		stackable: !!promo.stackable,
		start_date: promo.start_date || '',
		end_date: promo.end_date || '',
		start_time: promo.start_time || '',
		end_time: promo.end_time || '',
		config: { ...defaultForm().config },
		items: [],
	}
	// Load full details
	loadPromoDetails(promo.name)
	showCreateForm.value = true
}

async function loadPromoDetails(name) {
	try {
		const data = await call('pos_next.api.promotions_v2.get_promotion', { name })
		if (data && data.rules && data.rules.length > 0) {
			const rule = data.rules[0]
			form.value.config = {
				buy_qty: rule.buy_qty || 2,
				free_qty: rule.free_qty || 1,
				discount_percentage: rule.discount_percentage || 10,
				cashback_threshold: rule.cashback_threshold || 100,
				cashback_percentage: rule.cashback_percentage || 5,
				cashback_max_cap: rule.cashback_max_cap || 0,
				bundle_qty: rule.bundle_qty || 3,
				bundle_fixed_price: rule.bundle_fixed_price || 0,
				max_categories: rule.max_categories || 3,
			}
		}
		if (data && data.promotion_items) {
			form.value.items = data.promotion_items
		}
	} catch (err) {
		console.error('Failed to load promotion details:', err)
	}
}

function validateForm() {
	formError.value = ''

	if (!form.value.promotion_name) {
		formError.value = __('Promotion name is required')
		return false
	}
	if (!form.value.promotion_type) {
		formError.value = __('Promotion type is required')
		return false
	}

	const cfg = form.value.config
	const type = form.value.promotion_type

	if (type === 'buy_x_get_y') {
		if (cfg.buy_qty < 1) { formError.value = __('Buy quantity must be ≥ 1'); return false }
		if (cfg.free_qty < 1) { formError.value = __('Free quantity must be ≥ 1'); return false }
		if (cfg.free_qty >= cfg.buy_qty) { formError.value = __('Free qty must be < Buy qty'); return false }
	}
	if (type === 'category_discount' && cfg.max_categories > 3) {
		formError.value = __('Maximum 3 categories allowed')
		return false
	}
	if (type === 'fixed_bundle' && cfg.bundle_qty < 2) {
		formError.value = __('Bundle requires at least 2 items')
		return false
	}
	if (type === 'cashback' && cfg.cashback_threshold <= 0) {
		formError.value = __('Cashback threshold must be > 0')
		return false
	}

	return true
}

async function savePromotion() {
	if (!validateForm()) return

	saving.value = true
	try {
		const payload = {
			promotion_name: form.value.promotion_name,
			promotion_type: form.value.promotion_type,
			branch: form.value.branch || null,
			priority: form.value.priority,
			stackable: form.value.stackable ? 1 : 0,
			start_date: form.value.start_date || null,
			end_date: form.value.end_date || null,
			start_time: form.value.start_time || null,
			end_time: form.value.end_time || null,
			config: form.value.config,
			items: form.value.items,
		}

		if (editingPromo.value) {
			await call('pos_next.api.promotions_v2.update_promotion', {
				name: editingPromo.value.name,
				data: payload,
			})
		} else {
			payload.enabled = 1
			await call('pos_next.api.promotions_v2.create_promotion', {
				data: payload,
			})
		}

		closeForm()
		await loadPromotions()
	} catch (err) {
		formError.value = err.message || __('Failed to save promotion')
	}
	saving.value = false
}

async function togglePromo(promo) {
	try {
		await call('pos_next.api.promotions_v2.toggle_promotion', {
			name: promo.name,
		})
		await loadPromotions()
	} catch (err) {
		console.error('Failed to toggle promotion:', err)
	}
}

async function deletePromo() {
	if (!editingPromo.value) return
	if (!confirm(__('Are you sure you want to delete this promotion?'))) return

	try {
		await call('pos_next.api.promotions_v2.delete_promotion', {
			name: editingPromo.value.name,
		})
		closeForm()
		await loadPromotions()
	} catch (err) {
		formError.value = err.message || __('Failed to delete promotion')
	}
}

function closeForm() {
	showCreateForm.value = false
	editingPromo.value = null
	form.value = defaultForm()
	formError.value = ''
}

// Lifecycle
onMounted(() => {
	loadPromotions()
})
</script>

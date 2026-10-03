import { toast } from "frappe-ui"
import { type Ref, computed, ref, watch } from "vue"

import { type TaxSettings, useUpdateTaxSettings } from "@/data/ticketTypes"
import type { EventTicketTypes, FrappeError } from "@/types"

type Settings = Pick<
	EventTicketTypes,
	"apply_tax" | "tax_inclusive" | "tax_label" | "tax_percentage"
>

export function useTaxSettingsForm(
	event: string,
	settings: Ref<Settings | undefined>,
	onSaved: () => void,
) {
	const applyTax = ref(false)
	const payer = ref<"participant" | "organiser">("participant")
	const taxLabel = ref("")
	const taxPercentage = ref(0)

	function discard() {
		if (!settings.value) return
		applyTax.value = settings.value.apply_tax
		payer.value = settings.value.tax_inclusive ? "organiser" : "participant"
		taxLabel.value = settings.value.tax_label
		taxPercentage.value = settings.value.tax_percentage
	}
	// Keyed on the tax values, so reloads for other parts of the page keep unsaved edits.
	watch(
		() => {
			const saved = settings.value
			return (
				saved &&
				[saved.apply_tax, saved.tax_inclusive, saved.tax_label, saved.tax_percentage].join()
			)
		},
		discard,
		{ immediate: true },
	)

	const draft = computed<TaxSettings>(() => ({
		apply_tax: applyTax.value ? 1 : 0,
		tax_inclusive: payer.value === "organiser" ? 1 : 0,
		tax_label: taxLabel.value.trim(),
		tax_percentage: Number(taxPercentage.value),
	}))

	const isDirty = computed(() => {
		const saved = settings.value
		if (!saved) return false
		return (
			draft.value.apply_tax !== Number(saved.apply_tax) ||
			draft.value.tax_inclusive !== Number(saved.tax_inclusive) ||
			draft.value.tax_label !== saved.tax_label ||
			draft.value.tax_percentage !== saved.tax_percentage
		)
	})

	const update = useUpdateTaxSettings()

	async function save() {
		if (!isDirty.value || update.loading) return
		try {
			await update.submit({ doctype: "Buzz Event", name: event, fieldname: draft.value })
			toast.success("Tax settings saved")
			onSaved()
		} catch {
			// The error stays under the fields.
		}
	}

	const errorMessage = computed(() => (update.error as FrappeError | null)?.message)

	return { applyTax, payer, taxLabel, taxPercentage, isDirty, save, discard, update, errorMessage }
}

export type TaxSettingsForm = ReturnType<typeof useTaxSettingsForm>

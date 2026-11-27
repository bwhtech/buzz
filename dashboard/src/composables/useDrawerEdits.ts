import { dialog, toast } from "frappe-ui"
import { computed, ref, type Ref, watch } from "vue"

import { useDrawerDraft } from "@/composables/useFormDraft"
import { matches } from "@/utils/formDraft"

type ConfirmText = { title: string; message: string; success: string }

/**
 * An always-editable drawer form: a draft copied from the saved values, and a save that asks
 * for confirmation first. `saveValues` throws to keep the dialog open. A `draftKey` keeps
 * unsaved edits in localStorage until they are saved or discarded.
 */
export function useDrawerEdits<T extends object>(
	getRecordName: () => string | undefined,
	getSavedValues: () => T | null,
	saveValues: (values: T) => Promise<void>,
	confirmText: ConfirmText,
	draftKey: () => string | false | null = () => null,
) {
	const draft = ref({}) as Ref<T>
	const storedDraft = useDrawerDraft(draftKey, draft, getSavedValues)
	const hasChanges = computed(() => {
		const savedValues = getSavedValues()
		return !!savedValues && !matches(draft.value, savedValues)
	})

	function discardChanges() {
		const savedValues = getSavedValues()
		if (savedValues) draft.value = { ...savedValues }
	}

	function openRecord() {
		discardChanges()
		storedDraft.restore()
	}

	// A reload for an unrelated change (say, enabling the record) keeps edits in progress.
	let previousSavedValues = getSavedValues()
	watch(getRecordName, openRecord, { immediate: true })
	watch(getSavedValues, (nextSavedValues) => {
		if (previousSavedValues && matches(draft.value, previousSavedValues)) discardChanges()
		previousSavedValues = nextSavedValues
	})

	function confirmAndSave() {
		dialog.confirm({
			title: confirmText.title,
			message: confirmText.message,
			confirmLabel: "Save",
			onConfirm: async () => {
				await saveValues(draft.value)
				storedDraft.clear()
				toast.success(confirmText.success)
			},
		})
	}

	return { draft, hasChanges, discardChanges, confirmAndSave }
}

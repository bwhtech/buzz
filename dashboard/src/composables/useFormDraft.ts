import { StorageSerializers, useEventListener, useLocalStorage } from "@vueuse/core"
import { type Ref, watch } from "vue"

import { type DraftOutcome, type StoredDraft, matches, restoredDraft } from "@/utils/formDraft"

/**
 * Keeps a form's unsaved edits in localStorage, so leaving the page for another tab —
 * or reloading — does not eat them.
 *
 * @param key - storage key; scope it to the user and the document it edits
 * @param form - the reactive form the page edits
 * @param baseline - the clean document the form is compared against
 */
export function useFormDraft<T extends object>(key: string, form: T, baseline: Ref<T>) {
	// Null rather than an empty object once the form is clean: vueuse only drops the key
	// on null, and a browser that opens many documents should not keep one entry each. A
	// null default leaves it guessing the serializer, and it guesses String.
	const stored = useLocalStorage<Partial<StoredDraft<T>> | null>(key, null, {
		serializer: StorageSerializers.object,
	})
	// Read once, up front: the page's own load rewrites the form, and the watcher below
	// would drop the draft as clean before anyone asked for it back.
	let onOpen: Partial<StoredDraft<T>> = { ...stored.value }

	watch(
		[form, baseline],
		() => {
			const edited = { ...form }
			const clean = { ...baseline.value }
			stored.value = matches(edited, clean) ? null : { baseline: clean, form: edited }
		},
		{ deep: true },
	)

	// Leaving the site is the one exit the page warns about, so taking it means the draft
	// goes too — a reload that put the text back would make the warning a lie. Written
	// straight through: the reactive write is queued, and the document is already going.
	// A page held for the back button is not leaving, so it keeps its draft.
	useEventListener(window, "pagehide", (leaving: PageTransitionEvent) => {
		if (!leaving.persisted) localStorage.removeItem(key)
	})

	/**
	 * Applies the draft this page opened with, and reports what became of it. Spent on
	 * the first call: a later reload of the document — a save, or a discard — is the page
	 * deliberately leaving those edits behind.
	 */
	function restore(): DraftOutcome<T>["status"] {
		const outcome = restoredDraft(onOpen, baseline.value)
		onOpen = {}
		if (outcome.status !== "none") Object.assign(form, outcome.form)
		return outcome.status
	}

	return { restore }
}

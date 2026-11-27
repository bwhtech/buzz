import { StorageSerializers, useEventListener, useLocalStorage } from "@vueuse/core"
import { toast } from "frappe-ui"
import { type Ref, watch } from "vue"

import { session } from "@/data/session"
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

/**
 * Keeps a drawer's unsaved edits in localStorage under `key`, so an accidental close or a
 * reload brings them back. A drawer warns about neither, so unlike a page the draft also
 * outlives the reload. The entry drops itself once the draft matches the baseline again.
 *
 * @param getKey - the drawer kind and record, or null to keep nothing
 */
export function useDrawerDraft<T extends object>(
	getKey: () => string | false | null,
	draft: Ref<T>,
	getBaseline: () => T | null,
) {
	const storageKey = () => {
		const key = getKey()
		return key && `buzz:drawer-draft:${session.user}:${key}`
	}

	watch(
		[draft, getBaseline],
		([form, baseline]) => {
			const key = storageKey()
			if (!key || !baseline) return
			if (matches(form, baseline)) localStorage.removeItem(key)
			else localStorage.setItem(key, JSON.stringify({ baseline, form }))
		},
		// After the drawer has seeded and restored, so a record switch never files the
		// previous record's draft under the new key.
		{ deep: true, flush: "post" },
	)

	/** Call right after seeding the draft from the baseline. */
	function restore() {
		const key = storageKey()
		const baseline = getBaseline()
		if (!key || !baseline) return
		const outcome = restoredDraft(readStored<T>(key), baseline)
		if (outcome.status === "none") return
		draft.value = outcome.form
		toast.info(
			outcome.status === "restored"
				? "Restored your unsaved changes"
				: "This changed elsewhere — check your restored changes before saving",
		)
	}

	function clear() {
		const key = storageKey()
		if (key) localStorage.removeItem(key)
	}

	return { restore, clear }
}

function readStored<T>(key: string): Partial<StoredDraft<T>> {
	try {
		return JSON.parse(localStorage.getItem(key) ?? "{}") ?? {}
	} catch {
		return {}
	}
}

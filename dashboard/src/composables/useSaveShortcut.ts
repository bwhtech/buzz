import { useEventListener } from "@vueuse/core"
import type { MaybeRefOrGetter } from "vue"
import { toValue } from "vue"

/**
 * Cmd/Ctrl+S saves, taking the shortcut the browser would spend on saving the document,
 * and leaving the site with unsaved edits gets the browser's warning. Moving to another
 * dashboard page unmounts the form and drops the edits, as on event Details.
 */
export function useSaveShortcut(save: () => unknown, isDirty: MaybeRefOrGetter<boolean>) {
	useEventListener(document, "keydown", (stroke: KeyboardEvent) => {
		if (stroke.key !== "s" || !(stroke.metaKey || stroke.ctrlKey) || stroke.altKey) return
		stroke.preventDefault()
		if (!stroke.repeat) save()
	})

	useEventListener(window, "beforeunload", (unload: BeforeUnloadEvent) => {
		if (toValue(isDirty)) unload.preventDefault()
	})
}

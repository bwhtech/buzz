import { useEventListener } from "@vueuse/core"
import { toast } from "frappe-ui"
import { onBeforeUnmount } from "vue"

const UNDO_WINDOW_MS = 5000

interface HeldWrite {
	message: string
	write: () => void
	// Restores the screen while the write is still held.
	undo: () => void
	// Writes the old value back when Undo lands after the write went out.
	revert?: () => void
}

interface Hold {
	write: () => void
	timer: number
}

// Holds a write for as long as the toast offers Undo, so a mis-click never reaches the server.
export function useHeldWrite() {
	let held: Hold | null = null

	function hold(request: HeldWrite) {
		flush()
		const current = { write: request.write, timer: window.setTimeout(flush, UNDO_WINDOW_MS) }
		held = current
		toast.success(request.message, {
			duration: UNDO_WINDOW_MS,
			action: { label: "Undo", onClick: () => undo(current, request) },
		})
	}

	function flush() {
		if (!held) return
		clearTimeout(held.timer)
		const { write } = held
		held = null
		write()
	}

	// Hovering the toast pauses its countdown but not the hold, so Undo can land late.
	function undo(current: Hold, request: HeldWrite) {
		if (held !== current) return request.revert?.()
		clearTimeout(current.timer)
		held = null
		request.undo()
	}

	// A held write still goes out when the page goes away. Closing the tab also asks
	// first, so the request has time to finish before the page unloads.
	onBeforeUnmount(flush)
	useEventListener(window, "beforeunload", (event: BeforeUnloadEvent) => {
		if (!held) return
		flush()
		event.preventDefault()
	})

	return { hold, flush }
}

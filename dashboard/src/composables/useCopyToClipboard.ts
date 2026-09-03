import { useClipboard } from "@vueuse/core"
import { toast } from "frappe-ui"

/**
 * Copies text and says so, or says why it could not.
 *
 * legacy: the async clipboard API is refused outside a secure context, and on an
 * http:// host in development that is every time.
 */
export function useCopyToClipboard() {
	const { copy } = useClipboard({ legacy: true })

	return async function copyToClipboard(text: string, message = "Copied to clipboard") {
		try {
			await copy(text)
			toast.success(message)
			return true
		} catch {
			toast.error("Could not copy to clipboard")
			return false
		}
	}
}

import { useCall } from "frappe-ui"

// v2 path: useCall reads the payload from `data`, which /api/method names `message`.
// Uncached: cacheKey would persist this user's inquiries to IndexedDB past a logout.
// Rows are only ever counted, so the sidebar and tab bar need no more than the key.
export function useMySponsorships() {
	return useCall<{ name: string }[]>({
		url: "/api/v2/method/buzz.api.sponsorships.get_user_sponsorship_inquiries",
	})
}

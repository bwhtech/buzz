import { useCall } from "frappe-ui"

// Only presence matters here: the sidebar drops its Sponsorship item for users with no
// enquiry. No cacheKey — it persists to IndexedDB and would outlive this user's session.
export function useMySponsorships() {
	return useCall<{ name: string }[]>({
		url: "/api/v2/method/buzz.api.sponsorships.get_user_sponsorship_inquiries",
	})
}

import { clearBookingCache } from "@/utils"
import { createResource } from "frappe-ui"
import { computed, reactive } from "vue"
import { userResource } from "./user"

interface LoginParams {
	email: string
	password: string
}

export function sessionUser(): string {
	const cookies = new URLSearchParams(document.cookie.split("; ").join("&"))
	const _sessionUser = cookies.get("user_id")
	if (!_sessionUser || _sessionUser === "Guest") {
		return ""
	}
	return _sessionUser
}

export const session = reactive({
	login: createResource({
		url: "login",
		makeParams({ email, password }: LoginParams) {
			return {
				usr: email,
				pwd: password,
			}
		},
		onSuccess() {
			window.location.reload()
		},
	}),
	logout: createResource({
		url: "logout",
		onSuccess() {
			userResource.reset()
			session.user = sessionUser()
			clearBookingCache()
			window.location.reload()
		},
	}),
	user: sessionUser(),
	isLoggedIn: computed((): boolean => !!session.user),
})

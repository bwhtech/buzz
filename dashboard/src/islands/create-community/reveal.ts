// Read by the team page's head script, which grows the new page out of `from`, and by the
// islands entry, which announces it. Keep the key in step with buzz_team.html.
export const CREATED_KEY = "buzz:community-created"

export type CreatedNotice = { name: string; url: string; from?: string }

const side = (value: number) => `${Math.max(0, value - 24)}px`

// The form's box as a clip-path inset, with room around it so the page grows from a card.
function insetAround(element: HTMLElement): string {
	const box = element.getBoundingClientRect()
	return [box.top, innerWidth - box.right, innerHeight - box.bottom, box.left].map(side).join(" ")
}

// Both documents opt in to a cross-document view transition; this one only for this navigation.
function optIntoViewTransition() {
	const style = document.createElement("style")
	style.textContent = "@view-transition { navigation: auto; }"
	document.head.append(style)
}

export function openCreatedCommunity(name: string, route: string, from: HTMLElement | null) {
	const notice: CreatedNotice = {
		name,
		url: `${location.origin}${route}`,
		from: from ? insetAround(from) : undefined,
	}
	sessionStorage.setItem(CREATED_KEY, JSON.stringify(notice))
	optIntoViewTransition()
	// Back from the new page returns to the landing page, not to the draft.
	history.replaceState(null, "", location.pathname)
	location.assign(route)
}

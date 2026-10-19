import { watchDebounced } from "@vueuse/core"
import { type MaybeRefOrGetter, type Ref, ref, toValue, watch } from "vue"

export type Availability = { available: boolean; message: string }

// Live availability of a slug as someone types. `availability` stays null while unchecked
// or checking; `savedSlug` is the slug already saved, which needs no check.
export function useSlugAvailability(
	slug: Ref<string>,
	check: (slug: string) => Promise<Availability | null>,
	savedSlug?: MaybeRefOrGetter<string | null | undefined>,
) {
	const availability = ref<Availability | null>(null)
	const checking = ref(false)

	const needsCheck = (value: string) => Boolean(value.trim() && value !== toValue(savedSlug))

	watch(
		slug,
		(value) => {
			availability.value = null
			checking.value = needsCheck(value)
		},
		{ immediate: true },
	)

	watchDebounced(
		slug,
		async (value) => {
			if (!needsCheck(value)) return
			// A failed check says nothing rather than spinning forever; the save still checks.
			const answer = await check(value).catch(() => null)
			// A later keystroke may have overtaken this request while it was in flight.
			if (slug.value !== value) return
			checking.value = false
			availability.value = answer
		},
		{ debounce: 400, immediate: true },
	)

	return { availability, checking }
}

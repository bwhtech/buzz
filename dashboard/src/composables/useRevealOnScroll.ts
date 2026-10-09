import { useIntersectionObserver } from "@vueuse/core"
import { type Ref, computed, ref } from "vue"

/** Renders a long, already-loaded list a page at a time as its foot scrolls into view. */
export function useRevealOnScroll<T>(
	items: () => T[],
	pageSize: number,
	root: Ref<HTMLElement | null> = ref<HTMLElement | null>(null),
) {
	const count = ref(pageSize)
	const sentinel = ref<HTMLElement | null>(null)

	useIntersectionObserver(
		sentinel,
		([entry]) => {
			if (entry?.isIntersecting && count.value < items().length) count.value += pageSize
		},
		{ root, rootMargin: "200px" },
	)

	return {
		visible: computed(() => items().slice(0, count.value)),
		sentinel,
		reset: () => (count.value = pageSize),
	}
}

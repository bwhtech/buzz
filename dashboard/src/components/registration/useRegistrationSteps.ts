import { computed, ref, type Ref } from "vue"

export type RegistrationStepId = "tickets" | "attendees" | "details" | "payment"

export interface RegistrationStep {
	id: RegistrationStepId
	label: string
	sub: string
}

export function useRegistrationSteps(steps: Ref<RegistrationStep[]>) {
	const current = ref(0)
	const direction = ref(1)
	const triedSteps = ref(new Set<RegistrationStepId>())

	const step = computed(() => steps.value[Math.min(current.value, steps.value.length - 1)])
	const isLast = computed(() => current.value >= steps.value.length - 1)
	const tried = computed(() => triedSteps.value.has(step.value.id))

	function go(index: number) {
		direction.value = index > current.value ? 1 : -1
		current.value = index
		window.scrollTo({ top: 0 })
	}

	function markTried() {
		triedSteps.value = new Set(triedSteps.value).add(step.value.id)
	}

	return { current, direction, step, isLast, tried, go, markTried }
}

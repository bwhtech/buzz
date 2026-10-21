import { StorageSerializers, createGlobalState, useSessionStorage, useStorage } from "@vueuse/core"

export interface ChecklistStep {
	name: string
	title: string
	description: string
	persona: string
	path: string
	completed: boolean
	optional: boolean
	locked: boolean
	completes_on: "visit" | "click" | null
	target: string | null
}

export interface ChecklistGroup {
	name: string
	title: string
	steps: ChecklistStep[]
}

// Survives the full page load a persona switch makes, and no further.
// Shared, so the checklist steps aside while the spotlight shows.
export const useSpotlightStep = createGlobalState(() =>
	useSessionStorage<ChecklistStep | null>("playground-spotlight", null, {
		serializer: StorageSerializers.object,
	}),
)

// A page visit or a click leaves no record to read back, so the browser remembers it per sandbox.
// One shared ref: the spotlight records a click the checklist has to show at once.
export const useBrowserCompletedSteps = createGlobalState(() => {
	const names = useStorage<string[]>(`playground-visited-${window.playground?.sandbox}`, [])
	const add = (name: string) => names.value.includes(name) || names.value.push(name)
	return { names, add }
})

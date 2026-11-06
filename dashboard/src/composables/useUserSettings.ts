import { ref } from "vue"

// Shared so the command palette opens the same dialog the user menu does.
export const userSettingsOpen = ref(false)
// The dialog mounts on its first open, so its editor loads only when needed.
export const userSettingsMounted = ref(false)

export function openUserSettings() {
	userSettingsMounted.value = true
	userSettingsOpen.value = true
}

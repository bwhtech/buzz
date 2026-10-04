<script setup lang="ts">
import { FrappeUIProvider, setConfig, useColorScheme } from "frappe-ui"
import { watch } from "vue"

import LoginDialog from "@/components/LoginDialog.vue"
import { useThemeColor } from "@/composables/useThemeColor"
import { userResource } from "@/data/user"

import Layout from "./layouts/Layout.vue"

setConfig("systemTimezone", window.timezone?.system || null)
setConfig("localTimezone", window.timezone?.user || null)

// Applies the stored theme on every page, not only those that render a theme toggle.
useColorScheme()
useThemeColor()

// The zone the user picked in Preferences wins over the boot value once their info
// lands, so dates render in it.
watch(
	() => userResource.data?.time_zone,
	(timeZone) => {
		if (timeZone) setConfig("localTimezone", timeZone)
	},
	{ immediate: true },
)
</script>

<template>
	<FrappeUIProvider>
		<Layout>
			<router-view />
		</Layout>
		<LoginDialog />
	</FrappeUIProvider>
</template>

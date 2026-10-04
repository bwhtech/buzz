<script setup lang="ts">
import { FrappeUIProvider, setConfig } from "frappe-ui"
import { watch } from "vue"

import LoginDialog from "@/components/LoginDialog.vue"
import { userResource } from "@/data/user"

import Layout from "./layouts/Layout.vue"

setConfig("systemTimezone", window.timezone?.system || null)
setConfig("localTimezone", window.timezone?.user || null)

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

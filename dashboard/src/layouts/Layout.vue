<template>
	<div
		class="min-h-dvh bg-surface-base text-ink-gray-8"
		:class="{ 'h-dvh overflow-hidden': fullBleed }"
	>
		<template v-if="routerReady && !fullBleed && !meta.ownHeader">
			<SiteHeader />
		</template>
		<div :class="contentClass">
			<template v-if="!routerReady">
				<ManagerShellPlaceholder v-if="fullBleed" />
			</template>
			<LoginRequired v-else-if="requires_auth && !session.isLoggedIn" />
			<slot v-else></slot>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue"
import { useRoute, useRouter } from "vue-router"

import LoginRequired from "@/components/LoginRequired.vue"
import SiteHeader from "@/components/SiteHeader.vue"
import { session } from "@/data/session"
import ManagerShellPlaceholder from "@/layouts/ManagerShellPlaceholder.vue"

const route = useRoute()
const router = useRouter()
const routerReady = ref(false)
const requires_auth = computed(() => !route.meta?.isPublic)
// Until the first navigation settles, `route` is the empty start location, so read the
// meta of the URL being loaded instead.
const startMeta = router.resolve(router.options.history.location).meta
const meta = computed(() => (routerReady.value ? route.meta : startMeta))
const fullBleed = computed(() => Boolean(meta.value.fullBleed))
// Wide pages lay out their own width under the site header.
const contentClass = computed(() => {
	if (fullBleed.value) return "h-full"
	return meta.value.wide ? "" : "max-w-4xl py-8 px-4 md:py-12 mx-auto"
})

router.isReady().then(() => {
	routerReady.value = true
})
</script>

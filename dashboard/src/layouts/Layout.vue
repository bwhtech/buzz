<template>
	<slot v-if="embedded" />
	<div
		v-else
		class="min-h-dvh bg-surface-base text-ink-gray-8"
		:class="{ 'h-dvh overflow-hidden': fullBleed }"
	>
		<Navbar v-if="routerReady && !fullBleed" />
		<div :class="fullBleed ? 'h-full' : 'max-w-4xl py-8 px-4 md:py-12 mx-auto'">
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
import Navbar from "@/components/Navbar.vue"
import { session } from "@/data/session"
import ManagerShellPlaceholder from "@/layouts/ManagerShellPlaceholder.vue"

const route = useRoute()
const router = useRouter()
const routerReady = ref(false)
const requires_auth = computed(() => !route.meta?.isPublic)
// Until the first navigation settles, `route` is the empty start location, so read the
// meta of the URL being loaded instead.
const startMeta = router.resolve(router.options.history.location).meta
const fullBleed = computed(() => Boolean((routerReady.value ? route.meta : startMeta).fullBleed))
const embedded = computed(() => Boolean((routerReady.value ? route.meta : startMeta).embedded))

router.isReady().then(() => {
	routerReady.value = true
})
</script>

<script setup lang="ts">
import { DesktopShell, Sidebar, Skeleton } from "frappe-ui"

import { useIsMobile } from "@/composables/useIsMobile"

const isMobile = useIsMobile()
</script>

<!-- The manager shell in skeleton form, held while the first route resolves. Spacing
     follows ManagerDesktopShell, so the real sidebar lands where these placeholders stood. -->
<template>
	<div v-if="isMobile" class="h-full bg-surface-elevation-1">
		<div class="flex flex-col gap-4 p-4">
			<Skeleton class="h-7 w-32 rounded-4" />
			<Skeleton v-for="row in 3" :key="row" class="h-24 w-full rounded-6" />
		</div>
	</div>
	<DesktopShell v-else :scroll="false">
		<template #sidebar>
			<Sidebar>
				<div class="flex h-14 shrink-0 items-center gap-2 px-2.5 pt-2">
					<Skeleton class="size-8 rounded-4" />
					<Skeleton class="h-4 w-16 rounded-4" />
				</div>
				<div class="mx-2 my-2 flex flex-col gap-0.5">
					<div v-for="row in 3" :key="row" class="flex h-7 items-center gap-2 px-2">
						<Skeleton class="size-4 rounded-3" />
						<Skeleton class="h-3.5 w-24 rounded-4" />
					</div>
				</div>
				<div class="mt-auto flex items-center gap-2 px-4 py-4">
					<Skeleton class="size-7 rounded-full" />
					<Skeleton class="h-4 w-24 rounded-4" />
				</div>
			</Sidebar>
		</template>

		<div class="flex flex-col h-full min-h-0 bg-surface-sidebar py-2 pl-1">
			<div class="flex h-full flex-col gap-6 rounded-l-6 bg-surface-elevation-1 p-4 shadow-base">
				<div class="flex items-center gap-3 pt-14">
					<Skeleton class="size-10 rounded-6" />
					<Skeleton class="h-6 w-40 rounded-4" />
				</div>
				<Skeleton v-for="row in 3" :key="row" class="h-32 w-full rounded-6" />
			</div>
		</div>
	</DesktopShell>
</template>

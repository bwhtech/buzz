<script setup lang="ts">
import { Skeleton } from "frappe-ui"
</script>

<template>
	<!-- Shaped like the loaded page rather than a generic block, so the content settles
		 into the boxes instead of replacing them. -->
	<div class="m-auto w-full max-w-[800px] space-y-8 px-4 py-8">
		<Skeleton class="aspect-[3/1] w-full rounded-7" />

		<div class="grid gap-8 md:grid-cols-5">
			<div class="space-y-8 md:col-span-3">
				<div class="space-y-3">
					<Skeleton class="h-10 w-2/3 rounded-4" />
					<Skeleton class="h-4 w-full rounded-4" />
					<Skeleton class="h-4 w-4/5 rounded-4" />
				</div>

				<div class="space-y-3">
					<Skeleton class="h-3 w-16 rounded-4" />
					<Skeleton class="h-48 w-full rounded-6" />
				</div>
			</div>

			<div class="space-y-8 md:col-span-2">
				<div class="space-y-1.5">
					<Skeleton class="h-3 w-20 rounded-4" />
					<Skeleton class="h-14 w-full rounded-6" />
				</div>

				<Skeleton class="h-40 w-full rounded-6" />

				<div class="space-y-3">
					<Skeleton class="h-3 w-16 rounded-4" />
					<Skeleton class="h-9 w-full rounded-4" />
					<Skeleton class="h-9 w-full rounded-4" />
				</div>
			</div>
		</div>
	</div>
</template>

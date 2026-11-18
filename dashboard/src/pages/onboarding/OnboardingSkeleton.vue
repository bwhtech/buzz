<!-- Holds the profile step's shape while the user and onboarding state load. -->
<template>
	<div
		class="flex flex-col gap-6 motion-safe:animate-pulse"
		role="status"
		:aria-label="__('Loading')"
	>
		<div class="h-1.5 w-20 rounded bg-surface-gray-2" />
		<div class="flex flex-col gap-2">
			<div class="h-6 w-48 rounded bg-surface-gray-2" />
			<div class="h-4 w-64 rounded bg-surface-gray-2" />
		</div>
		<div class="flex items-center gap-3">
			<div class="size-12 rounded-full bg-surface-gray-2" />
			<div class="h-4 w-32 rounded bg-surface-gray-2" />
		</div>
		<div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
			<div class="h-14 rounded bg-surface-gray-2" />
			<div class="h-14 rounded bg-surface-gray-2" />
		</div>
		<div class="h-14 rounded bg-surface-gray-2" />
	</div>
</template>

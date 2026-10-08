<script setup lang="ts">
import ProgressStatus from "@/components/common/ProgressStatus.vue"
import { openingTeam } from "@/composables/useWorkspaceOpening"
</script>

<template>
	<!-- Covers the page while the shell swaps into the workspace, so the change of context reads.
	     No fade in: the page mounts underneath at once and its skeletons would show through. -->
	<Transition
		leave-active-class="transition-opacity duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] motion-reduce:transition-none"
		leave-to-class="opacity-0"
	>
		<div
			v-if="openingTeam"
			class="absolute inset-0 z-20 flex flex-col justify-center bg-surface-elevation-1"
		>
			<ProgressStatus :text="`Opening ${openingTeam}`" />
		</div>
	</Transition>
</template>

<script setup lang="ts">
import { tagColorClasses } from "@/components/common/tags/tagColors"
import type { TagColor } from "@/types"

defineProps<{ label: string; color: TagColor }>()
</script>

<template>
	<span
		class="inline-flex h-5 max-w-full shrink-0 select-none items-center gap-1 whitespace-nowrap rounded-full px-2 text-xs"
		:class="tagColorClasses(color).chip"
	>
		<span class="truncate" :title="label">{{ label }}</span>
		<slot name="suffix" />
	</span>
</template>

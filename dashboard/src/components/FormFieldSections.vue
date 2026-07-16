<template>
	<div class="space-y-6">
		<div
			v-for="(section, section_index) in sections"
			:key="section_index"
			class="grid gap-4 grid-cols-1 sm:[grid-template-columns:var(--section-columns)]"
			:style="{
				'--section-columns': `repeat(${section.length}, minmax(0, 1fr))`,
			}"
		>
			<div v-for="(column, column_index) in section" :key="column_index" class="space-y-4">
				<template v-for="field in column" :key="field.fieldname">
					<slot name="field" :field="field" />
				</template>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { CustomField } from "@/types";
import { computed, type PropType } from "vue";

const props = defineProps({
	fields: {
		type: Array as PropType<CustomField[]>,
		default: () => [],
	},
});

const sections = computed(() => {
	const sections: CustomField[][][] = [];
	let current_section: CustomField[][] = [[]];
	for (const field of props.fields) {
		if (field.fieldtype === "Section Break") {
			if (current_section.some((column) => column.length)) {
				sections.push(current_section);
			}
			current_section = [[]];
			continue;
		}
		if (field.fieldtype === "Column Break") {
			current_section.push([]);
			continue;
		}
		current_section[current_section.length - 1].push(field);
	}
	if (current_section.some((column) => column.length)) {
		sections.push(current_section);
	}
	return sections;
});
</script>

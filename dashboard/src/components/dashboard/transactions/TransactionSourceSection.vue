<script setup lang="ts">
import DetailRow from "@/components/common/DetailRow.vue"
import TransactionSection from "@/components/dashboard/transactions/TransactionSection.vue"
import type { TransactionAnswer, TransactionDetail } from "@/types"

defineProps<{ transaction: TransactionDetail }>()

const answerLabel = (answer: TransactionAnswer) => answer.label || answer.fieldname || "Answer"

const answerValue = (answer: TransactionAnswer) =>
	answer.value === null || answer.value === undefined || answer.value === ""
		? null
		: String(answer.value)
</script>

<template>
	<TransactionSection title="Source">
		<dl class="space-y-3 text-base">
			<DetailRow
				v-for="(utm, index) in transaction.utm"
				:key="`utm-${index}`"
				:label="utm.utm_name ?? 'UTM'"
				:value="utm.value"
			/>
			<DetailRow
				v-for="(answer, index) in transaction.answers"
				:key="`answer-${index}`"
				:label="answerLabel(answer)"
				:value="answerValue(answer)"
			/>
		</dl>
	</TransactionSection>
</template>

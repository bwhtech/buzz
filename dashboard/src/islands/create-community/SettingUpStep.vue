<script setup lang="ts">
defineProps<{ name: string; tasks: string[]; done: number }>()

const ICONS = {
	done: "task-check lucide-circle-check text-ink-green-6",
	active:
		"lucide-circle-dashed text-ink-gray-7 animate-spin [animation-duration:2.4s] motion-reduce:animate-none",
	pending: "lucide-circle text-ink-gray-3",
}
const stateOf = (index: number, done: number) =>
	index < done ? "done" : index === done ? "active" : "pending"
</script>

<template>
	<div class="flex flex-col gap-6" role="status">
		<h2
			class="text-[32px] font-semibold tracking-[-0.035em] text-ink-gray-9 sm:text-[44px] sm:leading-[1.1]"
		>
			{{ __("Setting up {0}", [name]) }}
		</h2>
		<ul class="flex flex-col gap-3">
			<li
				v-for="(task, index) in tasks"
				:key="task"
				class="task flex items-center gap-2.5 text-lg transition-colors duration-200"
				:class="stateOf(index, done) === 'pending' ? 'text-ink-gray-5' : 'text-ink-gray-9'"
				:style="{ animationDelay: `${index * 50}ms` }"
			>
				<!-- Keyed, so a finished task mounts a fresh check that pops in. -->
				<span
					:key="stateOf(index, done)"
					class="size-[18px] shrink-0"
					:class="ICONS[stateOf(index, done)]"
					aria-hidden="true"
				/>
				{{ task }}
			</li>
		</ul>
	</div>
</template>

<style scoped>
/* The rows arrive one after another, then tick over in place. */
.task {
	animation: task-in 300ms cubic-bezier(0.23, 1, 0.32, 1) backwards;
}

@keyframes task-in {
	from {
		opacity: 0;
		transform: translateY(var(--task-rise, 6px));
	}
}

/* Not a <Transition>: the spinner it replaces never ends its animation, so out-in would wait forever. */
.task-check {
	animation: task-check-in 220ms cubic-bezier(0.23, 1, 0.32, 1);
}

@keyframes task-check-in {
	from {
		opacity: 0;
		transform: scale(var(--task-check-scale, 0.75));
	}
}

@media (prefers-reduced-motion: reduce) {
	.task {
		--task-rise: 0;
	}
	.task-check {
		--task-check-scale: 1;
	}
}
</style>

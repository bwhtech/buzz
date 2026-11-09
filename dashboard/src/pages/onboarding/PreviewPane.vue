<script setup lang="ts">
import createGlobe from "cobe"
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue"

import PreviewCard from "./PreviewCard.vue"
import { type Scene, flow, previewAddress, scene } from "./useOnboarding"

type City = [lat: number, lng: number]
type Globe = ReturnType<typeof createGlobe>

const HOME: City = [12.97, 77.6]
const NEARBY: City[] = [HOME, [19.08, 72.88], [13.08, 80.27], [18.52, 73.86]]
const WORLD: City[] = [
	HOME,
	[52.5, 13.4],
	[37.8, -122.4],
	[35.7, 139.7],
	[-33.9, 151.2],
	[51.5, -0.1],
	[40.7, -74],
	[1.35, 103.8],
	[48.86, 2.35],
	[6.52, 3.38],
	[-1.29, 36.82],
	[25.2, 55.27],
	[28.61, 77.21],
	[37.57, 126.98],
	[-23.55, -46.63],
	[43.65, -79.38],
	[59.33, 18.07],
	[-33.92, 18.42],
]
const ACCENT: [number, number, number] = [0.95, 0.42, 0.1]
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)")

type SceneSetup = { cities: City[]; size: number; focus: City | null }
const setups: Record<Scene, () => SceneSetup> = {
	profile: () => ({ cities: [HOME], size: 0.1, focus: HOME }),
	personal: () => ({ cities: NEARBY, size: 0.06, focus: HOME }),
	community: () => ({ cities: WORLD.slice(0, 14), size: 0.05, focus: null }),
	attendee: () => ({ cities: WORLD, size: 0.035, focus: null }),
	team: () => ({ cities: NEARBY, size: 0.07, focus: HOME }),
	event: () =>
		flow.event.medium === "In Person"
			? { cities: [HOME], size: 0.13, focus: HOME }
			: { cities: WORLD, size: 0.03, focus: null },
	done: () => ({ cities: WORLD, size: 0.04, focus: null }),
}

const revealed = computed(() => scene.value !== "profile")
const canvas = ref<HTMLCanvasElement>()
const ready = ref(false)
let globe: Globe | null = null
let phi = 4.6
let theta = 0.3
let setup = setups[scene.value]()
let bloomStart = performance.now()

const easeOut = (progress: number) => 1 - (1 - Math.min(Math.max(progress, 0), 1)) ** 3
const angleFor = ([lat, lng]: City) => [
	Math.PI - ((lng * Math.PI) / 180 - Math.PI / 2),
	(lat * Math.PI) / 180,
]

function markers(now: number) {
	return setup.cities.map((location, index) => ({
		location,
		size: setup.size * easeOut((now - bloomStart - index * 70) / 500),
	}))
}

function turn() {
	if (!setup.focus) {
		phi += reducedMotion.matches ? 0 : 0.003
		theta += (0.3 - theta) * 0.05
		return
	}
	const [targetPhi, targetTheta] = angleFor(setup.focus)
	const delta = Math.atan2(Math.sin(targetPhi - phi), Math.cos(targetPhi - phi))
	phi += delta * 0.06
	theta += (targetTheta * 0.6 - theta) * 0.06
}

function draw() {
	globe?.destroy()
	if (!canvas.value) return
	const dark = document.documentElement.getAttribute("data-theme") === "dark"
	const size = canvas.value.offsetWidth * 2
	globe = createGlobe(canvas.value, {
		devicePixelRatio: 2,
		width: size,
		height: size,
		phi,
		theta,
		dark: dark ? 1 : 0,
		diffuse: dark ? 1.4 : 0.6,
		mapSamples: 20000,
		mapBrightness: dark ? 5 : 1.4,
		baseColor: dark ? [0.32, 0.32, 0.32] : [1, 1, 1],
		glowColor: dark ? [0.16, 0.16, 0.16] : [0.96, 0.96, 0.96],
		markerColor: ACCENT,
		markers: [],
		onRender: (state) => {
			const now = performance.now()
			turn()
			state.phi = phi
			state.theta = theta
			state.markers = markers(now)
		},
	})
	requestAnimationFrame(() => (ready.value = true))
}

watch([scene, () => flow.event.medium], () => {
	setup = setups[scene.value]()
	bloomStart = performance.now()
})

const themeObserver = new MutationObserver(draw)
onMounted(() => {
	draw()
	themeObserver.observe(document.documentElement, { attributeFilter: ["data-theme"] })
})
onBeforeUnmount(() => {
	themeObserver.disconnect()
	globe?.destroy()
})
</script>

<template>
	<div
		class="absolute inset-0 flex flex-col items-center justify-center overflow-hidden px-10"
		:data-revealed="revealed || null"
	>
		<canvas
			ref="canvas"
			class="globe aspect-square w-full max-w-[460px]"
			:data-ready="ready || null"
			aria-hidden="true"
		/>
		<div class="card-group relative -mt-32 flex w-full flex-col items-center gap-4">
			<Transition name="preview-card" mode="out-in">
				<div :key="scene" class="flex w-full justify-center">
					<PreviewCard :scene="scene" />
				</div>
			</Transition>
			<p class="font-mono text-xs text-ink-gray-5">{{ previewAddress }}</p>
		</div>
	</div>
</template>

<style scoped>
/* Profile starts plain: the card sits centred and the globe waits. Moving on slides the
   card down and brings the globe up behind it. */
.globe {
	opacity: 0;
	transform: translateY(24px) scale(0.92);
	transition:
		opacity 500ms ease,
		transform 700ms cubic-bezier(0.23, 1, 0.32, 1);
}
[data-revealed] .globe[data-ready] {
	opacity: 1;
	transform: none;
	transition-delay: 120ms;
}
.card-group {
	transform: translateY(-170px);
	transition: transform 600ms cubic-bezier(0.77, 0, 0.175, 1);
}
[data-revealed] .card-group {
	transform: none;
}
.preview-card-enter-active {
	transition:
		opacity 240ms ease-out,
		transform 280ms cubic-bezier(0.23, 1, 0.32, 1);
}
.preview-card-leave-active {
	transition:
		opacity 120ms ease-out,
		transform 120ms ease-out;
}
.preview-card-enter-from {
	opacity: 0;
	transform: translateY(10px) scale(0.97);
}
.preview-card-leave-to {
	opacity: 0;
	transform: scale(0.98);
}
@media (prefers-reduced-motion: reduce) {
	.globe,
	.card-group {
		transition: opacity 300ms ease;
	}
	.preview-card-enter-from,
	.preview-card-leave-to {
		transform: none;
	}
}
</style>

<script setup lang="ts">
// The team's places on a map: a dot each, a numbered pin for each picked place, joined by a
// dashed line in order, and a name tag on the place in focus. The camera follows the focus.
import "maplibre-gl/dist/maplibre-gl.css"
import { useDebounceFn } from "@vueuse/core"
import type {
	GeoJSONSource,
	GeoJSONSourceSpecification,
	Map as MapLibreMap,
	Marker,
} from "maplibre-gl"
import { computed, onBeforeUnmount, onMounted, ref, useTemplateRef, watch } from "vue"

import type { Venue } from "@/data/venues"

export interface MapPadding {
	top: number
	right: number
	bottom: number
	left: number
}

const props = defineProps<{
	places: Venue[]
	selected: string[]
	active: string | null
	hovered: string | null
	padding: MapPadding
}>()
const emit = defineEmits<{ pick: [venue: Venue] }>()

// OpenFreeMap's hosted vector tiles, as on the event page: free, keyless and unmetered.
const MAP_STYLES = {
	light: "https://tiles.openfreemap.org/styles/positron",
	dark: "https://tiles.openfreemap.org/styles/dark",
}
const OSM_ATTRIBUTION =
	'<a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">&copy; OpenStreetMap contributors</a>'
const MAX_FIT_ZOOM = 15
const FLY_DURATION = 550

const container = useTemplateRef<HTMLElement>("container")
const isReady = ref(false)
let map: MapLibreMap | null = null
let markers: Marker[] = []
let library: typeof import("maplibre-gl") | null = null

const located = computed(() => props.places.filter((place) => place.latitude && place.longitude))
const byName = computed(() => new Map(located.value.map((place) => [place.name, place])))
const picked = computed(() => props.selected.flatMap((name) => byName.value.get(name) ?? []))

// What the camera frames: the picked places and the one in focus, or every place when none is.
const focus = computed(() => {
	const names = [...props.selected, props.active, props.hovered].filter(Boolean) as string[]
	const places = [...new Set(names)].flatMap((name) => byName.value.get(name) ?? [])
	return places.length ? places : located.value
})

function bounds(places: Venue[]) {
	const box = new library!.LngLatBounds()
	for (const place of places) box.extend([place.longitude!, place.latitude!])
	return box
}

function element(className: string, text = "") {
	return Object.assign(document.createElement("div"), { className, textContent: text })
}

function marker(place: Venue) {
	const index = props.selected.indexOf(place.name)
	const isHovered = props.hovered === place.name
	if (index >= 0) {
		const size = isHovered ? "size-[30px] text-sm" : "size-6 text-xs"
		return element(
			`grid ${size} place-items-center rounded-full border-2 border-[--surface-base] bg-[--ink-gray-9] font-semibold tabular-nums text-[--surface-base] shadow-lg`,
			String(index + 1),
		)
	}
	if (isHovered || props.active === place.name) return tag(place, props.active === place.name)
	const dot = element(
		"size-3.5 cursor-pointer rounded-full border-2 border-[--ink-gray-6] bg-surface-base shadow-sm",
	)
	dot.addEventListener("click", () => emit("pick", place))
	return dot
}

function tag(place: Venue, isActive: boolean) {
	const wrapper = element("pointer-events-none -ml-2 flex items-center gap-1.5")
	const ring = isActive
		? "border-[--surface-base] bg-[--ink-gray-9]"
		: "border-[--ink-gray-9] bg-surface-base"
	wrapper.append(
		element(`size-4 shrink-0 rounded-full border-[3px] shadow-md ${ring}`),
		element(
			"whitespace-nowrap rounded-[6px] bg-surface-base px-2 py-[3px] text-xs font-medium text-ink-gray-9 shadow-md",
			place.venue_name,
		),
	)
	return wrapper
}

function drawMarkers() {
	if (!map || !library) return
	for (const old of markers) old.remove()
	markers = located.value.map((place) => {
		const hasTag =
			props.selected.indexOf(place.name) < 0 && [props.active, props.hovered].includes(place.name)
		const pin = marker(place)
		// Pins and tags sit above the plain dots of nearby places.
		pin.style.zIndex = String(hasTag ? 3 : Number(props.selected.includes(place.name)) * 2)
		return new library!.Marker({ element: pin, anchor: hasTag ? "left" : "center" })
			.setLngLat([place.longitude!, place.latitude!])
			.addTo(map!)
	})
	const route = map.getSource<GeoJSONSource>("route")
	route?.setData(routeLine())
}

function routeLine(): GeoJSONSourceSpecification["data"] {
	const coordinates = picked.value.map((place) => [place.longitude!, place.latitude!])
	return { type: "Feature", properties: {}, geometry: { type: "LineString", coordinates } }
}

function addRoute() {
	map!.addSource("route", { type: "geojson", data: routeLine() })
	map!.addLayer({
		id: "route",
		type: "line",
		source: "route",
		layout: { "line-cap": "round" },
		// MapLibre cannot parse the theme's oklch() colours; this grey reads on both map styles.
		paint: { "line-color": "#888", "line-width": 2, "line-dasharray": [0.1, 3.5] },
	})
}

function fit(duration: number) {
	if (!map || !focus.value.length) return
	map.fitBounds(bounds(focus.value), { padding: props.padding, maxZoom: MAX_FIT_ZOOM, duration })
}

// Hovering down a list sweeps through rows; the camera moves once the pointer settles.
const flyToFocus = useDebounceFn(() => fit(FLY_DURATION), 140)

onMounted(async () => {
	library = await import("maplibre-gl")
	if (!container.value) return
	const theme = document.documentElement.dataset.theme === "dark" ? "dark" : "light"
	map = new library.Map({
		container: container.value,
		style: MAP_STYLES[theme],
		center: [78.9, 20.6],
		zoom: 3,
		// OpenStreetMap's data licence (ODbL) asks for its credit to stay in view.
		attributionControl: { compact: false, customAttribution: OSM_ATTRIBUTION },
	})
	fit(0)
	map.once("load", () => {
		addRoute()
		isReady.value = true
	})
	drawMarkers()
})

onBeforeUnmount(() => map?.remove())

watch(() => [props.places, props.selected, props.active, props.hovered], drawMarkers, {
	deep: true,
})
watch(
	() => [focus.value.map((place) => place.name).join(), props.padding.right, props.padding.top],
	flyToFocus,
)
</script>

<template>
	<div
		ref="container"
		class="bg-surface-gray-2 transition-opacity duration-300 ease-out [&_.maplibregl-canvas]:outline-none [&_.maplibregl-ctrl-attrib]:text-[10px] [&_.maplibregl-ctrl-attrib]:leading-4"
		:class="isReady ? 'opacity-100' : 'opacity-0'"
	/>
</template>

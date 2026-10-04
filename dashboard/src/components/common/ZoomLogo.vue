<script setup lang="ts">
withDefaults(defineProps<{ color?: string }>(), { color: "#2196F3" })
</script>

<template>
	<svg viewBox="4 4 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
		<path
			d="M15.9998 28C22.6275 28 28 22.627 28 15.9998C28 9.37249 22.6275 4 15.9998 4C9.37202 4 4 9.37249 4 15.9998C4 22.627 9.37249 28 15.9998 28Z"
			:fill="color"
		/>
		<path
			fill-rule="evenodd"
			clip-rule="evenodd"
			d="M11.0418 19.4297H18.9783V13.6101C18.9783 12.7333 18.2678 12.0228 17.391 12.0228H9.45445V17.8424C9.45445 18.7192 10.165 19.4297 11.0418 19.4297ZM20.036 17.3138L23.2106 19.4297V12.0228L20.0365 14.1392L20.036 17.3138Z"
			fill="white"
		/>
	</svg>
</template>

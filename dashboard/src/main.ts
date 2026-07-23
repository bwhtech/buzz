import { createApp } from "vue"

import App from "./App.vue"
import router from "./router"
import { initSocket } from "./socket"

import translationPlugin from "./translation"

import {
	Alert,
	Badge,
	Button,
	Dialog,
	ErrorMessage,
	FormControl,
	TextInput,
	frappeRequest,
	pageMetaPlugin,
	resourcesPlugin,
	setConfig,
} from "frappe-ui"

import "./index.css"

const globalComponents = {
	Button,
	TextInput,
	FormControl,
	ErrorMessage,
	Dialog,
	Alert,
	Badge,
}

const app = createApp(App)

setConfig("resourceFetcher", frappeRequest)

app.use(router)
app.use(translationPlugin)
app.use(resourcesPlugin)
app.use(pageMetaPlugin)

const socket = initSocket()
app.config.globalProperties.$socket = socket

for (const [key, component] of Object.entries(globalComponents)) {
	app.component(key, component)
}

app.mount("#app")

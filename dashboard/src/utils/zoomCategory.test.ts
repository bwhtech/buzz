import assert from "node:assert/strict"
import { test } from "node:test"
import { isZoomBackedCategory } from "./zoomCategory.ts"

test("webinar events are Zoom backed", () => {
	assert.equal(isZoomBackedCategory("Webinars"), true)
})

test("meeting events are Zoom backed", () => {
	assert.equal(isZoomBackedCategory("Zoom Meeting"), true)
})

test("other categories are not Zoom backed", () => {
	assert.equal(isZoomBackedCategory("Conferences"), false)
	assert.equal(isZoomBackedCategory("Meetups"), false)
})

test("a missing category is not Zoom backed", () => {
	assert.equal(isZoomBackedCategory(undefined), false)
	assert.equal(isZoomBackedCategory(""), false)
})

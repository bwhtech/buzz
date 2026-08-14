import assert from "node:assert/strict"
import { test } from "node:test"
import {
	allTimeZones,
	canonicalZone,
	zoneCity,
	zoneCountry,
	nowInZone,
	zoneGenericName,
	zoneOffsetLabel,
	zoneSearchText,
} from "./timeZones.ts"

// Mid-January and mid-July, so a zone that observes DST reads differently in each.
const WINTER = new Date("2026-01-15T12:00:00Z")
const SUMMER = new Date("2026-07-15T12:00:00Z")

test("the zone list carries UTC and the region zones", () => {
	const zones = allTimeZones()
	for (const zone of ["UTC", "Europe/London", "America/New_York"]) {
		assert.ok(zones.includes(zone), `${zone} missing from the list`)
	}
	assert.ok(zones.length > 100)
})

test("renamed zones reach the list under their current name", () => {
	const zones = allTimeZones()
	for (const [old_, current] of [
		["Asia/Calcutta", "Asia/Kolkata"],
		["Europe/Kiev", "Europe/Kyiv"],
	]) {
		assert.ok(zones.includes(current), `${current} missing from the list`)
		assert.ok(!zones.includes(old_), `${old_} still in the list`)
	}
})

test("a zone with no rename passes through", () => {
	assert.equal(canonicalZone("Europe/London"), "Europe/London")
})

test("a renamed zone still labels correctly", () => {
	assert.equal(zoneOffsetLabel("Asia/Kolkata", WINTER), "GMT+05:30")
	assert.equal(zoneCity("Asia/Kolkata"), "Kolkata")
})

test("every zone in the list can be labelled", () => {
	for (const zone of allTimeZones()) {
		assert.match(zoneOffsetLabel(zone, WINTER), /^GMT[+-]\d{2}:\d{2}$/, zone)
		assert.ok(zoneCity(zone).length > 0, zone)
	}
})

test("a half-hour offset keeps its minutes", () => {
	assert.equal(zoneOffsetLabel("Asia/Kolkata", WINTER), "GMT+05:30")
})

test("a zero offset spells out its sign and minutes", () => {
	assert.equal(zoneOffsetLabel("UTC", WINTER), "GMT+00:00")
	assert.equal(zoneOffsetLabel("Europe/London", WINTER), "GMT+00:00")
})

test("the offset follows daylight saving", () => {
	assert.equal(zoneOffsetLabel("Europe/London", SUMMER), "GMT+01:00")
	assert.equal(zoneOffsetLabel("America/New_York", WINTER), "GMT-05:00")
	assert.equal(zoneOffsetLabel("America/New_York", SUMMER), "GMT-04:00")
})

test("the city drops the region and the underscores", () => {
	assert.equal(zoneCity("Asia/Kolkata"), "Kolkata")
	assert.equal(zoneCity("America/New_York"), "New York")
	assert.equal(zoneCity("America/Argentina/Buenos_Aires"), "Buenos Aires")
	assert.equal(zoneCity("UTC"), "UTC")
})

test("a zone reports the country it sits in", () => {
	assert.equal(zoneCountry("Asia/Kolkata"), "India")
	assert.equal(zoneCountry("Europe/London"), "United Kingdom")
	assert.equal(zoneCountry("America/New_York"), "United States")
	assert.equal(zoneCountry("Pacific/Auckland"), "New Zealand")
})

test("an unknown zone has no country rather than throwing", () => {
	assert.equal(zoneCountry("Nowhere/Nothing"), "")
})

test("every zone on offer has a country", () => {
	// UTC is ours, not a place, so it is the one entry with nowhere to belong.
	const placeless = allTimeZones().filter((zone) => zone !== "UTC" && !zoneCountry(zone))
	assert.deepEqual(placeless, [])
})

test("an unknown zone is labelled empty rather than throwing", () => {
	assert.equal(zoneOffsetLabel("Nowhere/Nothing"), "")
	assert.equal(zoneGenericName("Nowhere/Nothing"), "")
})

test("a zone carries an everyday name", () => {
	assert.equal(zoneGenericName("Asia/Kolkata", WINTER), "India Standard Time")
	assert.equal(zoneGenericName("America/New_York", WINTER), "Eastern Time")
})

test("search text carries city, country and everyday name", () => {
	assert.equal(zoneSearchText("Asia/Kolkata"), "Kolkata, India, India Standard Time")
	// The zone id is matched separately by Combobox, so it is not repeated here.
	assert.ok(!zoneSearchText("Asia/Kolkata").includes("Asia/"))
})

test("search text drops the parts a zone has no answer for", () => {
	assert.equal(zoneSearchText("Nowhere/Nothing"), "Nothing")
})

test("the wall clock in a zone reads as Frappe's naive datetime", () => {
	assert.equal(nowInZone("Asia/Kolkata", WINTER), "2026-01-15 17:30:00")
	assert.equal(nowInZone("America/New_York", WINTER), "2026-01-15 07:00:00")
})

test("a zone the runtime cannot resolve falls back rather than throwing", () => {
	assert.match(nowInZone("Nowhere/Nothing", WINTER), /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/)
})

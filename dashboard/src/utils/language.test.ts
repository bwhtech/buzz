import assert from "node:assert/strict"
import { test } from "node:test"
import {
	buildPreferredLanguageCookie,
	readPreferredLanguage,
	resolveRequestedLanguage,
	takeLanguageFromQuery,
} from "./language.ts"

const enabledLanguageCodes = ["en", "de", "fr"]

function resolve(
	requestedLanguage: string,
	overrides: Record<string, unknown> = {},
) {
	return resolveRequestedLanguage({
		requestedLanguage,
		isLoggedIn: false,
		enabledLanguageCodes,
		currentLanguage: null,
		...overrides,
	})
}

test("a URL without ?lang is left untouched", () => {
	assert.deepEqual(
		takeLanguageFromQuery("https://buzz.test/b/account/bookings"),
		{
			cleanedUrl: null,
			requestedLanguage: null,
		},
	)
})

test("?lang is read off the URL and stripped from it", () => {
	assert.deepEqual(
		takeLanguageFromQuery("https://buzz.test/b/register/pycon?lang=de"),
		{
			cleanedUrl: "https://buzz.test/b/register/pycon",
			requestedLanguage: "de",
		},
	)
})

test("stripping ?lang keeps the other query parameters and the hash", () => {
	assert.deepEqual(
		takeLanguageFromQuery(
			"https://buzz.test/b/register/pycon?lang=de&coupon=EARLY#tickets",
		),
		{
			cleanedUrl: "https://buzz.test/b/register/pycon?coupon=EARLY#tickets",
			requestedLanguage: "de",
		},
	)
})

test("an empty ?lang is treated as absent", () => {
	assert.deepEqual(takeLanguageFromQuery("https://buzz.test/b?lang="), {
		cleanedUrl: null,
		requestedLanguage: null,
	})
})

test("an enabled language is applied for a guest", () => {
	assert.equal(resolve("de"), "de")
})

test("?lang is ignored for a logged-in user", () => {
	// A shared link must not silently rewrite someone's saved preference.
	assert.equal(resolve("de", { isLoggedIn: true }), null)
})

test("an unknown language code is never written to the cookie", () => {
	assert.equal(resolve("not-a-language"), null)
})

test("?lang matching the language already in effect changes nothing", () => {
	assert.equal(resolve("de", { currentLanguage: "de" }), null)
})

test("reads the preferred language out of a cookie string", () => {
	assert.equal(
		readPreferredLanguage("sid=abc123; preferred_language=de; user_id=Guest"),
		"de",
	)
	assert.equal(readPreferredLanguage("sid=abc123"), null)
	assert.equal(readPreferredLanguage(""), null)
})

test("the cookie is written for the whole site and survives the session", () => {
	const cookie = buildPreferredLanguageCookie("de")

	assert.match(cookie, /^preferred_language=de;/)
	assert.match(cookie, /path=\//)
	assert.match(cookie, /max-age=\d+/)
	assert.match(cookie, /SameSite=Lax/)
})

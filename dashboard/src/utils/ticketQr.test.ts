import assert from "node:assert/strict";
import { test } from "node:test";
import { extractTicketId } from "./ticketQr.ts";

test("uppercase ticket id is returned as-is", () => {
	assert.equal(extractTicketId("ABC123XYZ"), "ABC123XYZ");
});

test("lowercase frappe hash falls through to the length branch", () => {
	// Only matches because frappe hashes are 10 characters; the first branch is uppercase-only.
	assert.equal(extractTicketId("o3iuamhq0n"), "o3iuamhq0n");
});

test("ticket id is pulled out of a ticket url", () => {
	assert.equal(extractTicketId("http://buzz.test:8000/b/ticket/o3iuamhq0n"), "o3iuamhq0n");
});

test("query-string form is also recognised", () => {
	assert.equal(extractTicketId("https://buzz.test/scan?ticket=ABC123"), "ABC123");
});

test("short lowercase id without a ticket segment is not recognised", () => {
	assert.equal(extractTicketId("abc123"), null);
});

test("payload with nothing ticket-shaped returns null", () => {
	assert.equal(extractTicketId("hello there"), null);
});

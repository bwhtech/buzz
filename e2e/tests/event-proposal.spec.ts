import { test, expect } from "@playwright/test";
import { EventProposalPage } from "../pages";
import { callMethod, updateDoc } from "../helpers/frappe";

test.describe("Event Proposal Form - Rendering", () => {
	test("should display the proposal form", async ({ page }) => {
		const proposalPage = new EventProposalPage(page);
		await proposalPage.goto();
		await proposalPage.waitForFormLoad();
		await proposalPage.expectFormVisible();
	});

	test("should display the banner title", async ({ page }) => {
		const proposalPage = new EventProposalPage(page);
		await proposalPage.goto();
		await proposalPage.waitForFormLoad();
		await proposalPage.expectBannerTitle("Propose an Event");
	});

	test("should display the title field", async ({ page }) => {
		const proposalPage = new EventProposalPage(page);
		await proposalPage.goto();
		await proposalPage.waitForFormLoad();
		await proposalPage.expectFieldVisible("Title");
	});

	test("should display the submit button", async ({ page }) => {
		const proposalPage = new EventProposalPage(page);
		await proposalPage.goto();
		await proposalPage.waitForFormLoad();
		await proposalPage.expectSubmitButtonVisible();
	});
});

test.describe("Event Proposal Form - Submission", () => {
	test("should fill and submit a proposal", async ({ page }) => {
		const proposalPage = new EventProposalPage(page);
		await proposalPage.goto();
		await proposalPage.waitForFormLoad();

		const titleInput = proposalPage.getInputByLabel("Title");
		await titleInput.fill("E2E Test: Automated Testing with Playwright");

		await proposalPage.selectOptionByLabel("Event Category", "E2E Test Category");

		const aboutTextarea = page
			.locator('label:has-text("About the event")')
			.locator("..")
			.locator("textarea");
		await aboutTextarea.fill("An E2E test proposal about automated testing practices.");

		const { succeeded, status } = await proposalPage.submitAndExpectResponse();
		console.log(`Proposal submission: status=${status}, succeeded=${succeeded}`);
	});

	test("should show success banner after submission", async ({ page }) => {
		await page.route(/submit_event_proposal/, (route) =>
			route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({ message: null }),
			}),
		);

		const proposalPage = new EventProposalPage(page);
		await proposalPage.goto();
		await proposalPage.waitForFormLoad();

		const titleInput = proposalPage.getInputByLabel("Title");
		await titleInput.fill("E2E Test: Another Proposal for Success Banner");

		await proposalPage.selectOptionByLabel("Event Category", "E2E Test Category");

		const aboutTextarea = page
			.locator('label:has-text("About the event")')
			.locator("..")
			.locator("textarea");
		await aboutTextarea.fill("An E2E test proposal about building better events.");

		await proposalPage.submitAndExpectResponse();
		await proposalPage.expectSuccess();
	});
});

test.describe("Event Proposal Form - Access Control", () => {
	test("should show not found when proposals are disabled", async ({ page, request }) => {
		await updateDoc(request, "Buzz Settings", "Buzz Settings", {
			accept_event_proposals: 0,
		});

		try {
			const proposalPage = new EventProposalPage(page);
			await proposalPage.goto();
			await proposalPage.expectNotFound();
		} finally {
			await updateDoc(request, "Buzz Settings", "Buzz Settings", {
				accept_event_proposals: 1,
			});
		}
	});

	test("should return error via API when proposals are disabled", async ({ request }) => {
		await updateDoc(request, "Buzz Settings", "Buzz Settings", {
			accept_event_proposals: 0,
		});

		try {
			const result = await callMethod(
				request,
				"buzz.api.forms.get_event_proposal_form_data",
			).catch((err: Error) => err);

			expect(result).toBeInstanceOf(Error);
		} finally {
			await updateDoc(request, "Buzz Settings", "Buzz Settings", {
				accept_event_proposals: 1,
			});
		}
	});
});

test.describe("Event Proposal Form - API", () => {
	test("should return form data with expected shape", async ({ request }) => {
		const data = await callMethod<{
			form_fields: Array<{ fieldname: string }>;
			banner_title: string;
			form_title: string;
			success_title: string;
		}>(request, "buzz.api.forms.get_event_proposal_form_data");

		expect(data.form_fields).toBeInstanceOf(Array);
		expect(data.form_fields.length).toBeGreaterThan(0);
		expect(data.banner_title).toBeTruthy();
		expect(data.form_title).toBeTruthy();
		expect(data.success_title).toBeTruthy();
	});

	test("should not expose excluded fields in form data", async ({ request }) => {
		const data = await callMethod<{
			form_fields: Array<{ fieldname: string }>;
		}>(request, "buzz.api.forms.get_event_proposal_form_data");

		const fieldnames = data.form_fields.map((f) => f.fieldname);
		const excludedFields = ["status", "submitted_by", "host", "naming_series", "amended_from"];

		for (const excluded of excludedFields) {
			expect(fieldnames).not.toContain(excluded);
		}
	});
});

# 12 — Event settings: payments, registration & forms

| Phase | Depends on | Status |
|---|---|---|
| D | 01-dashboard/03 | Draft |

## Goal

The event Settings tab — everything else on the `Buzz Event` form: payment gateways, tax,
registration/guest-booking config, ticket email config, custom fields, custom forms, extra pages.
Completes single-event Desk parity.

## Demo criteria (definition of done)

Manager adds a payment gateway row and it appears at public checkout; sets
`registrations_close_at` in the past and public booking closes; adds a custom field and it shows
in the booking form.

## Scope

### In (grouped settings sections, all on `useDoc("Buzz Event")` unless noted)
- **Payments**: `payment_gateways` child rows (`Event Payment Gateway`: gateway Link + currency);
  `Offline Payment Method` list for the event (separate doctype CRUD); `free_webinar` toggle
- **Tax**: `apply_tax`, `tax_label`, `tax_percentage`, `tax_inclusive`
- **Registration**: `registrations_close_at`, `allow_guest_booking`,
  `guest_verification_method`, `external_registration_page` + `registration_url`,
  `default_ticket_type`, `attach_calendar_invite`
- **Ticket email**: `send_ticket_email`, `ticket_email_template` (Link → Email Template),
  `attach_email_ticket`, `ticket_print_format`
- **Sponsor deck**: `auto_send_pitch_deck`, `sponsor_deck_email_template`,
  `sponsor_deck_reply_to`, `sponsor_deck_cc`, `sponsor_deck_attachments`,
  `show_sponsorship_section`
- **Custom fields**: `Buzz Custom Field` CRUD for this event (label, type, options, required)
- **Forms & pages**: `custom_forms` child rows (`Buzz Event Form`) linking custom forms;
  `Additional Event Page` CRUD

### Out (deferred to)
- Team-level defaults (transfer/cancel/add-on windows, default email templates, sponsor-deck
  defaults) — live in `Buzz Team Settings` (`00-teams/05`), surfaced in the Team Settings dialog
  (step 13), not here. `Buzz Settings` (site-wide Single) stays Desk/System Manager for global
  admin config (login banner, proposal funnel)
- Email Template authoring UI — Link picker only; authoring stays Desk (Phase E)

## Backend changes

None expected — all doc/child CRUD under hooks. If offline-method or custom-field creation needs
validation beyond doctype controllers, add to existing controllers, not new endpoints.

## Frontend changes

- `src/pages/manage/event/SettingsTab.vue` — settings-page archetype: left anchor nav
  (sections above), right content cards; each card = `FormControl` group bound to `useDoc`,
  sticky save. Child-table editors reuse the row-editor pattern from steps 05/11.
- `data/eventSettings.ts` (offline methods, custom fields `useList`s).

## API contract

No new endpoints.

## Permissions notes

Manager+ writes; Viewer read-only. Gateway credentials themselves live in the gateway apps'
settings (System Manager) — this tab only *selects* gateways, never edits credentials.

## Demo script

1. Add Razorpay gateway row (INR) → public checkout offers it.
2. Enable tax 18% "GST" → checkout total shows tax line.
3. Set `registrations_close_at` past → public page shows "registrations closed"; clear it → open.
4. Add custom field "Company" (required) → booking form renders it; value lands in
   `Additional Field` rows.
5. Toggle `allow_guest_booking` off → guest checkout demands login.

## Acceptance criteria (merge gate)

### Automated tests — extend booking-flow tests (`buzz/tests/test_booking_flow.py` or existing module)
- `registrations_close_at` in the past → `get_event_booking_data`/`process_booking` reject with
  the closed-registrations error; cleared → accepted.
- `allow_guest_booking=0` → guest `process_booking` raises; logged-in booking succeeds.
- Tax config: `apply_tax` 18% → booking totals include tax line (inclusive + exclusive branches).
- Required `Buzz Custom Field` missing in submission → validation error; provided → stored in
  `Additional Field` rows.

### Browser checks (agent-browser, dev server :8080)
1. Settings tab → add Razorpay gateway row (INR) → fresh session checkout offers Razorpay.
2. Enable tax 18% "GST" → checkout shows tax line, math correct on screen.
3. Set `registrations_close_at` past → public page shows registrations-closed state; clear →
   bookable again.
4. Add required custom field "Company" → booking form renders it; submitting without it blocks
   with field error; with it → booking completes.
5. Toggle `allow_guest_booking` off → guest checkout demands login.
6. Anchor nav: each settings section scrolls/activates correctly; sticky save reflects dirty
   state per section.

## Dependencies & risks

- This tab touches many existing public-flow behaviors — regression pass over the booking flow is
  part of the demo, not optional.
- `sponsor_deck_attachments` child (files) needs `FileUploader` multi-attach handling.

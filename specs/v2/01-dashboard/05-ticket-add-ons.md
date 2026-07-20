# 05 — Ticket add-ons

| Phase | Depends on | Status |
|---|---|---|
| B | 01-dashboard/02 | Draft |

## Goal

`Ticket Add-on` CRUD in the workspace, including option lists (e.g. T-shirt sizes).

## Demo criteria (definition of done)

Manager adds "T-shirt (S/M/L), ₹299"; the public booking flow offers it with the size selector;
an attendee's selection lands in `Attendee Ticket Add-on`.

## Scope

### In
- Add-ons tab: table + create/edit dialog with options editor, enable/disable
- Coupons dialog follow-up: `free_add_ons` child rows editor (deferred from step 04)
### Out (deferred to)
- Attendee-side add-on change flow (already exists) — untouched

## Backend changes

None.

## Frontend changes

- `src/pages/manage/event/AddOnsTab.vue` — `List`: `title`, price (`format_currency`), options
  summary (chips), `enabled` Switch inline.
- `AddOnDialog.vue` — real fields: `title` (reqd), `price` + `currency`, `description`,
  `user_selects_option` (Switch) revealing an **options editor**: tag-style input writing
  newline-separated values into the `options` Small Text field (matches current backend parsing),
  `enabled`.
- Coupons: extend `CouponDialog.vue` with `free_add_ons` child-table editor (add-on Link +
  option) now that add-on selectors exist.
- `data/addons.ts`.

## API contract

No new endpoints.

## Permissions notes

Manager+ CRUD; Viewer read-only.

## Demo script

1. Create "T-shirt", ₹299, options S/M/L, user_selects_option on, enabled.
2. Public booking → add-on appears with size Select; book with "M".
3. Desk: `Attendee Ticket Add-on` row records the selection.
4. Disable the add-on → hidden from new bookings.

## Acceptance criteria (merge gate)

### Automated tests — `buzz/tests/test_add_ons.py` (new or extend existing)
- Options round-trip: save "S\nM\nL" via the editor payload → stored `options` string is exactly
  newline-delimited with no trailing newline; booking-side parser yields `["S","M","L"]`.
- Disabled add-on excluded from `get_event_booking_data` payload.

### Browser checks (agent-browser, dev server :8080)
1. Create "T-shirt" ₹299, options S/M/L via tag editor, enabled → row shows option chips.
2. Public booking flow → add-on card with size `Select` (3 options) → book with "M".
3. Assert `Attendee Ticket Add-on` records "M" (Desk/REST check).
4. Toggle `enabled` off → new booking session no longer shows the add-on.
5. Coupon dialog now offers `free_add_ons` rows referencing the add-on.

## Dependencies & risks

- `options` is newline-delimited Small Text — the editor must round-trip exactly (no trailing
  newline drift) or attendee selects break.

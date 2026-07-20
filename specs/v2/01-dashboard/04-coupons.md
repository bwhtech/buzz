# 04 — Coupons

| Phase | Depends on | Status |
|---|---|---|
| B | 01-dashboard/02 | Draft |

## Goal

`Buzz Coupon Code` management in the event workspace — create, edit, activate/deactivate, monitor
usage.

## Demo criteria (definition of done)

Manager creates a 10%-off coupon; attendee applies it at public checkout (existing
`validate_coupon`) and sees the discounted total; the Coupons tab shows `times_used` tick up.

## Scope

### In
- Coupons tab: table + create/edit dialog covering the discount path
- Free-tickets coupon type (`coupon_type`, `number_of_free_tickets`)
### Out (deferred to)
- `free_add_ons` child rows in the dialog → step 05 (needs add-ons UI patterns); until then that
  child table stays Desk-editable
- Cross-event coupons (`applies_to`/`event_category` scope) → render read-only note if set

## Backend changes

None — plain CRUD under team hooks (coupon has `event` link; team stamped via cascade).

## Frontend changes

- `src/pages/manage/event/CouponsTab.vue` — `List`: `code` (mono), type (discount/free-tickets
  `Badge`), value (`discount_value` + `discount_type` %/flat, or `number_of_free_tickets`),
  usage `times_used`/`max_usage_count`, validity `valid_from`–`valid_till`, `is_active` Switch
  inline. Header "New Coupon".
- `CouponDialog.vue` — `FormControl`s on real fields: `code` (reqd, uppercase), `coupon_type`
  Select, then conditional: discount → `discount_type`, `discount_value`,
  `maximum_discount_amount`, `minimum_order_value`; free tickets → `number_of_free_tickets`,
  `ticket_type` (Link, filtered to this event). Common: `valid_from`/`valid_till`,
  `max_usage_count`, `max_usage_per_user`, `is_active`.
- `data/coupons.ts` — `useList({ doctype: "Buzz Coupon Code", filters: { event } })`.

## API contract

No new endpoints (checkout reuses existing `buzz.api.validate_coupon`).

## Permissions notes

Manager+ CRUD; Viewer read-only. Code uniqueness errors surfaced from server via `toast.error`.

## Demo script

1. Create `LAUNCH10`, 10% off, max 100 uses, active.
2. Public checkout → apply `LAUNCH10` → total drops 10%.
3. Complete booking → tab shows `times_used = 1`.
4. Toggle inactive → checkout rejects the code.

## Acceptance criteria (merge gate)

### Automated tests
Extend existing coupon tests (or add `buzz/tests/test_coupons.py`) only for gaps exposed:
- `validate_coupon` respects `is_active=0`, `valid_till` past, `max_usage_count` reached,
  `minimum_order_value` unmet (skip cases already covered by existing suite — audit first).
- Team cascade: coupon created via dashboard carries the event's team (covered by
  `test_team_cascade`; assert once here if not parametrized).

### Browser checks (agent-browser, dev server :8080)
1. Create coupon `LAUNCH10` (10%, active) → row appears with usage 0/100.
2. Fresh session → public checkout → apply `LAUNCH10` → total reduced 10%; complete booking.
3. Coupons tab → `times_used` shows 1.
4. Toggle `is_active` off inline → checkout rejects the code with visible error message.
5. Create dialog: switching `coupon_type` swaps discount vs free-tickets field groups.
6. Duplicate code creation → server error surfaced as toast, dialog stays open.

## Dependencies & risks

- Coupon validation logic stays server-side in `validate_coupon` — the dialog never duplicates it.

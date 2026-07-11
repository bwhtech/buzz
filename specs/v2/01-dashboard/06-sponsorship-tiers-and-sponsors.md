# 06 — Sponsorship tiers & sponsors

| Phase | Depends on | Status |
|---|---|---|
| B | 01-dashboard/02 | Draft |

## Goal

Sponsors tab: manage `Sponsorship Tier` and `Event Sponsor`, and see incoming
`Sponsorship Enquiry` records — the sponsorship pipeline visible where the event lives.

## Demo criteria (definition of done)

Manager creates a "Gold ₹50k" tier and adds a sponsor with logo; both render on the public event
page's sponsors section. Incoming enquiries appear read-only with status.

## Scope

### In
- Tiers CRUD (`title`, `price`, `currency`)
- Sponsors CRUD grouped by tier (`company_name`, `tier`, `company_logo`, `website`, `country`)
- Enquiries list (read-only) with status badges
### Out (deferred to)
- Enquiry approval/payment-link workflow (exists via attendee flow + Desk) — surfacing actions
  here is a follow-up once payments v2 lands (future payments pillar)
- Pitch-deck email settings → step 12

## Backend changes

None.

## Frontend changes

- `src/pages/manage/event/SponsorsTab.vue` — three sections:
  1. **Tiers** — compact `List` (title, price) + `TierDialog` (3 fields).
  2. **Sponsors** — grouped by tier; each sponsor: `Avatar`-style logo, company_name, website
     link; `SponsorDialog`: `company_name` (reqd), `tier` (Select from this event's tiers),
     `company_logo` `FileUploader`, `website`, `country` (Link).
  3. **Enquiries** — read-only `List` of `Sponsorship Enquiry` for the event: company, tier,
     status `Badge`, created; row → slide-over detail (`Dialog` right placement) showing the
     enquiry; no mutations.
- `data/sponsors.ts` — three `useList`s keyed by event.

## API contract

No new endpoints.

## Permissions notes

Manager+ CRUD tiers/sponsors; enquiries read-only for all team roles except Frontdesk.
Existing attendee-side enquiry endpoints untouched.

## Demo script

1. Create tier "Gold" ₹50,000.
2. Add sponsor "Acme" with logo under Gold → public event page sponsors section shows logo.
3. Submit a sponsorship enquiry from the public flow → appears in Enquiries with "Pending Approval".

## Acceptance criteria (merge gate)

### Automated tests
None new — CRUD under hooks; `test_team_cascade`/`test_team_permissions` parametrized cases cover
`Sponsorship Tier`/`Event Sponsor`/`Sponsorship Enquiry`. Existing enquiry-dedup test
(fix `8eba8cb`) must stay green.

### Browser checks (agent-browser, dev server :8080)
1. Create tier "Gold" ₹50,000 → appears in Tiers section.
2. Add sponsor "Acme" (logo upload) under Gold → sponsors section groups it under Gold with logo.
3. Public event page → sponsors section renders Acme logo (image request 200).
4. Fresh session → submit sponsorship enquiry via public flow → Enquiries section shows it with
   "Pending Approval" badge; slide-over opens read-only.
5. Frontdesk-role member → Sponsors tab hidden/inaccessible.

## Dependencies & risks

- `Event Sponsor.enquiry` dedup validation (recent fix `8eba8cb`) lives server-side — dialog just
  surfaces errors.

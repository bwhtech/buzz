# KonfHub Gap Roadmap

Closes the main feature gaps between Buzz and [KonfHub](https://konfhub.com/), the event ticketing platform most Indian organisers compare us against. Each phase starts with a tracer bullet: the thinnest slice that crosses every layer (doctype → service → whitelisted API → dashboard → email/job → test), so it can be demoed and judged before the phase is widened.

## Context

KonfHub sells per event (India: 0% Freemium, 2% Lite, 3.75% Silver, custom Gold, plus 18% GST; elsewhere a flat $499 / $1,499 per event, see [pricing](https://konfhub.com/pricing) and [introduction](https://help.konfhub.com/introduction.md)). Reviewers praise ease of use and support and complain about limited page and form customization, price, no regional languages and a weak mobile admin ([Capterra](https://www.capterra.com/p/265126/KonfHub/reviews/)). Every help article is indexed at [help.konfhub.com/llms.txt](https://help.konfhub.com/llms.txt).

Buzz is already ahead on attendee self-service (transfer, add-on change, cancellation request), call for proposals, sponsorship sales, the Zoom integration, multi-currency on every event, offline payments and event templates. The roadmap below does not touch those.

## Principles

- **Dashboard first.** Organisers must not need Frappe desk for anything in this roadmap. Where a doctype already exists, the phase is dashboard and API work only.
- **Reuse before adding.** Coupons, add-ons, custom fields, refunds, approvals and cancellations already have models and controller methods. Build on them; do not fork new ones.
- **Follow the API conventions.** New endpoints live under `buzz/api/<domain>/` with pydantic schemas, a service class and `BuzzAPIError` subclasses (see the building-apis skill). Dashboard calls use `useCall` / `useList` / `useDoc` on `/api/v2/method/...`.
- **Team-scoped permissions.** Every new endpoint checks team membership through `buzz/permissions.py`. Frontdesk can check in; Viewer can read; only Admin and Owner change money or settings.
- **One tracer bullet per phase, then widen.** Each phase lists its tracer bullet first and its follow-up slices after. A phase is done when every slice has tests and an e2e path.

## Phase overview

| Phase | Theme | Size | KonfHub reference |
|---|---|---|---|
| 1 | Desk-only features into the dashboard | M | [Tickets](https://help.konfhub.com/dashboard/event-info/tickets.md), [Coupons](https://help.konfhub.com/dashboard/event-info/coupons.md), [Participants](https://help.konfhub.com/dashboard/participants.md) |
| 2 | Event-day check-in | M | [Check-in app](https://help.konfhub.com/apps/check-in-app.md) |
| 3 | Reaching attendees: reminders, targeting, WhatsApp | M | [Contact attendees](https://help.konfhub.com/dashboard/contact-attendees.md) |
| 4 | Capacity: waitlist, hidden tickets, group tickets | M | [Tickets](https://help.konfhub.com/dashboard/event-info/tickets.md) |
| 5 | Form builder with conditional questions | M | [Forms](https://help.konfhub.com/dashboard/event-info/forms.md) |
| 6 | GST invoices | S | [Advanced settings](https://help.konfhub.com/dashboard/advanced.md) |
| 7 | Certificates | S | [Pricing](https://konfhub.com/pricing) (Silver: standard, Gold: custom) |
| 8 | Organiser analytics | S | [Analytics](https://help.konfhub.com/dashboard/analytics.md) |
| 9 | Marketing: ticket widget, pixels, referrals | M | [Martech](https://help.konfhub.com/integrations/martech.md), [Gamification](https://help.konfhub.com/dashboard/gamification.md) |
| 10 | Outgoing webhooks | S | [Webhooks](https://help.konfhub.com/integrations/webhooks.md) |
| 11 | Sponsor lead capture | M | [Lead capture app](https://help.konfhub.com/apps/lead-capture-app.md) |
| 12 | Later: hybrid events, engagement, bulk upload | L | [Event app](https://help.konfhub.com/apps/event-app.md) |

Phases 1 to 4 are the priority. They cover the jobs organisers do on every event; the rest are self-contained and can be reordered on demand.

---

## Phase 1: Desk-only features into the dashboard

**Why.** KonfHub organisers run everything from one dashboard. Ours still go to desk for coupons, add-ons, approvals, cancellations, refunds, custom fields and the schedule. The backend for all of these exists, so this phase is the cheapest gap to close.

**What exists.**
- Coupons: `buzz/ticketing/doctype/buzz_coupon_code` (percentage or flat, max discount, minimum order, validity window, per-user and total limits, scope by event, category or ticket type, free add-ons). Applied at booking via `buzz/api/booking/coupons.py`.
- Add-ons: `buzz/ticketing/doctype/ticket_add_on`.
- Approvals: `Event Booking.status` (`Confirmed`, `Approval Pending`, `Approved`, `Rejected`) with `approve_booking` / `reject_booking` in `buzz/ticketing/doctype/event_booking/event_booking.py`.
- Cancellations: `buzz/ticketing/doctype/ticket_cancellation_request` (In Review, Accepted, Rejected).
- Refunds: `EventBooking.refund` and `sync_refunds`, `buzz/ticketing/doctype/event_booking_refund`.

### 1.1 Tracer bullet: coupons on the Registration tab

- **API.** `buzz/api/events/coupons.py`: `get_coupons(event)`, `save_coupon(event, coupon)`, `toggle_coupon(name, enabled)`. Schemas reuse the `Buzz Coupon Code` fields; usage count is computed from bookings, not stored twice.
- **Dashboard.** A "Coupons" section on `EventRegistrations.vue` under ticket types: list (code, discount, uses / limit, valid until, status) and a `CouponDrawer.vue` modelled on `TicketTypeDrawer.vue`. Scope picker limited to this event's ticket types.
- **Tests.** API: create, edit, disable, permission denied for Viewer. Playwright: create a 20% coupon, book with it, see the discounted total.
- **Done when** an organiser can create, edit and disable a coupon without opening desk, and the booking form applies it.

KonfHub parity notes: bulk-generated codes and per-ticket eligibility ([coupons](https://help.konfhub.com/dashboard/event-info/coupons.md)). Bulk generation is a follow-up slice; `Bulk Ticket Coupon` already exists on `Event Ticket` and should be reused.

### 1.2 Booking approvals

- Guests tab gets an "Awaiting approval" filter and row actions Approve / Reject calling the controller methods through `buzz/api/events/bookings.py`.
- Offline payments show the uploaded proof inline.
- Bulk approve and reject for selected rows ([participants](https://help.konfhub.com/dashboard/participants.md) has bulk approve, cancel, resend).

### 1.3 Cancellations and refunds

- Cancellation requests listed on the Guests tab with Accept / Reject. Accepting offers "Refund full / partial / none" and calls `EventBooking.refund`, mirroring KonfHub's cancellation flow ([participants](https://help.konfhub.com/dashboard/participants.md)).
- Refund status (`sync_refunds`) visible on the booking.
- Organiser-initiated cancel from the guest row, with the same refund choice.

### 1.4 Add-ons

- Add-on list and drawer on the Registration tab (title, price per currency, options, linked ticket types, capacity).
- KonfHub lets attendees buy add-ons after registering ([add-ons](https://help.konfhub.com/dashboard/event-info/ticket-add-ons.md), [blog](https://blog.konfhub.com/missed-an-add-on-during-registration-you-can-now-buy-it-later-on-konfhub)). We already let attendees change add-on preference; buying a new paid add-on later is a follow-up slice that needs a payment flow on an existing booking.

### 1.5 Schedule, tracks and speakers

- Talks tab gains a Schedule view: assign accepted talks to a slot and track, edit `Schedule Item`, `Event Track` and `Speaker Profile` without desk.
- Feedback responses (`Event Feedback`) listed on the More tab with CSV export.

---

## Phase 2: Event-day check-in

**Why.** KonfHub's check-in app ([docs](https://help.konfhub.com/apps/check-in-app.md)) supports QR and USB scanners, search by name, email or phone, walk-in registration, offline mode, badge printing, kiosk mode, multi-zone check-in and temporary volunteer codes. Ours (`dashboard/src/pages/CheckInScanner.vue`, `buzz/api/checkin/services.py`) only scans a QR and records an `Event Check In`. Event day decides whether an organiser comes back.

### 2.1 Tracer bullet: search and check in

- **API.** `buzz/api/checkin`: `search_tickets(event, query)` matching attendee name, email, phone or ticket ID, returning the same `TicketCheckinDetails` the scanner uses. Reuse `CheckinService.checkin`.
- **Dashboard.** A search box on the scanner page; tapping a result checks in through the existing flow. Live counter: checked in / total.
- **Tests.** API search scoped to the event and team; Frontdesk can search, Viewer cannot check in. Playwright: search by email, check in, counter increments.

### 2.2 Check-in list

- Guests tab gets a Checked in / Not checked in filter and column, so campaigns (Phase 3) and certificates (Phase 7) can target it.

### 2.3 Walk-ins

- "Add walk-in" on the scanner page creates a booking on a chosen ticket type with offline or free payment, then checks in.

### 2.4 Badges

- A `Badge Template` print format (name, company, ticket type, QR) rendered to PDF and printed from the scanner after check-in. Reuse the ticket print pipeline in `buzz/ticketing/print_format/standard_ticket` and `dashboard/src/utils/ticketPdf.ts`.
- KonfHub has a badge designer with single and double-sided silent printing; we start with one template per event and a size picker.

### 2.5 Multi-zone check-in

- `Event Check In` gains a `zone` (Day 1, Day 2, Lunch, Workshop). The scanner picks a zone; a ticket can check in once per zone. KonfHub gates this behind Gold.

### 2.6 Offline mode

- Cache the event's ticket list (ID, name, status) in IndexedDB when the scanner opens; queue check-ins offline and sync with conflict reporting. Needs a service worker; scope it to the scanner route. Ship last in this phase.

---

## Phase 3: Reaching attendees

**Why.** KonfHub sends scheduled campaigns targeted by ticket type and check-in status, plus WhatsApp confirmations and campaigns in India ([contact attendees](https://help.konfhub.com/dashboard/contact-attendees.md)). We have email announcements (`buzz/events/doctype/event_communication`, `EventCommunications.vue`) with scheduling but no automatic reminders and no WhatsApp.

### 3.1 Tracer bullet: automatic event reminder

- **Model.** `Buzz Event` gets `send_reminder` (check) and `reminder_hours_before` (int, default 24).
- **Job.** An hourly scheduler entry in `hooks.py` finds events starting in the window and enqueues one reminder per confirmed ticket, using a new `event_reminder` email template (date, venue or join link, QR). Idempotent: stamp `reminder_sent_on` on the event.
- **Dashboard.** Toggle and hours field on the Details or Announcements tab.
- **Tests.** Job sends once, skips cancelled tickets, does not resend.

### 3.2 Targeting by check-in status

- `Event Communication` recipients filter gains Checked in / Not checked in (depends on 2.2). Use case: post-event thank-you or "we missed you".

### 3.3 WhatsApp

- Integrate through a pluggable sender (`buzz/integrations/whatsapp.py`) behind `Buzz Settings`, starting with the Meta Cloud API. Templates: booking confirmation with ticket link, reminder.
- Announcements gain a channel choice: Email, WhatsApp, both.
- Phone is already captured for guest OTP; require it on the booking form when WhatsApp is on.

### 3.4 Campaign analytics

- Delivery and open counts per announcement from Frappe's `Email Queue` and `Communication` tracking. KonfHub only offers this on Gold.

---

## Phase 4: Capacity controls

**Why.** KonfHub ticket settings ([tickets](https://help.konfhub.com/dashboard/event-info/tickets.md)) include waitlists, hidden tickets unlocked by access code, group and team tickets, a checkout timer that releases unpaid slots, and email-domain restrictions. We only have capacity and auto-unpublish.

### 4.1 Tracer bullet: waitlist

- **Model.** `Event Ticket Type` gets `enable_waitlist` and `waitlist_mode` (Auto invite / Manual). A new `Event Waitlist Entry` doctype (event, ticket type, name, email, phone, status: Waiting, Invited, Booked, Expired, invite expiry).
- **Booking.** When a ticket type is sold out and the waitlist is on, the booking form shows "Join waitlist".
- **Release.** When a ticket is cancelled or capacity rises, Auto mode invites the next entry with a time-limited booking link; Manual mode surfaces it to the organiser.
- **Dashboard.** Waitlist list per ticket type on the Registration tab with Invite action.
- **Tests.** Join when sold out; cancellation invites the next person; expired invite moves on.

### 4.2 Hidden tickets

- `Event Ticket Type.access_code`; ticket types with a code are hidden until the code is entered on the booking form.

### 4.3 Checkout hold

- Pending bookings hold capacity for N minutes (`Buzz Settings`), released by a scheduler job. Prevents oversell during slow payments.

### 4.4 Group tickets and domain restriction

- `tickets_per_booking` minimum and maximum on a ticket type for group packs.
- `allowed_email_domains` on a ticket type for company or college-only events.

---

## Phase 5: Form builder with conditional questions

**Why.** KonfHub forms ([docs](https://help.konfhub.com/dashboard/event-info/forms.md)) have ready-made fields, drag-and-drop ordering, fields chosen per ticket and conditional questions. Our `buzz/buzz/doctype/buzz_custom_field` supports booking, ticket and form targets but is configured in desk only, with no conditions.

### 5.1 Tracer bullet: custom fields in the dashboard

- Registration tab "Questions" section: list, add, edit, reorder (drag), delete. Field types map to what `CustomFieldsSection.vue` already renders.
- API under `buzz/api/events/custom_fields.py`.
- Test: add a mandatory dropdown, see it on the booking form, answer stored on the ticket.

### 5.2 Per-ticket fields

- A field can be limited to selected ticket types.

### 5.3 Conditional questions

- `depends_on_field` and `depends_on_value` on `Buzz Custom Field`; `CustomFieldsSection.vue` hides and skips validation for fields whose condition is unmet. Server validation must apply the same rule.

### 5.4 Ready-made fields and file upload

- Presets (company, designation, T-shirt size, dietary preference) and an Attach field type.

---

## Phase 6: GST invoices

**Why.** KonfHub generates a GST invoice when the buyer enters a GST number ([advanced](https://help.konfhub.com/dashboard/advanced.md); Gold only on their side). We already store `invoice_requested`, the buyer's tax ID and billing address (`BillingDetails.vue`) and the team's tax details (`TeamTaxDetailsDialog.vue`), and compute tax (`buzz/api/events/taxes.py`). Only the document is missing.

### 6.1 Tracer bullet: invoice PDF on the booking

- A `Buzz Invoice` print format on `Event Booking` with seller and buyer details, line items, tax split (CGST/SGST for intra-state, IGST for inter-state, based on state codes in the two GSTINs), and a per-team sequential invoice number.
- Attached to the confirmation email when `invoice_requested` is set; downloadable from the attendee's booking page and the organiser's guest row.
- Tests: number sequence per team, tax split, no invoice when not requested.

### 6.2 Credit notes

- On refund, issue a credit note referencing the invoice.

---

## Phase 7: Certificates

**Why.** KonfHub sends participation certificates, optionally only to checked-in attendees, with a standard template on Silver and a custom design on Gold ([pricing](https://konfhub.com/pricing)). Essential for college events and workshops.

### 7.1 Tracer bullet: send certificates to checked-in attendees

- A default certificate print format (event, attendee name, date, verification ID).
- More tab: "Send certificates" with audience All / Checked in, sending through the announcements pipeline with the PDF attached.
- Public verify page at `/certificates/<id>`.
- Tests: only checked-in tickets get one; verification ID resolves.

### 7.2 Custom design

- Upload a background image and position name and date fields.

---

## Phase 8: Organiser analytics

**Why.** KonfHub analytics ([docs](https://help.konfhub.com/dashboard/analytics.md)) show registration trends, revenue, payment-method split, top companies and job titles, top UTM sources, and abandoned checkouts. We have a registration trend, ticket-type split, revenue cards and CSV export, and we already store UTM parameters (`buzz/events/doctype/utm_parameter`) but never report them.

### 8.1 Tracer bullet: UTM sources card

- A "Top sources" card on the Guests tab grouping bookings by `utm_source` / `utm_campaign` with counts and revenue.

### 8.2 Abandoned checkouts

- Count bookings that never reached payment authorisation, with contact details for follow-up. KonfHub calls this "Registration attempts".

### 8.3 Payment-method split and top companies

- Payment method from the payment request; company and designation from preset fields (depends on 5.4).

---

## Phase 9: Marketing

**Why.** KonfHub offers an embeddable ticket widget and register button (Silver), LinkedIn share, and Meta Pixel, Google Analytics and Tag Manager (Gold) ([martech](https://help.konfhub.com/integrations/martech.md)), plus referral contests with leaderboards ([gamification](https://help.konfhub.com/dashboard/gamification.md)). We only embed the login page (`LoginEmbed.vue`).

### 9.1 Tracer bullet: embeddable booking widget

- An `/b/embed/<event>` route rendering the booking form chromeless, reusing the postMessage pattern from `LoginEmbed.vue` for height and completion events. Copyable `<iframe>` snippet on the More tab. UTM parameters pass through ([KonfHub did the same](https://blog.konfhub.com/utm-integration-for-konfhub-track-where-your-event-registrations-come-from)).

### 9.2 Tracking pixels

- Per-event Meta Pixel ID and GA4 / GTM ID, fired on event page view and on booking success.

### 9.3 Referrals

- Each attendee gets a referral link (`?ref=<ticket>`); bookings store the referrer; a leaderboard on the More tab. Prizes stay manual.

---

## Phase 10: Outgoing webhooks

**Why.** KonfHub fires webhooks on registration, cancellation, check-in, check-out and lead capture, with retries ([webhooks](https://help.konfhub.com/integrations/webhooks.md)); Zapier is Gold only. Integrators will not pick us without this.

### 10.1 Tracer bullet: booking confirmed webhook

- Use Frappe's built-in `Webhook` doctype rather than a custom one: a team-scoped dashboard screen that creates `Webhook` records on `Event Booking` (on confirm), `Ticket Cancellation Request` (on accept) and `Event Check In` (on insert), filtered to the team's events, with a signing secret.
- Test: a confirmed booking enqueues one request with the expected payload.

---

## Phase 11: Sponsor lead capture

**Why.** KonfHub's lead capture app ([docs](https://help.konfhub.com/apps/lead-capture-app.md)) lets booth staff join with a sponsor code, scan attendee QRs, add notes and download leads; their exhibitor portal ([docs](https://help.konfhub.com/eventdashboard/exhibitor-portal.md)) adds listings, tasks and assets. Our sponsorship flow stops once the sponsor has paid.

### 11.1 Tracer bullet: scan a lead

- `Sponsor Lead` doctype (sponsor, ticket, notes, captured by). Sponsor contacts get a "Scan leads" page under `/b/account/sponsorships/<id>` reusing the QR scanner component; scanning shows the attendee's name and company (only fields the attendee consented to share).
- CSV download of leads for the sponsor.
- Tests: only the sponsor's staff can scan and read their leads.

### 11.2 Consent

- A booking-form checkbox "Share my details with sponsors I visit"; scans without consent record the visit but not contact details.

---

## Phase 12: Later

Large or speculative; spec separately when a customer asks.

- **Hybrid events.** Add `Hybrid` to `Buzz Event.medium`, showing venue and join link together.
- **Engagement.** Live polls and Q&A per session, session ratings. KonfHub bundles these into a Gold-only event app with AI matchmaking ([event app](https://help.konfhub.com/apps/event-app.md)).
- **Bulk upload.** CSV import of attendees onto a free or offline ticket type.
- **PWA.** Manifest and install prompt for the dashboard, building on the Phase 2 service worker.
- **Not planned.** AI face check-in and AI photo galleries ([gallery](https://help.konfhub.com/apps/ai-photo-gallery.md)) are differentiators for KonfHub's Gold tier, not gaps organisers raise with us.

## Open questions

- WhatsApp provider: Meta Cloud API directly, or a BSP such as Gupshup or Interakt for easier template approval?
- GST invoices: should invoice numbering live on the team or on a linked ERPNext company when one exists?
- Offline check-in: is IndexedDB caching of attendee names acceptable for privacy on shared volunteer phones, or should it cache ticket IDs only?
- Should any of these be gated per plan, the way KonfHub tiers them, or is everything available to every team?

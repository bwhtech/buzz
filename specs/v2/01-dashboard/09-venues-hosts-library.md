# 09 — Venues & hosts library

| Phase | Depends on | Status |
|---|---|---|
| D | 01-dashboard/01 | Draft |

## Goal

Team-level reusable resources get a sidebar home: `/manage/venues` and `/manage/hosts` — the
"Library" section. Unblocks fully-Desk-free event creation (Overview's venue/host Links need
somewhere to create entries).

## Demo criteria (definition of done)

Manager creates a venue and a host from the library; both are selectable in the event Overview
form; host logo renders on the public page.

## Scope

### In
- Venues page: CRUD on `Event Venue` (team-scoped)
- Hosts page: CRUD on `Event Host` incl. `social_media_links` child rows
### Out (deferred to)
- `Event Category` management — global taxonomy, stays Desk/System Manager
- Public host profile pages → future "public event frontend" pillar

## Backend changes

None (team field + hooks from 00-teams cover both doctypes).

## Frontend changes

- Sidebar: enable "Venues" (`lucide-map-pin`) and "Hosts" (`lucide-users`) under a "Library"
  `SidebarGroup`.
- `src/pages/manage/VenuesList.vue` — `List`: name, `type` Badge (per Select options), `address`
  excerpt. `VenueDialog`: name (doc name/title), `type` Select, `address` Textarea,
  `google_maps_embed_code` Code textarea (collapsed "Advanced" section), `latitude`/`longitude`.
- `src/pages/manage/HostsList.vue` — card grid (logo `Avatar`, name, `by_line`). `HostDialog`:
  name, `logo` FileUploader, `by_line`, `about` (`Editor`), `country`, `address`,
  `social_media_links` child editor (platform Select + URL rows).
- `data/venues.ts`, `data/hosts.ts`.

## API contract

No new endpoints.

## Permissions notes

Manager+ CRUD; Viewer read-only. Link fields in Overview (step 03) automatically list only the
team's venues/hosts thanks to query conditions applying to link searches.

## Demo script

1. `/manage/venues` → create "Community Hall", type + address → appears.
2. `/manage/hosts` → create host with logo + 2 social links.
3. Event Overview → venue/host selectable; save → public page shows host block.
4. Other team's manager sees neither entry in their library or link searches.

## Acceptance criteria (merge gate)

### Automated tests
None new — team-direct doctypes covered by `test_team_permissions` parametrized cases
(`Event Venue`, `Event Host` list isolation + role matrix).

### Browser checks (agent-browser, dev server :8080)
1. `/dashboard/manage/venues` → create "Community Hall" (type, address) → row appears.
2. `/dashboard/manage/hosts` → create host with logo + 2 social links → card renders logo.
3. Event Overview → venue Link search returns "Community Hall"; host Link returns the new host;
   save → public page shows host block.
4. Team-B manager session → venues/hosts lists empty of team A's entries; Overview Link search
   does not surface them (link-query scoping check).
5. Viewer-role member → library pages read-only (no New button).

## Dependencies & risks

- `Event Venue` uses the document name as its title (no separate name field) — dialog maps the
  name input accordingly (rename on edit uses `frappe.rename_doc` semantics; keep name immutable
  in UI, edit only other fields, to avoid rename complexity).

# 11 — Event templates

| Phase | Depends on | Status |
|---|---|---|
| D | 01-dashboard/02 | Draft |

## Goal

`Event Template` manageable from the dashboard and "New event from template" — repeat organizers
spin up configured events in one step.

## Demo criteria (definition of done)

Manager creates a template with 2 ticket types and 1 add-on; "New Event" dialog with that template
produces an event with those ticket types/add-ons pre-created.

## Scope

### In
- `/manage/templates` list + template editor (children: `template_ticket_types`,
  `template_add_ons`, `template_custom_fields`)
- Template picker in the New Event dialog + instantiation endpoint
### Out (deferred to)
- Template sharing across teams — templates are team-scoped like everything else

## Backend changes

`buzz/api/templates.py` (new):

```python
@frappe.whitelist()
def create_event_from_template(template: str, title: str, start_date: str, end_date: str | None = None) -> dict:
    """Creates Buzz Event copying template fields (category, medium, banner_image, host, venue,
    guest-booking config, tax config, email/deck config) + Event Ticket Type and Ticket Add-on
    records from the template child tables. Team from active team; Manager+.
    Audit event_template.py first — reuse existing instantiation logic if present."""
```

## Frontend changes

- Sidebar: enable "Templates" (`lucide-layout-template`).
- `src/pages/manage/TemplatesList.vue` — `List`: `template_name`, category, medium, counts of
  child rows.
- `src/pages/manage/TemplateEditor.vue` (route `/manage/templates/:id`) — sectioned form mirroring
  the doctype: basics (`template_name`, `category`, `medium`, `banner_image`, `host`, `venue`),
  booking config (`allow_guest_booking`, `guest_verification_method`), content
  (`short_description`, `about` Editor), tax (`apply_tax`, `tax_label`, `tax_percentage`),
  emails (`send_ticket_email`, `ticket_email_template`, sponsor deck fields), children as
  sectioned lists: ticket types (title/price/qty rows), add-ons, custom fields.
- `NewEventDialog` (step 01): optional "Start from template" `Select`; when set → calls
  `create_event_from_template` instead of plain insert.
- `data/templates.ts`.

## API contract

| Endpoint | Method | Params | Returns | Auth |
|---|---|---|---|---|
| `buzz.api.templates.create_event_from_template` | POST | `template, title, start_date, end_date?` | `{event}` | team Manager+ |

## Permissions notes

Templates team-scoped (00-teams/02 team-direct doctype). Manager+ CRUD.

## Demo script

1. Create template "Monthly Meetup" with 2 ticket types + 1 add-on.
2. New Event → pick template, title "July Meetup", date → created.
3. Workspace Tickets tab shows both ticket types; Add-ons shows the add-on.
4. Public page bookable immediately after publish.

## Acceptance criteria (merge gate)

### Automated tests — `buzz/tests/test_event_templates.py` (new)
`bench --site buzz.localhost run-tests --module buzz.tests.test_event_templates`
- `create_event_from_template`: template with 2 ticket types + 1 add-on + 1 custom field →
  event created copying scalar config (category, medium, tax, email settings) and children as
  real `Event Ticket Type`/`Ticket Add-on`/`Buzz Custom Field` rows with `event` + `team` stamped.
- Cross-team template use raises; Viewer caller raises.
- Template with empty children → event still created cleanly.

### Browser checks (agent-browser, dev server :8080)
1. `/dashboard/manage/templates` → create "Monthly Meetup" with 2 ticket types + 1 add-on in the
   editor → counts show in list.
2. Events list → "New Event" → pick the template, title "July Meetup", date → created; workspace
   Tickets tab shows both ticket types, Add-ons shows the add-on.
3. Publish → public page bookable with the template's ticket types.
4. Team-B manager → templates list does not contain team A's template.

## Dependencies & risks

- Instantiation copies must stamp `event` + let the team cascade stamp `team` — verify no
  `ignore_permissions` needed (creator is Manager+).

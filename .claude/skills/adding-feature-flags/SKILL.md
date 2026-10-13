---
name: adding-feature-flags
description: How per-team feature flags work in Buzz — a `feature_` Check field on Buzz Team Settings at permlevel 1, read with is_feature_enabled() on the server and isFeatureEnabled() in the dashboard. Use whenever the user says "feature flag", "put X behind a flag", "gate X per team", "only some teams should get X", or "turn X on for a team".
---

# Adding a feature flag

A feature flag is a `Check` field on **Buzz Team Settings** whose fieldname starts with
`feature_`. Adding the field adds the flag. There is no registry to keep in sync.

The flag is at `permlevel: 1`. System Manager writes it and Event Manager only reads it,
so a team cannot turn a feature on for itself.

Existing flags to copy: `feature_paid_events` (Event Ticket Type) and
`feature_multiple_locations` (Event Venue).

## 1. The field

In `buzz/events/doctype/buzz_team_settings/buzz_team_settings.json`, add the field to the
**Feature Flags** tab (after `flags_tab`, before `communications_tab`), and bump `modified`:

```json
{
 "default": "0",
 "description": "What turning it on allows, in one sentence.",
 "fieldname": "feature_<name>",
 "fieldtype": "Check",
 "label": "<Name>",
 "permlevel": 1
}
```

Default off. `test_every_flag_is_a_restricted_check_field` fails if the field is not a
Check at permlevel 1 or more. Run `bench --site buzz.localhost migrate`.

## 2. The server gate

Keep the flag name as a constant beside the code it gates, and check it in the doctype
controller, so Desk, the API and imports all hit the same rule:

```python
from buzz.events.doctype.buzz_team_settings.buzz_team_settings import is_feature_enabled

MULTIPLE_LOCATIONS_FLAG = "feature_multiple_locations"

def validate_multiple_locations_enabled(self):
	before = self.get_doc_before_save()
	if not self.team or (before and before.has_multiple_locations):
		return
	if not is_feature_enabled(self.team, MULTIPLE_LOCATIONS_FLAG):
		frappe.throw(_("Multiple locations are not enabled for this team. Contact your administrator."))
```

- Gate only the switch *into* the feature. Records that already use it stay editable.
- `is_feature_enabled` throws on an unknown flag, so a typo never reads as "off".
- `feature_flags(team)` returns every flag as a dict.

## 3. The dashboard

`get_my_teams` already returns each team's `feature_flags`. Read them with
`isFeatureEnabled` from `@/data/teams` for the current team. No new API call is needed:

```ts
import { isFeatureEnabled } from "@/data/teams"

const canPickMultiple = computed(() => isFeatureEnabled("feature_multiple_locations"))
```

When the page is about an event that may belong to a team other than the current one,
return a bool from that page's API instead (`paid_events_enabled` on
`get_event_ticket_types`).

Hide the control when the flag is off. When the record already uses the feature, keep
the control.

## 4. Tests

- `BuzzTeamFactory.create_owned_by` turns every flag on, so existing tests keep working.
  Add the new constant to its `set_settings` call in
  `buzz/tests/factories/buzz_team_factory.py`.
- One gate test turns the flag off. The team is usually shared by the class, so restore
  it with `addCleanup`:

```python
self.addCleanup(BuzzTeamFactory.set_settings, self.team, {MULTIPLE_LOCATIONS_FLAG: 1})
BuzzTeamFactory.set_settings(self.team, {MULTIPLE_LOCATIONS_FLAG: 0})
self.assertRaises(frappe.ValidationError, new_record.insert)
```

- If the shared Administrator test team or the e2e team uses the feature, turn the flag
  on in `buzz/install.py` (`setup_test_records`) or in `e2e/helpers/frappe.ts`.

## Turning a flag on for a team

As System Manager, open the team's **Buzz Team Settings** in Desk, go to the **Feature
Flags** tab, and tick the flag.

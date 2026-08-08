# Buzz — project memory

## Theme system (buzz/theme/ + buzz/themes/)

Ported from the standalone `frappe_themes` + `buzz_themes` apps into buzz.
Jinja-only: there is no SPA/Vue theming and `dashboard/` is not involved.

### Layout — two directories one letter apart, both load-bearing

    buzz/theme/          engine. Module path for module "Theme".
                         theme_resolver.py, jinja_helpers.py, doctype/,
                         buzz_theme/ (exported theme records).
    buzz/themes/<slug>/  theme content. APP path, because get_theme_dir()
                         joins frappe.get_app_path("buzz") + "themes".
    buzz/public/themes/<slug> -> ../../themes/<slug>   SYMLINK.

The symlink is how theme CSS/JS is served at `/assets/buzz/themes/<slug>/...`.
Without it every theme asset 404s with no useful error.

### Theme resolution order

    1. ?preview_theme=<name>        developer_mode only
    2. Buzz Event.theme             routes that capture an `event_route` group
    3. Buzz Settings.default_theme  everything else
    4. nothing -> renderer declines, normal Frappe routing

With `default_theme` unset the whole engine is inert. That is the safety valve:
nothing themed can break the site until someone selects a default.

`can_render()` must match the route BEFORE resolving the theme — the event is
only known once `event_route` has been captured. Do not "simplify" it back to
resolving the theme first.

### Gotchas paid for the hard way

**Jinja methods share one global namespace keyed by FUNCTION NAME.**
`frappe/utils/jinja.py:247` does `out[function_name] = obj`, last app wins. Buzz
originally shipped `theme_asset_url`, the same name `frappe_themes` uses, so on
any site with both installed buzz silently lost and every themed page rendered
with empty `href`/`src`. Helpers are now `buzz_theme_asset_url` /
`buzz_theme_config`. Never give a jinja method a name another app might use.

**A template that `{% extends %}` discards top-level OUTPUT nodes.**
`{{ frappe.throw(...) }}` at the top of an extending page never executes —
only statements (`{% set %}`) run. The not-found guards silently did nothing,
execution continued into `frappe.get_cached_doc("Buzz Event", None)`, and the
resulting `DoesNotExistError` (which carries a `doctype`) was converted by
`@handle_does_not_exist_error` into **403 Not Permitted for guests** instead of
404. Guards are now `{% set not_found = frappe.throw(...) %}`.

**Adding a module to an already-installed app needs a Module Def by hand.**
`add_module_defs()` runs only at install (`frappe/installer.py:724`), never on
migrate. Until the Module Def exists, `sync_for()` skips the module entirely and
the doctypes are silently not created. Fix:
`bench --site <site> execute frappe.installer.add_module_defs --kwargs "{'app':'buzz','ignore_if_duplicate':True}"`
then migrate.

**Records of a custom doctype do not auto-import on migrate.**
`get_doc_files()` walks a fixed list plus whatever is in the
`importable_doctypes` hook (`frappe/model/sync.py:151`). The module folder is
otherwise an EXPORT target only. `importable_doctypes = ["Buzz Theme"]` in
hooks.py is what ships the bundled themes as records.

**DocType names are globally unique — a module does not namespace them.**
Hence Buzz Theme / Buzz Theme Settings / Buzz Themed Route rather than reusing
frappe_themes' names. Renaming the doctype without renaming the
`.py`/`.json`/`.js` files and the controller class fails at RUNTIME with
ImportError, not at migrate time: `frappe/modules/utils.py:328` derives the
import path and `base_document.py:147` derives the class from the doctype name.

**`bench execute --kwargs` uses `eval`, not JSON** — pass Python literals
(`True`, not `true`).

### Route table

Ships via the idempotent patch `buzz.patches.seed_buzz_theme_routes`
(`^$`, `^home$`, `^events$`, `^events/<event_route>$`, `^category/<category_slug>$`).
`dynamic_pages_enabled` is on, so any `pages/<request-path>.html` in the active
theme chain is servable — a theme shipping `pages/b.html` WOULD hijack the SPA
at `/b`. No bundled theme does.

`^events$` -> `pages/events.html` is seeded but NO bundled theme ships that
page, so the route is dead until one does. It is harmless: `can_render()`
declines when the template is missing.

### Bundled themes

Three, all complete: `buzz_events_theme` (ticket stub), `sketchbook_theme`
(handwritten, ruled paper), `stickerpack_theme` (neo-brutalist — dot-grid
ground, 3px borders with 4px offset shadows, accent-cycled rotated cards).

`stickerpack_theme` was ported from a static prototype at
`hobby/ui/buzz_implementation/themes/stickerpack`. Two things that do not
survive such a port: the prototype registered `accent_bg`/`accent_fg`/
`rot_class` as Python globals in its own `render.py` (Frappe's Jinja has no
equivalent — they live in `components/macros/accents.html` here), and it
loaded Tailwind from the Play CDN (built locally here). Its category filter
chips were NOT ported.

An earlier `events_theme` was deleted: it shipped pages that `{% extends %}`
a `base.html` it did not contain, so it could never render standalone.
Deleting a theme means three places, not one: the folder, the
`public/themes/<slug>` symlink, AND the fixture folder — plus the DB record,
which survives a migrate because removing a fixture never deletes an
already-imported doc.

Theme templates query buzz doctypes directly in Jinja and ship no page
controllers, though the engine supports sibling `.py` controllers per page.
Each theme builds its own CSS: `yarn build:css` (Tailwind v4) inside the folder.
Theme JS/CSS is excluded from prettier+eslint in `.pre-commit-config.yaml`
alongside the other vendored bundles.

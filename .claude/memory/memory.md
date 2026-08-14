# Buzz — project memory

## Theme system

Ported from the standalone `frappe_themes` + `buzz_themes` apps into buzz; both were
then uninstalled. Jinja-only — no SPA/Vue theming, `dashboard/` is not involved.

### Layout

    buzz/buzz_themes/           engine. Module path for module "Buzz Themes".
                                theme_resolver.py, jinja_helpers.py, doctype/,
                                buzz_theme/ (exported theme records), tests/
    buzz/themes/<slug>/         PRIVATE templates: components/, pages/,
                                styles/tokens.css, tailwind.input.css
    buzz/public/themes/<slug>/  PUBLIC, real directories: tailwind.output.css,
                                scripts/, images/

The private/public split is load-bearing. These were once symlinks from public ->
private, which served the raw Jinja at `/assets/buzz/themes/<slug>/pages/...` —
data model, filters and all. Never symlink them back.

One toolchain at `buzz/themes/package.json` builds all three CSS outputs. Each
build must `cd` into its own theme dir: running them from `buzz/themes/` changes
Tailwind v4's source-detection root and every theme absorbs the others' utilities.

### Inheritance — the dedup mechanism

`Buzz Base Theme` owns the shared assets (alpine/lucide vendor JS, theme.js,
components.js, images/placeholder.svg). The three real themes set
`parent_theme = "Buzz Base Theme"`. `buzz_theme_asset_url()` walks the chain
child-first and returns the first theme that HAS the file, so a child overrides by
shipping the same relative path. This removed 1.12 MiB of byte-identical blobs.

### Theme resolution — one theme per site

    1. ?preview_theme=<name>            developer_mode only
    2. Buzz Settings.default_theme
    3. nothing -> renderer declines, normal Frappe routing

Per-event theming existed briefly and was removed on purpose: a listing page and
the events it linked to rendered in different design languages, so clicking a card
changed the design mid-journey. Hosted platforms attach the theme to the organizer
and let an event vary only content. Do not reintroduce `Buzz Event.theme`.

With `default_theme` unset the engine is inert — the safety valve.

### Configuration — nothing about identity is hardcoded

Brand and footer come from Frappe's own **Website Settings**: `app_name`,
`app_logo`, `brand_html`, `banner_image`, `footer_logo`, `copyright`, `address`,
`footer_items` (links AND socials — no bespoke social fields). `build_base_context`
calls `get_website_settings()`; without it themed pages render missing the
site-wide context Frappe's own renderers provide.

Per-theme presentational copy lives in a Single per theme (`Stickerpack Theme
Settings`, `Buzz Events Theme Settings`, `Sketchbook Theme Settings`), linked from
`Buzz Theme.theme_settings` and read in templates via `buzz_theme_config()`. Every
field falls back to the original literal so a blank never renders an empty heading.

### Gotchas paid for the hard way

**A fixture whose `modified` is not newer than the DB row is SILENTLY SKIPPED.**
Editing `buzz/buzz_themes/buzz_theme/<slug>/<slug>.json` does nothing until you also
bump `modified`. Cost time three separate times.

**Records of a custom doctype do not import on migrate** unless the doctype is in
the `importable_doctypes` hook (`frappe/model/sync.py`). The module folder is an
EXPORT target only.

**Adding a module to an installed app needs a Module Def created by hand** —
`add_module_defs()` runs only at install, never on migrate. Until it exists,
`sync_for()` skips the module and the doctypes are silently not created.

**Jinja methods share one global namespace keyed by FUNCTION NAME**
(`frappe/utils/jinja.py`, `out[function_name] = obj`, last app wins). Buzz's helpers
are `buzz_theme_asset_url` / `buzz_theme_config` because the unprefixed names lost
to `frappe_themes` and every page rendered with empty asset URLs — a silent failure
that looks like broken CSS, not an error.

**A template that `{% extends %}` discards top-level OUTPUT nodes.**
`{{ frappe.throw(...) }}` at the top of an extending page never runs; only `{% set %}`
does. The not-found guards silently did nothing and a missing event fell through to
`get_cached_doc(..., None)`, whose `DoesNotExistError` became **403 for guests**.
Guards must be `{% set not_found = frappe.throw(...) %}`.

**`(some_time|string)[:5]` is wrong.** Time fields are `timedelta`; `str()` gives
`9:00:00` unpadded, so the slice renders `9:00:`. Use
`frappe.utils.get_time(x).strftime('%H:%M')`.

**`free_webinar` no longer exists** — `buzz.patches.rename_free_webinar_to_free_event`
renamed it to `free_event`, and `free_event` is a PRICING flag, not a delivery mode.
"Is this a webinar" is `medium == "Online"`.

**Website Settings `address` arrives on the context as `footer_address`**, and
`get_website_settings()` already sets `context.boot` — don't call `get_boot_data()`
again.

**DocType names are globally unique; a module does not namespace them.** Hence
`Buzz Theme` / `Buzz Theme Settings` / `Buzz Themed Route`. Renaming a doctype
without renaming its `.py`/`.json`/`.js` and controller class fails at RUNTIME with
ImportError, not at migrate — it passes a migration and breaks on first page load.

**`bench execute --kwargs` uses `eval`** — pass Python literals (`True`, not `true`).

### Routes

Seeded by `buzz.patches.seed_buzz_theme_routes`: `^$`, `^home$`, `^events$`,
`^events/<event_route>$`, `^category/<category_slug>$`. `^events$` is dead — no
bundled theme ships `pages/events.html`.

`dynamic_pages_enabled` is on, so any `pages/<request-path>.html` is servable.
`RESERVED_PATH_SEGMENTS` in `theme_resolver.py` stops a theme hijacking `/login`,
`/app`, `/api`, `/b` etc — page_renderer hooks run BEFORE Frappe's own renderers
(`frappe/website/path_resolver.py`).

### Bundled themes

`buzz_default_theme` (dark/light minimal, ported from the Builder pages),
`buzz_events_theme` (ticket stub), `sketchbook_theme` (handwritten, ruled paper),
`stickerpack_theme` (neo-brutalist). All inherit `Buzz Base Theme`.

`buzz_default_theme` takes its palette from **frappe-ui's own semantic tokens** —
resolved out of `dashboard/node_modules/frappe-ui/tailwind/generated/colors.json`
(`themedVariables.light/dark` -> surface / ink / outline) and written into
`styles/tokens.css` as CSS variables. That is why themed pages and the Vue
dashboard share one grey ramp; re-resolve from that JSON rather than eyeballing
hexes if frappe-ui bumps its tokens.

**`tokens.css` is imported UNLAYERED, so every rule in it beats every Tailwind
utility — specificity is irrelevant.** `@import "tailwindcss"` declares
`@layer theme, base, components, utilities`; an unlayered rule outranks all of
them. So a bare `.card { background: ... }` silently wins over `bg-*` in the
markup, and `a.card { display: block }` beat `.flex` (this looked like a
specificity bug and was misdiagnosed as one). Wrap the component half of every
theme's tokens.css in `@layer components { ... }`, leaving only the `:root` /
`html[data-theme]` variable blocks unlayered. Verify with:
`python3 -c "css=open('tailwind.output.css').read(); i=css.find('.card{'); print(css[:i].count('{')-css[:i].count('}'))"`
— 1 means layered, 0 means it will override your markup.

Only `buzz_default_theme` is layered so far; the other three themes still have
this latent.

Venue maps use `openstreetmap.org/export/embed.html` (keyless, needs a bbox).
The old `staticmap.openstreetmap.de` is NXDOMAIN — that service was withdrawn.

Theme JS/CSS is excluded from prettier+eslint in `.pre-commit-config.yaml`, and
`buzz/public/themes/` had to be added there when the scripts moved out of
`buzz/themes/`.

## Environment

`gh` holds two accounts; only **Rl0007** can push to `buildwithhussain/buzz`. If a
push 403s as `ghostinmyterminal`, run `gh auth switch --user Rl0007`.

`apps/builder` has an UNCOMMITTED local fix: it imported `POSTHOG_HOST_FIELD` /
`POSTHOG_PROJECT_FIELD`, which frappe deleted in `2a48f956bf`, and that broke
`/desk` and `/app` with a 500 for every logged-in user. The repo has no `origin`,
so any update to builder silently re-breaks the desk the same way.

buzz.localhost admin password is `admin`.

# Site Management

## Finding existing sites

```bash
ls sites/
```

Ignore these entries: `assets`, `apps.txt`, `common_site_config.json`, `currentsite.txt`. Everything else is a site directory.

## Matching a site to an app

Convention: site name often contains the app name (e.g. `gameplan.localhost` for app `gameplan`).

To confirm which apps are on a site:
```bash
bench --site <site> list-apps
```

If multiple sites exist, check each until you find the one with the target app installed.

## Creating a new site

First, check if `root_password` is already set in `sites/common_site_config.json`. If not, recommend the user set it once so future site creation doesn't require the password each time:

```bash
bench set-config -g root_password '<pwd>'
```

Then create the site:

```bash
# If root_password is in common_site_config.json:
bench new-site <name>.localhost --admin-password admin

# Otherwise, pass it explicitly:
bench new-site <name>.localhost --db-root-password '<pwd>' --admin-password admin
```

Naming convention: `<app-name>.localhost` (e.g. `expense_tracker.localhost`).

## Other site commands

See [bench-operations.md](./bench-operations.md). Ask the user before you drop a site.

## Site config

Per-site config lives in `sites/<site>/site_config.json`. Global config in `sites/common_site_config.json`.

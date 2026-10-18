---
name: syncing-buzz-docs
description: Use when the Buzz user docs on docs.bwh.tech may be behind the app — after features land on develop, when asked to update, check or sync the Buzz wiki, to document a new dashboard feature, or to refresh docs screenshots and walkthrough videos.
---

# Syncing Buzz docs

The Buzz docs live in the wiki space `5jbt24ja3l` (`/buzz`) on docs.bwh.tech, frappectl profile
`bwh_docs`. The code on `upstream/develop` is the source of truth: docs follow it, never the
reverse.

**REQUIRED SUB-SKILL:** frappe-wiki-skill (`apps/wiki/skills/frappe-wiki-skill`) for every
wiki read and write. Below, `wikictl` is
`python3 ../wiki/skills/frappe-wiki-skill/scripts/wikictl.py`, run from `apps/buzz`.

## Rules

- Change no app code. Log app bugs you find in `wiki-media/CONTEXT.md`.
- Document the dashboard (`/b/...`) and public pages only. No Desk steps, `/app` paths,
  Desk screenshots or doctype names. A feature with no dashboard screen stays out, or gets
  one line ("ask your site administrator").
- Write in Simplified Technical English, matching the pages already there. Name UI controls
  in bold, exactly as the UI spells them.
- Publish only when the user says you may approve your own changes. Otherwise stop at
  `publish` without `--yes` and hand over the change list.

## Workflow

All working files live in `apps/buzz/wiki-media/` (gitignored). Read `CONTEXT.md` first: its
status table names the develop SHA the docs last matched.

1. **Find the gap.** `git fetch upstream develop`, then
   `git log --format='%h %s%n%b' <last-sha>..upstream/develop`. Skip test, ci and chore
   commits. List the user-visible changes per docs page.
2. **Run develop locally.** Check out `develop` level with `upstream/develop`, run
   `bench build --app buzz`, then from `wiki-media/` run `../../../env/bin/python seed_demo.py`
   and `../../../env/bin/python seed_event.py`. `seed_event.py` rebuilds Acme Product Summit; extend it
   when a feature needs demo data.
3. **Pull the docs.** `wikictl cr new buzz -t "Docs: sync to develop <sha>"`, export
   `WIKI_CR`, delete `wiki-media/docs`, then `wikictl pull wiki-media/docs`.
4. **Read the real UI.** `node explore.mjs` dumps each screen's text and a screenshot to
   `explore/`. `explore_drawers.mjs` and `explore_checkout.mjs` open drawers, menus and the
   booking steps. Confirm every label you write against these dumps or the Vue source.
5. **Edit pages** in `wiki-media/docs/`. A new page needs `order:` in its front matter, or
   it lands last in its group.
6. **Media.** Add scenes to `stills.mjs` / `stills_attendee.mjs`, run them, review a contact
   sheet (`../../../env/bin/python sheet.py out.png shots/*.png`), then `bash to_webp.sh` and
   `frappectl -s bwh_docs file upload ./_upload_v2/<file>.webp`. Videos: `node record.mjs
   <scene> --shots` to dry-run, reseed, then record for real. Review frames with ffmpeg
   before upload.
7. **Publish.** `wikictl sync wiki-media/docs -n`, then `sync`, then `publish --yes`. Check
   every `/files/...` and `/buzz/...` link with curl.
8. **Record state.** Add a row to the `CONTEXT.md` status table with the CR and the develop
   SHA.

## Gotchas

| Symptom | Fix |
|---|---|
| New page 404s at `/buzz/<slug>` | Routes here are flat. After merge, `wikictl set <group>/<slug> route=buzz/<slug>` in a new CR and publish. |
| Uploaded file comes back as `name<hash>.webp` | A file with that name exists. Never reuse a name: add `-v2`, `-v3`, and update the reference. |
| Check-in video says "No ticket matches this code" | The fake camera holds an old ticket. `../../../env/bin/python make_camera.py <ticket> _review/camera.y4m` after each reseed. |
| Video ends on an "already checked in" toast | The fake camera keeps scanning. Trim with `ffmpeg -t <seconds>`. |
| A dry run left data behind (accepted talk, new event) | `--shots` still clicks. Reseed before the real recording. |
| Price fields missing on Registration | The team lacks `feature_paid_events`. `seed_event.py` turns it on. |
| `grep '__('` finds nothing; zsh "no matches found" | Use `grep -F` for `__(`, and quote `--include` globs. |
| Full-page screenshot shows only the viewport | The dashboard scrolls an inner pane. Clip to the section's bounding box instead. |

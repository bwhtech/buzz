# Changelog

All notable changes to Buzz are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Release lines

- **`main` — 1.x (stable).** The supported release line. Fixes and self-contained
  features are merged to `develop` first and cherry-picked here with a
  `backport main` label.
- **`develop` — 2.x (beta).** Where the next major lands, including team-based
  multi-tenancy. Not yet released.

## [1.1.0] - 2026-08-06

### Breaking

- The dashboard has been migrated to **frappe-ui v1 and Vite 8** ([#283]). The
  dashboard build and any downstream customisation of dashboard components are
  affected — component imports, prop names and build output paths changed with the
  frappe-ui major. Rebuild the dashboard (`yarn build`) after upgrading. There is
  no change to the Python API surface or to any DocType schema, so no data
  migration is required for this release.

### Added

- Buzz Events can be backed by **Zoom Meetings**, creating the meeting and
  registering attendees through the optional `zoom_integration` app ([#292]).
- A **Buzz workspace dashboard** with charts and number cards ([#314]).
- Speakers can now see and edit their own talk proposals ([#276]).
- Buzz Event stores a short timezone label for display ([#282]).
- Event End Date is autofilled from Start Date and bounded by it ([#316]).

### Changed

- `buzz/api` is split into typed domain packages, with pydantic request/response
  schemas, service classes and enforced type annotations on whitelisted
  methods ([#307]).
- The phone field uses the `PhoneInput` component instead of a plain
  `FormControl` ([#290]).
- README hero revamped with logo and badges ([#285]).

### Fixed

- Accepting a talk proposal now asks for confirmation first ([#309]).
- "To" is prefilled when composing email on proposal doctypes ([#294]).
- Resolved semgrep blocking findings reported by the full-repo scan ([#281]).

### CI

- Fixed merge-queue trigger gaps; CI now runs on both `develop` and `main` ([#279]).

## [1.0.0] - 2026-07-21

Initial tagged release.

[#276]: https://github.com/bwhtech/buzz/pull/276
[#279]: https://github.com/bwhtech/buzz/pull/279
[#281]: https://github.com/bwhtech/buzz/pull/281
[#282]: https://github.com/bwhtech/buzz/pull/282
[#283]: https://github.com/bwhtech/buzz/pull/283
[#285]: https://github.com/bwhtech/buzz/pull/285
[#290]: https://github.com/bwhtech/buzz/pull/290
[#292]: https://github.com/bwhtech/buzz/pull/292
[#294]: https://github.com/bwhtech/buzz/pull/294
[#307]: https://github.com/bwhtech/buzz/pull/307
[#309]: https://github.com/bwhtech/buzz/pull/309
[#314]: https://github.com/bwhtech/buzz/pull/314
[#316]: https://github.com/bwhtech/buzz/pull/316
[1.1.0]: https://github.com/bwhtech/buzz/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/bwhtech/buzz/releases/tag/v1.0.0

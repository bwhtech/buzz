
<div align="center" markdown="1">

<a href="https://github.com/BuildWithHussain/buzz">
  <img src=".github/images/buzz-logo.png" height="90" alt="Buzz logo">
</a>

<h1>Buzz</h1>

**Open source, self-hosted event management platform.**<br>
Tickets, add-ons, sponsorships, check-ins, and attendee self-service — all driven by a single **Buzz Event**.

[![CI](https://github.com/BuildWithHussain/buzz/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/BuildWithHussain/buzz/actions/workflows/ci.yml)
[![UI Tests](https://github.com/BuildWithHussain/buzz/actions/workflows/ui-tests.yml/badge.svg?branch=main)](https://github.com/BuildWithHussain/buzz/actions/workflows/ui-tests.yml)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![GitHub commit activity](https://img.shields.io/github/commit-activity/m/BuildWithHussain/buzz)](https://github.com/BuildWithHussain/buzz/commits/main)
[![GitHub stars](https://img.shields.io/github/stars/BuildWithHussain/buzz?style=social)](https://github.com/BuildWithHussain/buzz/stargazers)

<a href="#installation">Installation</a> · <a href="./ARCHITECTURE.md">Architecture</a> · <a href="https://t.me/bwh_buzz">Telegram Group</a>

</div>

![Buzz Event DocType](.github/images/fe-event-main-form.png)

### Stack / Architecture

1. Frappe Framework: The Backend and Admin Interface
2. FrappeUI (based on Vue & TailwindCSS): For the frontend dashboard (for attendee, sponsors, etc.)
3. Frappe Builder: For the public pages like events list and details page.

### The Main Entity

The **Buzz Event** DocType/Form is the primary entity of the system. Once you have created an event, you can setup ticket types, sponsorship tiers, add-ons (like T-Shirts, Meals, etc.), schedule, and much more!

### Features

This is not an exhaustive list by any means, just to give you an idea 😃

#### Dynamic Ticket & Add-on Types

![Dynamic Ticket Types and Add-ons](.github/images/ticket-types-and-add-ons.png)

#### The Booking Form

Once you have defined the proper ticket types, add-ons, and publish your event, the booking form will dynamically use it for booking.

![Booking Form](.github/images/booking-form.png)

#### Payments App Integration

This app depends on Frappe's Payments app for online payments. You can select a Payment Gateway in the event form. BTW GST collection is just a check-box away 😉

#### The Dashboard

![Booking Details Page](.github/images/booking-details-page.png)

#### Ticket Management

The benefits of having a "self-service" dashboard for attendees is that they can modify their bookings on their own (the deadlines can be configured from the **Buzz Settings**). For example, changing their T-Shirt Size after booking:

![Change Add-on Preference](.github/images/ticket-updates.png)

They can also transfer tickets or request for cancellation.

#### Sponsorship Management

Folks can enquire about sponsoring an event and upon approval from the event management team (from desk), they can directly pay from the dashboard too:

![Sponsorship Payment](.github/images/sponsorship-payment.png)

*As soon as they pay, their logo appears on the event page!*

![Sponsorship Management](.github/images/sponsorship-management.png)

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app BuildWithHussain/buzz --branch main
bench install-app buzz
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/buzz
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade
### CI

This app can use GitHub Actions for CI. The following workflows are configured:

- CI: Installs this app and runs unit tests on every push to `develop` branch.
- Linters: Runs [Frappe Semgrep Rules](https://github.com/frappe/semgrep-rules) and [pip-audit](https://pypi.org/project/pip-audit/) on every pull request.


### License

agpl-3.0

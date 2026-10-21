# Buzz Playground

The Buzz Playground lets a visitor try Buzz without an account. Each visitor gets a private sandbox for 24 hours. The sandbox has demo data and a checklist that walks through the main features.

## What a visitor gets

A visitor opens `/b/playground` and clicks **Start exploring**. Buzz then makes a sandbox with:

- Three users: an organizer, an attendee and a front desk user. The visitor starts as the organizer.
- A team with a conference, a free meetup and a past event. The conference has guests, talk proposals, a sponsorship tier and sponsor enquiries.
- A floating bar with the time left, **Inbox**, **View as**, **Reset** and **Create your real account**.
- A getting-started checklist. Each step switches to the correct user, opens the correct page and highlights the control to use.

Buzz does not send email from a playground site. It copies each email into the sandbox inbox instead. The visitor can read tickets, PDF attachments and calendar invites there.

An hourly job deletes each sandbox after 24 hours, with its users, events and files.

## Before you start

Use a separate site for the playground. Do not turn it on for a site with real data:

- The site sends no email at all.
- Public event listings show only the visitor's own sandbox.
- Each sandbox adds users and records to the site.

The site also needs:

- The scheduler turned on, for the hourly cleanup job.
- A payment gateway in test mode, so that visitors can book paid tickets.

## Site config keys

| Key | Value | Purpose |
| --- | --- | --- |
| `buzz_playground` | `1` | Turns on the playground. |
| `mute_emails` | `1` | Stops all outgoing email. The playground stays off without it. |
| `buzz_playground_signup_url` | URL | Optional. The target of **Create your real account**. |
| `throttle_user_limit` | `1000` | Lets the site create more than 60 users an hour. Each sandbox creates three users. |

Store the three flags as numbers, not strings. A string value for `throttle_user_limit` makes user creation fail.

## Turn on the playground with bench

1. Set the config keys. The `-p` flag stores each value as a number:

   ```bash
   bench --site <site> set-config -p buzz_playground 1
   bench --site <site> set-config -p mute_emails 1
   bench --site <site> set-config -p throttle_user_limit 1000
   bench --site <site> set-config buzz_playground_signup_url "https://example.com/signup"
   ```

2. Turn on the scheduler:

   ```bash
   bench --site <site> enable-scheduler
   ```

3. Open `https://<site>/b/playground` and click **Start exploring**.

## Turn on the playground on Frappe Cloud

1. Open the site in the Frappe Cloud dashboard.
2. Open the **Site Config** section.
3. Add `buzz_playground` with the value `1`. Set the type to **Number**.
4. Add `mute_emails` with the value `1`. Set the type to **Number**.
5. Add `throttle_user_limit` with the value `1000`. Set the type to **Number**.
6. Optional: add `buzz_playground_signup_url` with your signup URL. Set the type to **String**.
7. Save the config.
8. Open `https://<site>/b/playground` and click **Start exploring**.

Frappe Cloud runs the scheduler by default.

## What Buzz changes on the site

When a visitor starts a sandbox, Buzz changes two settings:

- It turns off **Store Attached PDF Document** in System Settings. The visitor cannot write to the email queue that this setting uses.
- It turns on **Enable Communities** in Buzz Settings, so that the visitor can create a community from `/community`.

On a playground site, every response also gets the header `X-Robots-Tag: noindex, nofollow`.

## Limits

- One IP address can start or reset 30 sandboxes an hour. Visitors at one event often share an IP address.
- The inbox shows the last 100 emails of a sandbox.

## Turn off the playground

1. Remove `buzz_playground` from the site config, or set it to `0`.
2. Remove `mute_emails` if the site must send email again.

Buzz cancels each captured email in the queue. The site does not send old playground email after you turn email back on.

The cleanup job runs only while the playground is on. Sandboxes that exist when you turn it off stay on the site. To remove them, first take down your links to `/b/playground`. Then leave the playground on for 24 hours, so that the cleanup job deletes the last sandboxes.

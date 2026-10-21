# Combined PR #25: rollout review

Updated 2026-10-21. This is preparation for an owner-approved deployment,
not approval to merge or deploy. The combined branch includes PRs #7-#57
and subsequent regression repairs. Do not deploy solely on this checklist.

## Deployment behavior, from the repository

`.github/workflows/deploy.yml` deploys every push to `main`. It pulls main,
stops and rebuilds Compose services, then runs `migrate` and `collectstatic`.
There is no staging gate in that workflow. Merging to main therefore has a
production effect. The workflow's success message alone does not establish
application health.

`docker-compose.yaml` starts the web service by running `compilemessages`,
then `collectstatic`, then Gunicorn. Translation compilation is already part
of startup. Do not run `makemessages` or edit translations on the server.
The Dockerfile's standalone CMD does not run that Compose startup sequence.

Postgres uses the `postgres_data` volume. Media and static files use host bind
mounts. Back up data separately from code.

## Required checks before any approved rollout

- Verify the exact reviewed head and its CI results. A fork workflow marked
  `action_required` is not a passing test run. It needs the repository owner's
  review/approval in Actions.
- Build and start the exact candidate in an isolated environment with GIS
  libraries and PostGIS. Do not merge into main to create this test build.
- Install dependencies from requirements alone. Allauth requires its
  `socialaccount` extra, including the Google provider's JWT dependency.
- Run `python manage.py check`, `python manage.py test`, and
  `python manage.py migrate --plan`. Then apply migrations to an isolated
  database and test startup again. `migrate --dry-run` is not a valid command.
- Run `collectstatic` with production-style settings and verify manifest URLs.
  A successful local collectstatic command is not a full Docker build.
- Verify the server environment independently. Settings require
  `DJANGO_SECRET_KEY`, `ALLOWED_HOSTS` (space-separated), database configuration,
  and `GOOGLE_MAPS_API_KEY`. A running site does not prove all new paths work.
  Build-only dummy keys in the Dockerfile are not production credentials.
- Inspect desktop/mobile pages and complete the relevant workflows, including
  authentication, language switching, search, favorites, place/photo submission,
  reviews, profile changes, blog content, and the mobile tutorial.
- Verify real Google/Kakao OAuth, Maps, Turnstile and prayer providers in a
  suitable authorized environment. Local fixtures or mocked responses do not
  certify those services. Native translation accuracy needs human review.

Local regression evidence and remaining gaps belong in the PR's latest report.
Older test counts and earlier green runs do not certify a newer head.

## Schema changes and backup

The batch includes Django 5.2 and allauth 65.14.1. Even where there are no new
project migration files, package migrations still apply. Allauth account
migrations through 0009 and socialaccount through 0006 must be reviewed against
the actual database's migration state.

Before an approved deployment, the operator should create and verify a database
dump, a media backup, the environment/configuration backup, and the exact current
commit. Verify restoration on an isolated database. Confirm backup destinations
exist, access is restricted, and the backups are not empty. Retain the pre-upgrade
backup until the upgraded application's important workflows are verified.

## After an approved deployment

Check the deployment logs and process health, not only the final workflow line.
Confirm migration state, static assets and compiled translations. Exercise home,
explore/map, detail/gallery/reviews, login/register/provider login, submission
and CAPTCHA, profile, blog, prayer and secondary pages. Repeat key flows at
mobile width. Check application errors and configured monitoring.

## Rollback requires both code and data planning

A code revert is not guaranteed to restore the earlier application's behavior
against an upgraded database. Do not reset or delete production data as a casual
rollback step. Choose the rollback procedure with the operator after examining
the schema/data changes and any writes made since deployment.

Allauth's email lowercasing and duplicate-primary-email normalization include
irreversible data changes (reverse operations are no-ops). Exact restoration
requires the verified pre-upgrade database backup and a plan for post-deploy
writes. Prior scratch-database migration reversal and old-code smoke tests are
limited evidence, not proof every old-code workflow is compatible.

Static manifests and compiled catalogs must match the selected code. Media
uploads must remain preserved. Validate the rollback in isolation before relying
on it for production recovery.

## Not verified by this document

The droplet's live environment, backup health, production provider credentials,
Cloudflare settings, monitoring delivery, and a complete container image build
are not established by reading repository files. Do not describe them as checked
without corresponding current evidence.

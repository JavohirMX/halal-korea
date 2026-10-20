# Rollout checklist: merging the combined PR (#25, PRs #8-#32)

How this site deploys today (verified against `.github/workflows/deploy.yml` and
`docker-compose.yaml` on main):

- Every push to `main` triggers the "Deploy to Droplet" GitHub Action, which SSHs
  to the droplet and runs, in `/home/jmx/halal-korea`:
  `git pull origin main` -> `docker-compose down` -> `docker-compose up -d --build`
  -> `docker-compose exec -T web python manage.py migrate`
  -> `docker-compose exec -T web python manage.py collectstatic --noinput`
- Postgres runs in the `db` compose service (`postgis/postgis:15-3.3`, named volume
  `postgres_data`). Media files are a bind mount (`./media`). Static files are a
  bind mount (`./staticfiles`). Env comes from `.env` on the server.
- Consequence: **merging #25 to main deploys immediately.** There is no staging
  gate in the pipeline, so do the checks below *before* merging.

## 0. What is in the batch (verified per-branch against `main`)

- **Migrations: NONE.** No PR in #8-#32 adds or alters a migration. Zero
  backward-compat/ordering risk from the batch itself.
  - Exception not from this batch: `main` already has an unmade migration,
    `utils/0004_alter_systemmetric_metric_type` (verified with
    `makemigrations --check --dry-run` on main). The deploy runs `migrate`, not
    `makemigrations`, so this pending change does nothing until someone commits it.
    Recommended: run `python manage.py makemigrations utils`, review the generated
    file, and commit it as its own tiny PR *before* this rollout (or explicitly
    leave it pending; it is pre-existing either way).
- **Settings changes:** #14 turns on `ManifestStaticFilesStorage` when
  `DEBUG=False` (fingerprinted static URLs - requires collectstatic, which the
  deploy already runs). #17 only registers the settings-backed Google OAuth app
  when credentials are actually set (no behavior change on a server where
  `GOOGLE_OAUTH_CLIENT_ID/SECRET` are already set or a SocialApp exists in admin).
- **Docker changes:** #10 and #14 change the gunicorn command (adds
  `--threads 4 --timeout 60 --graceful-timeout 30 --keep-alive 5 --max-requests 1000
  --max-requests-jitter 100`) and #14 makes the web container run collectstatic at
  container start. Both take effect via the normal `docker-compose up -d --build`.
- **CI:** #23 adds `.github/workflows/ci.yml`. The first workflow run on this repo
  needs a one-time "Approve and run" click on the Actions tab (fork-PR gate).
- **Dependencies:** unchanged. `requirements.txt` is untouched by every PR
  (verified). #32 uses Pillow, already pinned (`Pillow==11.3.0`). The Docker image
  already installs `gettext`, so `compilemessages`/`makemessages` work in the
  container.
- **Static/media:** #9 commits a prebuilt `static/css/tailwind.build.css`; #15
  commits a Font Awesome subset. Both are picked up by collectstatic. No media
  (user-uploaded) files are touched by any PR.

## 1. Required environment variables (verified in `config/settings.py`)

These have **no default** and the app crashes without them - confirm they are in
the server's `.env` before merging (they already are on the running site, this is
a sanity check):

- `DJANGO_SECRET_KEY`
- `ALLOWED_HOSTS` - **space-separated** (`settings.py` parses with `.split()`,
  not commas)
- `DB_NAME` `DB_USER` `DB_PASSWORD` `DB_HOST` (and `DB_PORT` if not 5432)
- `GOOGLE_MAPS_API_KEY`

No PR in the batch adds any new required env var. Optional ones the batch can use
if present: none required.

## 2. Backup (before merging)

On the droplet:

```bash
cd /home/jmx/halal-korea
docker-compose exec -T db pg_dump -U "$DB_USER" "$DB_NAME" | gzip > ~/backups/halal-pre-pr25-$(date +%Y%m%d-%H%M).sql.gz
ls -lh ~/backups/   # confirm the file exists and is non-trivial in size
tar czf ~/backups/media-pre-pr25-$(date +%Y%m%d-%H%M).tgz media/
git rev-parse HEAD > ~/backups/pre-pr25-commit.txt   # the exact commit to roll back to
```

(Restore if ever needed: `docker-compose down`, recreate the db volume or
`psql` the dump back in, redeploy the old commit.)

## 3. Staging / pre-merge verification (no staging server exists - do it locally)

There is no staging environment in this repo, so verify the exact merge result
locally before pushing to main:

```bash
git checkout main && git pull
git merge --no-ff combined/all-prs        # the exact tree that will deploy
docker-compose up -d --build              # or your local equivalent
python manage.py migrate --dry-run        # expect: no migrations to apply
python manage.py collectstatic --noinput
python manage.py test                     # 576 tests, all passing, as of #32
```

Browser smoke on that local build (see checklist in section 5).

## 4. Deploy (happens automatically on merge)

1. Merge #25 on GitHub (this deploys immediately via the Action).
2. Watch the Action run; confirm "Deployment completed successfully!".
3. One-time right after this deploy: compile the translations (the deploy does
   NOT run this, and #28/#30 add new msgids):

```bash
docker-compose exec web python manage.py makemessages -l ko -l uz   # or run locally and commit
# fill in the new ko/uz translations (~43 new strings), then:
docker-compose exec web python manage.py compilemessages
docker-compose restart web
```

   Until then the ~43 new strings fall back to English - safe, just untranslated.

## 5. Post-deploy smoke checks (5 minutes)

- [ ] Home `/` loads, place cards show photos, no unstyled page (if the page looks
      unstyled, collectstatic did not pick up `tailwind.build.css` - rerun it)
- [ ] `/explore/` loads, list + map render, distance sorting works
- [ ] One `/place/<id>/` detail page: gallery, reviews, canonical URL has no
      query string
- [ ] `/users/login/` renders (Google/Kakao buttons), login works
- [ ] Submit-place flow renders and the Turnstile widget appears
- [ ] `/blog/`, one blog post, `/prayer/`, `/prayer/ramadan/`, `/donate/`,
      `/about/`, `/legal/` all render
- [ ] Switch language to Korean and Uzbek: flash messages and new strings show
      translated (after step 4.3)
- [ ] Mobile width (~390px): no horizontal scroll on home/explore/place detail
- [ ] `curl -sI https://<site>/static/css/tailwind.build.css` returns 200
- [ ] Error rate in `docker-compose logs web` looks normal; Sentry (if configured)
      shows no new exception types

## 6. Rollback

Fastest rollback is reverting the merge commit and letting the same pipeline
redeploy:

```bash
git revert -m 1 <merge-commit-sha>   # on main
git push origin main                 # triggers the same deploy workflow
```

or, directly on the droplet:

```bash
cd /home/jmx/halal-korea
git reset --hard $(cat ~/backups/pre-pr25-commit.txt)
docker-compose down && docker-compose up -d --build
docker-compose exec -T web python manage.py migrate
docker-compose exec -T web python manage.py collectstatic --noinput
```

No migrations ship with this batch, so no DB rollback is needed beyond the backup
safety net. Uploaded media is untouched. If static files look wrong after
rollback, rerun collectstatic (manifest fingerprints change back with the old
build).

## 7. If you prefer lower-risk batches instead of one merge

Order below is lowest-risk first, each independently revertable. Between batches:
deploy, run section 5's smoke checks, watch logs/Sentry for ~30 minutes (or
longer for the perf batch).

1. **#17 (test fixes)** - no user-facing change; fixes the 15 pre-existing test
   failures so later batches are measurable.
2. **#23 (CI)** - adds the CI workflow; needs the one-time Actions approval click.
3. **#18-#21 (mobile UX/photos)** - template-only tap targets, tutorial overflow,
   photo fallbacks.
4. **#22 (canonical)** + **#26, #27, #29 (a11y)** + **#28, #30 (i18n)** -
   template/string-only; run makemessages+compilemessages after.
5. **#31, #32 (blog perf)** - view query optimization + featured-image resizing
   (resizing only affects *new* uploads).
6. **#8, #9, #11-#16, #24 (perf/infra)** - the riskiest batch (static manifest
   storage, gunicorn flags, session/CSRF changes, caching). Check static files
   and login/session behavior carefully after this one.

The same section 3 local verification applies before each batch.

## Not verifiable from the repo (needs you)

- Whether the droplet's `.env` currently sets every variable in section 1 (I
  verified the app requires them, not that the server has them - the site is up,
  so presumably yes).
- Whether `~/backups` exists on the droplet; create it first if not.
- Cloudflare rules: #16 only makes HTML cache-eligible app-side; the actual edge
  caching needs the Cache Rules from #16's description added in the Cloudflare
  dashboard - optional, not required for this rollout.
- The Google Maps API key's HTTP referrer restrictions: if you ever rotate the
  key, the new key must allow the production domain.

## Standalone follow-ups (deliberately NOT in #25)

- **#37 (Django 5.1.6 -> 5.2.18 LTS)** - framework upgrade, merge separately
  after #25 with its own deploy window and smoke pass (home, explore, place
  detail, login/register, Google login, submit-place, blog, admin). Rollback:
  revert the single commit, reinstall requirements, restart.
- **allauth bump PR** (django-allauth 0.57.0 -> 65.x + `SOCIALACCOUNT_LOGIN_ON_GET=False`) -
  separate PR; verify Google social login manually after deploy since OAuth
  can't be exercised by the test suite.

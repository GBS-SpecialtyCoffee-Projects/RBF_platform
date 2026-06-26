# Refactor Roadmap — RBF_platform Cleanliness Pass

## Context

The codebase has a clear two-tier quality split. Newer code sets a good standard —
the `Connection`/`Forum`/`ForumMeeting` models are proper "fat models" with state
machines and query helpers; `notifications._send` is a clean single dispatch seam;
`platform_admin.py` uses `@admin_required` decorators consistently; `emails/_base_email.html`
centralizes email layout. Older code never caught up: business logic lives in views,
the farmer/roaster discovery + dashboard flows are near-duplicated, auth/role checks are
copy-pasted inline, ~130 lines of app JS sit inline in the global base template, and there's
accumulated dead code (debug prints, `views_old.py`, commented blocks, duplicate image trees).

**Goal:** bring the old code up to the standard the new code already sets, without changing
behavior. This is a **moderate** pass — dedupe logic, push logic onto models, extract
partials/JS, fix N+1s — but **keep `models.py` as one file** and **keep the custom
`AuthMiddleware`** as-is (no models-package split, no swap to Django's `@login_required`).
The refactor reuses existing good patterns rather than inventing new ones.

The work is phased so the zero-risk cleanup lands first and is verified before any logic moves.
Each phase is independently shippable and verified against the existing 66-test suite.

---

## Phase 0 — Zero-risk cleanup (do first)

No behavior change. Safe to do and verify first.

- **Delete dead modules:** `base/views_old.py` (unreferenced), `testcountycodes.py` (root stray),
  `static/image/hello.py` (1-line stray), `static/.DS_Store`.
- **Remove debug `print()`s:** `base/views/farmer.py:57,215,220,224,342,444`; commented prints in
  `base/views/roaster.py:427-428`.
- **Remove commented-out blocks:** `models.py` (`Farmer.COUNTRY_REGION_CODES` ~120, commented
  `FarmerPhoto.save/clean/__str__` 240-261, `RoasterPhoto.clean`, `Roaster.clean`,
  `MeetingRequest.clean`, `Story.__str__/language_list`); commented `signout` URL `urls.py:54`;
  commented `COUNTRY_CODE_CHOICES` block `views/forms.py:25-32`; commented `auth.py:14,34-38`.
- **Remove now-dead imports:** `Image` (PIL) and `COUNTRY_CODE_TO_REGION_CODE` in `models.py`
  (only used by the commented code being removed).
- **Fix `== False` idioms:** `farmer.py:29`, `roaster.py:24` → `not ...`.
- **Dedupe static image trees:** `static/image/` vs `static/img/` share 5 files
  (danurwendho…, esteban-benites…, joel-friedrich…, pablo-merchan-montes…, landingpagevideothumbnail.png).
  Pick one directory, update references, delete the other. **Grep every template for both paths first.**
- **Decide on `static/evk-calendar/`:** loaded globally in `main.html:18,46` but only used by a
  commented-out `<div id="cale">` in `farmer_dashboard.html:106-108`. Remove the global include
  (and the dead div) unless the calendar is planned for use.

Files: `base/views/farmer.py`, `base/views/roaster.py`, `base/models.py`, `base/urls.py`,
`base/views/forms.py`, `base/middleware/auth.py`, `base/templates/base/main.html`, `static/`.

**Stop and verify (66 tests + `manage.py check`) before Phase 1.**

---

## Phase 1 — Push logic onto models (fat models)

Add methods/properties so views and middleware stop re-deriving the same facts. Reuse the style
already used on `Connection`.

- **`User` helpers** (consolidates ~15 scattered `group == '...'` sites across
  `chat.py`, `roaster.py`, `farmer.py`, `account.py`, `auth.py`):
  - `User.is_farmer` / `User.is_roaster` (properties)
  - `User.profile` → `getattr(self,'farmer_profile',None) or getattr(self,'roaster_profile',None)`
    (the logic currently only in `notifications._display_name:60-63`)
  - `User.dashboard_url` → replaces the repeated "redirect to my/other dashboard" idiom
    (`roaster.py:158`, `farmer.py:100`)
- **`Farmer.is_complete`** property — replaces the free function `check_is_complete(farmer)`
  (`farmer.py:527`) and the ad-hoc `is_details_filled` checks (`farmer.py:29`, `roaster.py:24`,
  `auth.py:66-72`).
- **Photo-cap constant:** add `MAX_PHOTOS = 6` on `Farmer`/`Roaster` (or a shared mixin) to replace
  the hardcoded `6` in `farmer.py:38` and `roaster.py:54`.
- **`Farmer.cultivars_list`** property for the `cultivars.split(',')` parsing in `roaster.py:389`.
- **Profile-completion %** for orientation: move the percentage math (computed twice in
  `farmer_orientation`, `farmer.py:354-357,414-416`) onto a `Farmer.orientation_progress` property.
- **Collapse connection-bucket duplication:** `connection_buckets(user)` (`roaster.py:341-361`)
  re-implements `Connection.status_sets_for` (`models.py:457-473`). Make the model method the single
  source of truth and have the view use it.

Add focused unit tests for each new model method in `base/tests.py`.

Files: `base/models.py`, `base/tests.py`, callers in `base/views/*.py`, `base/middleware/auth.py`.

---

## Phase 2 — Thin the views (dedupe + decorators + N+1)

- **`@group_required('farmer'|'roaster')` decorator** in a new `base/views/decorators.py`
  (mirrors the existing `@admin_required`/`@superadmin_required` in `platform_admin.py`).
  Replace the ~8 inline `if request.user.group != '...': return redirect(...)` guards.
  *(This is a decorator alongside the middleware — the middleware stays.)*
- **One shared "safe redirect back" util** — `_redirect_back` is implemented 3× nearly identically
  (`roaster.py:151-158`, `forums.py:62-69`, `farmer.py:190-196`). Extract one helper.
- **Extract the discovery flow** shared by `connection_roasters` (`farmer.py:98-188`, ~90 lines) and
  `connection_farmers` (`roaster.py:236-339`, ~103 lines): the range-bucket filtering
  (`'0-500'/'500-2000'/…` → `gte/lte`), pagination, `filter_query_string`, and connection-state
  context. Move range filtering onto a `Roaster`/`Farmer` queryset/manager method; share the
  pagination + `can_request_meetings` (`Connection.pending_sent_count < MAX_PENDING_SENT`, repeated
  4×) context-building in a helper. Targets the two largest views.
- **Split the multi-form dashboards:** `farmer_dashboard` (`farmer.py:20-83`) and `roaster_dashboard`
  (`roaster.py:19-93`) each handle 4 POST forms inline. Route by a `form_type` hidden field to small
  per-form handlers (pattern already used in `admin_farmer_detail`).
- **Fix the `chat_list` N+1** (`chat.py:33-36`): last message + unread count are queried per
  conversation. Replace with annotations / `prefetch_related` on the already-annotated queryset.
- **Add `select_related('user')`** to the paginated `Roaster`/`Farmer` discovery querysets
  (`farmer.py:161`, `roaster.py:310`) and `prefetch_related` the 5 per-related queries in
  `farmer_view` (`roaster.py:384-388`) and `farmer_dashboard` (`farmer.py:32-39`).
- **Collapse twin views:** `manage_connection_request`/`manage_meeting_request` and the two
  `switch_story` copies (worked around as `switch_story2` in `urls.py:72`) — unify once the shared
  helpers exist; remove the `switch_story2` workaround.
- **Replace bare `except:` flow-control** in `switch_story` (`farmer.py:481`, `roaster.py:429`) and
  the broad `except Exception` in `roaster_view`/`farmer_view` with explicit lookups.
- **HTTP-method consistency:** use `@require_POST` (already used in `meetings.py`/`forums.py`) on
  mutating views instead of manual `HttpResponseNotAllowed` checks; fix `delete_farmer_photo`
  deleting on **GET** (`farmer.py:274`) to require POST like `delete_roaster_photo`.

Files: `base/views/{farmer,roaster,chat,decorators}.py`, `base/models.py`, `base/urls.py`.

---

## Phase 3 — Consolidate notifications

- **Add `attachments=None` to `_send`** (`notifications.py:69`) and fold
  `notify_meeting_calendar_invite` (`196-236`) into it — it currently re-inlines the entire
  render→`EmailMultiAlternatives`→send flow just to attach an `.ics`.
- **Move the inline email sender out of `account.py:215-225`** (`verify_email`) into a
  `notify_password_reset(...)` in `notifications.py`, so all email goes through one seam.

Files: `base/notifications.py`, `base/views/account.py`.

---

## Phase 4 — Templates & frontend

- **Extract inline JS to `static/js/`** (project already loads JS via `{% static %}`):
  - `main.html:48-178` (~130 lines of story/translation AJAX) → `static/js/profile_stories.js`.
  - The country-code search + toast JS duplicated in `farmer_signup.html:390-471` and
    `roaster_signup.html:268-348` → one shared `static/js/signup_form.js`.
- **Extract repeated partials:**
  - `_pagination.html` — the identical ~22-line pagination block copy-pasted across ~8 templates
    (`connection_farmers.html`, `connection_roasters.html`, `platform_admin/{farmers,roasters,forums,meetings,audit_log,resources}.html`).
  - Dashboard partials shared by `farmer_dashboard.html`/`roaster_dashboard.html`: `_profile_header.html`,
    `_photo_grid.html`, `_header_modal.html`; move the duplicated `.meeting-*` `<style>` blocks
    (`roaster_dashboard.html:123-147`, `farmer_dashboard.html:113-131`) into a stylesheet.
- **Move template logic into views/tags:** the pagination-window arithmetic
  (`{% ... page_obj.number|add:'-3' %}`) → a custom template tag or precomputed page range;
  list slicing `|slice:":5"` (`roaster_dashboard.html:153,161`) → view-provided querysets.
- **Fix `language_select.html` duplicate `{% extends %}`** (lines 1 and 9).

Files: `base/templates/base/*.html`, `static/js/`, `static/styles/`.

---

## Phase 5 — Type hints & style sweep (last)

- Add parameter/return type hints across `views/*.py`, `models.py`, `notifications.py`,
  `middleware/*.py` (currently ~0% typed). Do this last so signatures are already stable.
- Wrap lines to the 88-char limit (notably `views/forms.py`, `urls.py`).
- `urls.py` is one flat 78-entry list — optionally group with comments (no `include()` split needed
  for moderate scope); remove leftover test routes (`translation-test`, `account.test`,
  `urls.py:49-50`) after confirming the `test.html`/`translation_test.html` pages are non-production.

---

## Out of scope (per "moderate" appetite)

- Splitting `models.py` (849 lines) into a `models/` package.
- Replacing the custom `AuthMiddleware` with Django's `@login_required`/`LoginRequiredMixin`.
- A full `NamedLookup` abstract base for the 6 lookup tables, consolidating the 3 Bootstrap sources,
  and `urls.py` `include()`/namespacing — note as follow-ups, don't do now.

## Needs confirmation before touching

- **`MeetingRequest` model + `notify_meeting_event`** appear to be the **legacy** path superseded by
  `Connection` (per the `Connection` docstring, `models.py:344-350`). Several views and migration
  `0047_backfill_connections_from_meeting_requests` reference it. **Do not remove** until confirmed
  fully unused — flag for a separate decision.

---

## Verification

Run after **each phase** (not just at the end):

1. `./env/bin/python manage.py check` — no system issues.
2. `./env/bin/python manage.py test` — all **66 tests pass** (add new tests in Phases 1–2 for the
   model methods and shared helpers; count should grow).
3. For Phase 2 chat/N+1 work, optionally assert query counts with
   `django.test.utils.CaptureQueriesContext` in a test to prove the N+1 is gone.
4. For Phase 4 (templates/JS), live smoke test: `./env/bin/daphne -b 127.0.0.1 -p 8009
   rbf_platform.asgi:application`, load farmer + roaster dashboards and a signup page, confirm the
   moved JS (story edit, country-code search, toasts) still works and no console errors.
5. `git diff --stat` per phase to confirm the diff stays scoped to that phase.

Commit per phase with conventional messages (`refactor:`, `fix:`), branching off `ft/rbf_meeting`,
so each step is independently reviewable and revertible.

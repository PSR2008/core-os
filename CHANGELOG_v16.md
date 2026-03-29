# CORE OS v16 — Upgrade Changelog

## What Changed

### 1. PREMIUM SYSTEM REMOVED (Temporary)
- All premium gates removed from templates (index.html, profile.html, tasks, habits, etc.)
- `premium_service.py` updated with `PREMIUM_MODE = False` toggle
- Setting `PREMIUM_MODE = True` will instantly re-enable gating
- `is_premium=True` now passed from all routes
- ₹299 pricing and upgrade CTAs removed from all pages
- Lock icons (⊘) replaced with check marks (✓) throughout
- Achievement tier breakdown now visible to all users
- Full insight feed (all 5) now available to all users
- Weekly goals editor now available to all users
- Cross-domain AI insights (spend-mood, task-wellness) now visible to all

### 2. DASHBOARD IMPROVEMENTS
- Added **Recent Activity Feed** panel — shows today's completions, habit syncs, achievements, and alerts in a clean timeline
- Added **Today at a Glance** smart summary — 2×2 stats grid + AI-generated contextual summary text
- Premium gate labels removed from achievement section header
- Weekly goals "Edit Goals" link now shown to all users
- Dashboard title updated to "CORE OS — COMMAND CENTER"
- Page header spacing tightened for cleaner layout

### 3. VISUAL UPGRADE (CSS)
- Scanline overlay reduced from harsh to subtle (0.012 opacity)
- Glass cards: reduced shadow, smaller border radius (14px), cleaner backdrop blur
- Sidebar: cleaner gradient background, softer borders, refined logo sizing
- Section headers (`.sh`): lighter color for less visual noise
- Quick action buttons: better letter-spacing and sizing
- All metric cards: tightened padding and font sizing for better density
- Body background: subtle radial gradient for depth without glow overload
- Data ticker: cleaner background and border

### 4. MICRO-INTERACTIONS (motion.js)
- Activity feed items animate in with staggered translateX slide
- Quick stats counters animate on load
- QA button click ripple effect added
- Productivity ring color pulse added (danger color when score < 30, success when ≥ 75)
- Activity/summary section card entrance animation

### 5. LANDING PAGE (entrance.html)
- "Premium" removed from navbar, replaced with "Why CORE OS"
- Premium pricing section replaced with "Everything Unlocked" feature grid
- Hero description rewritten for clarity and stronger positioning
- Version updated to v16 throughout
- Hero eyebrow updated: "CORE_OS v16 — ALL SYSTEMS ONLINE"
- Footer premium link replaced with "Why CORE OS"

### 6. CONSISTENCY
- `₹299` and all pricing references removed across all templates
- `.premium-gate` class hidden via CSS with `display:none !important`
- Consistent `v16` version string across all pages
- All templates use same `display:none` pattern for premium elements

## Re-enabling Premium (when ready)
1. In `app/services/premium_service.py`, set `PREMIUM_MODE = True`
2. Restore `is_premium=u.is_premium` in `dashboard.py` and `api.py`
3. Re-add pricing section to `entrance.html` (see git history)
4. Re-add "UPGRADE" CTAs to profile.html

## Files Changed
- `app/services/premium_service.py` — PREMIUM_MODE toggle added
- `app/routes/dashboard.py` — is_premium=True
- `app/routes/api.py` — is_premium=True
- `app/static/style.css` — v16 CSS additions appended
- `app/static/motion.js` — micro-interaction additions appended
- `app/templates/index.html` — premium gates removed, activity feed added
- `app/templates/entrance.html` — premium section replaced, landing improved
- `app/templates/profile.html` — premium UI hidden
- `app/templates/tasks.html` — lock icons replaced
- `app/templates/habits.html` — lock icons replaced
- `app/templates/wellness.html` — lock icons replaced
- `app/templates/expenses.html` — lock icons replaced
- `app/templates/shop.html` — lock icons replaced
- `app/templates/auth/login.html` — version updated
- `app/templates/auth/register.html` — version updated

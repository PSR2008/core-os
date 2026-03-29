# CORE OS v16 — Manual Testing Checklist

## A. Landing Page (/)
- [ ] No "₹299" or pricing anywhere visible
- [ ] No "UPGRADE TO PREMIUM" buttons
- [ ] No "Premium" in navbar or mobile menu
- [ ] "Why CORE OS" link in navbar works (scrolls to access section)
- [ ] "Everything Unlocked" section shows 4 feature cards
- [ ] Hero description reads correctly
- [ ] Eyebrow shows "v16"
- [ ] Footer shows "BUILD v16"
- [ ] All CTAs (Get Started, Sign In) redirect correctly
- [ ] Mobile menu opens/closes correctly
- [ ] Three.js background renders
- [ ] Scroll-reveal animations fire correctly

## B. Auth Pages (/login, /register)
- [ ] No pricing or premium references visible
- [ ] Login form submits and works
- [ ] Register form submits and works
- [ ] Flash messages display correctly

## C. Dashboard (/dashboard)
- [ ] No "TIER_DETAIL: PREMIUM" badge in achievements section
- [ ] No "⭐ EDIT GOALS: PREMIUM" badge in weekly goals
- [ ] Achievement tier breakdown (bronze/silver/gold) visible to all users
- [ ] "EDIT GOALS →" link visible to all users
- [ ] Recent Activity Feed renders (bottom of page)
- [ ] Today at a Glance panel renders with 4 stats
- [ ] Smart summary text shows (green/blue/yellow/red based on score)
- [ ] Activity items animate in on load (staggered slide)
- [ ] QA buttons (NEW_TASK, SYNC_HABIT, LOG_EXPENSE, UPDATE_WELLNESS) have ripple on click
- [ ] Productivity ring animates correctly
- [ ] Threat bar animates correctly
- [ ] Habit chart renders (if habits exist)
- [ ] Expense chart renders (if expenses exist)
- [ ] All 5 AI insights visible (not just 2)
- [ ] All suggestions visible
- [ ] Stats carousel ticker scrolls
- [ ] Live clock updates
- [ ] Login streak shows if ≥ 2 days

## D. Tasks (/tasks)
- [ ] No lock icons (⊘) — all show ✓ instead
- [ ] No premium gates visible
- [ ] Task creation works
- [ ] Task completion works

## E. Habits (/habits)
- [ ] No lock icons or premium gates
- [ ] Habit sync works
- [ ] Streak display shows correctly

## F. Expenses (/expenses)
- [ ] No pricing or premium references
- [ ] Add expense works

## G. Wellness (/wellness)
- [ ] No premium gates
- [ ] Log wellness entry works

## H. Shop (/shop)
- [ ] No premium pricing visible
- [ ] Shop items display correctly

## I. Profile (/profile)
- [ ] No "₹299" visible anywhere
- [ ] No "UPGRADE" button visible
- [ ] Achievement tier breakdown visible
- [ ] Weekly goals editable

## J. Performance
- [ ] Dashboard loads in < 2 seconds
- [ ] No visible layout shift on load
- [ ] Animations don't cause jank (smooth 60fps)
- [ ] Sidebar toggle is smooth

## K. Mobile (< 768px)
- [ ] Sidebar hidden by default
- [ ] Quick action buttons 2-column
- [ ] Activity feed readable
- [ ] Landing page hero readable

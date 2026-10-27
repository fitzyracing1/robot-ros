# Branching and tagging standard

Rule zero: **nothing is lost.** No branch or tag is ever deleted or renamed, no force-push, no history rewrite. A branch is retired only after it is preserved as an `archive/<branch>` tag.

## Branch types
| Branch | Purpose |
|---|---|
| `main` | Always lit. Protected. Releases are cut from here. |
| `develop` | Integration branch, created from main. Feature PRs land here; develop merges into main only when lit. |
| `feat/<name>` | New capability, from develop, PR into develop. |
| `fix/<name>` | Non-urgent bug fix, from develop, PR into develop. |
| `try/<name>` | Throwaway experiment (the throwaway-fix-branch workflow): try ideas freely, prove it turns lit, then redo or PR the winner. Never merged blindly; archive before retiring. |
| `release/<x.y>` | Stabilize a release from develop; merges into main (tagged `vX.Y.Z`) and back into develop. |
| `hotfix/<name>` | Urgent fix from main; merges into main and back into develop. |

## Tag types
| Tag | Purpose |
|---|---|
| `vX.Y.Z` | Releases (semver), on main. |
| `lit-YYYYMMDD` | Snapshot of a lit main on that date. |
| `archive/<branch>` | Preserves a branch tip before it is retired, so nothing is lost. |

## Do we need `develop`? Yes.
Many agents push work in parallel. Without an integration branch their changes land straight on main and main can go dark. `develop` absorbs and tests that work together; main only moves forward when develop is lit. Cost: one extra merge per release. Worth it for a lit main.

## Existing refs mapped onto the standard
| Existing ref | Maps to | Action |
|---|---|---|
| `main` (73dd23c) | `main` | Kept unchanged. Tagged `lit-20261027` (CI lit). |
| (no other branches) | - | - |
| (no tags) | - | - |
New: `develop` created from main at 73dd23c.

## Recommended protection (not yet applied)
- `main`: require PR, require `ci` checks (sim, ros2-jazzy) lit, no force-push, no deletion.
- `develop`: require `ci` lit, no force-push, no deletion.
- Tags `v*`, `lit-*`, `archive/*`: protect against deletion/overwrite.

# Metrics Dashboard

Date: 2026-03-09  
Source artifacts: `biopsy_manifest.csv`, `biopsy_inventory.csv`, `biopsy_metrics.json`, `biopsy_complexity.csv`, `biopsy_duplicates.csv`

## 1) Size Metrics
| Metric | Value |
|---|---:|
| Total repo-owned files | 101 |
| Text files counted for LOC | 81 |
| Total LOC | 11,682 |
| Avg LOC per text file | 144.22 |
| Largest file | `frontend/css/main.css` (980 LOC) |
| Smallest file | `app/db/base.py` (4 LOC) |

## 2) File-Type Distribution
| Extension | Count |
|---|---:|
| `.py` | 42 |
| `.md` | 22 |
| `.html` | 7 |
| `.js` | 4 |
| `.css` | 1 |
| `.yml` | 1 |
| `.ini` | 2 |
| `.bat` | 2 |
| `.sh` | 2 |
| Binary assets (`.png`, `.webp`, etc.) | 9 |

## 3) Complexity Proxy (Python Functions)
| Bucket | Count |
|---|---:|
| Simple (`<5`) | 110 |
| Moderate (`5-10`) | 18 |
| Complex (`11-20`) | 5 |
| Very complex (`>20`) | 6 |
| Total functions analyzed | 139 |

Top complexity hotspots:
1. `absence_report` (`CyclomaticProxy=48`) in `app/api/v1/endpoints/reports.py`
2. `live_stats` (`24`) in `app/api/v1/endpoints/reports.py`
3. `get_current_user` (`22`) in `app/api/v1/deps.py`
4. `clear_attendance` (`21`) in `app/api/v1/endpoints/reports.py`
5. `scan_card` (`21`) in `app/api/v1/endpoints/employees.py`

## 4) Duplication Proxy
| Metric | Value |
|---|---:|
| Duplicate 6-line windows | 28 |
| Approx duplicate lines | 432 |
| Notes | Largest duplicates are intentional frontend boilerplate (head/layout blocks). |

## 5) API Surface
| Metric | Value |
|---|---:|
| Endpoint decorators detected (`@router.get/post/put/delete/patch`) | 30 |
| Backend endpoint modules | 4 (`auth`, `employees`, `reports`, `settings`) |

## 6) Test Surface
| Metric | Value |
|---|---:|
| Test files under `tests/` | 9 |
| Test functions detected | 41 |
| New/updated tests in this remediation | 3 files (`test_settings_validation`, `test_reports`, `test_scan`) |

## 7) Security/Hardening Delta
| Area | Status |
|---|---|
| Cookie CSRF host checks | Added |
| Auth cookie lifecycle consistency | Improved |
| CSV formula safety | Added |
| Settings/date validation strictness | Added |
| DB check constraints | Added |
| Public scan endpoint isolation/auth | Open high-risk decision |

## 8) Category Scores
| Category | Score (/10) |
|---|---:|
| Structure & Organization | 8 |
| Code Quality | 8 |
| Functionality | 7 |
| Database Integrity | 8 |
| Security | 8 |
| Performance | 8 |
| Error Handling | 8 |
| Documentation | 8 |
| Testing | 7 |
| Configuration | 8 |
| Dependencies | 7 |

Normalized overall: **85/100**

## 9) Chart Definitions (for external dashboarding)
1. `loc_by_extension` - bar chart from `biopsy_manifest.csv` grouped by extension.
2. `complexity_distribution` - histogram from `biopsy_complexity.csv` by `CyclomaticProxy`.
3. `top_complex_functions` - horizontal bar for top 10 `CyclomaticProxy`.
4. `duplication_windows` - pie chart split by boilerplate vs non-boilerplate duplicate windows.
5. `issue_severity` - stacked bar: critical/high/medium/low open vs fixed.

## 10) Interpretation
- Codebase is medium-sized with concentrated complexity in report aggregation paths.
- Security posture improved meaningfully, but release confidence is currently limited by environment-blocked runtime verification.
- Most immediate ROI remains in:
  - executing full integration tests,
  - resolving scan endpoint trust boundary,
  - reducing complexity in report endpoints.

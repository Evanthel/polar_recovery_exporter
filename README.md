# Polar Recovery Exporter
`polar_recovery_exporter.py` is a quiet daily exporter for Polar Open AccessLink data. It fetches the latest sleep and nightly recharge data, upserts one row into `polar_daily.csv`, and copies that latest CSV row to the clipboard on macOS and Windows.

The goal is to create a lightweight, analysis-ready dataset for personal tracking, journaling, or AI-assisted analysis. It focuses on a small set of high-signal recovery metrics such as HRV, sleep, and ANS rather than full activity tracking.

It is designed to run inside the official Polar example repository structure and use the same `config.yml` setup as the official example console app:

[https://github.com/polarofficial/accesslink-example-python](https://github.com/polarofficial/accesslink-example-python)

## Requirements

- Polar Flow account
- Python 3
- `polar_recovery_exporter.py` placed in the same folder as `config.yml`
- Official Polar example environment already set up

## Quick start

1. Clone this repo or download `polar_recovery_exporter.py`
2. Set up Polar AccessLink using the official example:
   [https://github.com/polarofficial/accesslink-example-python](https://github.com/polarofficial/accesslink-example-python)
3. Copy `polar_recovery_exporter.py` into the configured official example environment, next to `config.yml`
4. Run the script

## Setup

Set up the Polar API client, authorization flow, and `config.yml` exactly as in the official Polar example console app. After setup is complete, your `config.yml` should contain:

```yaml
access_token: YOUR_ACCESS_TOKEN
client_id: YOUR_CLIENT_ID
client_secret: YOUR_CLIENT_SECRET
user_id: YOUR_POLAR_USER_ID
```

## Run

Run the exporter:

```bash
python3 polar_recovery_exporter.py
```

The script runs silently, updates `polar_daily.csv`, and copies the latest written CSV row to the clipboard. On macOS it uses `pbcopy`. On Windows it uses `clip` or PowerShell's `Set-Clipboard`. The resulting CSV is designed to be easily used as input for spreadsheets, Python analysis, or AI tools (e.g. ChatGPT) for pattern discovery and decision support.

## macOS Shortcuts

You can set it up with a single `Run Shell Script` action.

Use the path to your configured Polar example directory, for example:

```bash
cd /path/to/your/accesslink-example-python
python3 polar_recovery_exporter.py
```

After each run, the newest CSV row is available directly in the clipboard, which is useful for Shortcuts, notes, journaling apps, or quick pasting into an AI tool.

## Clipboard support

- macOS: uses `pbcopy`
- Windows: uses `clip` or PowerShell `Set-Clipboard`
- Other platforms: the exporter still writes the CSV normally, but clipboard copy is skipped if no supported clipboard command is available

## CSV Output

The app currently writes these fields:

- `date`
- `fell_asleep_at`
- `sleep_hours`
- `deep_sleep_pct`
- `rem_sleep_pct`
- `sleep_score`
- `heart_rate_avg`
- `breathing_rate_avg`
- `hrv_avg`
- `hrv_30d_avg`
- `hrv_delta`
- `ans_charge`
- `ans_status`
- `nightly_recharge_status`
- `low_hrv_flag`
- `poor_sleep_flag`
- `high_stress_flag`

Example output:

```csv
date,fell_asleep_at,sleep_hours,deep_sleep_pct,rem_sleep_pct,sleep_score,heart_rate_avg,breathing_rate_avg,hrv_avg,hrv_30d_avg,hrv_delta,ans_charge,ans_status,nightly_recharge_status,low_hrv_flag,poor_sleep_flag,high_stress_flag
2026-01-01,23:45,7.50,22.00,24.00,78,56,13.10,58,54.20,3.80,2.40,ok,good,False,False,False
2026-01-02,00:10,6.80,18.50,21.30,67,61,13.70,46,54.00,-8.00,-3.10,poor,moderate,True,True,True
```

The sample rows above are illustrative only and do not represent real user data.

## Extending

The file is intentionally simple and easy to modify. You can freely modify, remove, or extend tracked health metrics. If Polar exposes a given field, you can quickly add it — even by pasting this file into an AI model and asking for extraction logic.

Useful additions with high signal-to-effort ratio include:

- nightly HR min/max
- skin temperature
- breathing-rate trend
- sleep continuity or interruptions
- HRV 3-day average
- rolling resting-HR baseline
- day of week
- subjective energy or stress score
- activity or training-load context

## Limitations

- Depends on Polar AccessLink API structure
- Requires local setup of the official Polar example repo
- Not intended for real-time or multi-user usage

## Notes

- The script is publishable as a drop-in app for the official Polar example repo structure.
- It is not a standalone single-file replacement for the whole Polar repo, because it still uses the local `accesslink` package and `utils.py` from that setup.
- Do not commit `config.yml`, `.env`, or `polar_daily.csv`. This repository's `.gitignore` excludes them by default.

## Changelog

- Added automatic clipboard copy of the latest CSV row after each run on macOS and Windows.
- Updated the documentation to describe the cross-platform clipboard behavior and Shortcuts-friendly workflow.

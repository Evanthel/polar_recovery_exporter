#!/usr/bin/env python

"""Minimal daily Polar export.

This script requires Polar Open AccessLink API configuration compatible with:
https://github.com/polarofficial/accesslink-example-python

Set up ``config.yml`` the same way as for the official example console app,
then run this file to fetch the latest sleep and nightly recharge data and
upsert a single row into ``polar_daily.csv``. The script is intentionally
quiet: no menu, no prints, only CSV output. Keep this file in the same folder
as ``config.yml`` and the official Polar example files. It is also easy to run
from macOS Shortcuts.

Feel free to edit, remove, or add health markers as needed. A practical way
to extend the app is to give this file as context to a current AI model and
ask for a new export field; if Polar exposes the data, the change is usually
small.

Start simple: most useful insights come from combining HRV, sleep, and a few
contextual signals. This setup is already quite robust, so it is usually best
to add new markers only when you notice your recovery markers dropping.

Easy high-ROI additions include nightly HR min/max, skin temperature, a
breathing-rate trend, sleep continuity or interruptions, an HRV 3-day average,
a rolling resting-HR baseline, day-of-week, subjective energy/stress scores,
or activity and training-load context.
"""

import csv
import os
from datetime import datetime

from accesslink import AccessLink
from utils import load_config


CONFIG_FILENAME = "config.yml"
CSV_FILENAME = "polar_daily.csv"

SLEEP_KEYS = ("sleep_score", "light_sleep", "deep_sleep", "rem_sleep")
RECHARGE_KEYS = (
    "heart_rate_variability_avg",
    "ans_charge",
    "ans_charge_status",
    "nightly_recharge_status",
    "breathing_rate_avg",
)


def status_label(value):
    return {
        1: "very poor",
        2: "poor",
        3: "moderate",
        4: "ok",
        5: "good",
        6: "very good",
    }.get(value, "unknown")


def collect_dated_records(payload, required_keys):
    """Find dated records inside nested API responses."""
    records = []

    def visit(node):
        if isinstance(node, dict):
            if "date" in node and any(key in node for key in required_keys):
                records.append(node)

            for value in node.values():
                if isinstance(value, (dict, list)):
                    visit(value)
        elif isinstance(node, list):
            for item in node:
                if isinstance(item, (dict, list)):
                    visit(item)

    visit(payload)
    return records


def get_latest_record(payload, required_keys):
    records = collect_dated_records(payload, required_keys)
    if not records:
        return None

    return sorted(records, key=lambda item: item["date"], reverse=True)[0]


def get_matching_or_latest_record(payload, required_keys, target_date):
    records = collect_dated_records(payload, required_keys)
    if not records:
        return None

    matching_record = next((item for item in records if item.get("date") == target_date), None)
    if matching_record:
        return matching_record

    return sorted(records, key=lambda item: item["date"], reverse=True)[0]


def calculate_hrv_30d_average(csv_path, current_date):
    if not os.path.exists(csv_path):
        return None

    with open(csv_path, "r") as csv_file:
        rows = [row for row in csv.DictReader(csv_file) if row.get("date") != current_date]

    hrv_values = []
    for row in rows[-30:]:
        try:
            if row.get("hrv_avg"):
                hrv_values.append(float(row["hrv_avg"]))
        except (TypeError, ValueError):
            pass

    if not hrv_values:
        return None

    return sum(hrv_values) / len(hrv_values)


def calculate_hrv_30d_average_from_recharge_payload(recharge_data, current_date):
    """Prefer Polar history over the local CSV when building the HRV baseline."""
    recharge_records = collect_dated_records(recharge_data, RECHARGE_KEYS)
    prior_records = sorted(
        (
            record for record in recharge_records
            if record.get("date") != current_date and record.get("heart_rate_variability_avg") is not None
        ),
        key=lambda item: item["date"],
    )

    if not prior_records:
        return None

    hrv_values = [float(record["heart_rate_variability_avg"]) for record in prior_records[-30:]]
    return sum(hrv_values) / len(hrv_values)


def format_csv_value(value):
    if isinstance(value, float):
        return "{:.2f}".format(value)

    if isinstance(value, str):
        try:
            if "." in value:
                return "{:.2f}".format(float(value))
        except ValueError:
            return value

    return value


def format_sleep_start_time(value):
    if not value:
        return None

    try:
        return datetime.fromisoformat(value).strftime("%H:%M")
    except ValueError:
        return value


def calculate_sleep_stage_percentage(stage_seconds, sleep):
    total_sleep_seconds = (
        sleep.get("light_sleep", 0) +
        sleep.get("deep_sleep", 0) +
        sleep.get("rem_sleep", 0)
    )

    if not total_sleep_seconds:
        return None

    return (stage_seconds / total_sleep_seconds) * 100


def upsert_csv_row(csv_path, row):
    fieldnames = list(row.keys())
    existing_rows = []

    if os.path.exists(csv_path):
        with open(csv_path, "r", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            existing_rows = list(reader)

            # Keep existing columns so repeated runs remain stable.
            if reader.fieldnames:
                for fieldname in reader.fieldnames:
                    if fieldname not in fieldnames:
                        fieldnames.append(fieldname)

    row_written = False
    normalized_rows = []

    for existing_row in existing_rows:
        merged_row = {
            fieldname: format_csv_value(existing_row.get(fieldname, ""))
            for fieldname in fieldnames
        }
        if existing_row.get("date") == row["date"]:
            merged_row.update({fieldname: row.get(fieldname, "") for fieldname in fieldnames})
            row_written = True
        normalized_rows.append(merged_row)

    if not row_written:
        normalized_rows.append({fieldname: row.get(fieldname, "") for fieldname in fieldnames})

    with open(csv_path, "w", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(normalized_rows)


def export_daily_csv(config_path=CONFIG_FILENAME, csv_path=CSV_FILENAME):
    """Fetch the latest daily data and upsert it into the CSV file."""
    config = load_config(config_path)
    accesslink = AccessLink(client_id=config["client_id"], client_secret=config["client_secret"])

    sleep_data = accesslink.get_sleep(access_token=config["access_token"])
    recharge_data = accesslink.get_recharge(access_token=config["access_token"])

    sleep = get_latest_record(sleep_data, SLEEP_KEYS)
    if not sleep:
        return

    recovery = get_matching_or_latest_record(recharge_data, RECHARGE_KEYS, sleep["date"])

    hrv_30d_avg = calculate_hrv_30d_average_from_recharge_payload(recharge_data, sleep["date"])
    if hrv_30d_avg is None:
        hrv_30d_avg = calculate_hrv_30d_average(csv_path, sleep["date"])

    hrv_avg = recovery.get("heart_rate_variability_avg") if recovery else None
    hrv_delta = (hrv_avg - hrv_30d_avg) if hrv_avg is not None and hrv_30d_avg is not None else None
    ans_status = status_label(recovery.get("ans_charge_status")) if recovery else None

    row = {
        "date": sleep["date"],
        "fell_asleep_at": format_sleep_start_time(sleep.get("sleep_start_time")),
        "sleep_hours": (sleep.get("light_sleep", 0) + sleep.get("deep_sleep", 0) + sleep.get("rem_sleep", 0)) / 3600,
        "deep_sleep_pct": calculate_sleep_stage_percentage(sleep.get("deep_sleep", 0), sleep),
        "rem_sleep_pct": calculate_sleep_stage_percentage(sleep.get("rem_sleep", 0), sleep),
        "sleep_score": sleep.get("sleep_score"),
        "heart_rate_avg": recovery.get("heart_rate_avg") if recovery else None,
        "breathing_rate_avg": recovery.get("breathing_rate_avg") if recovery else None,
        "hrv_avg": hrv_avg,
        "hrv_30d_avg": hrv_30d_avg,
        "hrv_delta": hrv_delta,
        "ans_charge": recovery.get("ans_charge") if recovery else None,
        "ans_status": ans_status,
        "nightly_recharge_status": status_label(recovery.get("nightly_recharge_status")) if recovery else None,
        "low_hrv_flag": hrv_delta is not None and hrv_delta < -5,
        "poor_sleep_flag": sleep.get("sleep_score") is not None and sleep.get("sleep_score") < 70,
        "high_stress_flag": ans_status in ["poor", "very poor"],
    }

    row = {key: format_csv_value(value) for key, value in row.items()}
    upsert_csv_row(csv_path, row)


if __name__ == "__main__":
    export_daily_csv()

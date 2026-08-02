#!/usr/bin/env python3
"""Generate per-schedule markdown docs from a Django JSON database dump."""

import argparse
import json
from pathlib import Path

import yaml

BACKUP_FILE = Path("backups/nx-20260801-203330.json")
CATEGORIES_FILE = Path("drug_categories.yaml")
DOCS_DIR = Path("docs")

SLOT_NAMES = {
    "A1": "Morning",
    "A2": "Late morning",
    "A3": "Midday",
    "B1": "Afternoon",
    "B2": "Evening",
    "B3": "Bedtime",
}

SLOT_ORDER = list(SLOT_NAMES.keys())


def ug_to_string(micrograms, second_micrograms=None):
    if second_micrograms:
        return ug_to_string(micrograms) + "/" + ug_to_string(second_micrograms)
    if micrograms % 1000 == 0:
        milligrams = micrograms // 1000
        if milligrams % 1000 == 0:
            return f"{milligrams // 1000:d}g"
        return f"{milligrams:d}mg"
    elif micrograms % 100 == 0 and micrograms < 100_000:
        return f"{micrograms / 1000:.1f}mg"
    elif micrograms % 10 == 0 and micrograms < 10_000:
        return f"{micrograms / 1000:.2f}mg"
    return f"{micrograms:d}ug"


def tablet_dose_str(tablet):
    num_tablets = tablet["num_tablets"]
    num_days = tablet["num_days"]
    if num_days == 1:
        return str(num_tablets if num_tablets != int(num_tablets) else int(num_tablets))
    return f"{num_tablets}/{num_days}d"


def slot_sort_key(slot_code):
    try:
        return SLOT_ORDER.index(slot_code)
    except ValueError:
        return len(SLOT_ORDER)


def generate(backup_path: Path, docs_dir: Path, num: int | None = None):
    categories = yaml.safe_load(CATEGORIES_FILE.read_text())
    prescription_drugs = set(categories.get("prescription", []))
    supplement_drugs = set(categories.get("supplement", []))

    data = json.loads(backup_path.read_text())

    drugs = {item["pk"]: item["fields"] for item in data if item["model"] == "nx.drug"}
    tablets = {item["pk"]: item["fields"] for item in data if item["model"] == "nx.tablet"}
    schedules = {item["pk"]: item["fields"] for item in data if item["model"] == "nx.schedule"}
    doses = [item["fields"] for item in data if item["model"] == "nx.dose"]

    # Group doses by schedule pk
    doses_by_schedule: dict[int, list] = {}
    for dose in doses:
        doses_by_schedule.setdefault(dose["schedule"], []).append(dose)

    docs_dir.mkdir(exist_ok=True)
    all_unknowns: set[str] = set()

    sorted_schedules = sorted(schedules.items(), key=lambda x: x[1]["date0"], reverse=True)
    if num is not None:
        sorted_schedules = sorted_schedules[:num]

    for i, (pk, sched) in enumerate(sorted_schedules):
        date0 = sched["date0"]
        reason = sched["reason"]
        filename = docs_dir / f"{date0}.md"
        # sorted_schedules is newest-first, so next=i-1, prev=i+1
        next_date = sorted_schedules[i - 1][1]["date0"] if i > 0 else None
        prev_date = sorted_schedules[i + 1][1]["date0"] if i < len(sorted_schedules) - 1 else None

        sched_doses = sorted(
            doses_by_schedule.get(pk, []),
            key=lambda d: slot_sort_key(d["slot"]),
        )

        # Collect slots used in this schedule, preserving SLOT_ORDER
        used_slots = sorted({d["slot"] for d in sched_doses}, key=slot_sort_key)

        # Build mappings per category: (drug_name, strength) -> {slot_code: dose_str}
        rx_rows: dict[tuple, dict[str, str]] = {}
        sup_rows: dict[tuple, dict[str, str]] = {}
        unk_rows: dict[tuple, dict[str, str]] = {}
        for dose in sched_doses:
            tablet = tablets[dose["tablet"]]
            drug = drugs[tablet["drug"]]
            name = drug["name"]
            strength = ug_to_string(tablet["tablet_micrograms"], tablet["second_micrograms"])
            key = (name, strength)
            if name in prescription_drugs:
                bucket = rx_rows
            elif name in supplement_drugs:
                bucket = sup_rows
            else:
                bucket = unk_rows
                all_unknowns.add(name)
            bucket.setdefault(key, {})
            bucket[key][dose["slot"]] = tablet_dose_str(tablet)

        slot_headers = [SLOT_NAMES.get(s, s) for s in used_slots]
        empty_cells = " | ".join([""] * len(used_slots))
        header = f"| Drug | {' | '.join(slot_headers)} |"
        divider = f"| :--- | {' | '.join([':---:'] * len(used_slots))} |"

        nav_parts = []
        if prev_date:
            nav_parts.append(f"[Previous]({prev_date}.md)")
        if next_date:
            nav_parts.append(f"[Next]({next_date}.md)")
        nav_line = " | ".join(nav_parts)

        lines = [
            f"# Schedule from {date0}",
            "",
            f"**Reason:** {reason}",
            nav_line,
            "",
            header,
            divider,
        ]

        def append_section(title, rows):
            if not rows:
                return
            lines.append(f"| **{title}** | {empty_cells} |")
            for key in sorted(rows):
                drug_name, strength = key
                cells = [rows[key].get(s, "") for s in used_slots]
                lines.append(f"| {drug_name} ({strength}) | {' | '.join(cells)} |")

        append_section("Prescription", rx_rows)
        append_section("Supplements", sup_rows)
        append_section("UNKNOWN", unk_rows)

        # Grand total across all rows
        totals = []
        for s in used_slots:
            total = sum(
                tablets[d["tablet"]]["num_tablets"]
                for d in sched_doses if d["slot"] == s
            )
            totals.append(str(int(total) if total == int(total) else total))
        lines.append(f"| **Total** | {' | '.join(f'**{t}**' for t in totals)} |")

        lines.append("")
        filename.write_text("\n".join(lines))
        print(f"  wrote {filename}")

    print(f"Done — {len(sorted_schedules)} files written to {docs_dir}/")
    if all_unknowns:
        print("\nWARNING: the following drugs were not found in drug_categories.yaml:")
        for name in sorted(all_unknowns):
            print(f"  - {name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backup", nargs="?", type=Path, default=BACKUP_FILE)
    parser.add_argument("--num", type=int, default=None, metavar="N",
                        help="generate only the N most recent schedules")
    args = parser.parse_args()
    generate(args.backup, DOCS_DIR, args.num)

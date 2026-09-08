#!/usr/bin/env python3
"""
Generate a synthetic crime-investigation dataset.

All values are fictional. No real phone numbers, bank accounts, FIR records,
or personal data are used.
"""

from __future__ import annotations

import argparse
import csv
import random
import string
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Dataset size targets (single split)
# ---------------------------------------------------------------------------
COUNTS = {
    "people": 2000,
    "background_people": 1900,
    "scenario_people": 100,
    "phones": 2800,
    "vehicles": 850,
    "bank_accounts": 2250,
    "locations": 160,
    "organizations": 100,
    "cdr": 60000,
    "transactions": 25000,
    "fir_initial": 720,
    "fir_supplementary": 30,
    "surveillance": 400,
    "case_references": 600,
    "chat_messages": 120000,
    "private_events": 5000,
    "crime_networks": 25,
}

NETWORK_EVIDENCE = {
    "cdr_per_network": 50,
    "transactions_per_network": 20,
    "chats_per_network": 40,
    "surveillance_per_network": 3,
}

CRIME_TYPES = [
    "fraud_ring",
    "money_laundering",
    "cyber_fraud",
    "extortion_ring",
    "theft_ring",
    "smuggling_chain",
]

NETWORK_ROLE_SETS = [
    ["suspect", "associate", "facilitator", "witness"],
    ["suspect", "handler", "associate", "complainant"],
    ["suspect", "facilitator", "associate", "witness"],
]

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Arjun", "Rohan", "Kabir", "Ishaan", "Reyansh",
    "Ananya", "Diya", "Priya", "Kavya", "Sneha", "Meera", "Riya", "Pooja",
    "Rahul", "Amit", "Suresh", "Rajesh", "Vikram", "Sanjay", "Manoj", "Deepak",
    "Neha", "Shreya", "Tanvi", "Nisha", "Swati", "Pallavi", "Kiran", "Lakshmi",
    "Harish", "Gopal", "Naveen", "Prakash", "Ashok", "Ramesh", "Sunil", "Vinod",
    "Fatima", "Zara", "Imran", "Salman", "Ayesha", "Sana", "Rizwan", "Farhan",
]

LAST_NAMES = [
    "Sharma", "Patel", "Singh", "Kumar", "Reddy", "Nair", "Iyer", "Gupta",
    "Mehta", "Desai", "Joshi", "Rao", "Chopra", "Malhotra", "Kapoor", "Verma",
    "Das", "Mukherjee", "Banerjee", "Chatterjee", "Pillai", "Menon", "Naik",
    "Khan", "Sheikh", "Ansari", "Ali", "Hussain", "Mirza", "Qureshi",
]

CITIES = [
    "Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Chennai", "Kolkata", "Pune",
    "Ahmedabad", "Jaipur", "Lucknow", "Chandigarh", "Indore", "Bhopal", "Nagpur",
    "Surat", "Kochi", "Visakhapatnam", "Patna", "Ranchi", "Guwahati",
]

GENDERS = ["Male", "Female", "Other"]

POLICE_STATIONS = [
    "Andheri Police Station", "Bandra Police Station", "Colaba Police Station",
    "Koramangala Police Station", "Whitefield Police Station", "Secunderabad Police Station",
    "T Nagar Police Station", "Park Street Police Station", "Koregaon Park Police Station",
    "Satellite Police Station", "Malviya Nagar Police Station", "Gomti Nagar Police Station",
    "Sector 17 Police Station", "MG Road Police Station", "Hazratganj Police Station",
]

ORG_TYPES = [
    "Logistics", "Finance", "Real Estate", "Import Export", "Construction",
    "Retail", "Technology", "Healthcare", "Transport", "Hospitality",
]

CHAT_TEMPLATES = [
    "Can you send the documents today?",
    "Meeting moved to tomorrow evening.",
    "Payment has been processed.",
    "Need an update on the shipment.",
    "Call me when you are free.",
    "Everything looks fine from my side.",
    "Please confirm the account details.",
    "We should discuss this offline.",
    "Transfer completed, check and confirm.",
    "Do not share this outside the group.",
    "Route changed, use the alternate plan.",
    "Got the package, thanks.",
    "Any news from the client?",
    "Reminder for the follow-up call.",
    "Share location before you leave.",
]

FIR_TEMPLATES = [
    "Complainant reports unauthorized withdrawal from business account linked to suspected fraud network.",
    "Theft of commercial goods reported from warehouse during overnight hours; suspects unknown.",
    "Cyber fraud complaint regarding impersonation and unauthorized fund transfer via mobile banking.",
    "Missing person report filed after individual failed to return from scheduled business travel.",
    "Cheating case registered involving forged property documents and misrepresentation.",
    "Assault complaint filed following dispute at commercial premises; medical report attached.",
    "Extortion complaint regarding repeated threatening calls demanding payment.",
    "Narcotics-related intelligence forwarded for verification and coordinated follow-up.",
    "Vehicle theft reported from residential parking area; CCTV footage requested.",
    "Money laundering indicators observed through layered transactions across multiple accounts.",
]

SURVEILLANCE_TEMPLATES = [
    "Subject observed meeting two associates near commercial hub; duration forty minutes.",
    "Vehicle linked to case parked outside target premises for extended period.",
    "Financial courier activity noted; subject exchanged envelope with unknown male.",
    "Subject switched mobile handset twice within surveillance window.",
    "Night movement detected between warehouse and secondary safe house location.",
    "Subject attended organizational meeting with known associates under watch.",
    "Repeated short calls observed before cash handoff at public location.",
    "Subject avoided main roads and used alternate route to destination.",
    "Intelligence corroborates prior FIR allegations regarding fund movement.",
    "Surveillance team lost visual contact near crowded market area for twelve minutes.",
]


@dataclass
class NetworkMember:
    person_id: str
    role: str


@dataclass
class NetworkRelationship:
    person_id_a: str
    person_id_b: str
    relationship_type: str


@dataclass
class CrimeNetwork:
    case_id: str
    scenario_name: str
    crime_type: str
    members: list[NetworkMember]
    relationships: list[NetworkRelationship]
    primary_suspect_id: str
    complexity: str = "standard"
    cutout_person_id: str | None = None
    intermediary_person_id: str | None = None
    resolution_notes: str = ""


@dataclass
class GeneratorContext:
    rng: random.Random
    output_dir: Path
    people: list[dict]
    phones: list[dict]
    accounts: list[dict]
    locations: list[dict]
    organizations: list[dict]
    cases: list[str]
    case_records: list[dict]
    scenario_person_ids: set[str]
    crime_networks: list[CrimeNetwork]
    person_phones: dict[str, list[str]]
    person_accounts: dict[str, list[str]]
    planted_cdr: list[dict]
    planted_transactions: list[dict]
    planted_chats: list[dict]
    planted_surveillance: list[dict]
    recorded_names: list[dict]
    recorded_phones: list[dict]
    identity_resolution_truth: list[dict]
    private_case_roles: list[dict]
    person_by_id: dict[str, dict]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic crime network dataset CSV files.")
    parser.add_argument("--output-dir", type=Path, default=Path("data"))
    parser.add_argument("--private-dir", type=Path, default=Path("private/eval"))
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def random_date(rng: random.Random, start: datetime, end: datetime) -> datetime:
    delta = end - start
    seconds = rng.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=seconds)


def random_phone(rng: random.Random, used: set[str]) -> str:
    while True:
        prefix = rng.choice(["6", "7", "8", "9"])
        number = prefix + "".join(rng.choice(string.digits) for _ in range(9))
        if number not in used:
            used.add(number)
            return number


def random_account(rng: random.Random, used: set[str]) -> str:
    while True:
        number = "".join(rng.choice(string.digits) for _ in range(14))
        if number not in used:
            used.add(number)
            return number


def random_vehicle_reg(rng: random.Random, used: set[str]) -> str:
    states = ["MH", "DL", "KA", "TS", "TN", "WB", "GJ", "RJ", "UP", "PB"]
    while True:
        reg = (
            f"{rng.choice(states)}{rng.randint(10, 99)}"
            f"{rng.choice('ABCDEFGHJKLMNPQRSTUVWXYZ')}"
            f"{rng.choice('ABCDEFGHJKLMNPQRSTUVWXYZ')}"
            f"{rng.randint(1000, 9999)}"
        )
        if reg not in used:
            used.add(reg)
            return reg


def generate_people(ctx: GeneratorContext) -> None:
    rows = []
    scenario_indices = set(ctx.rng.sample(range(COUNTS["people"]), COUNTS["scenario_people"]))
    start = datetime(1960, 1, 1)
    end = datetime(2005, 12, 31)

    for idx in range(COUNTS["people"]):
        person_id = f"P{idx + 1:05d}"
        name = f"{ctx.rng.choice(FIRST_NAMES)} {ctx.rng.choice(LAST_NAMES)}"
        dob = random_date(ctx.rng, start, end).strftime("%Y-%m-%d")
        gender = ctx.rng.choice(GENDERS)
        city = ctx.rng.choice(CITIES)
        row = {
            "person_id": person_id,
            "name": name,
            "dob": dob,
            "gender": gender,
            "city": city,
        }
        rows.append(row)
        if idx in scenario_indices:
            ctx.scenario_person_ids.add(person_id)

    ctx.people = rows


def generate_locations(ctx: GeneratorContext) -> None:
    rows = []
    used_names: set[str] = set()
    for idx in range(COUNTS["locations"]):
        city = ctx.rng.choice(CITIES)
        suffix = ctx.rng.choice(["Tower", "Plaza", "Market", "Junction", "Colony", "Park", "Hub"])
        base = f"{city} {suffix} {idx + 1}"
        while base in used_names:
            base = f"{city} {suffix} {idx + 1}-{ctx.rng.randint(10, 99)}"
        used_names.add(base)
        rows.append(
            {
                "location_id": f"L{idx + 1:04d}",
                "name": base,
                "city": city,
            }
        )
    ctx.locations = rows


def generate_organizations(ctx: GeneratorContext) -> None:
    rows = []
    used_names: set[str] = set()
    for idx in range(COUNTS["organizations"]):
        city = ctx.rng.choice(CITIES)
        prefix = ctx.rng.choice(["Nova", "Prime", "Global", "Metro", "Summit", "Apex", "Unity"])
        suffix = ctx.rng.choice(["Traders", "Holdings", "Services", "Enterprises", "Solutions"])
        name = f"{prefix} {suffix} {city}"
        while name in used_names:
            name = f"{prefix} {suffix} {city} {idx + 1}"
        used_names.add(name)
        rows.append(
            {
                "org_id": f"O{idx + 1:04d}",
                "name": name,
                "org_type": ctx.rng.choice(ORG_TYPES),
                "city": city,
            }
        )
    ctx.organizations = rows


def generate_phones(ctx: GeneratorContext) -> None:
    rows = []
    used_numbers: set[str] = set()
    person_ids = [person["person_id"] for person in ctx.people]
    weights = [3 if pid in ctx.scenario_person_ids else 1 for pid in person_ids]

    for idx in range(COUNTS["phones"]):
        person_id = ctx.rng.choices(person_ids, weights=weights, k=1)[0]
        rows.append(
            {
                "phone_id": f"PH{idx + 1:05d}",
                "phone_number": random_phone(ctx.rng, used_numbers),
                "person_id": person_id,
            }
        )
    ctx.phones = rows


def generate_bank_accounts(ctx: GeneratorContext) -> None:
    rows = []
    used_accounts: set[str] = set()
    person_ids = [person["person_id"] for person in ctx.people]
    weights = [3 if pid in ctx.scenario_person_ids else 1 for pid in person_ids]
    bank_names = ["Fictional National Bank", "Synthetic Cooperative Bank", "Mock Union Bank", "Sample Trust Bank"]

    for idx in range(COUNTS["bank_accounts"]):
        person_id = ctx.rng.choices(person_ids, weights=weights, k=1)[0]
        rows.append(
            {
                "account_id": f"A{idx + 1:05d}",
                "account_number": random_account(ctx.rng, used_accounts),
                "person_id": person_id,
                "bank_name": ctx.rng.choice(bank_names),
            }
        )
    ctx.accounts = rows


def generate_cases(ctx: GeneratorContext) -> None:
    case_count = max(COUNTS["scenario_people"], COUNTS["fir_initial"] // 3, 120)
    statuses = ["OPEN", "CLOSED", "UNDER_REVIEW", "PENDING"]
    start = datetime(2022, 1, 1)
    end = datetime(2025, 8, 31, 23, 59, 59)
    ctx.case_records = []

    for idx in range(case_count):
        case_id = f"CASE{idx + 1:04d}"
        has_description = ctx.rng.random() < 0.75
        ctx.case_records.append(
            {
                "case_id": case_id,
                "title": f"Synthetic Investigation {idx + 1:04d}",
                "description": ctx.rng.choice(FIR_TEMPLATES) if has_description else "",
                "status": "OPEN" if idx < case_count // 2 else ctx.rng.choice(statuses),
                "created_at": random_date(ctx.rng, start, end).strftime("%Y-%m-%d %H:%M:%S+00"),
            }
        )

    ctx.cases = [record["case_id"] for record in ctx.case_records]


def build_asset_maps(ctx: GeneratorContext) -> None:
    ctx.person_phones = {}
    for phone in ctx.phones:
        ctx.person_phones.setdefault(phone["person_id"], []).append(phone["phone_number"])
    ctx.person_accounts = {}
    for account in ctx.accounts:
        ctx.person_accounts.setdefault(account["person_id"], []).append(account["account_number"])


def ensure_scenario_assets(ctx: GeneratorContext) -> None:
    """Guarantee every scenario participant has phones and accounts for planted evidence."""
    build_asset_maps(ctx)
    used_phones = {phone["phone_number"] for phone in ctx.phones}
    used_accounts = {account["account_number"] for account in ctx.accounts}

    for person_id in sorted(ctx.scenario_person_ids):
        if person_id not in ctx.person_phones:
            ctx.phones.append(
                {
                    "phone_id": f"PH{len(ctx.phones) + 1:05d}",
                    "phone_number": random_phone(ctx.rng, used_phones),
                    "person_id": person_id,
                }
            )
        if person_id not in ctx.person_accounts:
            ctx.accounts.append(
                {
                    "account_id": f"A{len(ctx.accounts) + 1:05d}",
                    "account_number": random_account(ctx.rng, used_accounts),
                    "person_id": person_id,
                    "bank_name": ctx.rng.choice(
                        ["Synthetic National Bank", "Fictional City Bank", "Demo Cooperative Bank"]
                    ),
                }
            )

    build_asset_maps(ctx)


def pick_phone(ctx: GeneratorContext, person_id: str) -> str:
    phones = ctx.person_phones.get(person_id, [])
    if not phones:
        raise ValueError(f"No phone assigned to {person_id}")
    return ctx.rng.choice(phones)


def pick_account(ctx: GeneratorContext, person_id: str) -> str:
    accounts = ctx.person_accounts.get(person_id, [])
    if not accounts:
        raise ValueError(f"No account assigned to {person_id}")
    return ctx.rng.choice(accounts)


def typo_name(name: str, rng: random.Random) -> str:
    first, last = name.split(" ", 1)
    mutation = rng.choice(["swap", "drop", "double", "surname"])
    if mutation == "swap" and len(last) > 3:
        idx = rng.randint(0, len(last) - 2)
        chars = list(last)
        chars[idx], chars[idx + 1] = chars[idx + 1], chars[idx]
        last = "".join(chars)
    elif mutation == "drop" and len(last) > 4:
        idx = rng.randint(1, len(last) - 2)
        last = last[:idx] + last[idx + 1 :]
    elif mutation == "double" and len(last) > 3:
        idx = rng.randint(0, len(last) - 1)
        last = last[: idx + 1] + last[idx] + last[idx + 1 :]
    else:
        last = last[:-1] + rng.choice(["i", "e", "a", "y"])
    return f"{first} {last}"


def typo_phone(phone: str, rng: random.Random) -> str:
    idx = rng.randint(max(1, len(phone) - 4), len(phone) - 1)
    digit = rng.choice("0123456789")
    while digit == phone[idx]:
        digit = rng.choice("0123456789")
    return phone[:idx] + digit + phone[idx + 1 :]


def married_name(name: str, rng: random.Random) -> str:
    first, _ = name.split(" ", 1)
    return f"{first} {rng.choice(LAST_NAMES)}"


def person_lookup(ctx: GeneratorContext) -> None:
    ctx.person_by_id = {person["person_id"]: person for person in ctx.people}


def background_person_ids(ctx: GeneratorContext) -> list[str]:
    return [person["person_id"] for person in ctx.people if person["person_id"] not in ctx.scenario_person_ids]


def assign_network_complexity(ctx: GeneratorContext, network: CrimeNetwork, network_idx: int) -> None:
    complexity_cycle = (
        ["standard"] * 10
        + ["cutout"] * 5
        + ["layered_finance"] * 4
        + ["shared_sim"] * 3
        + ["name_obfuscation"] * 3
    )
    network.complexity = complexity_cycle[network_idx % len(complexity_cycle)]
    background = background_person_ids(ctx)
    background_ready = [
        person_id
        for person_id in background
        if person_id in ctx.person_phones and person_id in ctx.person_accounts
    ]
    if not background_ready:
        background_ready = background
    suspect = network.primary_suspect_id
    associates = [member.person_id for member in network.members if member.person_id != suspect]

    if network.complexity == "cutout" and background_ready:
        network.cutout_person_id = ctx.rng.choice(background_ready)
        network.resolution_notes = (
            f"Direct suspect-to-associate links are sparse. Follow cutout {network.cutout_person_id} "
            f"through call chain and timing correlation."
        )
    elif network.complexity == "layered_finance" and background_ready:
        network.intermediary_person_id = ctx.rng.choice(background_ready)
        network.resolution_notes = (
            f"Funds move through intermediary account holder {network.intermediary_person_id} "
            f"before reaching network members; case_id may be missing on early hops."
        )
    elif network.complexity == "shared_sim":
        network.resolution_notes = (
            "Shared burner handset appears in ownership history and call records; "
            "resolve owner changes before linking participants."
        )
    elif network.complexity == "name_obfuscation":
        network.resolution_notes = (
            "FIR and witness records use misspelled names and post-marriage surnames; "
            "resolve via recorded_names before graph linking."
        )
    else:
        network.resolution_notes = "Standard network with moderate record noise and partial case tagging."


def plant_complex_network_paths(
    ctx: GeneratorContext,
    network: CrimeNetwork,
    start: datetime,
    end: datetime,
    location_names: list[str],
    cdr_idx: int,
    txn_idx: int,
) -> tuple[int, int]:
    suspect = network.primary_suspect_id
    others = [member.person_id for member in network.members if member.person_id != suspect]
    if not others:
        return cdr_idx, txn_idx

    if network.complexity == "cutout" and network.cutout_person_id:
        cutout = network.cutout_person_id
        for person_a, person_b, tagged in [
            (suspect, cutout, False),
            (cutout, ctx.rng.choice(others), False),
            (suspect, ctx.rng.choice(others), True),
        ] * 8:
            ctx.planted_cdr.append(
                {
                    "cdr_id": f"CDR{cdr_idx:06d}",
                    "caller_phone": pick_phone(ctx, person_a),
                    "receiver_phone": pick_phone(ctx, person_b),
                    "timestamp": random_date(ctx.rng, start, end).strftime("%Y-%m-%d %H:%M:%S"),
                    "duration_seconds": str(ctx.rng.randint(20, 420)),
                    "tower_location": ctx.rng.choice(location_names),
                    "case_id": network.case_id if tagged else "",
                }
            )
            cdr_idx += 1

    if network.complexity == "layered_finance" and network.intermediary_person_id:
        intermediary = network.intermediary_person_id
        target = ctx.rng.choice(others)
        for sender_id, receiver_id, tagged in [
            (suspect, intermediary, False),
            (intermediary, target, False),
            (suspect, target, True),
        ] * 5:
            ctx.planted_transactions.append(
                {
                    "transaction_id": f"TXN{txn_idx:06d}",
                    "sender_account": pick_account(ctx, sender_id),
                    "receiver_account": pick_account(ctx, receiver_id),
                    "amount": f"{round(ctx.rng.uniform(40000, 300000), 2):.2f}",
                    "timestamp": random_date(ctx.rng, start, end).strftime("%Y-%m-%d %H:%M:%S"),
                    "case_id": network.case_id if tagged else "",
                }
            )
            txn_idx += 1

    if network.complexity == "shared_sim":
        associate = ctx.rng.choice(others)
        burner_number = random_phone(ctx.rng, {phone["phone_number"] for phone in ctx.phones})
        burner_id = f"PH{len(ctx.phones) + 1:05d}"
        ctx.phones.append(
            {"phone_id": burner_id, "phone_number": burner_number, "person_id": suspect}
        )
        build_asset_maps(ctx)
        ctx.planted_cdr.extend(
            [
                {
                    "cdr_id": f"CDR{cdr_idx:06d}",
                    "caller_phone": burner_number,
                    "receiver_phone": pick_phone(ctx, associate),
                    "timestamp": random_date(ctx.rng, start, end).strftime("%Y-%m-%d %H:%M:%S"),
                    "duration_seconds": str(ctx.rng.randint(15, 240)),
                    "tower_location": ctx.rng.choice(location_names),
                    "case_id": "",
                },
                {
                    "cdr_id": f"CDR{cdr_idx + 1:06d}",
                    "caller_phone": burner_number,
                    "receiver_phone": pick_phone(ctx, associate),
                    "timestamp": random_date(ctx.rng, start, end).strftime("%Y-%m-%d %H:%M:%S"),
                    "duration_seconds": str(ctx.rng.randint(15, 240)),
                    "tower_location": ctx.rng.choice(location_names),
                    "case_id": network.case_id,
                },
            ]
        )
        cdr_idx += 2

    return cdr_idx, txn_idx


def generate_identity_noise(ctx: GeneratorContext, fir_rows: list[dict]) -> None:
    """Create realistic name/phone variants: typos, marriage surname changes, bad manual entry."""
    ctx.recorded_names = []
    ctx.recorded_phones = []
    ctx.identity_resolution_truth = []
    name_idx = 1
    phone_idx = 1
    truth_idx = 1
    fir_by_case = {row["case_id"]: row for row in fir_rows if row["report_type"] == "initial"}
    network_fir_ids = {
        ctx.crime_networks[i].case_id: f"FIR{i + 1:05d}" for i in range(len(ctx.crime_networks))
    }

    for network in ctx.crime_networks:
        for member in network.members:
            person = ctx.person_by_id[member.person_id]
            canonical = person["name"]

            if person["gender"] == "Female" and ctx.rng.random() < 0.55:
                married = married_name(canonical, ctx.rng)
                ctx.recorded_names.append(
                    {
                        "record_id": f"RN{name_idx:05d}",
                        "case_id": network.case_id,
                        "source_type": "marriage_registry",
                        "source_id": network.case_id,
                        "recorded_name": married,
                        "recorded_dob": person["dob"],
                        "variant_type": "married_surname",
                        "person_id": member.person_id,
                        "is_erroneous": False,
                    }
                )
                name_idx += 1
                ctx.identity_resolution_truth.append(
                    {
                        "resolution_id": f"IRT{truth_idx:05d}",
                        "case_id": network.case_id,
                        "person_id": member.person_id,
                        "canonical_name": canonical,
                        "recorded_name": married,
                        "variant_type": "married_surname",
                        "notes": "Same person after marriage; FIR may still use maiden or married form.",
                    }
                )
                truth_idx += 1

            typo = typo_name(canonical, ctx.rng)
            fir_row = fir_by_case.get(network.case_id)
            source_id = network_fir_ids.get(network.case_id, fir_row["fir_id"] if fir_row else network.case_id)
            ctx.recorded_names.append(
                {
                    "record_id": f"RN{name_idx:05d}",
                    "case_id": network.case_id,
                    "source_type": "fir_entry",
                    "source_id": source_id,
                    "recorded_name": typo,
                    "recorded_dob": person["dob"],
                    "variant_type": "manual_typo",
                    "person_id": member.person_id,
                    "is_erroneous": True,
                }
            )
            name_idx += 1
            ctx.identity_resolution_truth.append(
                {
                    "resolution_id": f"IRT{truth_idx:05d}",
                    "case_id": network.case_id,
                    "person_id": member.person_id,
                    "canonical_name": canonical,
                    "recorded_name": typo,
                    "variant_type": "manual_typo",
                    "notes": "Officer-entered spelling error in FIR/witness sheet.",
                }
            )
            truth_idx += 1

            if fir_row:
                fir_row["complaint_text"] += (
                    f" Subject also referred to as {typo}. "
                    f"Phone noted in station diary as {typo_phone(pick_phone(ctx, member.person_id), ctx.rng)}."
                )

            registered_phone = ctx.person_phones[member.person_id][0]
            wrong_phone = typo_phone(registered_phone, ctx.rng)
            ctx.recorded_phones.append(
                {
                    "record_id": f"RP{phone_idx:05d}",
                    "case_id": network.case_id,
                    "source_type": "fir_entry",
                    "source_id": source_id,
                    "recorded_phone": wrong_phone,
                    "variant_type": "digit_transposition",
                    "person_id": member.person_id,
                    "is_erroneous": True,
                }
            )
            phone_idx += 1
            ctx.recorded_phones.append(
                {
                    "record_id": f"RP{phone_idx:05d}",
                    "case_id": network.case_id,
                    "source_type": "subscriber_record",
                    "source_id": member.person_id,
                    "recorded_phone": registered_phone,
                    "variant_type": "registered",
                    "person_id": member.person_id,
                    "is_erroneous": False,
                }
            )
            phone_idx += 1

    # Decoy wrong names that do not map cleanly to a person.
    for idx in range(120):
        ctx.recorded_names.append(
            {
                "record_id": f"RN{name_idx:05d}",
                "case_id": ctx.rng.choice(ctx.cases),
                "source_type": "field_note",
                "source_id": f"NOTE{idx + 1:04d}",
                "recorded_name": f"{ctx.rng.choice(FIRST_NAMES)} {ctx.rng.choice(LAST_NAMES)}",
                "recorded_dob": "",
                "variant_type": "unresolved_alias",
                "person_id": "",
                "is_erroneous": True,
            }
        )
        name_idx += 1


def generate_crime_networks(ctx: GeneratorContext) -> None:
    """Build intentional multi-person crime scenarios with known ground-truth links."""
    scenario_people = sorted(ctx.scenario_person_ids)
    group_size = len(scenario_people) // COUNTS["crime_networks"]
    if group_size < 3:
        raise ValueError("Not enough scenario participants for crime networks.")

    ctx.crime_networks = []
    for network_idx in range(COUNTS["crime_networks"]):
        start = network_idx * group_size
        member_ids = scenario_people[start : start + group_size]
        case_id = ctx.cases[network_idx]
        roles = NETWORK_ROLE_SETS[network_idx % len(NETWORK_ROLE_SETS)]
        members = [
            NetworkMember(person_id=person_id, role=roles[member_idx])
            for member_idx, person_id in enumerate(member_ids)
        ]
        primary = next(member for member in members if member.role == "suspect")
        crime_type = CRIME_TYPES[network_idx % len(CRIME_TYPES)]
        relationships: list[NetworkRelationship] = []
        relation_types = ["associate", "facilitator", "handler", "business_partner", "family"]
        for member in members:
            if member.person_id == primary.person_id:
                continue
            relationships.append(
                NetworkRelationship(
                    person_id_a=primary.person_id,
                    person_id_b=member.person_id,
                    relationship_type=ctx.rng.choice(relation_types),
                )
            )
        if len(members) >= 3:
            relationships.append(
                NetworkRelationship(
                    person_id_a=members[1].person_id,
                    person_id_b=members[2].person_id,
                    relationship_type="associate",
                )
            )
        ctx.crime_networks.append(
            CrimeNetwork(
                case_id=case_id,
                scenario_name=f"Synthetic {crime_type.replace('_', ' ').title()} {network_idx + 1}",
                crime_type=crime_type,
                members=members,
                relationships=relationships,
                primary_suspect_id=primary.person_id,
            )
        )
        assign_network_complexity(ctx, ctx.crime_networks[-1], network_idx)


def plant_network_evidence(ctx: GeneratorContext) -> None:
    """Insert deliberate calls, payments, chats, and intel for each crime network."""
    ctx.planted_cdr = []
    ctx.planted_transactions = []
    ctx.planted_chats = []
    ctx.planted_surveillance = []
    start = datetime(2023, 1, 1)
    end = datetime(2025, 12, 31)
    location_names = [loc["name"] for loc in ctx.locations]
    network_chat_templates = [
        "Use the alternate account for this transfer.",
        "Meet at the usual spot after the handoff.",
        "Police are asking questions, stay quiet.",
        "Split the amount across the three accounts.",
        "Destroy the old SIM after tonight.",
        "The buyer confirmed, proceed with delivery.",
        "Do not call me on the main line again.",
    ]

    cdr_idx = 1
    txn_idx = 1
    chat_idx = 1
    sur_idx = 1

    for network in ctx.crime_networks:
        member_ids = [member.person_id for member in network.members]
        pairs = {(rel.person_id_a, rel.person_id_b) for rel in network.relationships}
        pairs.update({(b, a) for a, b in pairs})

        cdr_idx, txn_idx = plant_complex_network_paths(
            ctx, network, start, end, location_names, cdr_idx, txn_idx
        )

        direct_cdr = max(10, NETWORK_EVIDENCE["cdr_per_network"] - (12 if network.complexity == "cutout" else 0))
        direct_txn = max(6, NETWORK_EVIDENCE["transactions_per_network"] - (8 if network.complexity == "layered_finance" else 0))

        for _ in range(direct_cdr):
            person_a, person_b = ctx.rng.choice(list(pairs))
            caller = pick_phone(ctx, person_a)
            receiver = pick_phone(ctx, person_b)
            ctx.planted_cdr.append(
                {
                    "cdr_id": f"CDR{cdr_idx:06d}",
                    "caller_phone": caller,
                    "receiver_phone": receiver,
                    "timestamp": random_date(ctx.rng, start, end).strftime("%Y-%m-%d %H:%M:%S"),
                    "duration_seconds": str(ctx.rng.randint(30, 900)),
                    "tower_location": ctx.rng.choice(location_names),
                    "case_id": network.case_id,
                }
            )
            cdr_idx += 1

        for _ in range(direct_txn):
            sender_id, receiver_id = ctx.rng.choice(list(pairs))
            ctx.planted_transactions.append(
                {
                    "transaction_id": f"TXN{txn_idx:06d}",
                    "sender_account": pick_account(ctx, sender_id),
                    "receiver_account": pick_account(ctx, receiver_id),
                    "amount": f"{round(ctx.rng.uniform(25000, 750000), 2):.2f}",
                    "timestamp": random_date(ctx.rng, start, end).strftime("%Y-%m-%d %H:%M:%S"),
                    "case_id": network.case_id,
                }
            )
            txn_idx += 1

        for _ in range(NETWORK_EVIDENCE["chats_per_network"]):
            person_a, person_b = ctx.rng.choice(list(pairs))
            ctx.planted_chats.append(
                {
                    "message_id": f"MSG{chat_idx:07d}",
                    "sender_phone": pick_phone(ctx, person_a),
                    "receiver_phone": pick_phone(ctx, person_b),
                    "timestamp": random_date(ctx.rng, start, end).strftime("%Y-%m-%d %H:%M:%S"),
                    "message_text": ctx.rng.choice(network_chat_templates),
                    "case_id": network.case_id,
                }
            )
            chat_idx += 1

        for member in network.members:
            display_name = typo_name(ctx.person_by_id[member.person_id]["name"], ctx.rng)
            for _ in range(NETWORK_EVIDENCE["surveillance_per_network"]):
                ctx.planted_surveillance.append(
                    {
                        "surveillance_id": f"SUR{sur_idx:05d}",
                        "case_id": network.case_id,
                        "timestamp": random_date(ctx.rng, start, end).strftime("%Y-%m-%d %H:%M:%S"),
                        "location": ctx.rng.choice(location_names),
                        "report_text": (
                            f"Field unit observed individual recorded as '{display_name}' meeting associates "
                            f"near {ctx.rng.choice(location_names)}. Possible link to ongoing case activity."
                        ),
                    }
                )
                sur_idx += 1


def generate_answer_key(ctx: GeneratorContext) -> tuple[list[dict], list[dict]]:
    summary_rows: list[dict] = []
    connection_rows: list[dict] = []
    conn_idx = 1

    for network in ctx.crime_networks:
        roles = "; ".join(f"{member.person_id}:{member.role}" for member in network.members)
        participants = ";".join(member.person_id for member in network.members)
        primary_ids = ";".join(
            member.person_id for member in network.members if member.role in {"suspect", "handler"}
        )
        relationship_pairs = "; ".join(
            f"{rel.person_id_a}-{rel.person_id_b}:{rel.relationship_type}" for rel in network.relationships
        )
        summary_rows.append(
            {
                "case_id": network.case_id,
                "scenario_name": network.scenario_name,
                "crime_type": network.crime_type,
                "complexity": network.complexity,
                "primary_suspect_ids": primary_ids,
                "all_participant_ids": participants,
                "roles": roles,
                "relationship_pairs": relationship_pairs,
                "min_expected_calls": str(NETWORK_EVIDENCE["cdr_per_network"]),
                "min_expected_transactions": str(NETWORK_EVIDENCE["transactions_per_network"]),
                "min_expected_chats": str(NETWORK_EVIDENCE["chats_per_network"]),
                "detection_hint": (
                    f"Resolve identity variants first, then trace {network.primary_suspect_id} "
                    f"via phones/accounts for {network.case_id}."
                ),
                "resolution_notes": network.resolution_notes,
            }
        )

        for rel in network.relationships:
            connection_rows.append(
                {
                    "connection_id": f"AKC{conn_idx:05d}",
                    "case_id": network.case_id,
                    "person_id_a": rel.person_id_a,
                    "person_id_b": rel.person_id_b,
                    "connection_type": rel.relationship_type,
                    "evidence_type": "relationship",
                    "detail": "Ground-truth social link between scenario participants.",
                }
            )
            conn_idx += 1
            phone_a = ctx.person_phones[rel.person_id_a][0]
            phone_b = ctx.person_phones[rel.person_id_b][0]
            connection_rows.append(
                {
                    "connection_id": f"AKC{conn_idx:05d}",
                    "case_id": network.case_id,
                    "person_id_a": rel.person_id_a,
                    "person_id_b": rel.person_id_b,
                    "connection_type": "communication",
                    "evidence_type": "cdr",
                    "detail": f"Planted call/chat trail includes phone pair {phone_a} <-> {phone_b}.",
                }
            )
            conn_idx += 1
            account_a = ctx.person_accounts[rel.person_id_a][0]
            account_b = ctx.person_accounts[rel.person_id_b][0]
            connection_rows.append(
                {
                    "connection_id": f"AKC{conn_idx:05d}",
                    "case_id": network.case_id,
                    "person_id_a": rel.person_id_a,
                    "person_id_b": rel.person_id_b,
                    "connection_type": "financial",
                    "evidence_type": "transaction",
                    "detail": f"Planted payment trail includes accounts {account_a} -> {account_b}.",
                }
            )
            conn_idx += 1

        if network.cutout_person_id:
            connection_rows.append(
                {
                    "connection_id": f"AKC{conn_idx:05d}",
                    "case_id": network.case_id,
                    "person_id_a": network.primary_suspect_id,
                    "person_id_b": network.cutout_person_id,
                    "connection_type": "cutout",
                    "evidence_type": "indirect_path",
                    "detail": "Suspect communicates via background cutout; link via call chain not direct tie.",
                }
            )
            conn_idx += 1
        if network.intermediary_person_id:
            connection_rows.append(
                {
                    "connection_id": f"AKC{conn_idx:05d}",
                    "case_id": network.case_id,
                    "person_id_a": network.primary_suspect_id,
                    "person_id_b": network.intermediary_person_id,
                    "connection_type": "financial_cutout",
                    "evidence_type": "indirect_path",
                    "detail": "Layered transaction path uses intermediary account holder.",
                }
            )
            conn_idx += 1

    return summary_rows, connection_rows


def generate_fir(ctx: GeneratorContext) -> list[dict]:
    rows: list[dict] = []
    start = datetime(2022, 1, 1)
    end = datetime(2025, 12, 31)
    used_pairs: set[tuple[str, str]] = set()
    network_case_ids = [network.case_id for network in ctx.crime_networks]

    for idx in range(COUNTS["fir_initial"]):
        fir_id = f"FIR{idx + 1:05d}"
        if idx < len(network_case_ids):
            case_id = network_case_ids[idx]
            complaint = (
                f"Initial synthetic FIR for planted crime network {case_id}. "
                f"{ctx.rng.choice(FIR_TEMPLATES)}"
            )
        else:
            case_id = ctx.rng.choice(ctx.cases)
            complaint = ctx.rng.choice(FIR_TEMPLATES)
        while (case_id, "initial") in used_pairs and len(used_pairs) < len(ctx.cases):
            case_id = ctx.rng.choice(ctx.cases)
        used_pairs.add((case_id, "initial"))
        rows.append(
            {
                "fir_id": fir_id,
                "case_id": case_id,
                "date": random_date(ctx.rng, start, end).strftime("%Y-%m-%d"),
                "police_station": ctx.rng.choice(POLICE_STATIONS),
                "complaint_text": complaint,
                "report_type": "initial",
            }
        )

    initial_cases = [row["case_id"] for row in rows]
    for idx in range(COUNTS["fir_supplementary"]):
        fir_id = f"FIR{COUNTS['fir_initial'] + idx + 1:05d}"
        case_id = ctx.rng.choice(initial_cases)
        rows.append(
            {
                "fir_id": fir_id,
                "case_id": case_id,
                "date": random_date(ctx.rng, start, end).strftime("%Y-%m-%d"),
                "police_station": ctx.rng.choice(POLICE_STATIONS),
                "complaint_text": f"Supplementary statement added to case {case_id}. "
                f"{ctx.rng.choice(FIR_TEMPLATES)}",
                "report_type": "supplementary",
            }
        )

    return rows


def generate_surveillance(ctx: GeneratorContext) -> list[dict]:
    rows = list(ctx.planted_surveillance)
    start = datetime(2023, 1, 1)
    end = datetime(2025, 12, 31)
    location_names = [loc["name"] for loc in ctx.locations]
    start_idx = len(rows)

    for idx in range(COUNTS["surveillance"] - start_idx):
        rows.append(
            {
                "surveillance_id": f"SUR{start_idx + idx + 1:05d}",
                "case_id": ctx.rng.choice(ctx.cases),
                "timestamp": random_date(ctx.rng, start, end).strftime("%Y-%m-%d %H:%M:%S"),
                "location": ctx.rng.choice(location_names),
                "report_text": ctx.rng.choice(SURVEILLANCE_TEMPLATES),
            }
        )
    return rows


def generate_case_references(ctx: GeneratorContext) -> list[dict]:
    rows = []
    source_types = ["witness_statement", "document_scan", "tip_off", "prior_case_link", "field_note", "lab_summary"]

    for idx in range(COUNTS["case_references"]):
        rows.append(
            {
                "reference_id": f"REF{idx + 1:05d}",
                "case_id": ctx.rng.choice(ctx.cases),
                "source_type": ctx.rng.choice(source_types),
                "reference_text": f"Synthetic case reference record {idx + 1} for investigative cross-check.",
            }
        )
    return rows


def generate_cdr(ctx: GeneratorContext, case_linked_count: int = 18000) -> list[dict]:
    rows = list(ctx.planted_cdr)
    start = datetime(2023, 1, 1)
    end = datetime(2025, 12, 31)
    phone_numbers = [phone["phone_number"] for phone in ctx.phones]
    scenario_numbers = [phone["phone_number"] for phone in ctx.phones if phone["person_id"] in ctx.scenario_person_ids]
    location_names = [loc["name"] for loc in ctx.locations]
    start_idx = len(rows)
    random_case_linked = max(0, case_linked_count - start_idx)

    for idx in range(COUNTS["cdr"] - start_idx):
        linked = idx < random_case_linked and scenario_numbers
        if linked:
            caller = ctx.rng.choice(scenario_numbers)
            receiver = ctx.rng.choice(phone_numbers)
            case_id = ctx.rng.choice(ctx.cases)
        else:
            caller = ctx.rng.choice(phone_numbers)
            receiver = ctx.rng.choice(phone_numbers)
            case_id = ""
        if caller == receiver:
            receiver = ctx.rng.choice(phone_numbers)
        rows.append(
            {
                "cdr_id": f"CDR{start_idx + idx + 1:06d}",
                "caller_phone": caller,
                "receiver_phone": receiver,
                "timestamp": random_date(ctx.rng, start, end).strftime("%Y-%m-%d %H:%M:%S"),
                "duration_seconds": str(ctx.rng.randint(5, 1800)),
                "tower_location": ctx.rng.choice(location_names),
                "case_id": case_id,
            }
        )
    return rows


def generate_transactions(ctx: GeneratorContext, case_linked_count: int = 9000) -> list[dict]:
    rows = list(ctx.planted_transactions)
    start = datetime(2023, 1, 1)
    end = datetime(2025, 12, 31)
    account_numbers = [acct["account_number"] for acct in ctx.accounts]
    scenario_accounts = [
        acct["account_number"] for acct in ctx.accounts if acct["person_id"] in ctx.scenario_person_ids
    ]
    start_idx = len(rows)
    random_case_linked = max(0, case_linked_count - start_idx)

    for idx in range(COUNTS["transactions"] - start_idx):
        linked = idx < random_case_linked and scenario_accounts
        if linked:
            sender = ctx.rng.choice(scenario_accounts)
            receiver = ctx.rng.choice(account_numbers)
            case_id = ctx.rng.choice(ctx.cases)
            amount = round(ctx.rng.uniform(5000, 500000), 2)
        else:
            sender = ctx.rng.choice(account_numbers)
            receiver = ctx.rng.choice(account_numbers)
            case_id = ""
            amount = round(ctx.rng.uniform(100, 25000), 2)
        if sender == receiver:
            receiver = ctx.rng.choice(account_numbers)
        rows.append(
            {
                "transaction_id": f"TXN{start_idx + idx + 1:06d}",
                "sender_account": sender,
                "receiver_account": receiver,
                "amount": f"{amount:.2f}",
                "timestamp": random_date(ctx.rng, start, end).strftime("%Y-%m-%d %H:%M:%S"),
                "case_id": case_id,
            }
        )
    return rows


def generate_chat_messages(ctx: GeneratorContext, case_linked_count: int = 25000) -> list[dict]:
    rows = list(ctx.planted_chats)
    start = datetime(2023, 1, 1)
    end = datetime(2025, 12, 31)
    phone_numbers = [phone["phone_number"] for phone in ctx.phones]
    scenario_numbers = [phone["phone_number"] for phone in ctx.phones if phone["person_id"] in ctx.scenario_person_ids]
    start_idx = len(rows)
    random_case_linked = max(0, case_linked_count - start_idx)

    for idx in range(COUNTS["chat_messages"] - start_idx):
        linked = idx < random_case_linked and scenario_numbers
        if linked:
            sender = ctx.rng.choice(scenario_numbers)
            receiver = ctx.rng.choice(phone_numbers)
            case_id = ctx.rng.choice(ctx.cases)
        else:
            sender = ctx.rng.choice(phone_numbers)
            receiver = ctx.rng.choice(phone_numbers)
            case_id = ""
        if sender == receiver:
            receiver = ctx.rng.choice(phone_numbers)
        rows.append(
            {
                "message_id": f"MSG{start_idx + idx + 1:07d}",
                "sender_phone": sender,
                "receiver_phone": receiver,
                "timestamp": random_date(ctx.rng, start, end).strftime("%Y-%m-%d %H:%M:%S"),
                "message_text": ctx.rng.choice(CHAT_TEMPLATES),
                "case_id": case_id,
            }
        )
    return rows


def generate_relationships(ctx: GeneratorContext) -> list[dict]:
    """Public relationships are noisy/incomplete — ground-truth links stay in private eval only."""
    rows: list[dict] = []
    scenario_people = [person for person in ctx.people if person["person_id"] in ctx.scenario_person_ids]
    relation_types = ["associate", "family", "business_partner", "employer", "tenant", "facilitator"]

    for idx in range(2500):
        person_a, person_b = ctx.rng.sample(scenario_people, 2)
        rows.append(
            {
                "relationship_id": f"REL{idx + 1:05d}",
                "person_id_a": person_a["person_id"],
                "person_id_b": person_b["person_id"],
                "relationship_type": ctx.rng.choice(relation_types),
                "case_id": ctx.rng.choice(ctx.cases),
            }
        )
    return rows


def generate_private_case_roles(ctx: GeneratorContext) -> list[dict]:
    rows: list[dict] = []
    for network in ctx.crime_networks:
        for member in network.members:
            rows.append(
                {
                    "case_role_id": f"CR{len(rows) + 1:05d}",
                    "case_id": network.case_id,
                    "person_id": member.person_id,
                    "role": member.role,
                }
            )
    ctx.private_case_roles = rows
    return rows


def generate_private_events(ctx: GeneratorContext) -> list[dict]:
    rows = []
    start = datetime(2022, 1, 1)
    end = datetime(2025, 12, 31)
    event_types = ["Meeting", "Observation", "Incident", "Property Transfer", "Travel", "Financial Activity"]
    scenario_people = [person for person in ctx.people if person["person_id"] in ctx.scenario_person_ids]
    location_names = [loc["name"] for loc in ctx.locations]

    for idx in range(COUNTS["private_events"]):
        person = ctx.rng.choice(scenario_people)
        event_type = ctx.rng.choice(event_types)
        location = ctx.rng.choice(location_names)
        rows.append(
            {
                "event_id": f"EV{idx + 1:05d}",
                "person_id": person["person_id"],
                "event_type": event_type,
                "timestamp": random_date(ctx.rng, start, end).strftime("%Y-%m-%d %H:%M:%S"),
                "description": f"{event_type} noted near {location} in {person['city']}.",
                "case_id": ctx.rng.choice(ctx.cases),
            }
        )
    return rows


def main() -> None:
    args = parse_args()
    rng = random.Random(args.seed)
    ctx = GeneratorContext(
        rng=rng,
        output_dir=args.output_dir,
        people=[],
        phones=[],
        accounts=[],
        locations=[],
        organizations=[],
        cases=[],
        case_records=[],
        scenario_person_ids=set(),
        crime_networks=[],
        person_phones={},
        person_accounts={},
        planted_cdr=[],
        planted_transactions=[],
        planted_chats=[],
        planted_surveillance=[],
        recorded_names=[],
        recorded_phones=[],
        identity_resolution_truth=[],
        private_case_roles=[],
        person_by_id={},
    )

    print("Generating core entities...")
    generate_people(ctx)
    person_lookup(ctx)
    generate_locations(ctx)
    generate_organizations(ctx)
    generate_cases(ctx)
    generate_phones(ctx)
    generate_bank_accounts(ctx)
    ensure_scenario_assets(ctx)
    generate_crime_networks(ctx)
    for network in ctx.crime_networks:
        for record in ctx.case_records:
            if record["case_id"] == network.case_id:
                record["title"] = network.scenario_name
                record["description"] = (
                    f"Synthetic {network.crime_type.replace('_', ' ')} case with planted multi-source evidence."
                )
                record["status"] = "OPEN"
                break
    plant_network_evidence(ctx)

    print("Generating vehicles and relationship data...")
    vehicles = []
    used_regs: set[str] = set()
    person_ids = [person["person_id"] for person in ctx.people]
    weights = [3 if pid in ctx.scenario_person_ids else 1 for pid in person_ids]
    for idx in range(COUNTS["vehicles"]):
        vehicles.append(
            {
                "vehicle_id": f"V{idx + 1:05d}",
                "registration_number": random_vehicle_reg(ctx.rng, used_regs),
                "person_id": ctx.rng.choices(person_ids, weights=weights, k=1)[0],
            }
        )

    ownership_rows = []
    start = datetime(2018, 1, 1)
    end = datetime(2025, 12, 31)
    for idx in range(3200):
        asset_type = ctx.rng.choice(["phone", "vehicle", "bank_account"])
        if asset_type == "phone":
            asset = ctx.rng.choice(ctx.phones)
            asset_id = asset["phone_id"]
            owner = asset["person_id"]
        elif asset_type == "vehicle":
            asset = ctx.rng.choice(vehicles)
            asset_id = asset["vehicle_id"]
            owner = asset["person_id"]
        else:
            asset = ctx.rng.choice(ctx.accounts)
            asset_id = asset["account_id"]
            owner = asset["person_id"]
        ownership_rows.append(
            {
                "ownership_id": f"OWN{idx + 1:05d}",
                "asset_type": asset_type,
                "asset_id": asset_id,
                "person_id": owner,
                "valid_from": random_date(ctx.rng, start, end).strftime("%Y-%m-%d"),
                "valid_to": "",
            }
        )

    print("Generating investigative records...")
    fir_rows = generate_fir(ctx)
    generate_identity_noise(ctx, fir_rows)
    surveillance_rows = generate_surveillance(ctx)
    case_reference_rows = generate_case_references(ctx)
    generate_private_case_roles(ctx)
    relationship_rows = generate_relationships(ctx)

    print("Generating high-volume activity data...")
    cdr_rows = generate_cdr(ctx)
    transaction_rows = generate_transactions(ctx)
    chat_rows = generate_chat_messages(ctx)
    private_event_rows = generate_private_events(ctx)

    output = args.output_dir
    print(f"Writing CSV files to {output.resolve()}...")

    write_csv(output / "people.csv", ["person_id", "name", "dob", "gender", "city"], ctx.people)
    write_csv(
        output / "cdr.csv",
        ["cdr_id", "caller_phone", "receiver_phone", "timestamp", "duration_seconds", "tower_location", "case_id"],
        cdr_rows,
    )
    write_csv(
        output / "transactions.csv",
        ["transaction_id", "sender_account", "receiver_account", "amount", "timestamp", "case_id"],
        transaction_rows,
    )
    write_csv(output / "vehicles.csv", ["vehicle_id", "registration_number", "person_id"], vehicles)
    write_csv(
        output / "fir.csv",
        ["fir_id", "case_id", "date", "police_station", "complaint_text"],
        [{k: row[k] for k in ["fir_id", "case_id", "date", "police_station", "complaint_text"]} for row in fir_rows],
    )
    write_csv(
        output / "surveillance.csv",
        ["surveillance_id", "case_id", "timestamp", "location", "report_text"],
        surveillance_rows,
    )

    write_csv(output / "phones.csv", ["phone_id", "phone_number", "person_id"], ctx.phones)
    write_csv(output / "bank_accounts.csv", ["account_id", "account_number", "person_id", "bank_name"], ctx.accounts)
    write_csv(output / "locations.csv", ["location_id", "name", "city"], ctx.locations)
    write_csv(output / "organizations.csv", ["org_id", "name", "org_type", "city"], ctx.organizations)
    write_csv(
        output / "cases.csv",
        ["case_id", "title", "description", "status", "created_at"],
        ctx.case_records,
    )
    write_csv(
        output / "case_references.csv",
        ["reference_id", "case_id", "source_type", "reference_text"],
        case_reference_rows,
    )
    write_csv(
        output / "chat_messages.csv",
        ["message_id", "sender_phone", "receiver_phone", "timestamp", "message_text", "case_id"],
        chat_rows,
    )
    write_csv(
        output / "relationships.csv",
        ["relationship_id", "person_id_a", "person_id_b", "relationship_type", "case_id"],
        relationship_rows,
    )
    write_csv(
        output / "recorded_names.csv",
        [
            "record_id",
            "case_id",
            "source_type",
            "source_id",
            "recorded_name",
            "recorded_dob",
            "variant_type",
            "person_id",
            "is_erroneous",
        ],
        ctx.recorded_names,
    )
    write_csv(
        output / "recorded_phones.csv",
        [
            "record_id",
            "case_id",
            "source_type",
            "source_id",
            "recorded_phone",
            "variant_type",
            "person_id",
            "is_erroneous",
        ],
        ctx.recorded_phones,
    )
    write_csv(
        output / "private_events.csv",
        ["event_id", "person_id", "event_type", "timestamp", "description", "case_id"],
        private_event_rows,
    )
    write_csv(
        output / "ownership_history.csv",
        ["ownership_id", "asset_type", "asset_id", "person_id", "valid_from", "valid_to"],
        ownership_rows,
    )
    write_csv(
        output / "fir_metadata.csv",
        ["fir_id", "case_id", "report_type"],
        [{"fir_id": row["fir_id"], "case_id": row["case_id"], "report_type": row["report_type"]} for row in fir_rows],
    )

    private_dir = args.private_dir
    private_dir.mkdir(parents=True, exist_ok=True)
    answer_key_rows, answer_key_connections = generate_answer_key(ctx)
    write_csv(
        private_dir / "answer_key.csv",
        [
            "case_id",
            "scenario_name",
            "crime_type",
            "complexity",
            "primary_suspect_ids",
            "all_participant_ids",
            "roles",
            "relationship_pairs",
            "min_expected_calls",
            "min_expected_transactions",
            "min_expected_chats",
            "detection_hint",
            "resolution_notes",
        ],
        answer_key_rows,
    )
    write_csv(
        private_dir / "answer_key_connections.csv",
        [
            "connection_id",
            "case_id",
            "person_id_a",
            "person_id_b",
            "connection_type",
            "evidence_type",
            "detail",
        ],
        answer_key_connections,
    )
    write_csv(
        private_dir / "case_roles_truth.csv",
        ["case_role_id", "case_id", "person_id", "role"],
        ctx.private_case_roles,
    )
    write_csv(
        private_dir / "identity_resolution_truth.csv",
        ["resolution_id", "case_id", "person_id", "canonical_name", "recorded_name", "variant_type", "notes"],
        ctx.identity_resolution_truth,
    )

    for stale in (
        output / "answer_key.csv",
        output / "answer_key_connections.csv",
        output / "case_roles.csv",
    ):
        if stale.exists():
            stale.unlink()

    summary = {
        "people": len(ctx.people),
        "scenario_people": len(ctx.scenario_person_ids),
        "crime_networks": len(ctx.crime_networks),
        "answer_key_cases": len(answer_key_rows),
        "recorded_names": len(ctx.recorded_names),
        "recorded_phones": len(ctx.recorded_phones),
        "phones": len(ctx.phones),
        "vehicles": len(vehicles),
        "bank_accounts": len(ctx.accounts),
        "locations": len(ctx.locations),
        "organizations": len(ctx.organizations),
        "cases": len(ctx.case_records),
        "cdr": len(cdr_rows),
        "transactions": len(transaction_rows),
        "fir_total": len(fir_rows),
        "fir_initial": COUNTS["fir_initial"],
        "fir_supplementary": COUNTS["fir_supplementary"],
        "surveillance": len(surveillance_rows),
        "case_references": len(case_reference_rows),
        "chat_messages": len(chat_rows),
        "private_events": len(private_event_rows),
        "relationships": len(relationship_rows),
        "ownership_history": len(ownership_rows),
    }

    print(f"\nPrivate eval written to {private_dir.resolve()} (admin only)")

    print("\nDataset generation complete:")
    for key, value in summary.items():
        print(f"  {key}: {value:,}")


if __name__ == "__main__":
    main()

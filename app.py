from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from datetime import date
from collections import deque, defaultdict
import time
import pandas as pd
import os
import smtplib
from email.mime.text import MIMEText
def send_email(to_email, subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = os.environ["EMAIL_USER"]
    msg["To"] = to_email

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(
            os.environ["EMAIL_USER"],
            os.environ["EMAIL_PASS"]
        )
        server.send_message(msg)
ALLOWED_ORIGINS = ["https://ciphercontinuum.com", "https://theciphercontinuum.com"]
TARGET_EQUATION = "C127_3434"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class Payload(BaseModel):
    name: str
    dob: str


@app.get("/health")
def health():
    return {"ok": True}


def compute_number(name: str, dob: str) -> dict:
    name_value = sum((ord(c.lower()) - 96) for c in name if c.isalpha())

    # dob still arrives as YYYY-MM-DD from Shopify,
    # but Numeromancy uses only month and day.
    y, m, d = map(int, dob.split("-"))

    numeric_name = name_value + m + d

    return {
        "result": numeric_name,
        "breakdown": {
            "name_value": name_value,
            "month": m,
            "day": d,
            "formula": "name_value + month + day"
        }
    }


def load_equations():
    df = pd.read_excel("Elahl_Parsed_Equations_FULL.xlsx", sheet_name=0)
    if "equation" not in df.columns:
        raise HTTPException(status_code=500, detail="Missing equation column")
    return df["equation"].dropna().astype(str).tolist()


def parse_eq(eq):
    if "_" not in eq:
        return None

    left, right = eq.split("_", 1)
    main = "".join(c for c in left if c.isdigit())
    bridge = "".join(c for c in right if c.isdigit())

    if not main or not bridge:
        return None

    return {"eq": eq, "main": main, "bridge": bridge}


def family_of(p):
    fam = set()
    fam.add(p["main"])
    fam.add(p["main"][::-1])
    fam.add(p["bridge"])
    fam.add(p["bridge"][::-1])

    if len(p["bridge"]) >= 3:
        first3 = p["bridge"][:3]
        last3 = p["bridge"][-3:]
        fam.update([first3, last3, first3[::-1], last3[::-1]])

    return fam


def build_map(equations):
    lookup = {}
    index = defaultdict(list)

    for eq in equations:
        p = parse_eq(eq)
        if not p:
            continue

        fam = family_of(p)
        lookup[eq] = fam

        for n in fam:
            index[n].append(eq)

    return lookup, index


# tiny in-memory rate limit
BUCKET = {}
RATE = 30


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    ip = request.headers.get("x-forwarded-for", request.client.host).split(",")[0].strip()
    now = int(time.time())
    reset = now // 3600

    if ip not in BUCKET or BUCKET[ip][0] != reset:
        BUCKET[ip] = [reset, RATE]
    else:
        if BUCKET[ip][1] == 0:
            from fastapi.responses import JSONResponse
            return JSONResponse({"error": "Rate limit exceeded"}, status_code=429)
        BUCKET[ip][1] -= 1

    return await call_next(request)


@app.post("/api/compute-name-number")
def compute(payload: Payload):
    try:
        date.fromisoformat(payload.dob)
    except:
        raise HTTPException(status_code=400, detail="Invalid date (YYYY-MM-DD)")

    out = compute_number(payload.name, payload.dob)
    out["version"] = "v1.0.0"
    return out


@app.post("/api/numeromancy-report")
def numeromancy_report(payload: Payload):
    result = corridor_55_debug(payload)

    intro = (
        "Your Numeric Name has generated three preview corridors. "
"The equations below are the first steps of your pathway. "
"The complete report contains 55 equations leading toward the final convergence: C127_3434."
    )

    return {
        "numeric_name": result["numeric_name"],
        "intro": intro,
        "preview_3_equations": result["preview_3_equations"],
        "full_55_equations": result["full_55_equations"],
        "equation_count": result["equation_count"],
        "final_equation": result["final_equation"]
    }

@app.post("/api/corridor-debug")
def corridor_debug(payload: Payload):
    try:
        date.fromisoformat(payload.dob)
    except:
        raise HTTPException(status_code=400, detail="Invalid date (YYYY-MM-DD)")

    result = compute_number(payload.name, payload.dob)
    numeric_name = result["result"]

    equations = load_equations()
    lookup, index = build_map(equations)

    start_keys = {str(numeric_name), str(numeric_name)[::-1]}
    starts = []
    for key in start_keys:
        starts.extend(index.get(key, []))

    starts = list(dict.fromkeys(starts))

    queue = deque([[s] for s in starts])
    visited = set(starts)
    path = []

    while queue:
        current_path = queue.popleft()
        current = current_path[-1]

        if current == TARGET_EQUATION:
            path = current_path
            break

        if len(current_path) >= 55:
            continue

        fam = lookup.get(current, set())
        next_eqs = []

        for n in fam:
            next_eqs.extend(index.get(n, []))

        next_eqs = list(dict.fromkeys(next_eqs))

        for nx in next_eqs:
            if nx not in visited:
                visited.add(nx)
                queue.append(current_path + [nx])

    return {
        "numeric_name": numeric_name,
        "start_candidates": starts[:5],
        "path_found": bool(path),
        "path_length": len(path),
        "path_preview": path[:10],
        "final_equation": path[-1] if path else None,
    }
@app.post("/api/corridor-55-debug")
def corridor_55_debug(payload: Payload):
    try:
        date.fromisoformat(payload.dob)
    except:
        raise HTTPException(status_code=400, detail="Invalid date (YYYY-MM-DD)")

    result = compute_number(payload.name, payload.dob)
    numeric_name = result["result"]

    equations = load_equations()
    lookup, index = build_map(equations)

    # First: find the real path to C127_3434
    start_keys = {str(numeric_name), str(numeric_name)[::-1]}
    starts = []
    for key in start_keys:
        starts.extend(index.get(key, []))

    starts = list(dict.fromkeys(starts))

    # If the viewer's number is already 127, do not start with the final anchor.
    # The final anchor must remain equation 55.
    starts = [eq for eq in starts if eq != TARGET_EQUATION]
    queue = deque([[s] for s in starts])
    visited = set(starts)
    path = []

    while queue:
        current_path = queue.popleft()
        current = current_path[-1]

        if current == TARGET_EQUATION:
            path = current_path
            break

        if len(current_path) >= 55:
            continue

        fam = lookup.get(current, set())
        next_eqs = []

        for n in fam:
            next_eqs.extend(index.get(n, []))

        next_eqs = list(dict.fromkeys(next_eqs))

        for nx in next_eqs:
            if nx not in visited:
                visited.add(nx)
                queue.append(current_path + [nx])

    if not path:
        return {
            "numeric_name": numeric_name,
            "path_found": False,
            "message": "No path to C127_3434 found."
        }

    # Second: expand path into 54 related unused equations
    base_path = path[:-1]  # remove C127_3434 temporarily
    expanded = list(base_path)
    used = set(expanded)
    i = 0

    while len(expanded) < 54 and expanded:
        current = expanded[i % len(expanded)]
        fam = lookup.get(current, set())

        candidates = []
        for n in fam:
            candidates.extend(index.get(n, []))

        candidates = [eq for eq in dict.fromkeys(candidates) if eq not in used and eq != TARGET_EQUATION]

        if candidates:
            chosen = candidates[0]
            expanded.append(chosen)
            used.add(chosen)
        else:
            i += 1
            if i > len(expanded) * 3:
                break

    full_55 = expanded[:54] + [TARGET_EQUATION]

    return {
        "numeric_name": numeric_name,
        "path_found": True,
        "original_path_length": len(path),
        "original_path": path,
        "equation_count": len(full_55),
        "preview_3_equations": full_55[:3],
        "first_10_equations": full_55[:10],
        "full_55_equations": full_55,
        "final_equation": full_55[-1]
    }
@app.post("/api/corridor-3-debug")
def corridor_3_debug(payload: Payload):
    try:
        date.fromisoformat(payload.dob)
    except:
        raise HTTPException(status_code=400, detail="Invalid date (YYYY-MM-DD)")

    result = compute_number(payload.name, payload.dob)
    numeric_name = result["result"]

    equations = load_equations()
    lookup, index = build_map(equations)

    start_keys = {str(numeric_name), str(numeric_name)[::-1]}
    starts = []
    for key in start_keys:
        starts.extend(index.get(key, []))

    starts = list(dict.fromkeys(starts))
    starts = [eq for eq in starts if eq != TARGET_EQUATION]

    def build_55_from_start(start_eq):
        base_path = [start_eq]
        expanded = list(base_path)
        used = set(expanded)
        i = 0

        while len(expanded) < 54 and expanded:
            current = expanded[i % len(expanded)]
            fam = lookup.get(current, set())

            candidates = []
            for n in fam:
                candidates.extend(index.get(n, []))

            candidates = [
                eq for eq in dict.fromkeys(candidates)
                if eq not in used and eq != TARGET_EQUATION
            ]

            if candidates:
                chosen = candidates[0]
                expanded.append(chosen)
                used.add(chosen)
            else:
                i += 1
                if i > len(expanded) * 3:
                    break

        full_55 = expanded[:54] + [TARGET_EQUATION]

        return {
            "start_equation": start_eq,
            "equation_count": len(full_55),
            "preview_3_equations": full_55[:3],
            "first_10_equations": full_55[:10],
            "full_55_equations": full_55,
            "final_equation": full_55[-1]
        }

    corridors = []
    for start in starts[:3]:
        corridors.append(build_55_from_start(start))

    return {
        "numeric_name": numeric_name,
        "start_candidates": starts[:10],
        "corridor_count": len(corridors),
        "corridors": corridors
    }
@app.post("/api/archive-mine-debug")
def archive_mine_debug(payload: Payload):
    try:
        date.fromisoformat(payload.dob)
    except:
        raise HTTPException(status_code=400, detail="Invalid date (YYYY-MM-DD)")

    result = corridor_3_debug(payload)

    mined = []

    for idx, corridor in enumerate(result["corridors"], start=1):
        equations = corridor["full_55_equations"]

        digit_families = defaultdict(int)

        for eq in equations:
            p = parse_eq(eq)
            if not p:
                continue

            fam = family_of(p)

            for n in fam:
                digit_families[n] += 1

        top_families = sorted(
            digit_families.items(),
            key=lambda x: x[1],
            reverse=True
        )[:12]

        mined.append({
            "corridor": idx,
            "start_equation": corridor["start_equation"],
            "preview_3_equations": corridor["preview_3_equations"],
            "top_digit_families": top_families,
            "final_equation": corridor["final_equation"]
        })

    return {
        "numeric_name": result["numeric_name"],
        "corridor_count": result["corridor_count"],
        "mining_note": "Top digit families show which number-neighborhoods dominate each corridor.",
        "corridors": mined
    }
@app.post("/api/shopify-order-paid")
async def shopify_order_paid(request: Request):
    data = await request.json()
    print("SHOPIFY DEBUG:", "email=", data.get("email"), "properties=", [item.get("properties", []) for item in data.get("line_items", [])], flush=True)

    email = data.get("email")
    line_items = data.get("line_items", [])

    name = None
    dob = None

    for item in line_items:
        props = item.get("properties", [])

        for p in props:
            prop_name = p.get("name")
            prop_value = p.get("value")

            if prop_name == "name":
                name = prop_value

            if prop_name == "dob" or prop_name == "_dob":
                dob = prop_value

            if prop_name == "birth_date" and not dob:
                month, day = prop_value.split("/")
                dob = f"1990-{month}-{day}"

    if not name or not dob:
        print("SHOPIFY BRANCH: missing data", "name=", name, "dob=", dob, flush=True)
        return {
            "status": "missing data",
            "email": email,
            "name": name,
            "dob": dob
        }

    result = corridor_3_debug(Payload(name=name, dob=dob))

    corridors = result.get("corridors", [])
    numeric_name = result.get("numeric_name")

    if len(corridors) != 3:
        print("SHOPIFY BRANCH: corridor count failure", "count=", len(corridors), flush=True)
        return {
            "status": "qc_required",
            "reason": "Expected 3 corridors",
            "email": email,
            "name": name,
            "dob": dob,
            "numeric_name": numeric_name,
            "corridor_count": len(corridors)
        }

    corridor_sections = []
    total_equations = 0

    for idx, corridor in enumerate(corridors, start=1):
        equations = corridor.get("full_55_equations", [])

        if len(equations) != 55:
            print("SHOPIFY BRANCH: equation count failure", "corridor=", idx, "count=", len(equations), flush=True)
            return {
                "status": "qc_required",
                "reason": f"Corridor {idx} does not contain 55 equations",
                "email": email,
                "name": name,
                "dob": dob,
                "numeric_name": numeric_name,
                "corridor": idx,
                "equation_count": len(equations)
            }

        total_equations += len(equations)

        corridor_text = "\n".join(equations)

        corridor_sections.append(
            f"""
CORRIDOR {idx}
Start Equation: {corridor.get("start_equation")}
Equation Count: {len(equations)}

{corridor_text}

Final Equation:
{corridor.get("final_equation")}
"""
        )

    if total_equations != 165:
        print("SHOPIFY BRANCH: total equation failure", "total=", total_equations, flush=True)
        return {
            "status": "qc_required",
            "reason": "Expected 165 total equations",
            "email": email,
            "name": name,
            "dob": dob,
            "numeric_name": numeric_name,
            "equations_count": total_equations
        }

    all_corridors_text = "\n".join(corridor_sections)

    message = f"""
NUMEROMANCY PRODUCTION SYSTEM v1.0
QUALITY-CONTROL PACKET

────────────────

Customer Name:
{name}

Customer Email:
{email}

Date of Birth:
{dob}

Numeric Name:
{numeric_name}

Corridor Families:
3

Equations per Corridor:
55

Total Equations:
165

────────────────

{all_corridors_text}

────────────────

QUALITY-CONTROL PAUSE

Verify before customer delivery:

1. Customer name
2. Numeric Name
3. Three corridor families
4. Fifty-five equations per corridor
5. One hundred sixty-five total equations
6. Final convergence
7. Manuscript variable replacement
8. Cover personalization
9. Digital PDF
10. Print-ready PDF

DO NOT DELIVER TO CUSTOMER
until final manuscript QC is approved.

────────────────

The Cipher Continuum
Numeromancy Production System v1.0

© 2026 Fawaz Elahl
"""

    import urllib.request
    import json

    qc_email = os.environ.get("EMAIL_USER")

    if not qc_email:
        print("SHOPIFY BRANCH: qc email not configured", flush=True)
        return {
            "status": "165 equations generated - qc email not configured",
            "customer_email": email,
            "name": name,
            "dob": dob,
            "numeric_name": numeric_name,
            "corridor_count": len(corridors),
            "equations_count": total_equations
        }

    send_email(
        qc_email,
        f"Numeromancy QC — {name} — Numeric Name {numeric_name}",
        message
    )

    print("SHOPIFY BRANCH: QC email sent", flush=True)

    return {
        "status": "165 equations generated - awaiting qc",
        "customer_email": email,
        "qc_email": qc_email,
        "name": name,
        "dob": dob,
        "numeric_name": numeric_name,
        "corridor_count": len(corridors),
        "equations_count": total_equations,
        "final_equations": [
            corridor.get("final_equation")
            for corridor in corridors
        ]
    }

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
        "Your Numeric Name opens a corridor of connected equations. "
        "The first three equations begin your preview in sequence. "
        "The full 55-equation report leads toward the final convergence: C127_3434."
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
@app.post("/api/shopify-order-paid")
async def shopify_order_paid(request: Request):
    data = await request.json()

    email = data.get("email")
    line_items = data.get("line_items", [])

    # Extract properties
    name = None
    dob = None

    for item in line_items:
        props = item.get("properties", [])
        for p in props:
            if p.get("name") == "name":
                name = p.get("value")
            if p.get("name") == "dob":
                dob = p.get("value")

    if not name or not dob:
        return {"status": "missing data"}

    # Generate report
    result = corridor_55_debug(
        Payload(name=name, dob=dob)
    )

    # Prepare email content
    equations = "\n".join(result["full_55_equations"])

    message = f"""
Hello {name},

Here is your 55-Equation Numeromancy Report:

{equations}

Final Convergence:
{result["final_equation"]}

— The Cipher Continuum
"""

    # For now: print instead of sending email
    print("=== SEND EMAIL TO ===", email)
    print(message)

    return {
        "status": "report generated",
        "email": email,
        "equations_count": len(result["full_55_equations"])
    }

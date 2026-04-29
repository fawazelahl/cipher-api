from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from datetime import date
from collections import deque, defaultdict
import time
import re
import pandas as pd

ALLOWED_ORIGINS = ["https://ciphercontinuum.com", "https://theciphercontinuum.com"]

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

TARGET_EQUATION = "C127_3434"


class Payload(BaseModel):
    name: str
    dob: str  # YYYY-MM-DD


@app.get("/health")
def health():
    return {"ok": True}


def compute_number(name: str, dob: str) -> dict:
    name_value = sum((ord(c.lower()) - 96) for c in name if c.isalpha())
    y, m, d = map(int, dob.split("-"))
    dob_value = (y + m + d) % 1000
    return {
        "result": name_value + dob_value,
        "breakdown": {"name_value": name_value, "dob_value": dob_value},
    }


def load_real_equations():
    df = pd.read_excel("Elahl_Parsed_Equations_FULL.xlsx", sheet_name=0)

    if "equation" not in df.columns:
        raise HTTPException(
            status_code=500,
            detail="Excel file must contain column named 'equation'",
        )

    return df["equation"].dropna().astype(str).tolist()


def parse_eq(eq: str):
    eq = eq.strip()

    if "_" not in eq:
        return None

    left, bridge = eq.split("_", 1)

    main_digits = "".join(ch for ch in left if ch.isdigit())
    bridge_digits = "".join(ch for ch in bridge if ch.isdigit())

    if not main_digits or not bridge_digits:
        return None

    return {
        "equation": eq,
        "main": main_digits,
        "bridge": bridge_digits,
    }


def family_of(parsed):
    main = parsed["main"]
    bridge = parsed["bridge"]

    fam = set()
    fam.add(main)
    fam.add(main[::-1])

    # Include whole bridge too
    fam.add(bridge)
    fam.add(bridge[::-1])

    if len(bridge) >= 3:
        first3 = bridge[:3]
        last3 = bridge[-3:]
        fam.add(first3)
        fam.add(last3)
        fam.add(first3[::-1])
        fam.add(last3[::-1])

    return fam


def build_indices(equations):
    lookup = {}
    num_index = defaultdict(list)

    for eq in equations:
        parsed = parse_eq(eq)
        if not parsed:
            continue

        fam = family_of(parsed)
        lookup[eq] = {"parsed": parsed, "family": fam}

        for n in fam:
            num_index[n].append(eq)

    return lookup, num_index


def find_path(equations, start_number: int, max_depth: int = 55):
    lookup, num_index = build_indices(equations)

    if TARGET_EQUATION not in lookup:
        return []

    start = str(start_number)
    start_keys = {start, start[::-1]}

    starts = []
    for key in start_keys:
        starts.extend(num_index.get(key, []))

    starts = list(dict.fromkeys(starts))

    if not starts:
        return []

    queue = deque([[s] for s in starts])
    visited = set(starts)

    while queue:
        path = queue.popleft()
        current = path[-1]

        if current == TARGET_EQUATION:
            return path

        if len(path) >= max_depth:
            continue

        current_family = lookup[current]["family"]

        next_equations = []
        for number in current_family:
            next_equations.extend(num_index.get(number, []))

        next_equations = list(dict.fromkeys(next_equations))

        for next_eq in next_equations:
            if next_eq not in visited:
                visited.add(next_eq)
                queue.append(path + [next_eq])

    return []


def to_55(path):
    if not path:
        return []

    if path[-1] != TARGET_EQUATION:
        return []

    if len(path) == 55:
        return path

    if len(path) > 55:
        return []

    needed = 55 - len(path)
    base = path[:-1]

    if not base:
        return []

    filler = []
    i = 0

    while len(filler) < needed:
        filler.append(base[i % len(base)])
        i += 1

    return path[:-1] + filler + [TARGET_EQUATION]


# tiny in-memory rate limit (30 req/hour/IP)
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

    t0 = time.time()
    out = compute_number(payload.name, payload.dob)
    out["version"] = "v1.0.0"
    out["latency_ms"] = int((time.time() - t0) * 1000)
    return out


@app.post("/api/numeromancy-report")
def numeromancy_report(payload: Payload):
    try:
        date.fromisoformat(payload.dob)
    except:
        raise HTTPException(status_code=400, detail="Invalid date (YYYY-MM-DD)")

    result = compute_number(payload.name, payload.dob)
    numeric_name = result["result"]

    equations = load_real_equations()

    raw_path = find_path(equations, numeric_name, max_depth=55)
    full_55 = to_55(raw_path)

    intro = (
        "Your Numeric Name opens a corridor of connected equations. "
        "This preview is drawn from the real equation library and directed toward "
        "the final convergence: C127_3434."
    )

    if not full_55:
        num = str(numeric_name)
        rev = num[::-1]
        matches = [eq for eq in equations if num in eq or rev in eq]
        preview = matches[:3] if matches else ["C127_3434"]

        return {
            "numeric_name": numeric_name,
            "intro": intro,
            "preview_3_equations": preview,
            "path_found": False,
            "raw_path_length": len(raw_path),
            "paid_report_message": "Unlock the full 55-Equation Numeromancy Report for $5 CAD.",
        }

    return {
        "numeric_name": numeric_name,
        "intro": intro,
        "preview_3_equations": full_55[:3],
        "full_55_equations": full_55,
        "equation_count": len(full_55),
        "final_anchor": TARGET_EQUATION,
        "path_found": True,
        "paid_report_message": "Unlock the full 55-Equation Numeromancy Report for $5 CAD.",
    }

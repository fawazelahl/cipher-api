from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from datetime import date
import time

ALLOWED_ORIGINS = ["https://ciphercontinuum.com", "https://theciphercontinuum.com"]

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
    y, m, d = map(int, dob.split("-"))
    dob_value = (y + m + d) % 1000
    return {
        "result": name_value + dob_value,
        "breakdown": {"name_value": name_value, "dob_value": dob_value}
    }

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

    import pandas as pd

    result = compute_number(payload.name, payload.dob)
    numeric_name = result["result"]

    df = pd.read_excel("Elahl_Parsed_Equations_FULL.xlsx", sheet_name=0)

    if "equation" not in df.columns:
        raise HTTPException(
            status_code=500,
            detail="Excel file must contain column named 'equation'"
        )

    equations = df["equation"].dropna().astype(str).tolist()

    num = str(numeric_name)
    rev = num[::-1]

    matches = [eq for eq in equations if num in eq or rev in eq]

    preview = matches[:3] if matches else ["C127_3434"]

    intro = (
        "Your Numeric Name opens a corridor of meaning. "
        "This preview is drawn from the real equation library. "
        "The full 55-equation report will be shaped toward C127_3434."
    )

    return {
        "numeric_name": numeric_name,
        "intro": intro,
        "preview_3_equations": preview,
        "matching_equations_found": len(matches),
        "paid_report_message": "Unlock the full 55-Equation Numeromancy Report for $5 CAD."
    }
    @app.post("/api/corridor-debug")
def corridor_debug(payload: Payload):
    try:
        date.fromisoformat(payload.dob)
    except:
        raise HTTPException(status_code=400, detail="Invalid date (YYYY-MM-DD)")

    import pandas as pd
    from collections import deque, defaultdict

    result = compute_number(payload.name, payload.dob)
    numeric_name = result["result"]

    df = pd.read_excel("Elahl_Parsed_Equations_FULL.xlsx", sheet_name=0)
    equations = df["equation"].dropna().astype(str).tolist()

    def parse_eq(eq):
        if "_" not in eq:
            return None
        left, right = eq.split("_", 1)
        main = "".join(c for c in left if c.isdigit())
        bridge = "".join(c for c in right if c.isdigit())
        if not main or not bridge:
            return None
        return {"eq": eq, "main": main, "bridge": bridge}

    def family(p):
        f = set()
        f.add(p["main"])
        f.add(p["main"][::-1])
        f.add(p["bridge"])
        f.add(p["bridge"][::-1])
        if len(p["bridge"]) >= 3:
            f3 = p["bridge"][:3]
            l3 = p["bridge"][-3:]
            f.update([f3, l3, f3[::-1], l3[::-1]])
        return f

    parsed = []
    for eq in equations:
        p = parse_eq(eq)
        if p:
            p["family"] = family(p)
            parsed.append(p)

    lookup = {p["eq"]: p for p in parsed}
    index = defaultdict(list)
    for p in parsed:
        for n in p["family"]:
            index[n].append(p["eq"])

    TARGET = "C127_3434"

    start_keys = {str(numeric_name), str(numeric_name)[::-1]}
    starts = []
    for k in start_keys:
        starts.extend(index.get(k, []))

    starts = list(dict.fromkeys(starts))

    queue = deque([[s] for s in starts])
    visited = set(starts)

    path = []

    while queue:
        current_path = queue.popleft()
        current = current_path[-1]

        if current == TARGET:
            path = current_path
            break

        if len(current_path) >= 55:
            continue

        fam = lookup.get(current, {}).get("family", set())

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
        "path_found": len(path) > 0,
        "path_length": len(path),
        "path_preview": path[:10],
        "final_equation": path[-1] if path else None
    }

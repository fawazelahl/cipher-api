TARGET_EQUATION = "C127_3434"
EXPECTED_CORRIDORS = 3
EQUATIONS_PER_CORRIDOR = 55
EXPECTED_TOTAL_EQUATIONS = 165


def validate_engine_result(engine_result):
    corridors = engine_result.get("corridors", [])

    if len(corridors) != EXPECTED_CORRIDORS:
        raise ValueError(
            f"QC FAILED: expected {EXPECTED_CORRIDORS} corridors, "
            f"received {len(corridors)}"
        )

    total_equations = 0

    for index, corridor in enumerate(corridors, start=1):
        equations = corridor.get("full_55_equations", [])

        if len(equations) != EQUATIONS_PER_CORRIDOR:
            raise ValueError(
                f"QC FAILED: corridor {index} contains "
                f"{len(equations)} equations; expected "
                f"{EQUATIONS_PER_CORRIDOR}"
            )

        if equations[-1] != TARGET_EQUATION:
            raise ValueError(
                f"QC FAILED: corridor {index} ends at "
                f"{equations[-1]}, not {TARGET_EQUATION}"
            )

        total_equations += len(equations)

    if total_equations != EXPECTED_TOTAL_EQUATIONS:
        raise ValueError(
            f"QC FAILED: received {total_equations} total equations; "
            f"expected {EXPECTED_TOTAL_EQUATIONS}"
        )

    return {
        "status": "qc_passed",
        "corridor_count": len(corridors),
        "equations_per_corridor": EQUATIONS_PER_CORRIDOR,
        "total_equations": total_equations,
        "final_equation": TARGET_EQUATION,
    }

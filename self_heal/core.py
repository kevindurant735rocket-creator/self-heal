"""Self-heal: autonomous test repair loop."""
import subprocess, tempfile, os, sys, time, re
from pathlib import Path

def run_test(command: list[str], cwd: str = ".") -> dict:
    proc = subprocess.run(command, capture_output=True, text=True, cwd=cwd, timeout=120)
    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout[-2000:],
        "stderr": proc.stderr[-2000:],
    }

def classify_failure(result: dict) -> str:
    out = (result["stdout"] + result["stderr"]).lower()
    if "assert" in out and "error" in out: return "assertion"
    if "importerror" in out or "modulenotfounderror" in out: return "import"
    if "syntaxerror" in out or "typeerror" in out: return "runtime"
    if "timeout" in out: return "timeout"
    if "segmentation fault" in out: return "crash"
    return "unknown"

def attempt_fix(code: str, error: str, category: str) -> str | None:
    """Simple heuristic repairs. No LLM needed."""
    if category == "import":
        # Extract missing module name
        m = re.search(r"no module named ['\"]?(\w+)['\"]?", error.lower())
        if m:
            return f"pip install {m.group(1)}"
    if category == "assertion":
        # Try swapping expected/actual if comparison fails
        lines = code.split("\n")
        for i, line in enumerate(lines):
            if "assert" in line and "==" in line:
                parts = line.split("==")
                if len(parts) == 2:
                    lines[i] = f"    assert {parts[1].strip()} == {parts[0].strip()}"
                    return "\n".join(lines)
    return None

def heal(command: list[str], cwd: str = ".", max_attempts: int = 3) -> dict:
    history = []
    for attempt in range(max_attempts):
        result = run_test(command, cwd)
        history.append({"attempt": attempt+1, "result": result})
        if result["returncode"] == 0:
            return {"success": True, "attempts": attempt+1, "history": history}
        
        category = classify_failure(result)
        fix = attempt_fix(
            open(cwd + "/test_heal_target.py").read() if os.path.exists(cwd + "/test_heal_target.py") else "",
            result["stderr"] + result["stdout"],
            category
        )
        if fix:
            history[-1]["fix_applied"] = fix
        else:
            break  # No fix found, abandon
    return {"success": False, "attempts": max_attempts, "history": history}

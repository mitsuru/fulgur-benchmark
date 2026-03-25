#!/usr/bin/env python3
"""
Benchmark script comparing fulgur, fullbleed, and weasyprint as external CLI tools.
"""

import argparse
import json
import os
import platform
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from datetime import date
from pathlib import Path


# ---------------------------------------------------------------------------
# CLI command templates
# ---------------------------------------------------------------------------

COMMANDS = {
    "fulgur":     ["fulgur", "render", "{input}", "-o", "{output}"],
    "fullbleed":  ["fullbleed", "render", "--html", "{input}", "--out", "{output}"],
    "weasyprint": ["weasyprint", "{input}", "{output}"],
}


# ---------------------------------------------------------------------------
# System information
# ---------------------------------------------------------------------------

def get_system_info() -> dict:
    """Collect OS, CPU model, and total memory."""
    os_name = platform.system()

    # CPU model
    cpu = platform.processor() or "unknown"
    if os_name == "Linux":
        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if line.startswith("model name"):
                        cpu = line.split(":", 1)[1].strip()
                        break
        except OSError:
            pass
    elif os_name == "Darwin":
        try:
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                cpu = result.stdout.strip()
        except OSError:
            pass

    # Total memory
    memory = "unknown"
    if os_name == "Linux":
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        kb = int(line.split()[1])
                        memory = f"{kb // 1024} MB"
                        break
        except OSError:
            pass
    elif os_name == "Darwin":
        try:
            result = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                memory = f"{int(result.stdout.strip()) // (1024 * 1024)} MB"
        except OSError:
            pass

    return {"os": os_name, "cpu": cpu, "memory": memory}


# ---------------------------------------------------------------------------
# Tool availability
# ---------------------------------------------------------------------------

def check_tool(tool_name: str) -> bool:
    """Return True if the tool binary is on PATH."""
    return shutil.which(tool_name) is not None


def build_command(template: list[str], input_path: str, output_path: str) -> list[str]:
    """Substitute {input} and {output} placeholders in a command template."""
    return [part.replace("{input}", input_path).replace("{output}", output_path)
            for part in template]


# ---------------------------------------------------------------------------
# Memory measurement helpers
# ---------------------------------------------------------------------------

def measure_with_time_v(cmd: list[str], output_path: str) -> int | None:
    """
    Run *cmd* under `/usr/bin/time -v` and parse peak RSS in KB.
    Returns None if `/usr/bin/time` is not available.
    """
    time_bin = "/usr/bin/time"
    if not os.path.isfile(time_bin):
        return None

    wrapped = [time_bin, "-v"] + cmd
    result = subprocess.run(
        wrapped,
        capture_output=True,
        text=True,
    )
    for line in result.stderr.splitlines():
        if "Maximum resident set size" in line:
            try:
                return int(line.split(":")[-1].strip())
            except ValueError:
                pass
    return None


def measure_with_resource(cmd: list[str]) -> int | None:
    """
    Measure peak RSS using resource.getrusage after running the child process.
    Returns peak RSS in KB (normalised from macOS pages if needed).
    """
    import resource  # Unix only

    # Fork so that we can measure the child's maxrss separately.
    pid = os.fork()
    if pid == 0:
        # Child
        os.execvp(cmd[0], cmd)
        os._exit(1)  # pragma: no cover
    else:
        # Parent: wait for child
        _, _ = os.waitpid(pid, 0)
        usage = resource.getrusage(resource.RUSAGE_CHILDREN)
        maxrss = usage.ru_maxrss
        # On macOS ru_maxrss is in bytes; on Linux it's in KB.
        if platform.system() == "Darwin":
            maxrss = maxrss // 1024
        return maxrss


# ---------------------------------------------------------------------------
# Single benchmark run
# ---------------------------------------------------------------------------

def run_once(tool: str, cmd_template: list[str], input_path: str) -> tuple[float, int | None, int | None]:
    """
    Execute the tool once, returning (elapsed_seconds, memory_kb, output_size_bytes).
    A fresh temp file is used for each run so size is always measured.
    """
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        output_path = tmp.name

    try:
        cmd = build_command(cmd_template, input_path, output_path)

        # Try Linux /usr/bin/time -v first for memory
        # We time it separately so our perf_counter wraps the real process.
        start = time.perf_counter()
        memory_kb = measure_with_time_v(cmd, output_path)
        elapsed = time.perf_counter() - start

        if memory_kb is None:
            # Fallback: run normally (no memory) or use resource on Unix
            if hasattr(os, "fork"):
                start = time.perf_counter()
                memory_kb = measure_with_resource(cmd)
                elapsed = time.perf_counter() - start
            else:
                start = time.perf_counter()
                subprocess.run(cmd, check=True, capture_output=True)
                elapsed = time.perf_counter() - start

        # Output size
        try:
            output_size = os.path.getsize(output_path)
        except OSError:
            output_size = None

        return elapsed, memory_kb, output_size
    finally:
        try:
            os.unlink(output_path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Full benchmark for one (tool, document) pair
# ---------------------------------------------------------------------------

def benchmark_tool(
    tool: str,
    cmd_template: list[str],
    input_path: str,
    runs: int,
    warmup: int,
) -> dict:
    """
    Run warmup + measured runs, return a result dict.
    """
    # Warmup runs (results discarded)
    for _ in range(warmup):
        run_once(tool, cmd_template, input_path)

    times_s: list[float] = []
    memory_samples: list[int] = []
    last_output_size: int | None = None

    for _ in range(runs):
        elapsed, mem_kb, out_size = run_once(tool, cmd_template, input_path)
        times_s.append(elapsed)
        if mem_kb is not None:
            memory_samples.append(mem_kb)
        if out_size is not None:
            last_output_size = out_size

    times_ms = [round(t * 1000, 2) for t in times_s]
    median_ms = round(statistics.median(times_ms), 2)

    memory_kb = round(statistics.median(memory_samples)) if memory_samples else None

    return {
        "time_ms": {"median": median_ms, "runs": times_ms},
        "memory_kb": memory_kb,
        "output_size_bytes": last_output_size,
    }


# ---------------------------------------------------------------------------
# HTML document generation
# ---------------------------------------------------------------------------

def generate_test_documents(output_dir: str) -> dict[str, str]:
    """
    Generate test HTML documents using templates.generate and return
    a mapping of {document_name: file_path}.
    """
    # Add project root to sys.path so templates package is importable
    project_root = str(Path(__file__).parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from templates.generate import generate_all
    return generate_all(output_dir)


# ---------------------------------------------------------------------------
# Markdown table output
# ---------------------------------------------------------------------------

def print_markdown_table(results: list[dict]) -> None:
    header = "| {:<10} | {:<10} | {:>9} | {:>11} | {:>13} |".format(
        "Document", "Tool", "Time (ms)", "Memory (MB)", "PDF Size (KB)"
    )
    separator = "|{:-<12}|{:-<12}|{:-<11}|{:-<13}|{:-<15}|".format("", "", "", "", "")

    print(header)
    print(separator)

    for r in results:
        doc = r["document"]
        tool = r["tool"]

        time_val = r.get("time_ms")
        if isinstance(time_val, dict):
            time_str = f"{time_val['median']:>9.0f}"
        elif time_val == "not installed":
            time_str = f"{'n/a':>9}"
        else:
            time_str = f"{'?':>9}"

        mem_kb = r.get("memory_kb")
        if mem_kb is not None and mem_kb != "not installed":
            mem_str = f"{mem_kb / 1024:>11.1f}"
        else:
            mem_str = f"{'n/a':>11}"

        size_bytes = r.get("output_size_bytes")
        if size_bytes is not None and size_bytes != "not installed":
            size_str = f"{size_bytes / 1024:>13.0f}"
        else:
            size_str = f"{'n/a':>13}"

        print(f"| {doc:<10} | {tool:<10} | {time_str} | {mem_str} | {size_str} |")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark fulgur, fullbleed, and weasyprint PDF renderers."
    )
    parser.add_argument(
        "--runs", type=int, default=5, metavar="N",
        help="Number of measured runs per tool/document combination (default: 5)."
    )
    parser.add_argument(
        "--warmup", type=int, default=1, metavar="N",
        help="Number of warmup runs before measurement (default: 1)."
    )
    parser.add_argument(
        "--fulgur-dev", metavar="PATH",
        help="Path to a development build of fulgur to benchmark alongside the installed version."
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Build the command map, optionally adding fulgur-dev
    commands = dict(COMMANDS)
    if args.fulgur_dev:
        dev_path = str(Path(args.fulgur_dev).resolve())
        commands["fulgur-dev"] = [dev_path, "render", "{input}", "-o", "{output}"]

    # Ensure results/ directory exists
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)

    system_info = get_system_info()
    today = date.today().isoformat()

    # Generate test HTML documents to a temp directory
    html_dir = tempfile.mkdtemp(prefix="fulgur-bench-html-")
    try:
        print("Generating test HTML documents...", flush=True)
        documents = generate_test_documents(html_dir)

        all_results: list[dict] = []

        for doc_name, input_path in sorted(documents.items()):
            for tool, cmd_template in commands.items():
                print(f"  Benchmarking {tool} on '{doc_name}'...", flush=True)

                if not check_tool(cmd_template[0]):
                    print(f"    {tool} not installed, skipping.")
                    all_results.append({
                        "tool": tool,
                        "document": doc_name,
                        "time_ms": "not installed",
                        "memory_kb": "not installed",
                        "output_size_bytes": "not installed",
                    })
                    continue

                try:
                    metrics = benchmark_tool(
                        tool, cmd_template, input_path,
                        runs=args.runs, warmup=args.warmup
                    )
                    all_results.append({
                        "tool": tool,
                        "document": doc_name,
                        **metrics,
                    })
                except Exception as exc:  # noqa: BLE001
                    print(f"    ERROR running {tool}: {exc}", file=sys.stderr)
                    all_results.append({
                        "tool": tool,
                        "document": doc_name,
                        "time_ms": f"error: {exc}",
                        "memory_kb": None,
                        "output_size_bytes": None,
                    })
    finally:
        shutil.rmtree(html_dir, ignore_errors=True)

    # ------------------------------------------------------------------
    # JSON output
    # ------------------------------------------------------------------
    output = {
        "date": today,
        "system": system_info,
        "results": all_results,
    }

    json_path = results_dir / f"benchmark-{today}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"\nResults written to {json_path}\n")

    # ------------------------------------------------------------------
    # Markdown table to stdout
    # ------------------------------------------------------------------
    print_markdown_table(all_results)


if __name__ == "__main__":
    main()

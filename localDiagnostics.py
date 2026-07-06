import subprocess
import requests
import time
import os
import sys
from datetime import datetime

APP_URL = "http://localhost:8081/health"
REPORT_DIR = "reports"

def run_command(command):
    """Safely execute a Linux command and return stdout."""
    print(f"Executing: {' '.join(command)}")
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        if result.stdout:
            print(result.stdout)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Command failed with return code {e.returncode}!", file=sys.stderr)
        print(f"Details: {e.stderr}", file=sys.stderr)
        sys.exit(1)


def get_memory():
    return run_command(["free", "-h"])


def get_disk():
    return run_command(["df", "-h"])


def get_cpu():
    return run_command(["top", "-b", "-n", "1"])


def get_network():
    return run_command(["ss", "-tuln"])


def exercise_api(num_requests=50):
    """
    Sends requests to the local FastAPI application.
    Returns:
        successful_requests,
        failed_requests,
        average_latency
    """
    successful = 0
    failed = 0
    latencies = []

    print(f"\nRunning workload ({num_requests} requests)...")

    for _ in range(num_requests):

        start = time.perf_counter()

        try:
            response = requests.get(APP_URL, timeout=5)

            latency = time.perf_counter() - start

            if response.status_code == 200:
                successful += 1
                latencies.append(latency)
            else:
                failed += 1

        except Exception:
            failed += 1

    average = 0

    if latencies:
        average = sum(latencies) / len(latencies)

    return successful, failed, average


def parse_cpu(cpu_output):
    """
    Return only the header and top 5 CPU consumers.
    """
    lines = cpu_output.splitlines()

    if len(lines) <= 6:
        return cpu_output

    return "\n".join(lines[:6])


def generate_report(before, after, workload):

    os.makedirs(REPORT_DIR, exist_ok=True)

    filename = os.path.join(REPORT_DIR, "latest_report.txt")

    successful, failed, avg_latency = workload

    report = f"""
    ====================================================
            LOCAL SYSTEM DIAGNOSTIC REPORT
    ====================================================

    Generated:
    {datetime.now()}

    ----------------------------------------------------
    CPU (Before Workload)
    ----------------------------------------------------
    {parse_cpu(before["cpu"])}

    ----------------------------------------------------
    CPU (After Workload)
    ----------------------------------------------------
    {parse_cpu(after["cpu"])}

    ----------------------------------------------------
    Memory (Before)
    ----------------------------------------------------
    {before["memory"]}

    ----------------------------------------------------
    Memory (After)
    ----------------------------------------------------
    {after["memory"]}

    ----------------------------------------------------
    Disk
    ----------------------------------------------------
    {after["disk"]}

    ----------------------------------------------------
    Network Connections
    ----------------------------------------------------
    {after["network"]}

    ----------------------------------------------------
    FastAPI Workload
    ----------------------------------------------------
    Requests Sent : {successful + failed}

    Successful   : {successful}

    Failed        : {failed}

    Average Latency : {avg_latency:.4f} seconds


    SUMMARY
    ----------------------------------------------------

    Diagnostics completed successfully.

    Review the statistics above before deploying to Azure.
    """

    with open(filename, "w") as file:
        file.write(report)
    return filename, report


def run_diagnostics():

    print("\n")
    print("=== Running Local System Diagnostics ===")

    print("\nCollecting baseline metrics...")

    before = {
        "cpu": get_cpu(),
        "memory": get_memory(),
        "disk": get_disk(),
        "network": get_network()
    }

    workload = exercise_api()

    print("Collecting post-workload metrics...")

    after = {
        "cpu": get_cpu(),
        "memory": get_memory(),
        "disk": get_disk(),
        "network": get_network()
    }

    filename, report = generate_report(
        before,
        after,
        workload
    )

    print(report)
    print(f"\nReport saved to: {filename}")
    return report


if __name__ == "__main__":
    run_diagnostics()
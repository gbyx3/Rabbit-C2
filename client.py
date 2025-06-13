import subprocess
import requests

URL = "<CHANGEME>"
AGENT_ID = "<CHANGEME>"
USERNAME = "<CHANGEME>"
PASSWORD = "<CHANGEME>
USERAGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:139.0) Gecko/20100101 Firefox/139.0"
HEADERS = {
    "X-Agent-ID": AGENT_ID,
    "X-Username": USERNAME,
    "X-Password": PASSWORD,
    "User-Agent": USERAGENT,
}
DEBUG = False

# Optional. if you want to use client certificate authentication on the web server
CLIENT_CERT = None
CLIENT_KEY = None


def get_queue():
    headers = HEADERS
    headers["X-Action"] = "get_queue"
    return requests.get(URL, headers=headers).json()


def remove_from_queue(sequence):
    headers = HEADERS
    headers["sequence"] = str(sequence)
    headers["X-Action"] = "remove_from_queue"
    return requests.get(URL, headers=headers).json()


def run_command(cmd):
    res = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
    return res.decode()


def report_output(output, sequence):
    headers = HEADERS
    headers["X-Action"] = "report_output"
    data = {"result": output, "sequence": sequence}
    return requests.get(URL, headers=headers, json=data).json()


if __name__ == "__main__":
    for job in get_queue():
        status = job.get("status", "unknown")
        if status != "queued":
            continue
        cmd = job["cmd"]
        sequence = job["sequence"]
        try:
            output = run_command(cmd)
        except subprocess.CalledProcessError as e:
            output = f"Command failed with error: {e.output.decode()}"
        if DEBUG:
            print(f"Running command: {cmd}")
            print(f"Output: {output}")
            print(f"Sequence: {sequence}")
        report_output(output, sequence)

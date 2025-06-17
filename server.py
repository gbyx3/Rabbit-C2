import bottle
import json
import datetime
import redis
import uuid
import os

# Initialize the Bottle application
app = bottle.Bottle()


def agentcheck(fn):
    def _wrap(*args, **kwargs):
        agent = bottle.request.headers.get("X-Agent-ID", None)
        trusted_agent = read_redis(f"agent:{agent}", db=1)
        if trusted_agent:
            username = bottle.request.headers.get("X-Username", None)
            password = bottle.request.headers.get("X-Password", None)
            if (
                username == trusted_agent["username"]
                and password == trusted_agent["password"]
            ):
                return fn(*args, **kwargs)
        bottle.response.status = 401
        return {"result": "failed", "message": "Unauthorized access"}

    return _wrap


def connect(db=0):
    """Connect to the Redis database."""
    redis_password = os.getenv("REDIS_PASSWORD")
    if not redis_password:
        raise ConnectionError(
            "Redis authentication failed: REDIS_PASSWORD environment variable not set."
        )
    return redis.StrictRedis(
        "127.0.0.1",
        port=6379,
        db=db,
        password=redis_password,
    )


def update_redis(key, value, db=0):
    """Update a key in the Redis database."""
    r = connect(db)
    r.set(key, json.dumps(value))
    return True


def read_redis(key, db=0):
    """Read a key from the Redis database."""
    r = connect(db)
    value = r.get(key)
    if value is None:
        return None
    return json.loads(value)


def get_queue():
    """Get the queue for the agent from the settings."""
    agent_id = bottle.request.headers.get("X-Agent-ID")
    agent_config = read_redis(f"agent:{agent_id}", db=1)
    if not agent_config:
        return False
    queue = agent_config.get("queue", None)
    r = connect(0)
    now = datetime.datetime.now()
    formatted = now.strftime("%Y-%m-%d %H:%M")
    r.set(agent_id, formatted)
    if not queue:
        return False
    return queue


# Error handler for AuthenticationError
@app.error(500)
def error500(error):
    return bottle.static_file("error.html", root=".")


@app.route("/<filename:re:script\.js|style\.css|bg\.jpg|error\.html>")
def serve_static(filename):
    return bottle.static_file(filename, root=".")


@app.route("/", method="GET")
@agentcheck
def index():
    action = bottle.request.headers.get("X-Action", False)
    if not action:
        bottle.response.status = 400
        return {"result": "failed"}
    if action == "get_queue":
        queue_id = get_queue()
        if not queue_id:
            bottle.response.status = 404
            return {"result": "failed", "message": "Queue not found for agent."}
        return json.dumps(read_redis(queue_id) or [])
    elif action == "remove_from_queue":
        sequence = bottle.request.headers.get("Sequence", None)
        if not sequence:
            bottle.response.status = 400
            return {"result": "failed", "message": "Missing sequence in command"}
        queue_id = get_queue()
        if not queue_id:
            bottle.response.status = 404
            return {"result": "failed", "message": "Queue not found for agent."}
        queue = read_redis(queue_id)
        sequence_found = False
        for item in queue:
            if item.get("sequence") == int(sequence):
                queue.remove(item)
                sequence_found = True
                break
        if sequence_found:
            update_redis(queue_id, queue)
            return {"status": "success", "message": f"Key '{sequence}' deleted."}
        return {"status": "failed", "message": f"Key '{sequence}' not found."}
    elif action == "report_output":
        output = bottle.request.json
        sequence = output.get("sequence", None)
        if not sequence:
            bottle.response.status = 400
            return {"result": "failed", "message": "Missing sequence in command"}
        queue_id = get_queue()
        if not queue_id:
            bottle.response.status = 404
            return {"result": "failed", "message": "Queue not found for agent."}
        queue = read_redis(queue_id)
        if not queue:
            bottle.response.status = 404
            return {"result": "failed", "message": "Queue is empty or does not exist"}
        for idx, job in enumerate(queue):
            if job.get("sequence") == int(sequence):
                job["output"] = output.get("result", "N/A")
                job["status"] = "completed"
                queue.pop(idx)
                queue.append(job)
                break
        else:
            bottle.response.status = 404
            return {
                "status": "failed",
                "message": f"Sequence {sequence} not found in queue.",
            }
        update_redis(queue_id, queue)
        return {
            "status": "success",
            "message": f"Output for sequence {sequence} updated.",
        }
    return {"result": "failed", "message": "Unknown action"}


@app.route("/admin/", method=["GET", "POST", "DELETE"])
def admin():
    r = connect(db=1)
    if bottle.request.method == "GET":
        agents_data = []
        for key in r.keys("agent:*"):
            agent_id = key.decode().replace("agent:", "")
            agent = read_redis(f"agent:{agent_id}", db=1)
            queue = read_redis(agent["queue"]) if agent.get("queue") else []
            last_connected = connect().get(agent_id)
            agents_data.append(
                {
                    "id": agent_id,
                    "username": agent.get("username", "Unknown User"),
                    "queue": queue or [],
                    "queue_id": agent.get("queue", "No Queue"),
                    "name": agent.get("name", "Unknown Agent"),
                    "last_connected": (
                        last_connected.decode() if last_connected else "Never"
                    ),
                    "photo": agent.get("photo"),
                }
            )
        return bottle.template("landing", agents=agents_data)
    elif bottle.request.method == "POST":
        try:
            data = bottle.request.json
            agent_id = data.get("agent_id", None)
            command = data.get("command", None)
            if not agent_id or not command:
                bottle.response.status = 400
                return {"status": "failed", "message": "Missing agent_id or command"}
            queue_id = read_redis(f"agent:{agent_id}", db=1).get("queue")
            if not queue_id:
                bottle.response.status = 404
                return {"status": "failed", "message": "Agent not found"}
            queue = read_redis(queue_id) or []
            sequence = queue[-1]["sequence"] + 1 if queue else 1
            job = {
                "cmd": command,
                "sequence": sequence,
                "output": "",
                "status": "queued",
            }
            queue.append(job)
            update_redis(queue_id, queue)
            return {"status": "success", "message": f"Job added to {agent_id}"}
        except Exception as e:
            bottle.response.status = 500
            return {"status": "failed", "message": str(e)}

    elif bottle.request.method == "DELETE":
        try:
            data = bottle.request.json
            agent_id = data.get("agent_id")
            sequence = data.get("sequence")
            if not agent_id or not sequence:
                bottle.response.status = 400
                return {"status": "failed", "message": "Missing agent_id or sequence"}
            queue_id = read_redis(f"agent:{agent_id}", db=1).get("queue")
            if not queue_id:
                bottle.response.status = 404
                return {"status": "failed", "message": "Agent not found"}
            queue = read_redis(queue_id)
            if not queue:
                bottle.response.status = 404
                return {"status": "failed", "message": "Queue not found"}
            sequence_found = False
            for item in queue:
                if item.get("sequence") == int(sequence):
                    queue.remove(item)
                    sequence_found = True
                    break
            if sequence_found:
                update_redis(queue_id, queue)
                return {"status": "success", "message": f"Job {sequence} deleted"}
            return {"status": "failed", "message": f"Job {sequence} not found"}
        except Exception as e:
            bottle.response.status = 500
            return {"status": "failed", "message": str(e)}


@app.route("/agent/", method=["GET"])
def agent_details():
    r = connect(db=1)
    agent_id = bottle.request.query.get("agent_id", None)
    agents_data = []
    for key in r.keys("agent:*"):
        agent_id_key = key.decode().replace("agent:", "")
        agent = read_redis(f"agent:{agent_id_key}", db=1)
        queue = read_redis(agent["queue"]) if agent.get("queue") else []
        agent_info = {
            "id": agent_id_key,
            "username": agent.get("username", "Unknown User"),
            "queue": queue or [],
            "queue_id": agent.get("queue", "No Queue"),
            "name": agent.get("name", "Unknown Agent"),
        }
        if agent_id is None or agent_id_key == agent_id:
            agents_data.append(agent_info)
    return bottle.template("index", agents=agents_data, agent_id=agent_id)


@app.route("/agent/manage/", method=["POST", "DELETE"])
def manage_agent():
    r = connect(db=1)
    if bottle.request.method == "DELETE":
        agent_id = bottle.request.query.get("agent_id", None)
        if not agent_id:
            bottle.response.status = 400
            return {"result": "failed", "message": "Missing agent_id parameter"}

        agent_key = f"agent:{agent_id}"
        if not r.exists(agent_key):
            bottle.response.status = 404
            return {"result": "failed", "message": "Agent not found"}

        r.delete(agent_key)
        bottle.response.status = 200
        return {
            "result": "success",
            "message": f"Agent {agent_id} deleted successfully",
        }
    elif bottle.request.method == "POST":
        data = bottle.request.json
        agent_id = uuid.uuid4().hex
        username = data.get("agent_username")
        password = data.get("agent_password")
        name = data.get("agent_name", "Unknown Agent")
        photo = data.get("agent_photo", None)

        if not agent_id or not username or not password:
            bottle.response.status = 400
            return {"result": "failed", "message": "Missing required parameters"}

        agent_key = f"agent:{agent_id}"
        if r.exists(agent_key):
            bottle.response.status = 400
            return {"result": "failed", "message": "Agent already exists"}

        agent_data = {
            "id": agent_id,
            "username": username,
            "password": password,
            "name": name,
            "photo": photo,
            "queue": f"queue:{agent_id}",
        }

        update_redis(agent_key, agent_data, db=1)
        return {"result": "success", "message": f"Agent {agent_id} added successfully"}
    return {"result": "unknown", "message": "Unsupported method"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False, reloader=True)

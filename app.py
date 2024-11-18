import os
import json
import logging
import sys
import time
from datetime import datetime
from typing import Iterator

from flask import Flask, Response, render_template, request, stream_with_context
from google.cloud import firestore

# Set up logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Set the environment variable for Firestore credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/Users/rupinbapuji/Documents/flasky/sensor-frontend/credentials.json"

# Initialize Firestore client
db = firestore.Client()

# Initialize Flask app
application = Flask(__name__)

@application.route("/")
def index() -> str:
    return render_template("index.html")

def fetch_data() -> Iterator[str]:
    """
    Fetch data from Firestore and stream it to the client.
    """
    if request.headers.getlist("X-Forwarded-For"):
        client_ip = request.headers.getlist("X-Forwarded-For")[0]
    else:
        client_ip = request.remote_addr or ""

    try:
        logger.info("Client %s connected", client_ip)
        while True:
            # Fetch data from Firestore
            # print("Fetching data from Firestore")
            docs = db.collection('sensor_readings').order_by('timestamp').stream()
            data = [doc.to_dict() for doc in docs]
            # print(data)

            for entry in data:
                json_data = json.dumps(
                    {
                        "sensor1": entry['sensor1'],
                        "sensor2": entry['sensor2'],
                        "timestamp": entry['timestamp'].strftime("%Y-%m-%d %H:%M:%S"),
                    }
                )
                yield f"data:{json_data}\n\n"
            time.sleep(1)
    except GeneratorExit:
        logger.info("Client %s disconnected", client_ip)

@application.route("/chart-data")
def chart_data() -> Response:
    response = Response(stream_with_context(fetch_data()), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response

if __name__ == "__main__":
    application.run(host="0.0.0.0", port=5001, threaded=True)
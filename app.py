import json
import logging
import sys
import time
from datetime import datetime, timedelta
from typing import Iterator

from flask import Flask, Response, render_template, request, stream_with_context
from google.cloud import firestore
import os

# Set up logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Initialize Flask app
application = Flask(__name__)

# Set your Google Cloud credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "credentials.json"

# Initialize Firestore client
db = firestore.Client()

@application.route("/")
def index() -> str:
    return render_template("index.html")

def generate_sensor_data() -> Iterator[str]:
    """
    Reads data from Firestore and streams it to the client.
    """
    if request.headers.getlist("X-Forwarded-For"):
        client_ip = request.headers.getlist("X-Forwarded-For")[0]
    else:
        client_ip = request.remote_addr or ""

    try:
        logger.info("Client %s connected", client_ip)
        last_timestamp = datetime.now() - timedelta(seconds=5)

        while True:
            readings = (
                db.collection('sensor_readings')
                .where('timestamp', '>', last_timestamp)
                .order_by('timestamp')
                .limit(10)
                .stream()
            )

            for reading in readings:
                data = reading.to_dict()
                last_timestamp = data['timestamp']
                
                timestamp = data['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
                
                json_data = json.dumps({
                    "time": timestamp,
                    "sensor1": data['sensor1'],
                    "sensor2": data['sensor2'],
                })
                yield f"data:{json_data}\n\n"
            
            time.sleep(1)
    except GeneratorExit:
        logger.info("Client %s disconnected", client_ip)

@application.route("/chart-data")
def chart_data() -> Response:
    response = Response(stream_with_context(generate_sensor_data()), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response

if __name__ == "__main__":
    print("Starting sensor dashboard server...")
    print("Access the dashboard at: http://localhost:5001")
    application.run(host="0.0.0.0", port=5001, threaded=True)


from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv
from flask_cors import CORS
import os

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# ✅ Use local MongoDB URI directly or through .env
# Either use the line below:
MONGODB_URI = os.getenv("mongodb://localhost:27017")
client = MongoClient(MONGODB_URI)

# Database and Collection
db = client["webhooks"]
events_collection = db["events"]

# Home route (UI)
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        return "✅ Webhook is ready to receive POST requests from GitHub.", 200

    if request.content_type != 'application/json':
        return jsonify({"error": "415 Unsupported Media Type: Content-Type must be application/json"}), 415

    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON payload received"}), 400

        event_type = request.headers.get('X-GitHub-Event', 'undefined')
        timestamp = datetime.utcnow().isoformat()
        author = (
            data.get('pusher', {}).get('name')
            or data.get('sender', {}).get('login')
            or "Unknown"
        )
        print("👤 Author:", author)

        from_branch = None
        to_branch = None
        request_id = "unknown"

        if event_type == "push":
            to_branch = data.get('ref', '').split('/')[-1]
            request_id = data.get('after', 'no-after-sha')
        elif event_type == "pull_request":
            from_branch = data['pull_request']['head']['ref']
            to_branch = data['pull_request']['base']['ref']
            request_id = data['pull_request']['head']['sha']
        elif event_type == "merge_group":  # Bonus
            from_branch = data.get('from')
            to_branch = data.get('to')
            request_id = data.get('head_commit', {}).get('id', 'unknown')
        else:
            return jsonify({"message": f"Unhandled event type: {event_type}"}), 200

        # Prepare document to store
        event_doc = {
            "request_id": request_id,
            "action": event_type,
            "author": author,
            "from_branch": from_branch,
            "to_branch": to_branch,
            "timestamp": timestamp
        }

        # Insert into MongoDB
        result = events_collection.insert_one(event_doc)
        return jsonify({"message": "Event stored", "id": str(result.inserted_id)}), 200

    except Exception as e:
        import traceback
        print("❌ Exception occurred:")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500



@app.route('/events', methods=['GET'])
def get_events():
    events = list(events_collection.find().sort("timestamp", -1))
    for e in events:
        e['_id'] = str(e['_id'])
    return jsonify(events)

if __name__ == '__main__':
    print("🚀 Starting Flask app...")
    app.run(host='0.0.0.0',port=8080,debug=True)

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
    print("🧭 GET / → index.html served")
    return render_template('index.html')


@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    print(f"\n📡 Incoming {request.method} request on /webhook")
    print(f"📨 Headers: {dict(request.headers)}")
    print(f"🔍 Content-Type: {request.content_type}")

    if request.method == 'GET':
        return "✅ Webhook is ready to receive POST requests from GitHub.", 200

    if request.content_type != 'application/json':
        print("🚫 Unsupported Media Type!")
        return jsonify({"error": "415 Unsupported Media Type: Content-Type must be application/json"}), 415

    try:
        print("🔔 Attempting to parse JSON payload...")
        data = request.get_json()
        print("💿💿Data:", data)

        if not data:
            print("⚠️ No JSON payload received.")
            return jsonify({"error": "No JSON payload received"}), 400

        print("📦 Raw Payload:", data)

        event_type = request.headers.get('X-GitHub-Event', 'undefined')
        print("📬 GitHub Event Type:", event_type)

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
            print(f"✅ PUSH → {author} pushed to {to_branch}, commit SHA: {request_id}")

        elif event_type == "pull_request":
            from_branch = data['pull_request']['head']['ref']
            to_branch = data['pull_request']['base']['ref']
            request_id = data['pull_request']['head']['sha']
            print(f"✅ PULL REQUEST → {author} PR from {from_branch} to {to_branch}, SHA: {request_id}")

        elif event_type == "merge_group":  # Bonus
            from_branch = data.get('from')
            to_branch = data.get('to')
            request_id = data.get('head_commit', {}).get('id', 'unknown')
            print(f"✅ MERGE → {author} merged {from_branch} to {to_branch}, SHA: {request_id}")

        else:
            print("⚠️ Unhandled event type:", event_type)
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
        print("💾 Inserting into MongoDB...")
        result = events_collection.insert_one(event_doc)
        print(f"📝 Event stored in MongoDB with ID: {result.inserted_id}")
        return jsonify({"message": "Event stored", "id": str(result.inserted_id)}), 200

    except Exception as e:
        import traceback
        print("❌ Exception occurred:")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500



# Fetch events for frontend
@app.route('/events', methods=['GET'])
def get_events():
    print("✅ /events route hit")
    events = list(events_collection.find().sort("timestamp", -1))
    for e in events:
        e['_id'] = str(e['_id'])
    return jsonify(events)

if __name__ == '__main__':
    print("🚀 Starting Flask app...")
    app.run(host='0.0.0.0',port=8080,debug=True)

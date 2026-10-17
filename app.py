
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient
from pymongo.errors import PyMongoError

load_dotenv()

app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data.json"

# Connect to MongoDB Atlas
mongo_uri = os.getenv("MONGO_URI")
client = None
submissions_collection = None

if mongo_uri:
    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        db = client["flask_assignment"]
        submissions_collection = db["submissions"]
        print("MongoDB Atlas connected successfully.")
    except PyMongoError as error:
        print(f"MongoDB connection failed: {error}")
        if client:
            client.close()
        client = None
        submissions_collection = None


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api")
def api():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, list):
            raise ValueError("The JSON file must contain a list.")
        return app.json.response(data)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        app.logger.error("Could not read API data: %s", error)
        return {"error": "Unable to load API data."}, 500


@app.route("/submit", methods=["POST"])
def submit():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    message = request.form.get("message", "").strip()

    # Validate submitted fields
    if not name or not email or not message:
        return render_template(
            "index.html",
            error="All fields are required.",
            name=name,
            email=email,
            message=message
        ), 400

    if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        return render_template(
            "index.html",
            error="Please enter a valid email address.",
            name=name,
            email=email,
            message=message
        ), 400

    if submissions_collection is None:
        return render_template(
            "index.html",
            error="Database is unavailable. Please check the Atlas connection.",
            name=name,
            email=email,
            message=message
        ), 503

    try:
        submissions_collection.insert_one({
            "name": name,
            "email": email,
            "message": message
        })

        return redirect(url_for("success"))

    except PyMongoError:
        app.logger.exception("Failed to save form submission")
        return render_template(
            "index.html",
            error="Unable to save your data. Please try again.",
            name=name,
            email=email,
            message=message
        ), 500


@app.route("/success")
def success():
    return render_template("success.html")


if __name__ == "__main__":
    app.run(debug=True)

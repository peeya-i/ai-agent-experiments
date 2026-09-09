"""Flask application for Travel Itinerary Builder."""
import os
from flask import Flask, render_template, request, jsonify, send_file, Response
import config
from pipeline.orchestrator import PipelineOrchestrator
from services.tracker import Tracker
from services.export_service import generate_text_itinerary, generate_pdf_itinerary

app = Flask(__name__)
app.config['SECRET_KEY'] = 'travel-builder-secret-2026'

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/generate", methods=["POST"])
def api_generate():
    try:
        data = request.get_json() or {}
        origin = data.get("origin", "").strip() or "New York, USA"
        destination = data.get("destination", "").strip()
        if not destination:
            return jsonify({"success": False, "error": "Destination is required."}), 400

        try:
            budget = float(data.get("budget", 1000.0))
        except (ValueError, TypeError):
            budget = 1000.0

        try:
            duration = int(data.get("duration", 3))
        except (ValueError, TypeError):
            duration = 3

        interests_raw = data.get("interests", "")
        if isinstance(interests_raw, list):
            interests = interests_raw
        else:
            interests = [i.strip() for i in str(interests_raw).split(",") if i.strip()]

        departure_date = data.get("departure_date", "")

        orchestrator = PipelineOrchestrator()
        result = orchestrator.run(
            origin=origin,
            destination=destination,
            days=duration,
            budget=budget,
            interests=interests,
            departure_date=departure_date
        )
        return jsonify(result)

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/history", methods=["GET"])
def api_history():
    metrics = Tracker.get_metrics()
    usages = Tracker.get_all_usages()
    return jsonify({
        "success": True,
        "metrics": metrics,
        "itineraries": usages
    })

@app.route("/api/itinerary/<run_id>", methods=["GET"])
def api_get_itinerary(run_id):
    itinerary_state = Tracker.get_run_itinerary(run_id)
    if not itinerary_state:
        return jsonify({"success": False, "error": "Itinerary not found."}), 404
    return jsonify({"success": True, "state": itinerary_state})

@app.route("/api/events/<run_id>", methods=["GET"])
def api_get_events(run_id):
    events = Tracker.get_events_for_run(run_id)
    return jsonify({"success": True, "run_id": run_id, "events": events})

@app.route("/download/txt/<run_id>", methods=["GET"])
def download_txt(run_id):
    itinerary_state = Tracker.get_run_itinerary(run_id)
    if not itinerary_state:
        return "Itinerary not found", 404
    text_content = generate_text_itinerary(itinerary_state)
    dest = itinerary_state.get("user_input", {}).get("destination", "trip").replace(" ", "_")
    return Response(
        text_content,
        mimetype="text/plain",
        headers={"Content-Disposition": f"attachment;filename=itinerary_{dest}_{run_id}.txt"}
    )

@app.route("/download/pdf/<run_id>", methods=["GET"])
def download_pdf(run_id):
    itinerary_state = Tracker.get_run_itinerary(run_id)
    if not itinerary_state:
        return "Itinerary not found", 404
    pdf_buffer = generate_pdf_itinerary(itinerary_state)
    dest = itinerary_state.get("user_input", {}).get("destination", "trip").replace(" ", "_")
    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"itinerary_{dest}_{run_id}.pdf"
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config.PORT, debug=config.DEBUG)

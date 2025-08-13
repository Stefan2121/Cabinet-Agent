from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from datetime import datetime
import os
import pytz
from .models import Patient, Appointment
from . import db


bp = Blueprint("main", __name__)

# Use fixed clinic timezone for consistent local scheduling
TZ_NAME = os.getenv("APP_TIMEZONE", "Europe/Bucharest")
TZ = pytz.timezone(TZ_NAME)


@bp.route("/patients", methods=["GET", "POST"])
def patients_view():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()

        if not full_name:
            return render_template(
                "patients.html",
                patients=Patient.query.order_by(Patient.full_name).all(),
                error="Numele complet este obligatoriu.",
            )

        patient = Patient(full_name=full_name, phone=phone or None, email=email or None)
        db.session.add(patient)
        db.session.commit()
        return redirect(url_for("main.patients_view"))

    patients = Patient.query.order_by(Patient.full_name).all()
    return render_template("patients.html", patients=patients, error=None)


@bp.route("/calendar")
def calendar_view():
    return render_template("calendar.html")


@bp.route("/api/patients", methods=["GET", "POST"])
def api_patients():
    if request.method == "POST":
        data = request.get_json(force=True, silent=True) or {}
        full_name = (data.get("full_name") or "").strip()
        phone = (data.get("phone") or "").strip() or None
        email = (data.get("email") or "").strip() or None

        if not full_name:
            return jsonify({"error": "Numele complet este obligatoriu"}), 400

        patient = Patient(full_name=full_name, phone=phone, email=email)
        db.session.add(patient)
        db.session.commit()
        return jsonify({"id": patient.id, "full_name": patient.full_name}), 201

    patients = Patient.query.order_by(Patient.full_name).all()
    return jsonify([{"id": p.id, "full_name": p.full_name} for p in patients])


def parse_to_local_naive(dt_str: str):
    try:
        # Support both Z and offset formats
        aware = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        if aware.tzinfo is None:
            # Treat naive input as local time
            local_naive = aware
        else:
            # Convert to clinic local time, then drop tzinfo
            local_naive = aware.astimezone(TZ).replace(tzinfo=None)
        return local_naive
    except Exception:
        return None


@bp.route("/api/events")
def api_events():
    start = request.args.get("start")
    end = request.args.get("end")
    if not start or not end:
        return jsonify([])

    start_dt = parse_to_local_naive(start)
    end_dt = parse_to_local_naive(end)
    if not start_dt or not end_dt:
        return jsonify([])

    appointments = Appointment.query.filter(
        Appointment.start_at >= start_dt, Appointment.end_at <= end_dt
    ).all()

    events = []
    for a in appointments:
        title = a.patient.full_name if a.patient else "Programare"
        events.append(
            {
                "id": a.id,
                "title": title,
                # Send as local naive; FullCalendar interpretează ca timp local
                "start": a.start_at.isoformat(),
                "end": a.end_at.isoformat(),
                "extendedProps": {"note": a.note or ""},
            }
        )
    return jsonify(events)


@bp.route("/api/events", methods=["POST"])
def api_create_event():
    data = request.get_json(force=True, silent=True) or {}
    patient_id = data.get("patient_id")
    start = data.get("start")
    end = data.get("end")
    note = (data.get("note") or "").strip() or None

    if not patient_id or not start or not end:
        return jsonify({"error": "Câmpuri lipsă"}), 400

    start_dt = parse_to_local_naive(start)
    end_dt = parse_to_local_naive(end)
    if not start_dt or not end_dt:
        return jsonify({"error": "Format dată invalid"}), 400

    patient = Patient.query.get(patient_id)
    if not patient:
        return jsonify({"error": "Pacientul nu există"}), 404

    appt = Appointment(
        patient_id=patient.id,
        start_at=start_dt,
        end_at=end_dt,
        note=note,
        reminder_sent=False,
    )
    db.session.add(appt)
    db.session.commit()
    return jsonify({"id": appt.id}), 201


@bp.route("/api/events/<int:appointment_id>", methods=["PUT", "DELETE"])
def api_update_event(appointment_id: int):
    appt = Appointment.query.get_or_404(appointment_id)

    if request.method == "DELETE":
        db.session.delete(appt)
        db.session.commit()
        return "", 204

    data = request.get_json(force=True, silent=True) or {}

    start = data.get("start")
    end = data.get("end")
    note = data.get("note")

    if start:
        start_dt = parse_to_local_naive(start)
        if not start_dt:
            return jsonify({"error": "Format dată invalid pentru start"}), 400
        appt.start_at = start_dt
    if end:
        end_dt = parse_to_local_naive(end)
        if not end_dt:
            return jsonify({"error": "Format dată invalid pentru end"}), 400
        appt.end_at = end_dt
    if note is not None:
        appt.note = note.strip() or None

    # Reset reminder flag on any change, so the patient will get a new reminder
    appt.reminder_sent = False
    db.session.commit()
    return jsonify({"ok": True})
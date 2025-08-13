from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from datetime import datetime
import os
import pytz
from .models import Patient, Appointment, Doctor
from . import db
from .mail import send_reminder_for_appointment


bp = Blueprint("main", __name__)

# Use fixed clinic timezone for consistent local scheduling
TZ_NAME = os.getenv("APP_TIMEZONE", "Europe/Bucharest")
TZ = pytz.timezone(TZ_NAME)


@bp.route("/doctors", methods=["GET", "POST"])
def doctors_view():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip() or None
        if not name:
            return render_template(
                "doctors.html",
                doctors=Doctor.query.order_by(Doctor.name).all(),
                error="Numele medicului este obligatoriu.",
            )
        doctor = Doctor(name=name, email=email)
        db.session.add(doctor)
        db.session.commit()
        return redirect(url_for("main.doctors_view"))

    return render_template("doctors.html", doctors=Doctor.query.order_by(Doctor.name).all(), error=None)


@bp.route("/doctors/<int:doctor_id>/delete", methods=["POST"]) 
def delete_doctor(doctor_id: int):
    doctor = Doctor.query.get_or_404(doctor_id)
    db.session.delete(doctor)
    db.session.commit()
    return redirect(url_for("main.doctors_view"))


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
    doctors = Doctor.query.order_by(Doctor.name).all()
    return render_template("calendar.html", doctors=doctors)


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


@bp.route("/api/doctors", methods=["GET", "POST"])
def api_doctors():
    if request.method == "POST":
        data = request.get_json(force=True, silent=True) or {}
        name = (data.get("name") or "").strip()
        email = (data.get("email") or "").strip() or None
        if not name:
            return jsonify({"error": "Numele este obligatoriu"}), 400
        doctor = Doctor(name=name, email=email)
        db.session.add(doctor)
        db.session.commit()
        return jsonify({"id": doctor.id, "name": doctor.name}), 201

    doctors = Doctor.query.order_by(Doctor.name).all()
    return jsonify([{"id": d.id, "name": d.name} for d in doctors])


@bp.route("/api/doctors/<int:doctor_id>", methods=["DELETE"])
def api_delete_doctor(doctor_id: int):
    doctor = Doctor.query.get_or_404(doctor_id)
    db.session.delete(doctor)
    db.session.commit()
    return "", 204


SERVICES = [
    "Consult",
    "Detartraj",
    "Obturatie carie",
    "Extracție",
    "Tratament canal",
    "Albire",
]


@bp.route("/api/services")
def api_services():
    return jsonify(SERVICES)


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
    doctor_id = request.args.get("doctor_id", type=int)
    if not start or not end or not doctor_id:
        return jsonify([])

    start_dt = parse_to_local_naive(start)
    end_dt = parse_to_local_naive(end)
    if not start_dt or not end_dt:
        return jsonify([])

    appointments = Appointment.query.filter(
        Appointment.doctor_id == doctor_id,
        Appointment.start_at >= start_dt,
        Appointment.end_at <= end_dt,
    ).all()

    events = []
    for a in appointments:
        title = f"{a.patient.full_name} • {a.service}" if a.patient else f"Programare • {a.service}"
        events.append(
            {
                "id": a.id,
                "title": title,
                "start": a.start_at.isoformat(),
                "end": a.end_at.isoformat(),
                "extendedProps": {
                    "note": a.note or "",
                    "patient": {
                        "name": a.patient.full_name if a.patient else "",
                        "phone": a.patient.phone if a.patient else "",
                        "email": a.patient.email if a.patient else "",
                    },
                    "service": a.service,
                    "doctor_id": a.doctor_id,
                },
            }
        )
    return jsonify(events)


@bp.route("/api/events", methods=["POST"])
def api_create_event():
    data = request.get_json(force=True, silent=True) or {}
    patient_id = data.get("patient_id")
    doctor_id = data.get("doctor_id")
    start = data.get("start")
    end = data.get("end")
    service = (data.get("service") or "Consult").strip()
    note = (data.get("note") or "").strip() or None

    if not patient_id or not start or not end or not doctor_id:
        return jsonify({"error": "Câmpuri lipsă"}), 400

    start_dt = parse_to_local_naive(start)
    end_dt = parse_to_local_naive(end)
    if not start_dt or not end_dt:
        return jsonify({"error": "Format dată invalid"}), 400

    patient = Patient.query.get(patient_id)
    doctor = Doctor.query.get(doctor_id)
    if not patient:
        return jsonify({"error": "Pacientul nu există"}), 404
    if not doctor:
        return jsonify({"error": "Medicul nu există"}), 404

    if service not in SERVICES:
        service = "Consult"

    appt = Appointment(
        patient_id=patient.id,
        doctor_id=doctor.id,
        start_at=start_dt,
        end_at=end_dt,
        service=service,
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
    service = data.get("service")

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
    if service:
        appt.service = service if service in SERVICES else appt.service

    appt.reminder_sent = False
    db.session.commit()
    return jsonify({"ok": True})


@bp.route("/api/events/<int:appointment_id>/send_reminder", methods=["POST"])
def api_send_reminder(appointment_id: int):
    appt = Appointment.query.get_or_404(appointment_id)
    ok = send_reminder_for_appointment(appt)
    if ok:
        db.session.commit()
        return jsonify({"ok": True})
    return jsonify({"error": "Trimitere eșuată"}), 500
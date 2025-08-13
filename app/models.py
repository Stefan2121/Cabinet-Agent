from datetime import datetime
from . import db


class Doctor(db.Model):
    __tablename__ = "doctors"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    appointments = db.relationship(
        "Appointment",
        backref="doctor",
        lazy=True,
        cascade="all, delete-orphan",
    )


class Patient(db.Model):
    __tablename__ = "patients"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    appointments = db.relationship(
        "Appointment",
        backref="patient",
        lazy=True,
        cascade="all, delete-orphan",
    )


class Appointment(db.Model):
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False)
    service = db.Column(db.String(60), nullable=False, default="Consult")
    start_at = db.Column(db.DateTime, nullable=False, index=True)
    end_at = db.Column(db.DateTime, nullable=False)
    note = db.Column(db.Text, nullable=True)
    reminder_sent = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
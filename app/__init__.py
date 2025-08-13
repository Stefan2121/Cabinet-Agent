import os
import sys
from flask import Flask, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler


db = SQLAlchemy()
scheduler = BackgroundScheduler(timezone=os.getenv('APP_TIMEZONE', 'Europe/Bucharest'))


def create_app():
    bundled_base = getattr(sys, "_MEIPASS", None)
    base_dir = bundled_base if bundled_base else os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    app = Flask(
        __name__,
        static_folder=os.path.join(base_dir, "static"),
        template_folder=os.path.join(base_dir, "templates"),
    )

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-me")
    # Default DB to local file in current working dir for portability
    db_path = os.getenv("DATABASE_URL", "sqlite:///dental.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = db_path
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    with app.app_context():
        from . import models  # noqa: F401
        db.create_all()
        # Seed default doctors if none exist
        from .models import Doctor
        if Doctor.query.count() == 0:
            db.session.add_all([
                Doctor(name="Dr. Popescu"),
                Doctor(name="Dr. Ionescu"),
            ])
            db.session.commit()

    # Register routes
    from .routes import bp as main_bp
    app.register_blueprint(main_bp)

    # Root redirect to calendar
    @app.route("/")
    def index():
        return redirect(url_for("main.calendar_view"))

    # Schedule reminder job
    from .mail import send_appointment_reminder_emails

    def run_reminders():
        try:
            with app.app_context():
                send_appointment_reminder_emails()
        except Exception as e:
            print(f"Eroare job reminder: {e}")

    if not scheduler.running:
        scheduler.add_job(
            run_reminders,
            "interval",
            hours=1,
            id="reminder_job",
            replace_existing=True,
        )
        try:
            scheduler.start()
        except Exception:
            pass

    return app
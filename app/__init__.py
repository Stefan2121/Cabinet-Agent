import os
from flask import Flask, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler


db = SQLAlchemy()
scheduler = BackgroundScheduler(timezone=os.getenv('APP_TIMEZONE', 'Europe/Bucharest'))


def create_app():
    app = Flask(__name__, static_folder="../static", template_folder="../templates")

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-me")
    db_path = os.getenv("DATABASE_URL", "sqlite:////workspace/dental.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = db_path
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    with app.app_context():
        from . import models  # noqa: F401
        db.create_all()

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
        from datetime import datetime
        try:
            # Ensure app context for DB operations
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
            # In some environments scheduler may fail to start (e.g., fork limitations)
            pass

    return app
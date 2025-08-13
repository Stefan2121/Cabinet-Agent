import os
from dotenv import load_dotenv
import threading
import webbrowser

load_dotenv()

from app import create_app

app = create_app()


def _open_browser():
    try:
        webbrowser.open_new("http://127.0.0.1:5000/")
    except Exception:
        pass


if __name__ == "__main__":
    debug = os.getenv("DEBUG", "false").lower() == "true"
    if os.getenv("OPEN_BROWSER", "true").lower() == "true":
        threading.Timer(1.0, _open_browser).start()
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", 5000)), debug=debug, use_reloader=False)
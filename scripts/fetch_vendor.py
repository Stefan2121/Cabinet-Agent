import os
import urllib.request

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
VENDOR_DIR = os.path.join(BASE_DIR, "static", "vendor")

URLS = [
    ("https://cdn.tailwindcss.com", os.path.join(VENDOR_DIR, "tailwind.js")),
    ("https://cdn.jsdelivr.net/npm/fullcalendar@6.1.15/index.global.min.js", os.path.join(VENDOR_DIR, "fullcalendar", "index.global.min.js")),
    ("https://cdn.jsdelivr.net/npm/fullcalendar@6.1.15/index.global.min.css", os.path.join(VENDOR_DIR, "fullcalendar", "index.global.min.css")),
    ("https://cdn.jsdelivr.net/npm/fullcalendar@6.1.15/locales/ro.global.min.js", os.path.join(VENDOR_DIR, "fullcalendar", "locales", "ro.global.min.js")),
]


def download(url: str, path: str):
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
    print(f"Downloading {url} -> {path}")
    urllib.request.urlretrieve(url, path)


def main():
    for url, path in URLS:
        download(url, path)
    print("Done.")


if __name__ == "__main__":
    main()
# Agenda Cabinet Stomatologic

Aplicație web simplă pentru gestionarea pacienților și programărilor unui cabinet stomatologic, cu remindere automate pe email cu 2 zile înainte.

## Tehnologii
- Flask + SQLite
- FullCalendar pentru vizualizarea programărilor (lună / săptămână)
- Tailwind CSS pentru UI
- APScheduler pentru jobul de remindere

## Configurare
1. Python 3.10+
2. Instalează dependențele:
```bash
pip install -r requirements.txt
```
3. (Opțional) Configurează variabilele de mediu pentru email. Creează un fișier `.env` sau exportă în shell:
```
SECRET_KEY=schimba-ma
APP_TIMEZONE=Europe/Bucharest
DATABASE_URL=sqlite:////workspace/dental.db

# Config SMTP (opțional; dacă lipsesc, emailurile se vor afișa în consolă)
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=utilizator@example.com
SMTP_PASS=parola
SENDER_EMAIL=utilizator@example.com
SENDER_NAME=Cabinet Stomatologic
```
4. Rulează aplicația:
```bash
python app.py
```
Apoi deschide `http://localhost:5000`.

## Funcționalități
- Înregistrare pacienți (nume, telefon, email)
- Calendar lună/săptămână, creare programări prin selectarea intervalului
- Reprogramare prin drag & drop sau editare din modal
- Ștergere programare
- Reminder automat pe email cu 2 zile înainte (rulează orar; dacă SMTP nu e configurat, se loghează în consolă)

## Note
- Datele sunt stocate în `SQLite` la calea setată de `DATABASE_URL` (implicit `/workspace/dental.db`).
- Timpurile sunt tratate ca timp local (ex. `Europe/Bucharest`).

## Rulare în browser (web) - producție
- Instalează gunicorn:
```bash
pip install gunicorn
```
- Rulează serverul WSGI:
```bash
gunicorn -w 2 -b 0.0.0.0:5000 wsgi:app
```
- Pentru deploy pe un server Linux: rulează gunicorn ca serviciu systemd sau într-un container Docker în spatele unui reverse proxy (ex. Nginx).

## Build EXE pentru Windows (installer)
1. Pe Windows, cu Python instalat, creează un mediu și instalează dependențele și PyInstaller:
```powershell
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller
```
2. Descarcă asset-urile vendor (o singură dată):
```powershell
py scripts\fetch_vendor.py
```
3. Construiește executabilul:
```powershell
pyinstaller --noconsole --onefile ^
  --add-data "templates;templates" ^
  --add-data "static;static" app.py
```
4. (Opțional) Creează un installer folosind Inno Setup sau NSIS, incluzând fișierul `dist\app.exe`.

## Medici inițiali
- La prima pornire, dacă nu există medici în baza de date, se adaugă automat: `Simona Hutanu` și `Iustin Dumitrescu`.

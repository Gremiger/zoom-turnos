"""Toma una foto de los turnos de MUSCULACION de hoy y la agrega a data/observaciones.csv.

Solo agrega una fila cuando el número de reservas de un turno cambió respecto de la
última vez que se vio, así el CSV crece poco. Credenciales en ZOOM_EMAIL / ZOOM_PASSWORD.
"""
import csv
import http.cookiejar
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = "https://espaciozoom.misactividades.com"
BRANCH_ID = "299d25ab-759c-4fb6-b72f-d824b4559091"  # SEDE BANDA NORTE RIO IV
ACTIVITY = "MUSCULACION"
TZ = ZoneInfo("America/Argentina/Cordoba")
CSV_PATH = Path(__file__).parent / "data" / "observaciones.csv"
FIELDS = ["observado", "fecha", "hora", "reservas", "cupo"]
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"


def make_opener():
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    opener.addheaders = [("User-Agent", UA), ("X-Requested-With", "XMLHttpRequest")]
    return opener


def login(opener, email, password):
    page = opener.open(f"{BASE}/account/login", timeout=30).read().decode()
    token = re.search(r'name="__RequestVerificationToken" type="hidden" value="([^"]+)"', page).group(1)
    body = urllib.parse.urlencode({"Email": email, "Password": password, "__RequestVerificationToken": token}).encode()
    resp = opener.open(f"{BASE}/account/login", data=body, timeout=30).read().decode()
    if '"success":true' not in resp:
        sys.exit(f"Login falló: {resp[:200]}")


def fetch_slots(opener, date):
    qs = urllib.parse.urlencode({"branchId": BRANCH_ID, "date": date})
    html = opener.open(f"{BASE}/bookings/getbookings?{qs}", timeout=30).read().decode()
    slots = {}
    for block in html.split('id="booking-')[1:]:
        m = re.search(r'data-activity="([^"]+)".*?data-date="([^"]+)" data-time="([^"]+)"', block, re.S)
        n = re.search(r"(\d+) de (\d+) lugares", block)
        if m and n and m.group(1) == ACTIVITY and m.group(2) == date:
            slots[m.group(3)] = (int(n.group(1)), int(n.group(2)))
    return slots


def last_seen(rows):
    last = {}
    for r in rows:
        last[(r["fecha"], r["hora"])] = (int(r["reservas"]), int(r["cupo"]))
    return last


def main():
    now = datetime.now(TZ)
    today = now.strftime("%Y-%m-%d")
    opener = make_opener()
    login(opener, os.environ["ZOOM_EMAIL"], os.environ["ZOOM_PASSWORD"])
    slots = fetch_slots(opener, today)

    rows = []
    if CSV_PATH.exists():
        with CSV_PATH.open() as f:
            rows = list(csv.DictReader(f))
    previous = last_seen(rows)

    new_rows = [
        {"observado": now.strftime("%Y-%m-%d %H:%M"), "fecha": today, "hora": hora, "reservas": b, "cupo": c}
        for hora, (b, c) in sorted(slots.items())
        if previous.get((today, hora)) != (b, c)
    ]
    CSV_PATH.parent.mkdir(exist_ok=True)
    write_header = not CSV_PATH.exists()
    with CSV_PATH.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if write_header:
            w.writeheader()
        w.writerows(new_rows)
    print(f"{now:%H:%M} turnos visibles: {len(slots)}, filas nuevas: {len(new_rows)}")


if __name__ == "__main__":
    main()

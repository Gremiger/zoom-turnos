# zoom-turnos

Registra cada 10 minutos la ocupación de los turnos de MUSCULACION de la Sede Banda Norte Río IV
(espaciozoom.misactividades.com) y publica un mapa de calor en GitHub Pages (`docs/index.html`).

- `scrape.py` — login + foto de los turnos de hoy → `data/observaciones.csv` (solo agrega filas cuando cambia un número).
- `report.py` — calcula la ocupación final de cada turno (última foto antes de inicio + 30 min) y genera la página.
- `.github/workflows/scrape.yml` — corre ambos cada 10 min y commitea si hubo cambios.

Secrets necesarios: `ZOOM_EMAIL`, `ZOOM_PASSWORD`.

Local: `ZOOM_EMAIL=... ZOOM_PASSWORD=... python3 scrape.py && python3 report.py`

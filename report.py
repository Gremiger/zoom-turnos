"""Genera docs/index.html: ocupación final promedio de MUSCULACION por día de la semana y horario.

La "foto final" de un turno es la última observación antes de que cierre su reserva
(inicio + 30 min). Si no hubo ninguna antes, se usa la primera posterior.
"""
import csv
import html
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from statistics import mean
from zoneinfo import ZoneInfo

ROOT = Path(__file__).parent
CSV_PATH = ROOT / "data" / "observaciones.csv"
OUT = ROOT / "docs" / "index.html"
TZ = ZoneInfo("America/Argentina/Cordoba")
CUTOFF = timedelta(minutes=30)
DAYS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
WORK_HOURS = (9, 15)  # lun-vie: turnos que empiezan en [9, 15) no sirven


def final_snapshots(rows):
    by_slot = defaultdict(list)
    for r in rows:
        by_slot[(r["fecha"], r["hora"])].append(r)
    finals = {}
    for (fecha, hora), obs in by_slot.items():
        cutoff = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M") + CUTOFF
        obs.sort(key=lambda r: r["observado"])
        before = [r for r in obs if datetime.strptime(r["observado"], "%Y-%m-%d %H:%M") <= cutoff]
        pick = before[-1] if before else obs[0]
        finals[(fecha, hora)] = (int(pick["reservas"]), int(pick["cupo"]))
    return finals


def is_work_slot(weekday, hora):
    h = int(hora[:2])
    return weekday < 5 and WORK_HOURS[0] <= h < WORK_HOURS[1]


def color(pct):
    # verde (vacío) -> amarillo -> rojo (lleno); escala hasta 60 % para que se note la diferencia
    t = min(pct / 60, 1)
    hue = 130 - 130 * t
    return f"hsl({hue:.0f} 65% 45%)"


def render(finals, n_obs):
    stats = defaultdict(list)  # (weekday, hora) -> [pct...]
    for (fecha, hora), (b, c) in finals.items():
        wd = datetime.strptime(fecha, "%Y-%m-%d").weekday()
        stats[(wd, hora)].append(100 * b / c if c else 0)
    horas = sorted({h for _, h in stats})
    fechas = sorted({f for f, _ in finals})

    head = "".join(f"<th>{d}</th>" for d in DAYS)
    body = []
    for hora in horas:
        cells = []
        for wd in range(7):
            vals = stats.get((wd, hora))
            if not vals:
                cells.append('<td class="na">·</td>')
                continue
            avg = mean(vals)
            cls = "work" if is_work_slot(wd, hora) else ""
            tip = f"{DAYS[wd]} {hora}: promedio {avg:.0f}% · mín {min(vals):.0f}% · máx {max(vals):.0f}% · {len(vals)} días"
            cells.append(
                f'<td class="{cls}" style="background:{color(avg)}" title="{html.escape(tip)}">'
                f"{avg:.0f}%<small>n={len(vals)}</small></td>"
            )
        body.append(f"<tr><th>{hora}</th>{''.join(cells)}</tr>")

    ranking = sorted(
        ((mean(v), wd, h, len(v)) for (wd, h), v in stats.items() if not is_work_slot(wd, h)),
    )[:10]
    rank_html = "".join(
        f"<li><b>{DAYS[wd]} {h}</b> — {avg:.0f}% en promedio <small>({n} días)</small></li>"
        for avg, wd, h, n in ranking
    )

    recent = []
    for fecha in fechas[-7:][::-1]:
        wd = datetime.strptime(fecha, "%Y-%m-%d").weekday()
        items = " ".join(
            f'<span class="chip" style="border-color:{color(100 * b / c)}">{h} <b>{b}</b>/{c}</span>'
            for (f, h), (b, c) in sorted(finals.items())
            if f == fecha
        )
        recent.append(f"<tr><th>{DAYS[wd]} {fecha[8:]}/{fecha[5:7]}</th><td>{items}</td></tr>")

    updated = datetime.now(TZ).strftime("%d/%m/%Y %H:%M")
    period = f"{fechas[0]} → {fechas[-1]}" if fechas else "sin datos todavía"
    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Musculación Banda Norte</title>
<style>
:root {{ --bg:#f6f6f4; --fg:#1b1b1b; --muted:#6b6b6b; --card:#fff; --line:#e3e3e0; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#141414; --fg:#eee; --muted:#9a9a9a; --card:#1e1e1e; --line:#333; }} }}
body {{ margin:0; padding:24px 16px; background:var(--bg); color:var(--fg); font:15px/1.45 system-ui,sans-serif; }}
main {{ max-width:900px; margin:auto; }}
h1 {{ font-size:22px; margin:0 0 4px; }} h2 {{ font-size:17px; margin:28px 0 8px; }}
.muted {{ color:var(--muted); font-size:13px; }}
.wrap {{ overflow-x:auto; }}
table.heat {{ border-collapse:separate; border-spacing:3px; width:100%; }}
.heat th {{ font-weight:600; font-size:13px; padding:4px; }}
.heat td {{ color:#fff; text-align:center; border-radius:6px; padding:6px 2px; font-weight:600; min-width:48px; }}
.heat td small {{ display:block; font-weight:400; font-size:10px; opacity:.85; }}
.heat td.work {{ opacity:.25; }}
.heat td.na {{ background:transparent; color:var(--muted); }}
ol {{ padding-left:22px; }} li {{ margin:3px 0; }}
table.recent th {{ text-align:left; padding:6px 10px 6px 0; white-space:nowrap; font-weight:600; vertical-align:top; }}
.chip {{ display:inline-block; border:2px solid; border-radius:12px; padding:1px 8px; margin:2px; font-size:13px; background:var(--card); }}
</style></head><body><main>
<h1>Musculación · Sede Banda Norte Río IV</h1>
<p class="muted">Ocupación final de cada turno (reservas al cierre, inicio + 30 min) sobre el cupo.
Período: {period} · {n_obs} observaciones · actualizado {updated}.</p>

<h2>Horarios más tranquilos <span class="muted">(sin lun–vie 9–15)</span></h2>
<ol>{rank_html or "<li>Todavía no hay datos.</li>"}</ol>

<h2>Promedio por día y horario</h2>
<p class="muted">Verde = vacío, rojo = 60 % o más. Atenuado: lun–vie 9 a 15. Pasá el mouse para ver mín/máx.</p>
<div class="wrap"><table class="heat"><tr><th></th>{head}</tr>{''.join(body)}</table></div>

<h2>Últimos días</h2>
<div class="wrap"><table class="recent">{''.join(recent)}</table></div>
</main></body></html>
"""


def main():
    rows = []
    if CSV_PATH.exists():
        with CSV_PATH.open() as f:
            rows = list(csv.DictReader(f))
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(render(final_snapshots(rows), len(rows)))
    print(f"Reporte: {OUT}")


if __name__ == "__main__":
    main()

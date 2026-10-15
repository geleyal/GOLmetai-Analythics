from __future__ import annotations

import io
import json
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
import requests
import streamlit as st
from mplsoccer import Pitch

APP_TITLE = "GOLmetai Analytics"
BASE_RAW = "https://raw.githubusercontent.com/hudl/open-data/master/data"
HEADERS = {"User-Agent": "GOLmetai-Analytics/0.1 (open football-data research project)"}

st.set_page_config(page_title=APP_TITLE, page_icon="⚽", layout="wide")

# ---------- Data access ----------
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_json(url: str) -> Any:
    """Fetch a public JSON resource and cache it for one hour."""
    response = requests.get(url, headers=HEADERS, timeout=45)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=3600, show_spinner=False)
def load_competitions() -> pd.DataFrame:
    data = fetch_json(f"{BASE_RAW}/competitions.json")
    df = pd.DataFrame(data)
    if df.empty:
        return df
    df["competition_label"] = df.apply(
        lambda r: f"{r.get('competition_name', 'Competición')} — {r.get('season_name', 'Temporada')} ({r.get('country_name', 'Sin país')})",
        axis=1,
    )
    return df.sort_values(["competition_name", "season_name"], ascending=[True, False])


@st.cache_data(ttl=3600, show_spinner=False)
def load_matches(competition_id: int, season_id: int) -> pd.DataFrame:
    data = fetch_json(f"{BASE_RAW}/matches/{competition_id}/{season_id}.json")
    df = pd.DataFrame(data)
    if df.empty:
        return df
    for col in ["home_team", "away_team"]:
        if col not in df.columns:
            df[col] = None
    df["home_name"] = df["home_team"].apply(lambda x: x.get("home_team_name", "Local") if isinstance(x, dict) else "Local")
    df["away_name"] = df["away_team"].apply(lambda x: x.get("away_team_name", "Visitante") if isinstance(x, dict) else "Visitante")
    df["match_label"] = df.apply(
        lambda r: f"{str(r.get('match_date', 'Fecha desconocida'))[:10]} · {r['home_name']} vs {r['away_name']} · ID {r.get('match_id', '?')}",
        axis=1,
    )
    return df.sort_values("match_date", ascending=False)


@st.cache_data(ttl=3600, show_spinner=False)
def load_events(match_id: int) -> pd.DataFrame:
    raw = fetch_json(f"{BASE_RAW}/events/{match_id}.json")
    rows: list[dict[str, Any]] = []
    for e in raw:
        loc = e.get("location")
        player = e.get("player") or {}
        team = e.get("team") or {}
        event_type = (e.get("type") or {}).get("name", "Unknown")
        period = e.get("period")
        minute = e.get("minute", 0) or 0
        second = e.get("second", 0) or 0
        # Convert the provider's match clock into a clock within each half.
        if period == 1:
            half_minute = float(minute) + float(second) / 60
        elif period == 2:
            half_minute = max(0.0, float(minute) - 45) + float(second) / 60
        elif period == 3:
            half_minute = max(0.0, float(minute) - 90) + float(second) / 60
        elif period == 4:
            half_minute = max(0.0, float(minute) - 105) + float(second) / 60
        else:
            half_minute = float(minute) + float(second) / 60
        pass_data = e.get("pass") or {}
        shot_data = e.get("shot") or {}
        dribble_data = e.get("dribble") or {}
        duel_data = e.get("duel") or {}
        carry_data = e.get("carry") or {}
        outcome = (pass_data.get("outcome") or {}).get("name")
        shot_outcome = (shot_data.get("outcome") or {}).get("name")
        dribble_outcome = (dribble_data.get("outcome") or {}).get("name")
        duel_type = (duel_data.get("type") or {}).get("name")
        end_loc = pass_data.get("end_location") or shot_data.get("end_location") or carry_data.get("end_location")
        rows.append({
            "event_id": e.get("id"), "match_id": match_id,
            "period": period, "minute": int(minute), "second": int(second),
            "half_minute": half_minute, "timestamp": e.get("timestamp", ""),
            "player": player.get("name", "(Sin jugador)"),
            "team": team.get("name", "(Sin equipo)"), "type": event_type,
            "x": loc[0] if isinstance(loc, list) and len(loc) >= 2 else None,
            "y": loc[1] if isinstance(loc, list) and len(loc) >= 2 else None,
            "end_x": end_loc[0] if isinstance(end_loc, list) and len(end_loc) >= 2 else None,
            "end_y": end_loc[1] if isinstance(end_loc, list) and len(end_loc) >= 2 else None,
            "pass_outcome": outcome, "shot_outcome": shot_outcome,
            "dribble_outcome": dribble_outcome, "duel_type": duel_type,
            "pass_goal_assist": bool(pass_data.get("goal_assist", False)),
            "pass_key_pass": bool(pass_data.get("shot_assist", False)),
            "pass_length": pass_data.get("length"),
            "pass_angle": pass_data.get("angle"),
            "under_pressure": bool(e.get("under_pressure", False)),
        })
    return pd.DataFrame(rows)


# ---------- Analysis ----------
def in_time_window(df: pd.DataFrame, half: str, start: float, end: float) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    if half == "Primer tiempo":
        d = df[df["period"] == 1]
    elif half == "Segundo tiempo":
        d = df[df["period"] == 2]
    elif half == "Prórroga":
        d = df[df["period"].isin([3, 4])]
    else:
        d = df
    return d[(d["half_minute"] >= start) & (d["half_minute"] <= end)].copy()


def player_metrics(df: pd.DataFrame, player: str) -> dict[str, float | int | str]:
    d = df[df["player"] == player].copy()
    passes = d[d["type"] == "Pass"]
    completed = passes[passes["pass_outcome"].isna()]
    shots = d[d["type"] == "Shot"]
    on_target_outcomes = {"Goal", "Saved", "Saved to Post"}
    dribbles = d[d["type"] == "Dribble"]
    recoveries = d[d["type"] == "Ball Recovery"]
    interceptions = d[d["type"] == "Interception"]
    pressures = d[d["type"] == "Pressure"]
    tackles = d[(d["type"] == "Duel") & (d["duel_type"] == "Tackle")]
    clearances = d[d["type"] == "Clearance"]
    fouls = d[d["type"].isin(["Foul Committed", "Foul Won"])]
    dispossessed = d[d["type"].isin(["Dispossessed", "Miscontrol"])]
    carries = d[d["type"] == "Carry"]
    goals = int((shots["shot_outcome"] == "Goal").sum())
    return {
        "Jugador": player,
        "Pases intentados": int(len(passes)),
        "Pases completados": int(len(completed)),
        "Precisión de pase (%)": round(100 * len(completed) / len(passes), 1) if len(passes) else 0.0,
        "Tiros": int(len(shots)),
        "Tiros a puerta*": int(shots["shot_outcome"].isin(on_target_outcomes).sum()),
        "Goles": goals,
        "Asistencias registradas": int(d["pass_goal_assist"].sum()),
        "Regates intentados": int(len(dribbles)),
        "Regates completados": int((dribbles["dribble_outcome"] == "Complete").sum()),
        "Recuperaciones": int(len(recoveries)),
        "Intercepciones": int(len(interceptions)),
        "Entradas registradas": int(len(tackles)),
        "Presiones": int(len(pressures)),
        "Despejes": int(len(clearances)),
        "Faltas cometidas/recibidas": int(len(fouls)),
        "Pérdidas (dispossessed/miscontrol)": int(len(dispossessed)),
        "Conducciones registradas": int(len(carries)),
        "Acciones con coordenadas": int(d["x"].notna().sum()),
    }


def draw_heatmap(df: pd.DataFrame, player: str, title: str):
    d = df[(df["player"] == player) & df["x"].notna() & df["y"].notna()]
    pitch = Pitch(pitch_type="statsbomb", pitch_color="#101820", line_color="#dbe4ee", linewidth=1)
    fig, ax = pitch.draw(figsize=(8, 5))
    fig.patch.set_facecolor("#101820")
    ax.set_facecolor("#101820")
    if len(d):
        stat = pitch.bin_statistic(d["x"], d["y"], statistic="count", bins=(12, 8))
        pitch.heatmap(stat, ax=ax, cmap="magma", edgecolors="#101820", alpha=0.88)
        # Show event locations subtly on top of the heatmap.
        pitch.scatter(d["x"], d["y"], ax=ax, s=5, color="#ffffff", alpha=0.18, zorder=3)
    ax.set_title(title, color="white", fontsize=12, pad=12)
    fig.tight_layout()
    return fig


def draw_pass_map(df: pd.DataFrame, player: str, title: str):
    d = df[(df["player"] == player) & (df["type"] == "Pass")].dropna(subset=["x", "y", "end_x", "end_y"])
    pitch = Pitch(pitch_type="statsbomb", pitch_color="#101820", line_color="#dbe4ee", linewidth=1)
    fig, ax = pitch.draw(figsize=(8, 5))
    fig.patch.set_facecolor("#101820")
    ax.set_facecolor("#101820")
    if len(d):
        completed = d["pass_outcome"].isna()
        if completed.any():
            pitch.arrows(d.loc[completed, "x"], d.loc[completed, "y"], d.loc[completed, "end_x"], d.loc[completed, "end_y"], ax=ax, color="#38bdf8", width=1.5, headwidth=4, alpha=0.75)
        if (~completed).any():
            pitch.arrows(d.loc[~completed, "x"], d.loc[~completed, "y"], d.loc[~completed, "end_x"], d.loc[~completed, "end_y"], ax=ax, color="#fb7185", width=1.5, headwidth=4, alpha=0.8)
    ax.set_title(title, color="white", fontsize=12, pad=12)
    fig.tight_layout()
    return fig


# ---------- Interface ----------
st.markdown("# ⚽ GOLmetai Analytics")
st.caption("Comparador de rendimiento · datos abiertos de StatsBomb · análisis por intervalos")
st.info("Fuente de esta versión: StatsBomb Open Data. Solo aparecen competiciones y partidos publicados en ese repositorio. Si publicas análisis derivados, atribuye los datos a StatsBomb y consulta sus condiciones de uso.")

try:
    with st.spinner("Cargando competiciones disponibles..."):
        comps = load_competitions()
except Exception as exc:
    st.error("No se pudo conectar con StatsBomb Open Data. Comprueba tu conexión e inténtalo de nuevo.")
    st.code(str(exc))
    st.stop()

if comps.empty:
    st.warning("No se encontraron competiciones en la fuente de datos.")
    st.stop()

comp_labels = comps["competition_label"].tolist()
selected_comp_label = st.selectbox("Competición y temporada", comp_labels)
comp_row = comps.loc[comps["competition_label"] == selected_comp_label].iloc[0]

try:
    matches = load_matches(int(comp_row["competition_id"]), int(comp_row["season_id"]))
except Exception as exc:
    st.error("No se pudieron cargar los partidos de esta competición/temporada.")
    st.code(str(exc))
    st.stop()

if matches.empty:
    st.warning("Esta selección no tiene partidos disponibles.")
    st.stop()
match_labels = matches["match_label"].tolist()
selected_match_label = st.selectbox("Partido", match_labels)
match_row = matches.loc[matches["match_label"] == selected_match_label].iloc[0]
match_id = int(match_row["match_id"])

try:
    with st.spinner("Cargando eventos del partido..."):
        events = load_events(match_id)
except Exception as exc:
    st.error("No se pudieron cargar los eventos del partido.")
    st.code(str(exc))
    st.stop()

if events.empty:
    st.warning("Este partido no tiene eventos disponibles en la fuente.")
    st.stop()

# Time controls: interval values are minutes within the selected period.
st.subheader("1. Selecciona el periodo y el intervalo")
period_label = st.radio("Periodo", ["Primer tiempo", "Segundo tiempo", "Todo el partido", "Prórroga"], horizontal=True)
if period_label in ("Primer tiempo", "Segundo tiempo"):
    default_end = 45
    max_end = 60  # includes typical stoppage time and gives some margin
elif period_label == "Prórroga":
    default_end = 15
    max_end = 30
else:
    default_end = 90
    max_end = 120
c1, c2 = st.columns(2)
with c1:
    start_min = st.number_input("Desde el minuto", min_value=0, max_value=max_end, value=0, step=1)
with c2:
    end_min = st.number_input("Hasta el minuto", min_value=0, max_value=max_end, value=default_end, step=1)
if start_min > end_min:
    st.error("El minuto inicial debe ser menor o igual al minuto final.")
    st.stop()

filtered = in_time_window(events, period_label, float(start_min), float(end_min))
if period_label == "Todo el partido":
    # In full-match mode, use the absolute match clock for the selected interval.
    filtered = events[(events["minute"] + events["second"] / 60 >= start_min) & (events["minute"] + events["second"] / 60 <= end_min)].copy()

players = sorted(p for p in filtered["player"].dropna().unique().tolist() if p != "(Sin jugador)")
if len(players) < 2:
    # Keep choices available even if a player has no event in the current time slice.
    players = sorted(p for p in events["player"].dropna().unique().tolist() if p != "(Sin jugador)")
if len(players) < 2:
    st.warning("No hay suficientes jugadores identificados para comparar este partido.")
    st.stop()

st.caption(f"Eventos dentro del filtro: {len(filtered):,}. Los minutos se interpretan dentro del periodo elegido; 'Todo el partido' utiliza el reloj de partido del proveedor.")
st.subheader("2. Elige los jugadores")
p1, p2 = st.columns(2)
with p1:
    player_a = st.selectbox("Jugador A", players, index=0)
with p2:
    default_b = 1 if len(players) > 1 else 0
    player_b = st.selectbox("Jugador B", players, index=default_b)
if player_a == player_b:
    st.warning("Selecciona dos jugadores diferentes para comparar.")
    st.stop()

# Summary table
st.subheader("3. Comparación estadística")
metrics_a = player_metrics(filtered, player_a)
metrics_b = player_metrics(filtered, player_b)
metric_df = pd.DataFrame([metrics_a, metrics_b]).set_index("Jugador").T
st.dataframe(metric_df, use_container_width=True)

# Side-by-side maps
st.subheader("4. Mapas de calor")
ha, hb = st.columns(2)
with ha:
    st.pyplot(draw_heatmap(filtered, player_a, f"{player_a} · mapa de acciones"), use_container_width=True)
with hb:
    st.pyplot(draw_heatmap(filtered, player_b, f"{player_b} · mapa de acciones"), use_container_width=True)
st.caption("El mapa refleja las coordenadas de eventos registradas, no un seguimiento continuo de cada posición del futbolista.")

st.subheader("5. Mapas de pases")
pa, pb = st.columns(2)
with pa:
    st.pyplot(draw_pass_map(filtered, player_a, f"{player_a} · pases"), use_container_width=True)
with pb:
    st.pyplot(draw_pass_map(filtered, player_b, f"{player_b} · pases"), use_container_width=True)
st.caption("Azul = pase completado; rosa = pase con resultado registrado como fallido. La clasificación depende de los campos disponibles en StatsBomb.")

st.subheader("6. Acciones del intervalo")
show_cols = ["minute", "second", "team", "player", "type", "x", "y", "end_x", "end_y", "pass_outcome", "shot_outcome", "dribble_outcome"]
show_cols = [c for c in show_cols if c in filtered.columns]
player_events = filtered[filtered["player"].isin([player_a, player_b])][show_cols].sort_values(["minute", "second"])
st.dataframe(player_events, use_container_width=True, hide_index=True)

csv_bytes = player_events.to_csv(index=False).encode("utf-8-sig")
st.download_button("Descargar eventos comparados (CSV)", data=csv_bytes, file_name=f"golmetai_match_{match_id}_{start_min}-{end_min}.csv", mime="text/csv")

with st.expander("Metodología y limitaciones"):
    st.markdown("""
    - Los datos se obtienen de **StatsBomb Open Data** y se consultan desde el repositorio público de GitHub.
    - Las métricas cuentan eventos registrados; no son equivalentes a todas las definiciones de proveedores comerciales.
    - `Tiros a puerta*` cuenta goles y resultados de tiro registrados como `Saved` o `Saved to Post`; algunos proveedores clasifican los postes de otra manera.
    - La precisión de pase considera completados los pases cuyo campo `pass.outcome` está vacío.
    - Las entradas se aproximan con eventos de tipo `Duel` cuyo subtipo es `Tackle`; revisa la definición de la fuente antes de publicar cifras.
    - Los mapas de calor se basan en coordenadas de eventos. No son mapas de tracking continuo ni necesariamente equivalen a mapas comerciales de ocupación.
    - Si publicas o redistribuyes análisis derivados, atribuye la fuente a StatsBomb y revisa sus términos de uso vigentes.
    """)

st.divider()
st.caption("GOLmetai Analytics · prototipo gratuito · no afiliado a StatsBomb")

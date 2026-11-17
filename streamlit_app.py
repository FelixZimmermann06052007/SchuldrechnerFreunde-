import math
import re
from fractions import Fraction

import streamlit as st


MAX_EXAKT = 16


def euro(cent: int) -> str:
    return f"{cent / 100:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def parse_betrag(text: str) -> int:
    text = str(text).strip().replace("€", "").replace(" ", "")
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        wert = float(text)
    except ValueError:
        raise ValueError("Bitte einen gültigen Betrag eingeben, z. B. 12,50 €.")
    if not math.isfinite(wert) or wert <= 0:
        raise ValueError("Der Betrag muss eine positive Zahl sein.")
    return int(round(wert * 100))


def netto_salden(schulden, erledigt=()):
    salden = {}
    for schuldner, glaeubiger, cent in schulden:
        salden[schuldner] = salden.get(schuldner, 0) - cent
        salden[glaeubiger] = salden.get(glaeubiger, 0) + cent
    for von, an, cent in erledigt:
        salden[von] = salden.get(von, 0) + cent
        salden[an] = salden.get(an, 0) - cent
    return salden


def greedy_ausgleich(items):
    salden = {name: saldo for name, saldo in items if saldo != 0}
    zahlungen = []
    while salden:
        schuldner = min(salden, key=salden.get)
        glaeubiger = max(salden, key=salden.get)
        betrag = min(-salden[schuldner], salden[glaeubiger])
        zahlungen.append((schuldner, glaeubiger, betrag))
        salden[schuldner] += betrag
        salden[glaeubiger] -= betrag
        for name in (schuldner, glaeubiger):
            if salden[name] == 0:
                del salden[name]
    return zahlungen


def optimaler_ausgleich(salden):
    personen = [(name, saldo) for name, saldo in sorted(salden.items()) if saldo]
    n = len(personen)
    if n == 0:
        return [], True
    if n > MAX_EXAKT:
        return greedy_ausgleich(personen), False

    werte = [saldo for _, saldo in personen]
    voll = (1 << n) - 1
    summen = [0] * (voll + 1)
    for maske in range(1, voll + 1):
        bit = maske & -maske
        summen[maske] = summen[maske ^ bit] + werte[bit.bit_length() - 1]

    dp = [0] * (voll + 1)
    wahl = [0] * (voll + 1)
    for maske in range(1, voll + 1):
        bester, bester_i = -1, 0
        for i in range(n):
            if maske >> i & 1:
                kandidat = dp[maske ^ (1 << i)]
                if kandidat > bester:
                    bester, bester_i = kandidat, i
        dp[maske] = bester + (1 if summen[maske] == 0 else 0)
        wahl[maske] = bester_i

    reihenfolge = []
    maske = voll
    while maske:
        i = wahl[maske]
        reihenfolge.append(i)
        maske ^= 1 << i
    reihenfolge.reverse()

    gruppen, aktuell, laufsumme = [], [], 0
    for i in reihenfolge:
        aktuell.append(personen[i])
        laufsumme += werte[i]
        if laufsumme == 0:
            gruppen.append(aktuell)
            aktuell, laufsumme = [], 0

    zahlungen = []
    for gruppe in gruppen:
        zahlungen.extend(greedy_ausgleich(gruppe))
    return zahlungen, True


def teile_rechnung(zahler, gesamt_cent, teilnehmer_text):
    teile = [teil.strip() for teil in re.split(r"[,;\\n]", teilnehmer_text) if teil.strip()]
    if not zahler.strip() or not teile:
        raise ValueError("Bitte Zahler und mindestens einen Teilnehmer angeben.")
    namen, gewichte, anteile_vorhanden = [], [], 0
    for teil in teile:
        if ":" in teil:
            name, gewicht_text = teil.rsplit(":", 1)
            gewicht_text = gewicht_text.replace("%", "").strip()
            try:
                gewicht = Fraction(gewicht_text.replace(",", "."))
            except (ValueError, ZeroDivisionError):
                raise ValueError(f"Ungültiger Anteil: {teil}")
            anteile_vorhanden += 1
        else:
            name, gewicht = teil, Fraction(1)
        name = name.strip()
        if not name or gewicht <= 0:
            raise ValueError("Namen und Anteile müssen gültig und positiv sein.")
        namen.append(name)
        gewichte.append(gewicht)
    if anteile_vorhanden not in (0, len(teile)):
        raise ValueError("Bitte entweder bei allen Teilnehmern Anteile angeben oder bei keinem.")
    if len({n.casefold() for n in namen}) != len(namen):
        raise ValueError("Ein Teilnehmer ist doppelt aufgeführt.")

    gesamtgewicht = sum(gewichte)
    roh = [Fraction(gesamt_cent) * g / gesamtgewicht for g in gewichte]
    anteile = [r.numerator // r.denominator for r in roh]
    rest = gesamt_cent - sum(anteile)
    for i in sorted(range(len(namen)), key=lambda j: roh[j] - anteile[j], reverse=True)[:rest]:
        anteile[i] += 1
    anteile_dict = dict(zip(namen, anteile))
    schulden = [(n, zahler.strip(), c) for n, c in anteile_dict.items()
                if c > 0 and n.casefold() != zahler.strip().casefold()]
    return schulden, anteile_dict


def graphviz_dot(kanten, salden, titel):
    personen = sorted(set(salden) | {p for a, b, _ in kanten for p in (a, b)}, key=str.casefold)
    zeilen = ["digraph G {", '  graph [rankdir="LR", bgcolor="transparent", label="' + titel + '", labelloc="t"];',
              '  node [shape="ellipse", style="filled", fontname="Arial"];',
              '  edge [fontname="Arial"];']
    for p in personen:
        saldo = salden.get(p, 0)
        farbe = "#a8e0b0" if saldo > 0 else "#f2a9a9" if saldo < 0 else "#dddddd"
        safe = p.replace('"', '\\"')
        zeilen.append(f'  "{safe}" [fillcolor="{farbe}"];')
    for a, b, cent in kanten:
        aa, bb = a.replace('"', '\\"'), b.replace('"', '\\"')
        zeilen.append(f'  "{aa}" -> "{bb}" [label="{euro(cent)}"];')
    zeilen.append("}")
    return "\\n".join(zeilen)


st.set_page_config(page_title="Schuldenrechner Freunde", page_icon="💶", layout="wide")
st.title("💶 Schuldenrechner für Freunde")
st.caption("Wer schuldet wem was? Erfasse gemeinsame Ausgaben und berechne einen möglichst einfachen Ausgleich.")

if "schulden" not in st.session_state:
    st.session_state.schulden = []
if "erledigt" not in st.session_state:
    st.session_state.erledigt = []


with st.sidebar:
    st.header("Neue Schuld erfassen")
    with st.form("neue_schuld", clear_on_submit=True):
        schuldner = st.text_input("Wer muss zahlen?")
        glaeubiger = st.text_input("Wer bekommt das Geld?")
        betrag_text = st.text_input("Betrag in Euro", placeholder="z. B. 12,50")
        beschreibung = st.text_input("Beschreibung", placeholder="z. B. Pizza")
        add = st.form_submit_button("Schuld hinzufügen", use_container_width=True)
    if add:
        try:
            cent = parse_betrag(betrag_text)
            if not schuldner.strip() or not glaeubiger.strip():
                raise ValueError("Bitte beide Namen angeben.")
            if schuldner.strip().casefold() == glaeubiger.strip().casefold():
                raise ValueError("Schuldner und Gläubiger müssen verschieden sein.")
            st.session_state.schulden.append({"von": schuldner.strip(), "an": glaeubiger.strip(),
                                               "cent": cent, "text": beschreibung.strip() or "Ohne Beschreibung",
                                               "bezahlt": False})
            st.success("Schuld wurde hinzugefügt.")
        except ValueError as exc:
            st.error(str(exc))

    st.divider()
    st.header("Rechnung teilen")
    with st.form("rechnung_teilen", clear_on_submit=True):
        zahler = st.text_input("Wer hat bezahlt?", key="split_zahler")
        gesamt_text = st.text_input("Gesamtbetrag in Euro", key="split_betrag", placeholder="z. B. 60,00")
        split_text = st.text_input("Teilnehmer / Anteile", placeholder="Anna, Ben, Clara")
        st.caption("Gleiche Teile: Anna, Ben, Clara · Ungleich: Anna:50, Ben:30, Clara:20")
        split_submit = st.form_submit_button("Rechnung aufteilen", use_container_width=True)
    if split_submit:
        try:
            cent = parse_betrag(gesamt_text)
            neue, _ = teile_rechnung(zahler, cent, split_text)
            for von, an, wert in neue:
                st.session_state.schulden.append({"von": von, "an": an, "cent": wert,
                                                   "text": "Geteilte Rechnung", "bezahlt": False})
            st.success("Rechnung wurde aufgeteilt.")
        except ValueError as exc:
            st.error(str(exc))

    st.divider()
    if st.button("Beispieldaten laden", use_container_width=True):
        beispiel = [
            ("Anna", "Ben", 2000, "Kino"), ("Ben", "Clara", 3000, "Pizza"),
            ("Clara", "Anna", 1000, "Eis"), ("Dennis", "Anna", 2500, "Konzertticket"),
            ("Clara", "Dennis", 1500, "Benzin"), ("Emma", "Ben", 1200, "Getränke"),
            ("Dennis", "Emma", 800, "Taxi")]
        st.session_state.schulden = [{"von": a, "an": b, "cent": c, "text": t, "bezahlt": False}
                                     for a, b, c, t in beispiel]
        st.session_state.erledigt = []
        st.rerun()
    if st.button("Alles zurücksetzen", type="secondary", use_container_width=True):
        st.session_state.schulden = []
        st.session_state.erledigt = []
        st.rerun()


offen = [(d["von"], d["an"], d["cent"]) for d in st.session_state.schulden if not d["bezahlt"]]
salden = netto_salden(offen, st.session_state.erledigt)
plan, exakt = optimaler_ausgleich(salden)
vorher = []
summen = {}
for a, b, c in offen:
    summen[(a, b)] = summen.get((a, b), 0) + c
vorher = [(a, b, c) for (a, b), c in summen.items()]
personen = sorted(set(salden) | {p for a, b, _ in offen for p in (a, b)}, key=str.casefold)

c1, c2, c3 = st.columns(3)
c1.metric("Personen", len(personen))
c2.metric("Offene Schulden", len(offen))
c3.metric("Noch nötige Zahlungen", len(plan))

st.subheader("Netto-Salden")
if salden:
    saldo_cols = st.columns(min(4, max(1, len(salden))))
    for i, (person, saldo) in enumerate(sorted(salden.items(), key=lambda x: x[0].casefold())):
        with saldo_cols[i % len(saldo_cols)]:
            st.metric(person, euro(abs(saldo)), "bekommt" if saldo > 0 else "muss zahlen" if saldo < 0 else "ausgeglichen")
else:
    st.info("Noch keine offenen Schulden eingetragen.")

st.subheader("Ausgleich")
if plan:
    if not exakt:
        st.warning(f"Bei mehr als {MAX_EXAKT} beteiligten Personen wird eine schnelle Näherung verwendet.")
    st.dataframe([{"Wer zahlt?": a, "An wen?": b, "Betrag": euro(c)} for a, b, c in plan],
                 use_container_width=True, hide_index=True)
    with st.expander("Zahlungen als erledigt markieren"):
        for i, (a, b, c) in enumerate(plan):
            key = f"done_{i}_{a}_{b}_{c}"
            if st.checkbox(f"{a} → {b}: {euro(c)}", key=key):
                st.session_state.erledigt.append((a, b, c))
                st.rerun()
else:
    st.success("Alles ist ausgeglichen. Es sind keine Zahlungen mehr nötig.")

left, right = st.columns(2)
with left:
    st.subheader("Ursprüngliche Schulden")
    if vorher:
        st.graphviz_chart(graphviz_dot(vorher, salden, "Offene Schulden"), use_container_width=True)
    else:
        st.caption("Noch keine Schulden vorhanden.")
with right:
    st.subheader("Optimaler Ausgleich")
    if plan:
        st.graphviz_chart(graphviz_dot(plan, salden, "Ausgleichsplan"), use_container_width=True)
    else:
        st.caption("Kein Ausgleich nötig.")

st.subheader("Alle erfassten Schulden")
if st.session_state.schulden:
    for i, d in enumerate(st.session_state.schulden):
        cols = st.columns([0.7, 2, 2, 1.2, 2, 1.2])
        cols[0].write("✓" if d["bezahlt"] else "—")
        cols[1].write(d["von"])
        cols[2].write(d["an"])
        cols[3].write(euro(d["cent"]))
        cols[4].write(d["text"])
        if cols[5].button("Erledigt" if not d["bezahlt"] else "Wieder öffnen", key=f"toggle_{i}"):
            d["bezahlt"] = not d["bezahlt"]
            st.rerun()
else:
    st.caption("Noch keine Einträge.")

if st.session_state.erledigt:
    st.caption(f"{len(st.session_state.erledigt)} Ausgleichszahlung(en) als erledigt markiert.")
    if st.button("Letzte erledigte Zahlung zurücknehmen"):
        st.session_state.erledigt.pop()
        st.rerun()

st.divider()
st.caption("Hinweis: Die Daten liegen während der Sitzung im Arbeitsspeicher. Bei einem Neustart der App können sie verloren gehen.")

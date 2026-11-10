
Schuldenausgleich – Wer schuldet wem was, und wie gleicht man alles mit
möglichst wenigen Zahlungen aus?
=====================================================================

IDEE
  Freunde schulden sich gegenseitig Geld (A -> B -> C -> ...). Die App
  berechnet, wie man alle Schulden mit der kleinsten Anzahl an Zahlungen
  ausgleicht, und zeichnet das Ganze als Graph (Personen = Knoten,
  Schulden = Pfeile).

BENUTZUNG
  Einfach in PyCharm ausführen (Rechtsklick -> Run). Es werden nur
  Module der Python-Standardbibliothek benötigt (tkinter), es muss
  also nichts installiert werden.

FUNKTIONEN
  - Schulden mit Beschreibung erfassen (z.B. "Pizza").
  - Bezahlt-Markierung:
      * Einzelne Schulden lassen sich als bezahlt markieren (dann werden
        sie nicht mehr mitgerechnet).
      * Zahlungen aus dem optimalen Ausgleich lassen sich als erledigt
        markieren (Doppelklick oder Button). Es werden nur noch die
        offenen Zahlungen angezeigt.
  - "Rechnung teilen": Einer hat bezahlt, mehrere Personen nehmen teil.
    Gleiche Teile ("Anna, Ben, Clara") oder ungleiche Anteile
    ("Anna:50, Ben:30, Clara:20") – die Schulden werden automatisch
    erzeugt (auf den Cent genau).
  - Graph: Knoten lassen sich mit der Maus verschieben, die Pfeildicke
    zeigt die Höhe des Betrags, und "Ausgleich animieren" zeigt den
    Übergang von den ursprünglichen Schulden zum optimalen Ausgleich.

ALGORITHMUS
  1. Für jede Person wird der Netto-Saldo berechnet
     (+ = bekommt Geld, - = muss Geld zahlen). Alle Beträge werden
     intern in Cent (ganze Zahlen) gerechnet, damit es keine
     Rundungsfehler gibt.
  2. Das Minimum an Zahlungen ergibt sich so: Man zerlegt die Personen
     in möglichst viele Gruppen, deren Salden sich jeweils zu 0 addieren.
     Eine Gruppe mit k Personen braucht genau k-1 Zahlungen.
     -> Mehr Gruppen = weniger Zahlungen.
     Das exakte Optimum wird per Bitmasken-Dynamic-Programming
     gefunden (bis MAX_EXAKT Personen mit Saldo != 0). Bei mehr
     Personen wird ein Greedy-Verfahren benutzt (höchstens n-1 Zahlungen).
"""

import math
import re
import tkinter as tk
from fractions import Fraction
from tkinter import ttk, messagebox

# Bis zu dieser Anzahl Personen (mit Saldo != 0) wird das exakte Optimum
# berechnet (Rechenaufwand wächst mit 2^n).
MAX_EXAKT = 16

# Darstellung
KNOTEN_R = 26
ANIM_SCHRITTE = 40  # Anzahl Bilder der Animation
ANIM_MS = 25  # Millisekunden pro Bild
FARBE_PFEIL = "#3b6ea5"
FARBE_GLAEUBIGER = "#a8e0b0"
FARBE_SCHULDNER = "#f2a9a9"
FARBE_NEUTRAL = "#dddddd"


# ----------------------------------------------------------------------
# Logik
# ----------------------------------------------------------------------
def euro(cents):
    """Formatiert Cent als deutschen Euro-Betrag, z.B. 1250 -> '12,50 €'."""
    s = f"{abs(cents) / 100:,.2f}"  # 1,234.50
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return ("-" if cents < 0 else "") + s + " €"


def parse_betrag(text):
    """Wandelt Eingaben wie '12,50', '12.5' oder '1.234,56' in Cent um."""
    text = text.strip().replace("€", "").replace(" ", "")
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        wert = float(text)
    except ValueError:
        raise ValueError("Der Betrag ist keine gültige Zahl (z.B. 12,50).") from None
    if not math.isfinite(wert):
        raise ValueError("Der Betrag ist keine gültige Zahl (z.B. 12,50).")
    return int(round(wert * 100))


def netto_salden(schulden, erledigt=()):
    """schulden: Liste von (schuldner, glaeubiger, cent).
    erledigt: bereits geleistete Zahlungen (von, an, cent).
    Rückgabe: dict person -> saldo (positiv = bekommt Geld)."""
    salden = {}
    for schuldner, glaeubiger, betrag in schulden:
        salden[schuldner] = salden.get(schuldner, 0) - betrag
        salden[glaeubiger] = salden.get(glaeubiger, 0) + betrag
    # Wer schon gezahlt hat, schuldet weniger; wer Geld bekam, bekommt weniger.
    for von, an, betrag in erledigt:
        salden[von] = salden.get(von, 0) + betrag
        salden[an] = salden.get(an, 0) - betrag
    return salden


def greedy_ausgleich(items):
    """items: Liste (name, saldo) mit Summe 0.
    Größter Schuldner zahlt an größten Gläubiger. Liefert höchstens
    len(items)-1 Zahlungen als Liste (von, an, cent)."""
    salden = {name: s for name, s in items if s != 0}
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
    """Berechnet eine Zahlungsliste mit möglichst wenigen Zahlungen.
    Rückgabe: (zahlungen, exakt) – exakt=False bei Greedy-Fallback."""
    personen = [(p, s) for p, s in sorted(salden.items()) if s != 0]
    n = len(personen)
    if n == 0:
        return [], True
    if n > MAX_EXAKT:
        return greedy_ausgleich(personen), False

    werte = [s for _, s in personen]
    voll = (1 << n) - 1

    # Summe der Salden für jede Teilmenge (Bitmaske)
    summen = [0] * (voll + 1)
    for maske in range(1, voll + 1):
        tiefstes_bit = maske & -maske
        summen[maske] = summen[maske ^ tiefstes_bit] + werte[tiefstes_bit.bit_length() - 1]

    # dp[maske] = maximale Anzahl disjunkter Gruppen mit Summe 0 in 'maske'
    dp = [0] * (voll + 1)
    wahl = [0] * (voll + 1)
    for maske in range(1, voll + 1):
        bester, bester_i = -1, 0
        for i in range(n):
            if maske >> i & 1:
                v = dp[maske ^ (1 << i)]
                if v > bester:
                    bester, bester_i = v, i
        dp[maske] = bester + (1 if summen[maske] == 0 else 0)
        wahl[maske] = bester_i

    # Rekonstruktion: Reihenfolge der Personen, Gruppen enden bei Summe 0
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
            aktuell = []

    zahlungen = []
    for gruppe in gruppen:
        zahlungen.extend(greedy_ausgleich(gruppe))
    return zahlungen, True


def aggregiere(kanten):
    """Fasst gleiche Pfeile (a -> b) zusammen und summiert die Beträge."""
    summe = {}
    for a, b, c in kanten:
        summe[(a, b)] = summe.get((a, b), 0) + c
    return [(a, b, c) for (a, b), c in summe.items()]


def teile_rechnung(zahler, gesamt_cent, teilnehmer_text, kanon=lambda name: name):
    """Teilt eine Rechnung, die 'zahler' bezahlt hat, auf mehrere Personen.

    teilnehmer_text:
      "Anna, Ben, Clara"            -> alle gleich viel
      "Anna:50, Ben:30, Clara:20"   -> Anteile (Prozent oder beliebige
                                       Gewichte, es muss nicht 100 ergeben)

    Rückgabe: (schulden, anteile)
      schulden: Liste (schuldner, zahler, cent) – ohne den Zahler selbst
      anteile:  dict name -> Anteil in Cent (Summe == gesamt_cent)
    Die Verteilung ist auf den Cent genau (Restcents gehen an die
    größten Nachkommaanteile). Bei ungültigen Eingaben: ValueError.
    """
    zahler = kanon(zahler.strip())
    if not zahler:
        raise ValueError("Bitte angeben, wer bezahlt hat.")
    if gesamt_cent <= 0:
        raise ValueError("Der Gesamtbetrag muss größer als 0 sein.")

    teile = [t.strip() for t in re.split(r"[,;\n]", teilnehmer_text) if t.strip()]
    if not teile:
        raise ValueError("Bitte mindestens einen Teilnehmer angeben.")

    namen, gewichte, mit_anteil = [], [], 0
    for teil in teile:
        if ":" in teil:
            name, anteil = teil.rsplit(":", 1)
            anteil = anteil.replace("%", "").replace(",", ".").strip()
            try:
                gewicht = Fraction(anteil)
            except (ValueError, ZeroDivisionError):
                raise ValueError(f"Ungültiger Anteil bei '{teil}'.") from None
            mit_anteil += 1
        else:
            name, gewicht = teil, Fraction(1)
        name = kanon(name.strip())
        if not name:
            raise ValueError(f"Es fehlt ein Name bei '{teil}'.")
        if gewicht <= 0:
            raise ValueError(f"Der Anteil von {name} muss größer als 0 sein.")
        namen.append(name)
        gewichte.append(gewicht)

    if 0 < mit_anteil < len(teile):
        raise ValueError("Entweder bei allen Teilnehmern einen Anteil angeben oder bei keinem.")
    kleine = [n.lower() for n in namen]
    if len(set(kleine)) != len(kleine):
        raise ValueError("Ein Teilnehmer ist doppelt aufgeführt.")

    gesamtgewicht = sum(gewichte)
    roh = [Fraction(gesamt_cent) * g / gesamtgewicht for g in gewichte]
    anteile = [r.numerator // r.denominator for r in roh]  # abgerundet
    rest = gesamt_cent - sum(anteile)
    # Restcents an die größten Nachkommastellen verteilen
    reihenfolge = sorted(range(len(namen)), key=lambda i: roh[i] - anteile[i], reverse=True)
    for i in reihenfolge[:rest]:
        anteile[i] += 1

    anteile_dict = dict(zip(namen, anteile))
    schulden = [(n, zahler, c) for n, c in anteile_dict.items()
                if c > 0 and n.lower() != zahler.lower()]
    return schulden, anteile_dict


# ----------------------------------------------------------------------
# Zeichnen
# ----------------------------------------------------------------------
def mische(farbe1, farbe2, t):
    """Mischt zwei Hex-Farben (t=0 -> farbe1, t=1 -> farbe2)."""

    def rgb(h):
        h = h.lstrip("#")
        return [int(h[i:i + 2], 16) for i in (0, 2, 4)]

    a, b = rgb(farbe1), rgb(farbe2)
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def pfeilbreite(cent, max_cent):
    """Dickere Pfeile für höhere Beträge."""
    if max_cent <= 0:
        return 2.0
    return 1.5 + 6.0 * math.sqrt(cent / max_cent)


def kurve(p0, p1):
    """Leicht gekrümmte Linie von Knoten p0 nach p1 (Hin- und Rückrichtung
    laufen so nebeneinander). Rückgabe: (punkte, label_position) oder None."""
    x0, y0 = p0
    x1, y1 = p1
    dx, dy = x1 - x0, y1 - y0
    laenge = math.hypot(dx, dy)
    if laenge < 2 * KNOTEN_R + 6:
        return None
    nx, ny = -dy / laenge, dx / laenge
    versatz = 0.24 * laenge
    kx = (x0 + x1) / 2 + nx * versatz
    ky = (y0 + y1) / 2 + ny * versatz

    punkte = []
    for k in range(41):
        t = k / 40
        px = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * kx + t ** 2 * x1
        py = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * ky + t ** 2 * y1
        if math.hypot(px - x0, py - y0) > KNOTEN_R + 1 and \
                math.hypot(px - x1, py - y1) > KNOTEN_R + 3:
            punkte.append((px, py))
    if len(punkte) < 2:
        return None
    label = (0.25 * x0 + 0.5 * kx + 0.25 * x1, 0.25 * y0 + 0.5 * ky + 0.25 * y1)
    return punkte, label


def zeichne_kante(canvas, daten, cent, farbe, breite, anteil=1.0, mit_label=True):
    """Zeichnet einen Pfeil. anteil < 1 zeichnet nur den Anfang (Animation)."""
    if anteil <= 0:
        return
    punkte, (lx, ly) = daten
    n = max(2, int(len(punkte) * anteil))
    flach = [c for pt in punkte[:n] for c in pt]
    pfeil = (round(8 + breite * 1.6), round(10 + breite * 1.9), round(3 + breite * 0.8))
    canvas.create_line(*flach, fill=farbe, width=breite, arrow=tk.LAST, arrowshape=pfeil)
    if mit_label:
        txt = canvas.create_text(lx, ly, text=euro(cent), font=("Helvetica", 9), fill="#222")
        x_a, y_a, x_b, y_b = canvas.bbox(txt)
        bg = canvas.create_rectangle(x_a - 2, y_a - 1, x_b + 2, y_b + 1,
                                     fill="white", outline="#ccc")
        canvas.tag_lower(bg, txt)


# ----------------------------------------------------------------------
# Dialog "Rechnung teilen"
# ----------------------------------------------------------------------
class TeilenDialog(tk.Toplevel):
    """Fenster, in dem eine Rechnung auf mehrere Personen aufgeteilt wird."""

    def __init__(self, master, personen, kanon, callback):
        super().__init__(master)
        self.title("Rechnung teilen")
        self.resizable(False, False)
        self.kanon = kanon
        self.callback = callback

        rahmen = ttk.Frame(self, padding=12)
        rahmen.grid(row=0, column=0)

        ttk.Label(rahmen, text="Rechnung teilen", font=("Helvetica", 12, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))

        ttk.Label(rahmen, text="Wer hat bezahlt?").grid(row=1, column=0, sticky="w")
        self.cb_zahler = ttk.Combobox(rahmen, width=34, values=personen)
        self.cb_zahler.grid(row=1, column=1, pady=2)

        ttk.Label(rahmen, text="Gesamtbetrag in €:").grid(row=2, column=0, sticky="w")
        self.e_betrag = ttk.Entry(rahmen, width=36)
        self.e_betrag.grid(row=2, column=1, pady=2)

        ttk.Label(rahmen, text="Beschreibung:").grid(row=3, column=0, sticky="w")
        self.e_text = ttk.Entry(rahmen, width=36)
        self.e_text.grid(row=3, column=1, pady=2)

        ttk.Label(rahmen, text="Teilnehmer / Anteile:").grid(row=4, column=0, sticky="w")
        self.e_teilnehmer = ttk.Entry(rahmen, width=36)
        self.e_teilnehmer.grid(row=4, column=1, pady=2)

        ttk.Label(
            rahmen, foreground="#555", wraplength=470, justify="left",
            text="Gleiche Teile:  Anna, Ben, Clara\n"
                 "Ungleiche Anteile:  Anna:50, Ben:30, Clara:20  "
                 "(Prozent oder beliebige Gewichte, bei allen Teilnehmern angeben)\n"
                 "Der Zahler darf mit in der Liste stehen – sein eigener Anteil "
                 "wird nicht als Schuld gebucht."
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(6, 4))

        self.vorschau = tk.Text(rahmen, height=9, width=58, state="disabled",
                                font=("Consolas", 10), background="#f6f6f6")
        self.vorschau.grid(row=6, column=0, columnspan=2, pady=4)

        knoepfe = ttk.Frame(rahmen)
        knoepfe.grid(row=7, column=0, columnspan=2, sticky="e", pady=(6, 0))
        ttk.Button(knoepfe, text="Abbrechen", command=self.destroy).grid(row=0, column=0, padx=4)
        ttk.Button(knoepfe, text="Übernehmen", command=self._uebernehmen).grid(row=0, column=1)

        for feld in (self.cb_zahler, self.e_betrag, self.e_text, self.e_teilnehmer):
            feld.bind("<KeyRelease>", self._aktualisiere_vorschau)
        self.cb_zahler.bind("<<ComboboxSelected>>", self._aktualisiere_vorschau)
        self.bind("<Return>", lambda e: self._uebernehmen())
        self.bind("<Escape>", lambda e: self.destroy())

        self._aktualisiere_vorschau()

        self.transient(master)
        self.wait_visibility()
        self.grab_set()
        self.cb_zahler.focus_set()

    def _berechne(self):
        gesamt = parse_betrag(self.e_betrag.get())
        return teile_rechnung(self.cb_zahler.get(), gesamt,
                              self.e_teilnehmer.get(), self.kanon)

    def _zeige(self, zeilen):
        self.vorschau.config(state="normal")
        self.vorschau.delete("1.0", tk.END)
        self.vorschau.insert(tk.END, "\n".join(zeilen))
        self.vorschau.config(state="disabled")

    def _aktualisiere_vorschau(self, _event=None):
        if not (self.cb_zahler.get().strip() and self.e_betrag.get().strip()
                and self.e_teilnehmer.get().strip()):
            self._zeige(["Fülle Zahler, Betrag und Teilnehmer aus,",
                         "dann siehst du hier die Vorschau."])
            return
        try:
            schulden, anteile = self._berechne()
        except ValueError as fehler:
            self._zeige([str(fehler)])
            return
        zeilen = ["Anteile:"]
        zeilen += [f"  {name}: {euro(c)}" for name, c in anteile.items()]
        zeilen += ["", "Neue Schulden:"]
        zeilen += [f"  {s} schuldet {g}: {euro(c)}" for s, g, c in schulden] or ["  (keine)"]
        self._zeige(zeilen)

    def _uebernehmen(self):
        try:
            schulden, _ = self._berechne()
        except ValueError as fehler:
            messagebox.showwarning("Rechnung teilen", str(fehler), parent=self)
            return
        if not schulden:
            messagebox.showinfo("Rechnung teilen",
                                "Es entstehen keine Schulden (nur der Zahler nimmt teil).",
                                parent=self)
            return
        beschreibung = self.e_text.get().strip() or "Geteilte Rechnung"
        self.callback(schulden, beschreibung)
        self.destroy()


# ----------------------------------------------------------------------
# Hauptfenster
# ----------------------------------------------------------------------
class SchuldenApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Schuldenausgleich")
        self.geometry("1300x820")
        self.minsize(1100, 680)

        # Jede Schuld: {"von", "an", "cent", "text", "bezahlt"}
        self.schulden = []
        # Bereits erledigte Zahlungen aus dem Ausgleich: (von, an, cent)
        self.erledigt = []

        # Position der Knoten (relativ 0..1), gemeinsam für beide Graphen
        self.pos = {}
        self.manuell = set()  # per Maus verschobene Knoten
        self._drag = None
        self._anim = None
        self._anim_schritt = 0

        self.ausblenden = tk.BooleanVar(value=False)
        self.daten = {"personen": [], "vorher": [], "plan": [], "salden": {},
                      "exakt": True, "max_cent": 1}

        self._baue_oberflaeche()
        self.aktualisieren()

    # ---------- Aufbau ----------
    def _baue_oberflaeche(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # ===== Linke Seite: Eingabe und Schuldenliste =====
        links = ttk.Frame(self, padding=10)
        links.grid(row=0, column=0, sticky="ns")
        links.rowconfigure(8, weight=1)

        ttk.Label(links, text="Neue Schuld", font=("Helvetica", 12, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))

        ttk.Label(links, text="Schuldner (zahlt):").grid(row=1, column=0, sticky="w")
        self.cb_schuldner = ttk.Combobox(links, width=24)
        self.cb_schuldner.grid(row=1, column=1, pady=2, sticky="ew")

        ttk.Label(links, text="Gläubiger (bekommt):").grid(row=2, column=0, sticky="w")
        self.cb_glaeubiger = ttk.Combobox(links, width=24)
        self.cb_glaeubiger.grid(row=2, column=1, pady=2, sticky="ew")

        ttk.Label(links, text="Betrag in €:").grid(row=3, column=0, sticky="w")
        self.e_betrag = ttk.Entry(links, width=26)
        self.e_betrag.grid(row=3, column=1, pady=2, sticky="ew")

        ttk.Label(links, text="Beschreibung:").grid(row=4, column=0, sticky="w")
        self.e_text = ttk.Entry(links, width=26)
        self.e_text.grid(row=4, column=1, pady=2, sticky="ew")

        for feld in (self.cb_schuldner, self.cb_glaeubiger, self.e_betrag, self.e_text):
            feld.bind("<Return>", lambda e: self.hinzufuegen())

        ttk.Button(links, text="Hinzufügen", command=self.hinzufuegen).grid(
            row=5, column=0, columnspan=2, sticky="ew", pady=(6, 2))
        ttk.Button(links, text="Rechnung teilen …", command=self.rechnung_teilen).grid(
            row=6, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        kopf = ttk.Frame(links)
        kopf.grid(row=7, column=0, columnspan=2, sticky="ew")
        ttk.Label(kopf, text="Erfasste Schulden", font=("Helvetica", 11, "bold")).pack(side="left")
        ttk.Checkbutton(kopf, text="Bezahlte ausblenden", variable=self.ausblenden,
                        command=self.aktualisieren).pack(side="right")

        tf = ttk.Frame(links)
        tf.grid(row=8, column=0, columnspan=2, sticky="nsew", pady=4)
        tf.rowconfigure(0, weight=1)
        tf.columnconfigure(0, weight=1)
        self.tv_schulden = ttk.Treeview(
            tf, columns=("ok", "von", "an", "betrag", "text"), show="headings",
            height=12, selectmode="extended")
        for spalte, titel, breite, anker in (("ok", "✓", 28, "center"),
                                             ("von", "Schuldner", 80, "w"),
                                             ("an", "Gläubiger", 80, "w"),
                                             ("betrag", "Betrag", 78, "e"),
                                             ("text", "Beschreibung", 130, "w")):
            self.tv_schulden.heading(spalte, text=titel)
            self.tv_schulden.column(spalte, width=breite, anchor=anker, stretch=(spalte == "text"))
        self.tv_schulden.tag_configure("bezahlt", foreground="#999999")
        self.tv_schulden.bind("<Double-1>", lambda e: self.bezahlt_umschalten())
        sb = ttk.Scrollbar(tf, orient="vertical", command=self.tv_schulden.yview)
        self.tv_schulden.configure(yscrollcommand=sb.set)
        self.tv_schulden.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")

        reihe1 = ttk.Frame(links)
        reihe1.grid(row=9, column=0, columnspan=2, sticky="ew", pady=2)
        reihe1.columnconfigure((0, 1), weight=1)
        ttk.Button(reihe1, text="Bezahlt ✓ umschalten", command=self.bezahlt_umschalten).grid(
            row=0, column=0, sticky="ew", padx=(0, 2))
        ttk.Button(reihe1, text="Ausgewählte löschen", command=self.loeschen).grid(
            row=0, column=1, sticky="ew", padx=(2, 0))

        reihe2 = ttk.Frame(links)
        reihe2.grid(row=10, column=0, columnspan=2, sticky="ew", pady=2)
        reihe2.columnconfigure((0, 1), weight=1)
        ttk.Button(reihe2, text="Beispiel laden", command=self.beispiel).grid(
            row=0, column=0, sticky="ew", padx=(0, 2))
        ttk.Button(reihe2, text="Alles zurücksetzen", command=self.zuruecksetzen).grid(
            row=0, column=1, sticky="ew", padx=(2, 0))

        ttk.Label(
            links, justify="left", foreground="#555",
            text="Legende:  grün = bekommt netto Geld,  rot = muss netto zahlen,\n"
                 "grau = ausgeglichen.  Pfeildicke = Höhe des Betrags.\n"
                 "Tipp: Knoten im Graphen mit der Maus verschieben."
        ).grid(row=11, column=0, columnspan=2, sticky="w", pady=(8, 0))

        # ===== Rechte Seite: Graphen, Steuerung, Ergebnis =====
        rechts = ttk.Frame(self, padding=(0, 10, 10, 10))
        rechts.grid(row=0, column=1, sticky="nsew")
        rechts.columnconfigure(0, weight=1)
        rechts.columnconfigure(1, weight=1)
        rechts.rowconfigure(0, weight=3)
        rechts.rowconfigure(2, weight=2)

        self.canvas_vorher = tk.Canvas(rechts, bg="white", highlightthickness=1,
                                       highlightbackground="#bbb")
        self.canvas_vorher.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self.canvas_nachher = tk.Canvas(rechts, bg="white", highlightthickness=1,
                                        highlightbackground="#bbb")
        self.canvas_nachher.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        for canvas in (self.canvas_vorher, self.canvas_nachher):
            canvas.bind("<Configure>", self._groesse_geaendert)
            canvas.bind("<ButtonPress-1>", self._maus_druck)
            canvas.bind("<B1-Motion>", self._maus_zieh)
            canvas.bind("<ButtonRelease-1>", self._maus_los)
            canvas.bind("<Motion>", self._maus_bewegt)

        steuer = ttk.Frame(rechts)
        steuer.grid(row=1, column=0, columnspan=2, sticky="ew", pady=6)
        steuer.columnconfigure(0, weight=1)
        self.lbl_info = ttk.Label(steuer, font=("Helvetica", 11, "bold"))
        self.lbl_info.grid(row=0, column=0, sticky="w")
        ttk.Button(steuer, text="▶ Ausgleich animieren", command=self.animation_starten).grid(
            row=0, column=1, padx=4)
        ttk.Button(steuer, text="Layout zurücksetzen", command=self.layout_zuruecksetzen).grid(
            row=0, column=2)

        unten = ttk.Frame(rechts)
        unten.grid(row=2, column=0, columnspan=2, sticky="nsew")
        unten.columnconfigure(0, weight=1)
        unten.columnconfigure(1, weight=1)
        unten.rowconfigure(0, weight=1)

        plan_rahmen = ttk.LabelFrame(unten, text="Offene Zahlungen (Doppelklick = bezahlt)",
                                     padding=6)
        plan_rahmen.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        plan_rahmen.rowconfigure(0, weight=1)
        plan_rahmen.columnconfigure(0, weight=1)
        self.tv_plan = ttk.Treeview(plan_rahmen, columns=("von", "an", "betrag"),
                                    show="headings", height=6, selectmode="extended")
        for spalte, titel, breite, anker in (("von", "Zahlt", 110, "w"),
                                             ("an", "An", 110, "w"),
                                             ("betrag", "Betrag", 90, "e")):
            self.tv_plan.heading(spalte, text=titel)
            self.tv_plan.column(spalte, width=breite, anchor=anker)
        self.tv_plan.bind("<Double-1>", lambda e: self.zahlung_erledigt())
        self.tv_plan.grid(row=0, column=0, sticky="nsew")
        plan_knoepfe = ttk.Frame(plan_rahmen)
        plan_knoepfe.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        plan_knoepfe.columnconfigure((0, 1), weight=1)
        ttk.Button(plan_knoepfe, text="Als bezahlt markieren",
                   command=self.zahlung_erledigt).grid(row=0, column=0, sticky="ew", padx=(0, 2))
        ttk.Button(plan_knoepfe, text="Letzte Zahlung zurücknehmen",
                   command=self.zahlung_zurueck).grid(row=0, column=1, sticky="ew", padx=(2, 0))

        self.txt = tk.Text(unten, height=10, wrap="word", state="disabled",
                           font=("Consolas", 10))
        self.txt.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

    # ---------- Berechnung ----------
    def _berechne(self):
        offen = [(d["von"], d["an"], d["cent"]) for d in self.schulden if not d["bezahlt"]]
        salden = netto_salden(offen, self.erledigt)
        plan, exakt = optimaler_ausgleich(salden)
        vorher = aggregiere(offen)
        namen = {p for d in self.schulden for p in (d["von"], d["an"])}
        namen |= {p for von, an, _ in self.erledigt for p in (von, an)}
        personen = sorted(namen, key=str.lower)
        max_cent = max([c for _, _, c in vorher + plan] or [1])
        return {"personen": personen, "vorher": vorher, "plan": plan, "salden": salden,
                "exakt": exakt, "max_cent": max_cent}

    def _layout_pflegen(self):
        """Neue Personen auf einen Kreis setzen; verschobene Knoten bleiben."""
        personen = self.daten["personen"]
        for p in list(self.pos):
            if p not in personen:
                del self.pos[p]
                self.manuell.discard(p)
        n = len(personen)
        for i, p in enumerate(personen):
            if p in self.manuell and p in self.pos:
                continue
            if n == 1:
                self.pos[p] = (0.5, 0.55)
            else:
                winkel = -math.pi / 2 + 2 * math.pi * i / n
                self.pos[p] = (0.5 + 0.34 * math.cos(winkel), 0.55 + 0.32 * math.sin(winkel))

    # ---------- Aktionen ----------
    def _bekannter_name(self, name):
        """Verwendet die Schreibweise eines schon vorhandenen Namens."""
        for vorhanden in self.daten["personen"]:
            if vorhanden.lower() == name.lower():
                return vorhanden
        return name

    def hinzufuegen(self):
        schuldner = self.cb_schuldner.get().strip()
        glaeubiger = self.cb_glaeubiger.get().strip()
        if not schuldner or not glaeubiger:
            messagebox.showwarning("Eingabe", "Bitte Schuldner und Gläubiger angeben.")
            return
        if schuldner.lower() == glaeubiger.lower():
            messagebox.showwarning("Eingabe", "Schuldner und Gläubiger müssen verschieden sein.")
            return
        try:
            cent = parse_betrag(self.e_betrag.get())
        except ValueError as fehler:
            messagebox.showwarning("Eingabe", str(fehler))
            return
        if cent <= 0:
            messagebox.showwarning("Eingabe", "Der Betrag muss größer als 0 sein.")
            return

        self.schulden.append({
            "von": self._bekannter_name(schuldner),
            "an": self._bekannter_name(glaeubiger),
            "cent": cent,
            "text": self.e_text.get().strip(),
            "bezahlt": False,
        })
        self.e_betrag.delete(0, tk.END)
        self.e_text.delete(0, tk.END)
        self.cb_schuldner.focus_set()
        self.aktualisieren()

    def rechnung_teilen(self):
        TeilenDialog(self, self.daten["personen"], self._bekannter_name,
                     self.rechnung_uebernehmen)

    def rechnung_uebernehmen(self, neue_schulden, beschreibung):
        for von, an, cent in neue_schulden:
            self.schulden.append({"von": self._bekannter_name(von),
                                  "an": self._bekannter_name(an),
                                  "cent": cent, "text": beschreibung, "bezahlt": False})
        self.aktualisieren()

    def bezahlt_umschalten(self):
        auswahl = self.tv_schulden.selection()
        if not auswahl:
            messagebox.showinfo("Bezahlt", "Bitte zuerst eine oder mehrere Schulden in der "
                                           "Liste auswählen.")
            return
        for iid in auswahl:
            d = self.schulden[int(iid)]
            d["bezahlt"] = not d["bezahlt"]
        self.aktualisieren()

    def loeschen(self):
        for iid in sorted((int(i) for i in self.tv_schulden.selection()), reverse=True):
            del self.schulden[iid]
        self.aktualisieren()

    def zahlung_erledigt(self):
        auswahl = self.tv_plan.selection()
        if not auswahl:
            messagebox.showinfo("Zahlung", "Bitte zuerst eine oder mehrere Zahlungen in der "
                                           "Liste 'Offene Zahlungen' auswählen.")
            return
        plan = self.daten["plan"]
        self.erledigt.extend(plan[int(iid)] for iid in auswahl)
        self.aktualisieren()

    def zahlung_zurueck(self):
        if self.erledigt:
            self.erledigt.pop()
            self.aktualisieren()

    def zuruecksetzen(self):
        if self.schulden and not messagebox.askyesno(
                "Zurücksetzen", "Wirklich alle Schulden und Zahlungen löschen?"):
            return
        self.schulden.clear()
        self.erledigt.clear()
        self.pos.clear()
        self.manuell.clear()
        self.aktualisieren()

    def beispiel(self):
        def s(von, an, cent, text):
            return {"von": von, "an": an, "cent": cent, "text": text, "bezahlt": False}

        self.schulden = [
            s("Anna", "Ben", 2000, "Kino"),
            s("Ben", "Clara", 3000, "Pizza"),
            s("Clara", "Anna", 1000, "Eis"),
            s("Dennis", "Anna", 2500, "Konzertticket"),
            s("Clara", "Dennis", 1500, "Benzin"),
            s("Emma", "Ben", 1200, "Getränke"),
            s("Dennis", "Emma", 800, "Taxi"),
        ]
        self.erledigt = []
        self.pos.clear()
        self.manuell.clear()
        self.aktualisieren()

    # ---------- Anzeige ----------
    def aktualisieren(self):
        self._anim_stop()
        self.daten = self._berechne()
        self._layout_pflegen()
        self._liste_fuellen()
        self._plan_fuellen()
        personen = self.daten["personen"]
        self.cb_schuldner["values"] = personen
        self.cb_glaeubiger["values"] = personen
        self.zeichne_graphen()
        self._info_und_text()

    def _liste_fuellen(self):
        self.tv_schulden.delete(*self.tv_schulden.get_children())
        for i, d in enumerate(self.schulden):
            if d["bezahlt"] and self.ausblenden.get():
                continue
            self.tv_schulden.insert(
                "", tk.END, iid=str(i),
                values=("✓" if d["bezahlt"] else "", d["von"], d["an"],
                        euro(d["cent"]), d["text"]),
                tags=("bezahlt",) if d["bezahlt"] else ())

    def _plan_fuellen(self):
        self.tv_plan.delete(*self.tv_plan.get_children())
        for i, (von, an, cent) in enumerate(self.daten["plan"]):
            self.tv_plan.insert("", tk.END, iid=str(i), values=(von, an, euro(cent)))

    def _info_und_text(self):
        d = self.daten
        if not self.schulden:
            info = "Füge links Schulden hinzu, teile eine Rechnung oder lade das Beispiel."
        elif not d["plan"]:
            info = "Alles ist ausgeglichen – keine offenen Zahlungen."
        else:
            info = (f"{len(d['vorher'])} offene Schuldbeziehung(en)  ->  "
                    f"{len(d['plan'])} Zahlung(en) nötig")
            if not d["exakt"]:
                info += "  (Näherung, viele Personen)"
        if self.erledigt:
            info += f"   |   {len(self.erledigt)} Zahlung(en) erledigt"
        self.lbl_info.config(text=info)

        zeilen = []
        if d["personen"]:
            zeilen.append("NETTO-SALDEN" + (" (nach erledigten Zahlungen)" if self.erledigt else ""))
            for p in d["personen"]:
                s = d["salden"].get(p, 0)
                if s > 0:
                    text = f"bekommt noch {euro(s)}"
                elif s < 0:
                    text = f"muss noch {euro(-s)} zahlen"
                else:
                    text = "ist ausgeglichen"
                zeilen.append(f"  {p}: {text}")
        if self.erledigt:
            zeilen += ["", "ERLEDIGTE ZAHLUNGEN"]
            zeilen += [f"  {von} hat {euro(c)} an {an} gezahlt" for von, an, c in self.erledigt]
        anzahl_bezahlt = sum(1 for s in self.schulden if s["bezahlt"])
        if anzahl_bezahlt:
            zeilen += ["", f"{anzahl_bezahlt} Schuld(en) als bezahlt markiert (nicht mitgerechnet)"]

        self.txt.config(state="normal")
        self.txt.delete("1.0", tk.END)
        self.txt.insert(tk.END, "\n".join(zeilen))
        self.txt.config(state="disabled")

    # ---------- Graph ----------
    def _groesse(self, canvas):
        return max(canvas.winfo_width(), 200), max(canvas.winfo_height(), 200)

    def _punkt(self, canvas, person):
        w, h = self._groesse(canvas)
        x, y = self.pos[person]
        return x * w, y * h

    def _kanten_spec(self, kanten):
        m = self.daten["max_cent"]
        return [(a, b, c, FARBE_PFEIL, pfeilbreite(c, m), 1.0, True) for a, b, c in kanten]

    def zeichne_graphen(self):
        self._zeichne(self.canvas_vorher, "Ursprüngliche (offene) Schulden",
                      self._kanten_spec(self.daten["vorher"]))
        self._zeichne(self.canvas_nachher, "Optimaler Ausgleich",
                      self._kanten_spec(self.daten["plan"]))

    def _zeichne(self, canvas, titel, kanten):
        """kanten: Liste (von, an, cent, farbe, breite, anteil, mit_label)."""
        canvas.delete("all")
        w, h = self._groesse(canvas)
        canvas.create_text(w / 2, 16, text=titel, font=("Helvetica", 11, "bold"))
        personen = self.daten["personen"]
        if not personen:
            canvas.create_text(w / 2, h / 2, text="(noch keine Schulden)", fill="#888")
            return

        for a, b, cent, farbe, breite, anteil, mit_label in kanten:
            daten = kurve(self._punkt(canvas, a), self._punkt(canvas, b))
            if daten:
                zeichne_kante(canvas, daten, cent, farbe, breite, anteil, mit_label)

        for p in personen:
            x, y = self._punkt(canvas, p)
            saldo = self.daten["salden"].get(p, 0)
            farbe = FARBE_GLAEUBIGER if saldo > 0 else FARBE_SCHULDNER if saldo < 0 else FARBE_NEUTRAL
            canvas.create_oval(x - KNOTEN_R, y - KNOTEN_R, x + KNOTEN_R, y + KNOTEN_R,
                               fill=farbe, outline="#555", width=2)
            name = p if len(p) <= 9 else p[:8] + "…"
            canvas.create_text(x, y, text=name, font=("Helvetica", 9, "bold"))

    def _groesse_geaendert(self, _event):
        if self._anim is None:
            self.zeichne_graphen()

    def layout_zuruecksetzen(self):
        self._anim_stop()
        self.pos.clear()
        self.manuell.clear()
        self._layout_pflegen()
        self.zeichne_graphen()

    # ---------- Knoten per Maus verschieben ----------
    def _knoten_bei(self, canvas, x, y):
        for p in reversed(self.daten["personen"]):
            px, py = self._punkt(canvas, p)
            if math.hypot(px - x, py - y) <= KNOTEN_R + 2:
                return p, px, py
        return None

    def _maus_druck(self, event):
        lief = self._anim_stop()
        treffer = self._knoten_bei(event.widget, event.x, event.y)
        if treffer:
            p, px, py = treffer
            self._drag = (p, px - event.x, py - event.y)
        if lief:
            self.zeichne_graphen()

    def _maus_zieh(self, event):
        if not self._drag:
            return
        p, ox, oy = self._drag
        w, h = self._groesse(event.widget)
        x = min(max((event.x + ox) / w, 0.07), 0.93)
        y = min(max((event.y + oy) / h, 0.12), 0.93)
        self.pos[p] = (x, y)
        self.manuell.add(p)
        self.zeichne_graphen()

    def _maus_los(self, _event):
        self._drag = None

    def _maus_bewegt(self, event):
        treffer = self._knoten_bei(event.widget, event.x, event.y)
        event.widget.config(cursor="hand2" if treffer else "")

    # ---------- Animation ----------
    def animation_starten(self):
        if not self.daten["vorher"] and not self.daten["plan"]:
            messagebox.showinfo("Animation", "Es gibt noch nichts zu animieren – "
                                             "füge zuerst Schulden hinzu.")
            return
        self._anim_stop()
        self.zeichne_graphen()
        self._anim_schritt = 0
        self._anim_bild()

    def _anim_stop(self):
        """Stoppt eine laufende Animation. Rückgabe: True, wenn eine lief."""
        if self._anim is not None:
            self.after_cancel(self._anim)
            self._anim = None
            return True
        return False

    def _anim_bild(self):
        t = self._anim_schritt / ANIM_SCHRITTE
        e = t * t * (3 - 2 * t)  # weiches Ein- und Ausblenden
        m = self.daten["max_cent"]
        kanten = []
        # Alte Pfeile verblassen und werden dünner ...
        for a, b, c in self.daten["vorher"]:
            kanten.append((a, b, c, mische(FARBE_PFEIL, "#ffffff", e),
                           max(1.0, pfeilbreite(c, m) * (1 - e)), 1.0, e < 0.5))
        # ... während die neuen Pfeile von Schuldner zu Gläubiger "wachsen".
        for a, b, c in self.daten["plan"]:
            kanten.append((a, b, c, FARBE_PFEIL, pfeilbreite(c, m), e, e >= 1.0))
        self._zeichne(self.canvas_nachher, "Optimaler Ausgleich", kanten)

        if self._anim_schritt < ANIM_SCHRITTE:
            self._anim_schritt += 1
            self._anim = self.after(ANIM_MS, self._anim_bild)
        else:
            self._anim = None
            self.zeichne_graphen()


def main():
    app = SchuldenApp()
    app.mainloop()


if __name__ == "__main__":
    main()

# Schuldenrechner für Freunde

Eine Streamlit-Web-App, mit der Freunde gemeinsame Ausgaben erfassen, Rechnungen aufteilen und einen möglichst zahlungsarmen Schuldenausgleich berechnen können.

## Lokal starten

Python 3.10 oder neuer wird empfohlen.

```bash
python -m pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Deployment auf Streamlit Community Cloud

1. Dieses GitHub-Repository öffnen und sicherstellen, dass `streamlit_app.py` und `requirements.txt` im Hauptverzeichnis liegen.
2. Bei [Streamlit Community Cloud](https://share.streamlit.io/) mit GitHub anmelden.
3. **Create app** auswählen.
4. Repository `FelixZimmermann06052007/SchuldrechnerFreunde-`, Branch `main` und Datei `streamlit_app.py` auswählen.
5. **Deploy** anklicken. Nach dem Build stellt Streamlit eine teilbare `streamlit.app`-Adresse bereit.

## Funktionen

- Schulden zwischen Personen erfassen und als bezahlt markieren
- Rechnungen gleichmäßig oder nach Anteilen aufteilen
- Netto-Salden berechnen
- Ausgleich mit möglichst wenigen Zahlungen berechnen (bis zu 16 beteiligte Personen exakt; darüber Näherungsverfahren)
- Ursprüngliche Schulden und Ausgleich als Graph darstellen

## Hinweis zu Daten

Die App speichert Einträge aktuell im Streamlit-Sitzungszustand. Das ist für eine gemeinsame, dauerhafte Nutzung durch mehrere Freunde noch keine gemeinsame Datenbank: Daten können bei Neustarts oder neuen Sitzungen verloren gehen und Sitzungen teilen ihre Daten nicht automatisch. Für dauerhaft gemeinsame Daten sollte später eine Datenbank angebunden werden.

Die bisherige `Schuldrechner.py` ist eine Tkinter-Desktop-App. Streamlit kann Tkinter-Fenster nicht als Weboberfläche ausführen; deshalb ist `streamlit_app.py` eine Web-Umsetzung der Kernfunktionen. Die ursprüngliche Datei bleibt unverändert erhalten.

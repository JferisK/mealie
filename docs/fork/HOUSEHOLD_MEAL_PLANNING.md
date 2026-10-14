# Haushalts-Essensplanung: Architektur und Entwicklungsplan

Stand: 14.10.2026. Status: abgestimmter Produktumfang, Implementierung ausstehend.
Diese öffentliche Dokumentation enthält ausschließlich allgemeine Anforderungen, keine persönlichen Gesundheitswerte.

## Verbindliche Release-Basis

- Neuester stabiler Upstream-Release laut GitHub releases/latest am Prüftag: [v3.28.0](https://github.com/mealie-recipes/mealie/releases/tag/v3.28.0), veröffentlicht 24.09.2026.
- Release-Commit: `0552eaa4a80031b8572849cca0ed95d07f1be001`.
- Neue Basis im Fork: `upstream/v3.28.0`.
- Dieser Planungsbranch basiert direkt auf diesem Release, nicht auf dem alten Fork-Stand.
- Vor Implementierungsbeginn neuesten stabilen Release erneut prüfen. Kein Entwicklungsstart auf 3.3.2.
- Der bestehende Default-Branch `mealie-next` bleibt vorerst historisch auf 3.3.2. Eine Änderung des Default-Branches ist mit dem verfügbaren Connector nicht vorgenommen worden.
- Aktuelle geprüfte Frontend-Toolchain: Nuxt 4, Vue 3, Vuetify 4, pnpm; Release Notes nennen Python 3.14.
- Kleine additive Änderungen, bestehende API/Komponenten wiederverwenden; regelmäßige Upstream-Updates über überprüfbare PRs.

## Technische Bestandsaufnahme

Geprüft: frontend/package.json, mealie/schema/meal_plan/new_meal.py und mealie/schema/recipe/recipe_nutrition.py auf v3.28.0.
Der Plan unterstützt bereits breakfast, lunch, dinner, side, snack, drink und dessert. Diese Kategorien nicht neu erfinden.
CreatePlanEntry enthält Datum, Typ, Titel, Text und recipe_id, aber keine persönlichen Portionsmengen.
Nutrition enthält optionale Stringwerte für Kalorien und Makros, jedoch keine explizite Bezugsmenge oder Quellenqualität.
Eine vollständige Analyse sämtlicher Upstream-Funktionen und ein Build stehen noch aus.

Historische Referenz: [PR #6399](https://github.com/mealie-recipes/mealie/pull/6399), Branch feature/planner-calorie-tracking.
Der PR wurde ohne Merge geschlossen, weil die Nährwertgrundlagen zuerst verbessert werden sollten.
Als UX-Referenz verwenden, nicht unverändert übernehmen:
- localStorage-Ziele durch serverseitige Nutzerziele ersetzen.
- Pauschales Teilen durch Rezeptportionen durch explizite Bezugsmenge ersetzen.
- Fehlende Nährwerte nicht als null Kalorien darstellen.
- Feste Portion=1 durch persönliche Portionen ersetzen.
- Historische Testbehauptungen sind keine aktuelle Testausführung.

## Produktumfang

Zwei getrennte Nutzer in einem gemeinsamen Haushalt. Ganze Tage inklusive Frühstück und Snacks; mittags kleinere, leichter bekömmliche Mahlzeiten, abends mehr Spielraum.
Überwiegend gemeinsame Gerichte mit persönlichen Varianten und Mengen. Ernährungsanforderungen pro Profil: glutenfrei/laktosefrei, einschließlich separat konfigurierbarer Spurenregel.
Mehrere Gerichte und kombinierbare Komponenten am Sonntag vorkochen; Kochzeit flexibel, Abwechslung über die Woche.
KI pflegt Rezepte nach Auftrag selbstständig; Wochenplanung wird vor Speicherung bestätigt.
Gefrierbestand über Chat und schnelle Buttons, QR-Etiketten später.
Keine Budget- oder Preisverwaltung. VPS/Portainer-Aufräumen erst in der Hostingphase.

## Architekturentscheidungen

Mealie bleibt führend für Rezepte, Planung und Einkauf. Erweiterungen für Portionen und Chargen werden additiv in Backend/API eingeführt.
Ein separater MCP-Dienst spricht die authentifizierte Mealie-API; er erhält keine Portainer-/Docker-Verwaltungsrechte.
ChatGPT Mobile bevorzugt, aber Funktionsnachweis durch echten Lese-/Schreibtest erforderlich. Claude Mobile, Codex und Claude Code als Alternativen.
Bestehende MCP-Projekte vor Eigenbau prüfen:
- https://github.com/timo-reymann/mealie-mcp-server
- https://github.com/cometto2007/mealie-mcp-server
Prüfkriterien: Lizenz, Wartung, aktuelle API-Kompatibilität, Authentifizierung, Streamable HTTP, Toolumfang, Fehlerbehandlung und Idempotenz. Noch kein Projekt endgültig ausgewählt.
Portainer-MCP ist optional und bleibt eine separate Verwaltungsanbindung.

Die iPhone-App dient ausschließlich als HealthKit-Brücke, nicht als zweite Rezeptoberfläche.
Health-Daten und Ziele sind nutzerbezogen geschützt; Haushaltsmitgliedschaft allein erlaubt keinen Zugriff auf die Gesundheitsdaten anderer.
Langfristige Ziele können später aus einem privaten Begleitdokument übernommen werden. Keine automatische bidirektionale Drive-Synchronisation voraussetzen.

## Vorgeschlagenes Datenmodell (noch kein implementiertes Schema)

| Entität | Inhalt / Invariante |
|---|---|
| NutritionBasis | Gesamtgericht, Portion, 100 g oder unbekannt; Quelle, Einheit, Berechnungsstand |
| IngredientNutrition | strukturierte Menge, Roh-/Garbezug, Produkt-/Lebensmitteldatenquelle, Stand |
| NutritionProfile | persönliche Präferenzen, Ausschlüsse und bestätigte Zielversion |
| GoalRevision | Eingaben, Formelversion, Annahmen, Vorschlag, Bestätigung, Gültigkeit |
| MealAllocation | Planeintrag, Person, Variante, Portionen/Gramm und Plan-/Verzehrstatus |
| CookBatch | tatsächlich gekochte Rezeptversion, Ausbeute und Komponenten |
| FreezeBatch | Charge, Restmenge, Einheit, Einfrierdatum, Fach, Nährwertsnapshot |
| StockMovement | Einlagern, Entnehmen, Korrigieren, Verwerfen; Idempotenzschlüssel |
| Reservation | geplante Menge einer Charge, unabhängig von tatsächlicher Entnahme |
| HealthObservation | Person, Messart, Quelle, Messzeit, externe ID, Synchronisationsstand |

Rezeptänderungen dürfen eingefrorene Chargen nicht rückwirkend umrechnen.
Unbekannt bleibt unbekannt. Aggregationen zeigen Teilabdeckung. Ein geplanter Tag ist kein Nachweis tatsächlichen Verzehrs.
Verfügbare Gefriermenge = physischer Bestand minus Reservierungen. Bestätigung eines Plans reserviert; tatsächliche Entnahme bucht ab.
Kochmengen, Einkaufsbedarf und konsumierte Mengen getrennt halten. Fertige Gefriergerichte dürfen nicht nochmals als neu zu kaufende Zutaten zählen.

## Nährwerte und wissenschaftliche Zielprüfung

Berechnung aus strukturierten Zutaten und nachvollziehbaren Datenquellen. Datenanbieter und Lizenz vor Implementierung auswählen.
Bezugsmenge und Roh-/Gargewicht dürfen nicht stillschweigend geraten werden. KI-Schätzungen klar kennzeichnen und nicht als belegte Werte ausgeben.
Gluten-/Laktose- und Gefriereignung jeweils ja/nein/ungeklärt mit Grundlage; Einfrier-/Aufwärmhinweise separat.
Monatliche Überprüfung erzeugt einen begründeten Vorschlag, ändert aber keine aktiven Ziele ohne Bestätigung.
Gängige Grundumsatzformeln anhand wissenschaftlicher Primärquellen vergleichen; Eignung und Unsicherheit, Aktivitätsannahmen und Proteinberechnung dokumentieren.
Noch keine konkrete Formel oder persönlichen Zielwerte freigegeben. Formelprüfung und tatsächlicher Verlauf ergänzen sich.
Kein doppeltes Addieren von Trainingsenergie und Aktivitätsfaktor. Fehlende/veraltete Messungen lösen Datenbedarf statt erfundener Anpassungen aus.

## HealthKit

Beide Nutzer koppeln ihr eigenes iPhone und geben Daten individuell frei.
Zunächst lesend: Gewicht, Größe, Alter sowie Schritte/Trainings nach begründetem Zweck. Körperfett und Ruhe-/Aktivitätsenergie optional als ergänzende Vergleichsdaten.
Keine pauschale Erhebung sämtlicher Health-Datentypen. Freigaben, Quellen, fehlende Daten und Aktualität sichtbar machen.
Sichere Geräte-Kopplung; Deduplizierung, korrigierte/gelöschte Messungen, Widerruf und Löschung berücksichtigen.
Manueller Sync plus bestmögliche Hintergrundübertragung; keine Echtzeitgarantie.
Private Installation oder TestFlight genügt als Entwicklungsweg. Öffentlicher App Store ist kein Produktziel. TestFlight-Builds nach spätestens 90 Tagen erneuern.
HealthKit auf echten Geräten testen; Simulator allein ist kein Funktionsnachweis.

## Gestaltung

Helles modernes SaaS-Design innerhalb des vorhandenen Vue/Vuetify-Stacks.
Große Rezeptbilder, ruhige Typografie, verständliche Tags, klare Tageskarten und kompakte Wochenübersicht.
Personenwechsel, persönliche Kalorien/Proteinwerte und Datenvollständigkeit direkt erreichbar.
Eigene Ansichten: Heute, Woche, Sonntagskochen, Gefrierbestand, Einkauf.
Mobile Zielbreite zunächst 390 px; große Touchflächen, Tastaturbedienung und lesbare Kontraste.
Keine moralischen Gut-/Schlecht-Bewertungen von Mahlzeiten.

## Backlog mit Abhängigkeiten und Abnahme

### P0 — Aktuelle Basis und Integrationsspike
- [ ] Neueste stabile Version vor Start erneut feststellen; Unterschiede zu v3.28.0 prüfen.
- [ ] Upstream-Funktionsvergleich für Nährwerte, Portionsplanung, Einkaufslisten und Vorräte.
- [ ] MCP-Kandidaten prüfen und authentifizierten Lese-/Schreibtest durchführen.
- [ ] Client-Matrix dokumentieren, insbesondere ChatGPT Mobile mit realem Account.
Abnahme: dokumentierte kompatible Kombination aus Release, MCP, Auth und mindestens einem gewünschten Client. Keine behauptete mobile Unterstützung ohne Test.

### P1 — Nährwertbasis, Ziele und persönliche Portionen
- [ ] Additive Datenmodelle, API-Verträge und Migration entwerfen.
- [ ] Quellen-/Bezugsmodell und deterministische Berechnungslogik.
- [ ] Persönliche Varianten und Portionsmengen, serverseitige Zielversionen.
- [ ] Eignungstags mit ungeklärtem Status.
Abnahme: 2000 Gesamtkalorien/4 Portionen = 500; bereits portionsbezogene 500 bleiben 500. Null Portionen = 0, unbekannte Werte bleiben unbekannt. Dezimalkomma, Teilportionen und Haushaltsisolation testen.

### P2 — Vollständiger MCP-Ablauf
Abhängig von P1.
- [ ] Rezept anlegen/importieren und strukturieren.
- [ ] Zwei persönliche Portionen und Varianten planen.
- [ ] Wochenplan-Vorschau, danach ausdrückliche Bestätigung.
- [ ] Einkaufsliste aus Gesamtbedarf erzeugen.
- [ ] Wiederholbare Toolaufrufe, Konflikterkennung und Änderungsprotokoll.
Abnahme: Rezept → zwei Profile → Wochenplan → Bestätigung → Einkaufsliste funktioniert; Wiederholung erzeugt keine Duplikate, Vorschau verändert keinen Bestand.

### P3 — Gefrierverwaltung
Abhängig von P1, MCP-Anbindung auf P2 aufbauen.
- [ ] Chargen und Komponenten, Fach und Einfrierdatum.
- [ ] Reservierungen, Entnahmen, Korrekturen und Stornierungen.
- [ ] Chat und schnelle Buttons; QR später.
- [ ] Ältere geeignete Bestände im Plan berücksichtigen.
Abnahme: 6 einlagern, 2 reservieren = 6 vorhanden/4 frei; 2 entnehmen = 4 vorhanden. Gleichzeitige Entnahmen dürfen keinen negativen Bestand erzeugen. Rezeptänderungen lassen Chargensnapshots unverändert.

### P4 — Wochenansicht und Sonntagskochen
Abhängig von P1–P3.
- [ ] Mobile Tageskarten, Wochen-/Personenwechsel und Nährwertsummen.
- [ ] Kochmengen aus Gerichten und Komponenten aggregieren.
- [ ] Kühlschrank-/Gefrierzuordnung und Bestandsbezug.
- [ ] Einkaufsbedarf ohne doppelt verrechnete Zutaten oder Portionen.
Abnahme: vollständige Beispielwoche für zwei synthetische Profile, Varianten und Snacks; Kochliste, Einkauf und Reservierungen rechnerisch konsistent. Unvollständige Tage sichtbar.

### P5 — HealthKit und monatlicher Review
API-Verträge nach P1; unabhängig von finalem UI entwickelbar.
- [ ] Kleine iOS-Brücke mit individueller Freigabe und sicherem Sync.
- [ ] Wissenschaftliche Methodenauswahl als dokumentierter Review.
- [ ] Monatlicher Vorschlag mit alten/neuen Werten, Begründung und Bestätigung.
- [ ] Reale Gerätetests und Verteilungsweg.
Abnahme: wiederholter Sync ohne Duplikate; keine Einsicht in fremde Gesundheitsdaten; unbestätigter Vorschlag verändert aktive Ziele nicht. Widerruf/fehlende Daten getestet.

### P6 — Hosting und Betrieb (später)
- [ ] VPS-Inventur, konkreter Aufräumplan und Datensicherung.
- [ ] Versioniertes Image, Reverse Proxy/TLS, Datenbank, MCP-Authentifizierung.
- [ ] Migration und Restore-Probe, Rollbackplan und Updateverfahren.
- [ ] Portainer-MCP bei Bedarf separat.
Abnahme: reproduzierbarer Build und Wiederherstellung geprüft. Dieser Plan führt weder Deployment noch VPS-Löschungen aus.

## Prüfstatus dieses Planungs-PRs

Repository-Metadaten, aktuelle Release-Referenz und zentrale Schemas gelesen.
Keine Anwendung geändert, kein Build oder Laufzeittest ausgeführt.
Issues sind im Fork deaktiviert; dieses versionierte Backlog ist daher die ausführbare Aufgabenliste.

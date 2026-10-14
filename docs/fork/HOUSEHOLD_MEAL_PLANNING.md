# Haushaltsplanung auf Mealie v3.28.0

Stand: 14.10.2026. Implementierung auf dem Default-Branch `mealie-next`.
Basis ist der am Prüftag neueste stabile Release **v3.28.0**, Commit `0552eaa4a80031b8572849cca0ed95d07f1be001`.
Der frühere Stand 3.3.2 wurde ersetzt. Hosting, VPS-Aufräumen und echte Mobile-Verbindungen folgen separat.
Diese öffentliche Dokumentation enthält keine persönlichen Messwerte, Namen oder Zugangsdaten.

## Benutzen

Nach Migration und Start: Navigation **Your week** → `/household/planning`.
Zwei eigene Nutzerkonten in einem gemeinsamen Haushalt anlegen. Jeder pflegt sein eigenes Planungsprofil und verbindet seinen eigenen MCP-/Health-Zugang.
Die Rezepte kann der Assistent über MCP erstellen und bearbeiten; manuelle Rezeptpflege ist kein Pflichtschritt.

1. Assistent liest Haushaltspräferenzen und Bestand, erstellt klare Rezepte mit Zutatenmengen und Zubereitung.
2. Für die Planung ergänzt er strukturierte Zutaten mit Roh-/Garbezug, Nährwerten pro 100 g und echten Quellen.
3. Woche vorschlagen: Frühstück, Mittag, Abend, Snacks; eigene Portionen und bei Bedarf unterschiedliche Gerichte.
4. Vorschau prüfen und bestätigen. Tageswerte erscheinen je Person; frische Kochmengen und Einkauf werden zusammengefasst.
5. Sonntags nach tatsächlichem Kochen Portionen mit Datum/Fach einfrieren. Entnahme erst nach Bestätigung verbuchen.
6. Monatlich Messwerte synchronisieren, Zielvorschlag prüfen und ausdrücklich bestätigen.

## Implementiert

| Bereich | Verhalten |
|---|---|
| Wochenoberfläche | Responsive Tageskarten mit Rezeptbildern, Rezeptlinks, persönlichen Portionen und Kalorien; sieben Tage, Personenauswahl und Wochenwechsel |
| Nährwerte | Zutatenbasierte Rechnung, explizite Rezeptportionen, Roh-/Garbezug; fehlende/unsourced Werte bleiben unbekannt, nicht null Kalorien |
| Native Rezepte | Berechnete Nährwerte pro Portion und Rezept-Portionszahl werden atomar in das native Rezept übernommen; nicht belegte weitere Nährwerte bleiben leer |
| Verträglichkeit | glutenfrei/laktosefrei/freezer-friendly jeweils yes/no/unknown; positive GF/LF-Angaben brauchen Belegtext; Profile werden beim Planen geprüft |
| Persönliche Varianten | Mehrere Rezeptzuweisungen je Mahlzeit, unterschiedliche Mengen je Person; Vorlieben/Abneigungen für den Assistenten verfügbar |
| Bestätigte Woche | Unveränderlicher Plan mit Rezept-Nährwertsnapshots; ersetzen durch Stornieren und neue Vorschau; native Mealie-Kalendereinträge werden mitgeführt |
| Kochen und Einkauf | Gemeinsame Mengen aus persönlichen Portionen; vorhandene Gefrierportionen ausgeschlossen; Einkaufsliste mit serverseitigen Häkchen |
| Gefrierschrank | Charge, Einfrierdatum, Fach, Restmenge, reservierte/verfügbare Portionen, Rezeptsnapshot und Aufwärmhinweise |
| Bestandsführung | Reale Entnahme, Verwerfen, absolute Korrektur, idempotente IDs; Reservierung reduziert nicht den physischen Bestand |
| Ziele | Eigener geschützter Bereich, bestehende Ziele manuell oder Formelvorschläge, bestätigte Versionen, monatlich fällige Überprüfung |
| MCP | stdio und authentifiziertes Streamable HTTP; getrennte Benutzer-Credentials; Vorschau/Bestätigung, Rezept- und Bestandsaktionen |
| HealthKit | SwiftUI-Brücke als Quellcode mit Keychain, HTTPS, erlaubnisbasierter Synchronisation, echten Löschereignissen für Einzelmessungen und eigener Server-Löschfunktion |

Die native Mealie-Nährwertstruktur hat keine eigenständige Bezugsdefinition. Für angereicherte Rezepte ist die definierte Bezugsgröße **eine Planerportion**.
Ändert der Assistent Zutaten oder Portionszahl im Rezept, muss er anschließend `set_recipe_facts` mit den aktualisierten Grundlagen ausführen.
Die strukturierten Quellen und Verträglichkeitsmerkmale liegen im Planer; native Kategorien/Tags können zusätzlich über `patch_recipe` gepflegt werden.

## Architektur und Datenrechte

FastAPI-Controller → Planerservice → versioniertes SQLAlchemy-Dokument. Die additive Migration heißt `hp20261014`.
Gemeinsame Daten liegen unter `household:<id>`, private Daten unter `user:<id>`; IDs werden serverseitig aus der Authentifizierung abgeleitet.
Private Endpoints akzeptieren keine fremde Nutzer-ID. Die Mitgliederliste teilt ausschließlich Namen und Essenspräferenzen,
keine Gewichte, Geburtsdaten, Kalorienziele oder Messhistorien. Haushaltsmitglieder können gemeinsam Mahlzeiten und Bestände verwalten.

Schreibvorgänge benötigen `revision`; veraltete Stände liefern HTTP 409. Kalender und Planerdokument committen in derselben Transaktion.
Die Aggregate sind bewusst für einen kleinen Haushalt gebaut. Das ist keine Architektur für eine öffentlich betriebene Plattform mit vielen konkurrierenden Nutzern.
Private Messhistorie ist auf 20.000 Einträge begrenzt. Alte Daten können über die Health-API entfernt werden.
Die Daten sind Teil der normalen Datenbanksicherung; die Backup-Konvertierung bewahrt das verschachtelte JSON unverändert.
Serveradministratoren und Backup-Inhaber haben weiterhin technischen Datenbankzugriff.

## Wissenschaftliche Zielprüfung

Mifflin–St Jeor schätzt den Ruheenergieverbrauch:

`10 × Gewicht[kg] + 6,25 × Größe[cm] − 5 × Alter[Jahre] + Koeffizient (+5 / −161)`.

Verwendet wird der Mittelwert täglicher Gewichtsmittel aus den letzten sieben Tagen; mindestens drei Messtage sind nötig.
Der Vorschlag verwendet den ausdrücklich gewählten Aktivitätsfaktor und das vereinbarte Defizit. Watch-Aktivkalorien werden nicht zusätzlich addiert.
Harris–Benedict (Originalgleichung) wird als Vergleich angezeigt, nicht mit Mifflin gemittelt.
Ein Vergleich der ersten/letzten Sieben-Tage-Fenster innerhalb von 28 Tagen wird nur bei ausreichenden Daten berechnet.

Protein verwendet ein ausdrücklich festgelegtes Referenzgewicht und einen vereinbarten g/kg-Faktor.
Es wird **keine individuelle medizinische Empfehlung** aus Körpergewicht allein abgeleitet.
Formeln liefern Schätzungen, keine Messung und keine verlässliche langfristige lineare Gewichtsprognose.
Es gibt keine automatische Kalorienabsenkung oder heimliche Zieländerung. Die Monatsanzeige wird beim Abruf geprüft;
ein monatlicher Hintergrundjob/Push-Dienst ist noch nicht eingerichtet.

Quellen und technische Referenzen:

- [Mifflin et al., 1990, PMID 2305711](https://pubmed.ncbi.nlm.nih.gov/2305711/)
- [Harris & Benedict, Originalarbeit](https://pubmed.ncbi.nlm.nih.gov/16576330/)
- [NIDDK Body Weight Planner: dynamische Energiebilanz](https://www.niddk.nih.gov/research-funding/at-niddk/labs-branches/laboratory-biological-modeling/integrative-physiology-section/research/body-weight-planner)
- [Apple: HealthKit](https://developer.apple.com/documentation/healthkit)
- [Apple: HKAnchoredObjectQuery](https://developer.apple.com/documentation/healthkit/hkanchoredobjectquery)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Upstream v3.28.0](https://github.com/mealie-recipes/mealie/releases/tag/v3.28.0)
- [Historischer Wochenansicht-PR #6399](https://github.com/mealie-recipes/mealie/pull/6399)

## Einrichtung und Betriebsgrenzen

- [MCP-Anleitung](../../integrations/mcp/README.md): lokaler Client, Remote-Transport, Token-Trennung, Assistentenablauf.
- [HealthKit-Anleitung](../../integrations/health-ios/README.md): XcodeGen, Signierung, private Installation/TestFlight, Gerätetest.
- [Prüfprotokoll](VALIDATION.md): tatsächlich ausgeführte Prüfungen und offene Abnahme.

Vor einem vorhandenen Server-Upgrade vollständiges Backup erstellen und Wiederherstellung mit diesem Fork prüfen.
Den Mealie-Container **aus diesem Fork bauen**; das offizielle v3.28.0-Image enthält diese Erweiterungen nicht.
Die bestehende Mealie-Buildstruktur bleibt erhalten; die Migration läuft beim normalen Datenbankstart.
Beim Rücksetzen auf Upstream entweder das Backup wiederherstellen oder die Planermigration bewusst zurücknehmen (löscht Erweiterungsdaten).
Keine produktive Instanz wurde hier geändert.

Bewusste Grenzen dieser Lieferung:

- ChatGPT/Claude Mobile sind noch nicht mit einem gehosteten Server getestet. Der HTTP-MCP verwendet Bearer-Tokens;
  für Clients, die OAuth erwarten, fehlt noch ein passender OAuth-Gateway. Codex/Claude Code können stdio verwenden.
- iOS-Quellcode ist vorhanden, aber auf dieser Linux-Umgebung nicht mit Xcode gebaut, signiert oder auf einem iPhone geprüft.
- Einkauf ist die gemeinsame Wochen-Checkliste der Erweiterung, keine zweite Kopie in der nativen Shopping-Listenverwaltung.
- Keine automatische Vorratsschrank-Erkennung, Preise, QR-Etiketten, Drive-Dauersynchronisation oder Portainer-Verwaltung.
- Strenge Spurenvermeidung blockiert automatische Planbestätigung und verlangt individuelle Prüfung.
- Essensvorlieben, leichte Mittagsgerichte, Variationen und sinnvoller Ablauf des Sonntagskochens steuert der Assistent;
  es gibt keinen autonomen lokalen Rezeptgenerator oder Optimierungsdienst.
- Komponenten können als eigene Rezepte eingeplant werden; verschachtelte Unterrezepte mit automatischer Mengenauflösung sind nicht implementiert.
- Übersetzungsrichtlinie des Upstreams: nur en-US ergänzt; andere Sprachen verwenden den bestehenden Fallback.

Der frühere Planungs-PR wird durch die direkte Arbeit im Default-Branch abgelöst. Neue Upstream-Versionen künftig kontrolliert integrieren,
Migrationen und diese Regressionstests erneut ausführen; nicht blind auf einen beweglichen `latest`-Container wechseln.

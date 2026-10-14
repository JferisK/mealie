# Prüfprotokoll – 14.10.2026

Basis: Mealie v3.28.0. Es wurden keine produktiven Nutzerwerte oder Zugangsdaten für Tests verwendet.

## Integration in Mealie und deutsche Demo – 14.10.2026

Die frühere separate Wochen-Navigation und eigene Einkaufs-Checkliste wurden aus der Oberfläche entfernt.
Die Erweiterung liegt jetzt als zusätzliche Ansichten im nativen Essensplaner. Einkauf verwendet den
vorhandenen Mealie-Zutatendialog und dieselben nativen Einkaufslisten wie die restliche Anwendung.
Die aktuelle Rezept-Portionszahl skaliert die frischen Kochmengen; Gefrierportionen sind ausgeschlossen.
Fehlende Portionszahlen verhindern die Übernahme. Mengen werden nur nach Bestätigung hinzugefügt;
wiederholtes Hinzufügen ist additiv und wird in der Oberfläche sowie den MCP-Tools erklärt.

Nuxt-Produktionsbuild und gezieltes ESLint erfolgreich. Keine TypeScript-Meldungen in der neuen
Portionskomponente und dem geänderten Speiseplan-Router; vorhandene Upstream-Typfehler bleiben,
auch im bestehenden Rezept-Zutatendialog und DefaultLayout. Sechs MCP-Tests erfolgreich, einschließlich
Bruchteilskalierung, fehlender Rezept-Portionszahl, Bestätigungspflicht und nativer Einkaufs-Häkchen.
Der Browsercheck nutzt den gebauten Client mit synthetischen API-Antworten und deutschen Texten:
Weiterleitung der alten URL, Personenwechsel, native Zutatenauswahl samt skalierter POST-Nutzlast,
native Einkaufslistenseite und vier zusätzliche Ansichten bei 320/390/430/768/1280 Pixeln.
Die native Einkaufsseite meldet im Headless-Browser eine abgelehnte Wake-Lock-Berechtigung;
dieser bekannte Umgebungsfehler wurde separat erfasst. Keine weiteren JavaScript-Seitenfehler.
Die Demo-Namen sind Jakob und Sanja; die Rezept-/Zielwerte sind weiterhin fiktiv.
Kein produktiver Server- oder physischer iPhone-Test.

## Mobile-first UI – 14.10.2026

Die Planung verwendet einen ausgewählten Tag, einen Personenwechsel und eine optionale Wochenübersicht.
Eine feste Navigation am unteren Bildschirmrand verbindet Plan, Gefrierbestand, Kochplan, Einkauf und private Ziele.
Gefrierentnahmen werden mit einer Mengenbestätigung ausgeführt; Dezimalwerte bleiben erhalten.
Die Einkaufsliste bietet große antippbare Zeilen und einen Erledigungsfortschritt. Profilformulare sind eingeklappt.

Der aktualisierte Nuxt-Produktionsbuild und gezieltes ESLint sind erfolgreich. Der TypeScript-Gesamtcheck
enthält weiterhin Upstream-Fehler, aber keine Meldungen für die beiden geänderten Planerkomponenten.
Der gebaute Client wurde mit Playwright/Chromium und synthetischen API-Antworten geprüft:
Tages-/Personenwechsel, sieben Tage in der Wochenübersicht, Gefriersuche, bestätigte Entnahme von 0,5 Portionen,
Einkaufsfortschritt und unveränderte Dezimalfaktoren 1,4/1,2. Alle fünf Bereiche wurden bei 320, 390, 430,
768 und 1280 Pixeln ohne horizontales Seitenüberlaufen geprüft; keine JavaScript-Seitenfehler.
Screenshots zeigen diesen echten Client mit Demo-Daten. Dies ersetzt keinen Test auf einem physischen
iPhone/Safari oder mit einem produktiven Server. Die Backend-Prüfungen unten stammen aus dem vorherigen
Implementierungslauf; bei dieser UI-Änderung wurden keine Backend-Dateien geändert.

## Implementierungsprüfung

| Prüfung | Ergebnis |
|---|---|
| Nuxt Produktionsbuild `pnpm generate` | Erfolgreich; SPA/PWA-Artefakte erzeugt |
| ESLint für neue Vue-/TS-Dateien | Erfolgreich |
| TypeScript-Gesamtcheck | Bestehende Fehler in zahlreichen Upstream-Dateien; keine Meldung in den neuen Planerdateien beim abschließenden Lauf |
| Ruff Lint/Format für neue Python-Dateien | Erfolgreich |
| Mypy für Planer-Schema, Repository, Service und Controller | Erfolgreich, 6 Quelldateien |
| Planer-Service-/HTTP-Regression | 18 Tests erfolgreich |
| MCP HTTP-Initialisierung, Toolliste, Auth/Origin/Host, gleichzeitige Credentials und Bestätigungsflags | 3 Tests erfolgreich |
| Alembic SQLite-Migrationskette bis `hp20261014` | Erfolgreich auf leerer Testdatenbank |
| Backup-Konvertierung | Verschachtelte Planer-JSON-Daten und UUID-/Datumsstrings bleiben erhalten |
| iOS/Xcode/Signierung/Gerätetest | Nicht ausgeführt; kein Xcode/iPhone in dieser Umgebung |
| PostgreSQL-Integration | Hier nicht ausgeführt |
| Echter ChatGPT-/Claude-Mobile-End-to-End-Test | Nicht ausgeführt; Server noch nicht gehostet |

Die 18 Regressionstests prüfen unbekannte Nährwerte, Portionsrechnung, native Rezeptwerte,
Kalendermirror, unveränderliche Gefriersnapshots, Überbuchung, idempotente Entnahmen, Reservierungsfreigabe,
Zusammenfassung von Koch-/Einkaufsmengen, Revisionenkonflikte, Datenbereiche, Formelrechnung,
Messwertvalidierung, individuelle HTTP-Datenrechte, fehlende Authentifizierung und getrennte Zielbestätigung.

## Einschränkung des lokalen Backend-Testlaufs

Die vollständige Python-Installation scheiterte am optionalen LDAP-C-Modul, weil native LDAP-Header fehlten.
Die installierte Umgebung verwendet deshalb `uv sync --group dev --no-install-package python-ldap`.
Für die lokalen **HTTP-Tests** wurden nur die LDAP-Imports im Testprozess durch Mocks ersetzt;
Authentifizierung wird in den positiven HTTP-Tests ausdrücklich über FastAPI-Dependency-Overrides bereitgestellt.
Das ist kein Nachweis für LDAP-Anmeldung und kein vollständiger Mealie-Integrationstest.
Die zusätzlichen GitHub-Regressionen installieren die echten nativen LDAP-Abhängigkeiten und führen die Tests ohne diesen lokalen Ersatz aus.
Der separate Service-Testlauf benötigt den LDAP-Import überhaupt nicht.

## Reproduzieren mit vollständiger Entwicklungsumgebung

```sh
uv sync --group dev --frozen
PRODUCTION=false uv run pytest --confcutdir=tests/household_planner tests/household_planner -q
uv run --project integrations/mcp python -m unittest discover -s integrations/mcp
cd frontend
pnpm install --frozen-lockfile
pnpm generate
```

Die bestehenden Upstream-CI-Workflows bleiben erhalten. Eine zusätzliche `Household planner regression` prüft die Erweiterung.
Automatisches GitHub-Pages-Deployment ist im Fork deaktiviert; ein manueller Workflow-Start kann es später bewusst auslösen.
Kein VPS-Deployment, veröffentlichter iOS-Build oder grüner Gesamttest aller Upstream-Funktionen wird hier behauptet.

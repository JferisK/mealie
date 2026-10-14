# Prüfprotokoll – 14.10.2026

Basis: Mealie v3.28.0. Es wurden keine produktiven Nutzerwerte oder Zugangsdaten für Tests verwendet.

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

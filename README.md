# Tidal Playlist Creator

Native macOS desktop application that creates a TIDAL playlist from a pasted
list of songs. It runs locally and uses TIDAL's device-authorization OAuth
flow; it never stores a TIDAL password.

## Features

- Paste and automatically clean numbered or bulleted song lists.
- Search each song in TIDAL and show the first match.
- Simple confidence score with green, yellow, and red validation rows.
- Uncheck incorrect results and choose from alternative matches.
- Create a playlist and add the selected tracks.
- Export a UTF-8 text report.
- Save the OAuth session in the user's macOS application-data directory.

## Requirements

- macOS on Apple Silicon (arm64)
- Python 3.12 or newer
- A TIDAL account with an active subscription

`tidalapi` is an unofficial client library. Changes in TIDAL's private API may
require a future library update.

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python main.py
```

On first launch, click **Connect TIDAL**. The application opens TIDAL's secure
authorization page in the default system browser and waits for approval.

The saved session is stored under macOS Application Support, normally:

```text
~/Library/Application Support/eltermi/Tidal Playlist Creator/tidal_session.json
```

## Usage

1. Connect TIDAL.
2. Enter a playlist name and optional description.
3. Paste one song per line.
4. Click **Analyze**.
5. Uncheck questionable matches and click **Review Unchecked**, or double-click
   any result row to select an alternative.
6. Click **Create Playlist**.
7. Optionally click **Save Report**.

## Tests

```bash
pytest
```

## Build the macOS app

```bash
chmod +x build_mac.sh
./build_mac.sh
```

The app is generated at:

```text
dist/Tidal Playlist Creator.app
```

It can be opened with a double click. Since this personal build is not signed
or notarized, macOS Gatekeeper may require using **Open** from the Finder
context menu the first time.

To use a custom icon, place an `.icns` file at
`resources/icons/app.icns` before building.

## Automated builds and releases

GitHub Actions builds the application on every push to `main`, on version tags,
and when manually started from the **Actions** tab. The workflow runs the test
suite, creates the macOS `.app`, verifies the bundle and packages it as:

```text
Tidal-Playlist-Creator-<version>-macOS.zip
```

For normal pushes and manual builds, `<version>` is the seven-character commit
SHA. Download the package from the workflow run's **Artifacts** section. Build
artifacts are retained for 14 days.

To create a release:

```bash
git tag v1.0.0
git push origin v1.0.0
```

Tags must use the exact `vMAJOR.MINOR.PATCH` format. A successful tagged build
creates the GitHub Release automatically, generates release notes and attaches
`Tidal-Playlist-Creator-v1.0.0-macOS.zip`.

The automated build currently targets Apple Silicon only, matching the
application's existing and tested macOS build. Packages are ad-hoc signed by
PyInstaller, but they are not signed with an Apple Developer certificate or
notarized. Gatekeeper may therefore require opening the app from Finder's
context menu the first time.

## Project structure

```text
main.py
ui/
services/
tests/
.github/workflows/build.yml
requirements.txt
requirements-dev.txt
build_mac.sh
resources/icons/
```

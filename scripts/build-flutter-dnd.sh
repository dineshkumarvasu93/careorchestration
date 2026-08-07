#!/usr/bin/env bash
# Builds the Flutter drag-and-drop island and copies it into the static
# frontend so the HTML dashboard can embed it at /us017/flutter/index.html.
#
# Usage (from anywhere):  ./scripts/build-flutter-dnd.sh
# Requires the Flutter SDK on PATH (verify with `flutter --version`).
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(dirname "$script_dir")"
flutter_dir="$root/flutter_rule_config"
dest="$root/frontend/us017/flutter"

echo "Building Flutter web (base-href /us017/flutter/)..."
(cd "$flutter_dir" && flutter build web --base-href /us017/flutter/)

echo "Copying build output to $dest ..."
mkdir -p "$dest"
find "$dest" -mindepth 1 -maxdepth 1 ! -name README.md ! -name .gitkeep -exec rm -rf {} +
cp -R "$flutter_dir/build/web/." "$dest/"

echo "Done. Open the dashboard and the drag-and-drop island will load from ./flutter/."

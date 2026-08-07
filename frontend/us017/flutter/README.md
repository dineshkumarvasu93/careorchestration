# Flutter drag-and-drop build output

This folder holds the **compiled** Flutter Web build of the rule-modules
drag-and-drop island. It is loaded by `../rule-config-dashboard.html` via an
`<iframe src="./flutter/index.html">`.

The contents are generated — do not edit by hand. Build them with:

```powershell
# from the repository root
./scripts/build-flutter-dnd.ps1
```

or manually:

```bash
cd flutter_rule_config
flutter build web --base-href /us017/flutter/
# then copy build/web/* into this folder
```

Until you run the build, this folder is empty and the dashboard will show an
empty component area (the rest of the HTML page still works).

# Publishing v0.1.0

## GitHub Repository

1. Create a public repository named `quiet-progress`.
2. Push this project to the repository.
3. Add these topics:

   `windows desktop-widget productivity progress-bar time-tracker tkinter python minimalist japanese windows-desktop`

## Release

Install [GitHub CLI](https://cli.github.com/), run `gh auth login`, then:

```powershell
powershell -ExecutionPolicy Bypass -File tools\publish_release.ps1
```

The script publishes `release/quiet-progress-windows.zip` as `v0.1.0`.

## Social Preview

Open the repository settings and upload:

`docs/assets/social-preview.png`

The image is already exported at `1280x640`.

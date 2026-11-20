# SignPath Application Notes

## Project

```text
Name:       Reverse Update Studio
Repo:       https://github.com/Reddgen/reverse-update-studio
License:    MIT
Visibility: Public
```

## Build

Workflow:

```text
.github/workflows/windows.yml
```

Command:

```powershell
& "$env:WINDIR\Microsoft.NET\Framework64\v4.0.30319\csc.exe" `
  /nologo /target:winexe /out:dist\ReverseUpdateStudio.exe `
  /reference:System.Windows.Forms.dll launcher\Launcher.cs
```

Artifact:

```text
dist/ReverseUpdateStudio.exe
```

GitHub Actions artifact name:

```text
ReverseUpdateStudio-Windows-Launcher
```

## What the artifact is

A small C# launcher. It starts `Launch.cmd`, which starts the local Python
server and opens the web UI.

The launcher does **not** contain the analysis engine. The portable ZIP is
built separately and should be checksummed independently.

## What SignPath would sign

`ReverseUpdateStudio.exe` built by CI.

The Python/Ghidra payload is not an Authenticode target. Users should verify
the full ZIP SHA-256 as well.

## Application answers

- **Project type:** open-source desktop utility
- **License:** MIT
- **Build system:** GitHub Actions, `windows-latest`
- **Artifact:** `ReverseUpdateStudio.exe`
- **No secrets:** the workflow uses no tokens or private keys
- **No proprietary binaries:** the repo contains source and scripts only
- **Game data:** not included
- **Network:** local-first; binds to 127.0.0.1 by default

## After approval

SignPath normally provides a GitHub Action or API token. Add that as a
repository secret and sign the CI artifact; do not commit the token.

Example future workflow step:

```yaml
- uses: signpath/github-action-submit-signing-request@v1
  with:
    api-token: ${{ secrets.SIGNPATH_API_TOKEN }}
    organization-id: ${{ vars.SIGNPATH_ORGANIZATION_ID }}
    project-slug: reverse-update-studio
    signing-policy-slug: release-signing
    artifact-configuration-slug: exe
    github-artifact-id: ${{ steps.upload.outputs.artifact-id }}
    wait-for-completion: true
```

The exact inputs depend on the SignPath project configuration. Replace these
placeholders with the values SignPath provides after approval.

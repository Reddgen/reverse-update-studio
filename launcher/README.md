# Windows Launcher

Small signed-launcher candidate for SignPath.

It does not contain the analysis engine. It starts `Launch.cmd` from the same
folder, which starts the local Python server and opens the web UI.

Build:

```powershell
& "C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe" `
  /target:winexe /out:ReverseUpdateStudio.exe `
  /reference:System.Windows.Forms.dll Launcher.cs
```

The GitHub workflow builds this on `windows-latest` and uploads it as an
artifact. SignPath can sign the CI-produced `ReverseUpdateStudio.exe`.

This is a launcher signature, not a signature over the Python/Ghidra payload.
A production release should also sign or checksum the full portable ZIP.

# Code Signing

## Current state

The launcher was signed with a **development self-signed certificate**:

```text
CN=Reverse Update Studio Dev
Status: UnknownError
Reason: root certificate is not trusted
```

That is expected. A self-signed certificate cannot remove SmartScreen warnings.

## Production signing

Buy a code-signing certificate (OV or EV) from a CA, then:

```powershell
tools\sign_release.ps1 `
  -Path "build\ReverseUpdateStudio\Reverse Update Studio.exe" `
  -Pfx "C:\secure\reverse-update.pfx" `
  -PfxPassword "..." `
  -TimestampUrl "http://timestamp.digicert.com"
```

Or use a certificate already in the user store:

```powershell
tools\sign_release.ps1 `
  -Path "build\ReverseUpdateStudio\Reverse Update Studio.exe" `
  -Thumbprint "ABCDEF..." `
  -TimestampUrl "http://timestamp.digicert.com"
```

## Development signing

```powershell
tools\sign_release.ps1 -Path "path\to\app.exe" -SelfSigned
```

This attaches a signature but the chain is untrusted.

## What must be signed

- `Reverse Update Studio.exe` launcher
- any `.exe` or `.dll` shipped to users
- optional: the Inno `Setup.exe` under `reports/legacy/`

`Setup.cmd` is a batch file and cannot carry an Authenticode signature. The
portable ZIP itself can be signed with a detached signature or a signed checksum
file in a future release.

## Verify

```powershell
Get-AuthenticodeSignature "Reverse Update Studio.exe" |
  Format-List Status, StatusMessage, SignerCertificate
```

`Status = Valid` requires the CA chain to be trusted and the timestamp to verify.

## Release gate

Do not call the Windows build publicly signed until a CA certificate produces:

```text
Status: Valid
```

param(
  [Parameter(Mandatory=$true)][string[]]$Path,
  [string]$Thumbprint = "",
  [string]$Pfx = "",
  [string]$PfxPassword = "",
  [string]$TimestampUrl = "",
  [switch]$SelfSigned
)
$ErrorActionPreference = "Stop"

function Get-SigningCert {
  if ($Thumbprint) {
    $c = Get-ChildItem Cert:\CurrentUser\My | Where-Object { $_.Thumbprint -eq $Thumbprint } | Select-Object -First 1
    if (-not $c) { throw "certificate not found: $Thumbprint" }
    return $c
  }
  if ($Pfx) {
    $sec = ConvertTo-SecureString $PfxPassword -AsPlainText -Force
    return (Import-PfxCertificate -FilePath $Pfx -CertStoreLocation Cert:\CurrentUser\My -Password $sec)
  }
  if ($SelfSigned) {
    return New-SelfSignedCertificate -Type CodeSigningCert -Subject "CN=Reverse Update Studio Dev" `
      -CertStoreLocation Cert:\CurrentUser\My -KeyUsage DigitalSignature `
      -NotAfter (Get-Date).AddYears(2) -FriendlyName "Reverse Update Studio Dev Code Signing"
  }
  throw "provide -Thumbprint, -Pfx, or -SelfSigned"
}

$cert = Get-SigningCert
Write-Host "Signing with: $($cert.Subject) [$($cert.Thumbprint)]"
$files = @()
foreach ($p in $Path) {
  $item = Get-Item -LiteralPath $p
  if ($item.PSIsContainer) {
    $files += Get-ChildItem -LiteralPath $item.FullName -Recurse -File -Include *.exe,*.dll
  } else {
    $files += $item
  }
}
if (-not $files) { throw "no PE files found" }

$fail = 0
foreach ($f in $files) {
  try {
    $sp = @{ FilePath = $f.FullName; Certificate = $cert; HashAlgorithm = 'SHA256' }
    if ($TimestampUrl) { $args.TimestampServer = $TimestampUrl }
    $r = Set-AuthenticodeSignature @sp
    $sig = Get-AuthenticodeSignature -LiteralPath $f.FullName
    Write-Host ("{0}: {1} / {2}" -f $f.Name, $sig.Status, $sig.StatusMessage)
    if (-not $sig.SignerCertificate) { $fail++ }
  } catch {
    Write-Host ("{0}: SIGN FAILED: {1}" -f $f.Name, $_.Exception.Message)
    $fail++
  }
}
if ($fail) { exit 1 }
Write-Host "Signed $($files.Count) file(s)."
exit 0

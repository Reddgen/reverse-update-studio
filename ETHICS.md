# Acceptable Use and Ethics

This is guidance, **not legal advice**, and it does **not** modify the MIT
license in [LICENSE](LICENSE). The MIT license remains the legal grant for
original code.

## What the tool does

- Reads binaries statically.
- Compares two builds at function/method level.
- Maps PDB symbols to source file/line.
- Matches paths against a local library.
- Verifies encrypted, signed update packages.
- Applies/creates patch formats.

## What it does not do

- It does not execute, emulate, or sandbox the target.
- It does not bypass DRM, licensing, anti-cheat, or authentication.
- It does not decrypt protected game assets.
- It does not create a playable port.
- It does not grant rights to the analysed software.

## Good-faith uses

- Security research on software you own or are authorised to test.
- Incident response and defensive malware triage.
- Verifying that a release matches its source or previous build.
- Maintaining open-source projects with public PDBs.
- Game modding where the EULA and local law allow it.
- Education using open-source or self-built binaries.
- Software preservation with lawful copies.
- Checking update packages before installing them.

## Bad-faith uses

Do not use this project to:

- analyse software without permission where law or contract forbids it;
- bypass DRM, licence checks, anti-cheat, or access controls;
- build or distribute malware;
- repackage someone else's app with malicious changes;
- publish copyrighted ROMs, ISOs, PDBs, or proprietary binaries;
- expose personal data found in binaries or PDB paths;
- cheat in online games or violate a service's terms.

The maintainers do not support those uses.

## Educational use

Safe targets:

- OpenRCT2 public builds
- 0 A.D. public builds
- F-Droid APKs
- software you compiled yourself with PDBs
- synthetic test binaries

Suggested exercises:

1. Build two versions of a small open-source program with PDBs.
2. Compare them and identify changed functions.
3. Map a changed function to a source line.
4. Inspect an open-source APK and compare two versions.
5. Create a path library entry and trace a known sequence.
6. Verify an update package, then tamper with a copy and confirm rejection.

Do not use copyrighted game ROMs or proprietary PDBs in a public classroom
repository.

## Discretion checklist

Before analysing a file:

- Do I own it or have written authorisation?
- Is the target allowed by its licence/EULA?
- Am I avoiding DRM/anti-cheat circumvention?
- Is the machine isolated from production data?
- Am I avoiding uploading sensitive PDBs or personal paths?
- Will I publish findings responsibly?
- Have I removed third-party binaries before sharing results?

## Security research

- Get written scope and authorisation.
- Use a lab VM or disposable machine.
- Do not run untrusted samples.
- Follow coordinated disclosure.
- Keep evidence minimal and redacted.
- Follow local law and the target's bug-bounty policy.

## No warranty

The software is provided “as is”, without warranty. You are responsible for
how you use it and for the legality of the files you analyse.

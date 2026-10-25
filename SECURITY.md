# Security policy

Sweep runs with administrator rights and changes system settings, so security reports are taken seriously.

## Supported versions

Only the [latest release](https://github.com/drakedog-dev/sweep/releases/latest) receives fixes. Sweep offers new versions by itself when it starts.

## Reporting a vulnerability

Please **do not** open a public issue for a security problem.

Report it privately through GitHub: [**Report a vulnerability**](https://github.com/drakedog-dev/sweep/security/advisories/new). Include the Sweep version, your Windows version, the steps to reproduce and what an attacker could achieve.

What to expect:

- an acknowledgement within 3 days;
- an assessment and a plan within 10 days;
- a fixed release as soon as possible, with credit to you in the changelog unless you prefer otherwise.

## Scope

In scope: anything in this repository and the released installers, for example privilege escalation through Sweep, tampering with update downloads, unsafe handling of paths or registry keys, or ways to make Sweep delete something it should not.

Out of scope: problems in Windows itself, in winget, or in third-party programs that Sweep updates or uninstalls; reports from automated scanners without a working proof of concept.

## How releases are protected

- Releases are built only by GitHub Actions from this repository; nothing built on a personal computer is published.
- The release page lists the SHA-256 of every installer.
- Program updates are installed through winget, which checks each installer against the SHA-256 in the Microsoft catalogue before running it.
- Code signing through SignPath Foundation is being set up; see [CODE_SIGNING_POLICY.md](CODE_SIGNING_POLICY.md).

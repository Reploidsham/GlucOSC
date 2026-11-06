# Security

## Reporting a problem

Please report security problems privately through **Security > Report a vulnerability** on this repository, not in a public issue.

GlucOSC sends health data (your glucose readings) from your phone to your PC and into VRChat, where other players can see it. Problems that leak that data further than you expect, or that let someone else send fake readings to your avatar, count as security problems too.

## Checking a download

Every release has `SHA256SUMS.txt` and a signed build record (provenance) made by GitHub Actions. See [Check your download](README.md#check-your-download).

If a file's checksum does not match, or `gh attestation verify` fails, don't run it. Please open a report.

## What GlucOSC does with your data

- It reads from your phone's xDrip+ web service on your local network, using the secret you set (sent as a SHA-1 hash, as xDrip+ expects).
- It sends the values to VRChat on your own PC (`127.0.0.1:9000` by default).
- It does not contact any other server and has no telemetry.
- Your settings, including the xDrip+ secret, are stored in your user profile by Qt's settings system (Windows registry or `~/.config` on Linux), in plain text.

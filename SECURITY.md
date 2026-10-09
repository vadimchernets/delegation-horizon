# Security

This code reads local files and prints numbers. It makes no network calls, needs no keys and starts no other
programs. Work logs can still hold personal information, so the main risks are about data.

## Reporting a vulnerability

Please do not open a public issue. Open a private security advisory instead: repository page, then "Security",
then "Report a vulnerability". Describe what you found, how to reproduce it, and what it lets someone do.

## In scope

- A log or CSV file that makes a script run code, write outside the path it was given, or hang.
- A way to make a piece count as verified when the rules of Section 5.2 say it must not.
- A real name or other personal detail reaching a card that the log did not put there.

Supported version: the latest commit on `main`.

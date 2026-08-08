# Changelog — V7

- Corrected package-lock registry provenance: all 113 lockfile `resolved` prefixes are changed from a build-environment internal registry endpoint to public npm registry endpoint.
- Preserved exact package versions and integrity hashes; only `resolved` transport origin changes.
- Updated Runner to pass explicit public `--registry` and isolated `--cache` for `Registry` mode.
- Updated Static Gate to assert absence of internal registry URLs and presence of public registry URLs.

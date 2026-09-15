# bug-hunter research

Fetched 2026-09-15. Reference = model knows it; open source only if unsure. Full entry = model did not know it; cite the quote.

## Quoting and expansion
- [ShellCheck SC2086](https://www.shellcheck.net/wiki/SC2086) - unquoted expansion word-splits on IFS and globs; quote, or use arrays
- [POSIX Shell Command Language 2024](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html) - unquoted heredoc delimiter expands when redirection runs; quoted delimiter never expands

## Test and comparison semantics
- [Google Shell Style Guide](https://google.github.io/styleguide/shellguide.html) - prefer `[[ ]]`; `<`/`>` compare lexically, numbers need `(( ))` or `-lt`

## set -e and pipefail
- [BashFAQ/105](https://mywiki.wooledge.org/BashFAQ/105) - errexit off under if/&&/|| and their callees; pipes need pipefail; version-dependent

## Fresh start vs restart
- [Crash-Only Software 2003](https://dslab.epfl.ch/pubs/crashonly.pdf) - one start path = recovery from whatever state last run left

## Interrupt and partial state
- [POSIX rename() 2024](https://pubs.opengroup.org/onlinepubs/9799919799/functions/rename.html) - temp file then rename: target old or new, never partial
- [Cracauer SIGINT handling](https://www.cons.org/cracauer/sigint.html) - INT trap: restore state, `trap - INT; kill -INT $$`, not `exit N`

## Secrets hygiene
- [CWE-214](https://cwe.mitre.org/data/definitions/214.html) - secrets in argv or environment visible to other local processes

## Service readiness, background jobs
- [Wooledge ProcessManagement](https://mywiki.wooledge.org/ProcessManagement): "The sensible thing to check in order to determine whether the web server started successfully... is whether it's actually serving your web content!". Rule: ready = service answers its own protocol, not PID alive after sleep; background exit status only via `wait $pid`. Tell: `sleep N; kill -0 $pid`, `pgrep` or pidfile test used as health check; `cmd &` with no later `wait "$pid"`.

Unsourced: cross-platform parity, deprecated or absent tools, installer/uninstaller contract

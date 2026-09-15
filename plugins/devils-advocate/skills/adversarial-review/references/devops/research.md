# devops research

Fetched 2026-09-15. Reference = model knows it; open source only if unsure. Full entry = model did not know it; cite the quote.

## Image bloat
- [Docker best practices](https://docs.docker.com/build/building/best-practices/): "Even if you unset the environment variable in a future layer, it still persists in this layer and its value can be dumped." Rule: page has no layer-count rule; coalesce RUNs only when later layer deletes earlier output. Tell: `rm`/`unset` in own RUN after creating RUN; RUN count alone = no finding.

## Layer cache
- [Docker cache optimize](https://docs.docker.com/build/cache/optimize/) - copy manifests, install deps, then copy source

## Secrets and supply chain
- [Docker build secrets](https://docs.docker.com/build/building/secrets/) - ARG/ENV persist in final image; use secret or SSH mount
- [GitHub Actions secure use](https://docs.github.com/en/actions/reference/security/secure-use) - SHA-pin actions; OIDC over stored keys; no untrusted checkout in pull_request_target

## Runtime posture
- [OWASP Docker cheat sheet](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html) - no socket mount, non-root USER, drop caps, resource limits, read-only rootfs

## PID 1 and signals
- [pid_namespaces(7)](https://man7.org/linux/man-pages/man7/pid_namespaces.7.html) - PID 1 gets handled signals only; init needed without handler or children
- [Dockerfile reference](https://docs.docker.com/reference/dockerfile/) - shell-form ENTRYPOINT: app not PID 1, never receives docker stop SIGTERM

## Probes and drain
- [Kubernetes probes](https://kubernetes.io/docs/concepts/configuration/liveness-readiness-startup-probes/) - liveness does not wait readiness; wrong liveness cascades restarts under load
- [Kubernetes pod lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/) - endpoint removal concurrent with SIGTERM; preStop counts against 30s grace

## Rollback anchor
- [Kubernetes images](https://kubernetes.io/docs/concepts/containers/images/) - no :latest in prod: untrackable, hard rollback; digest stops mixed versions

## Pipeline gates
- [OWASP CICD-SEC-1](https://owasp.github.io/www-project-top-10-ci-cd-security-risks/CICD-SEC-01-Insufficient-Flow-Control-Mechanisms) - no prod deploy trigger without additional approval or review

## Config drift
- [12factor Config](https://12factor.net/config) - config varies per deploy, lives outside code; codebase open-sourceable without leaking credentials

## Container state
- [12factor Processes](https://12factor.net/processes) - stateless share-nothing; persistent data in backing service, never local disk

## Network exposure
- [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/) - pods allow all ingress and egress until policy selects them

Unsourced: volume backup path, internal-hop TLS, fail-loud required config

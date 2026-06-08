#!/usr/bin/env bash
set -euo pipefail

x265_latest_numeric_tag() {
  local version=""

  if [[ "${GITHUB_REF:-}" == refs/tags/[0-9].[0-9]* ]]; then
    version="${GITHUB_REF_NAME:-}"
  elif [[ "${GITHUB_REF:-}" == refs/tags/* ]]; then
    echo "Release artifacts require a numeric version tag, got ${GITHUB_REF_NAME:-}" >&2
    return 1
  else
    version=$(git tag --list '[0-9].[0-9]*' --sort=-v:refname | head -n1)
    if [ -z "$version" ] && [ -f .git/shallow ]; then
      echo "No numeric tag visible in shallow checkout; fetching tag refs" >&2
      git fetch --tags origin
      version=$(git tag --list '[0-9].[0-9]*' --sort=-v:refname | head -n1)
    fi
  fi

  if [ -z "$version" ]; then
    version="0.0"
    echo "::warning::No numeric version tag found; using $version as CI fallback"
  fi

  test -n "$version"
  printf '%s\n' "$version"
}

x265_describe_numeric_tag() {
  git describe --tags --match='[0-9].[0-9]*' HEAD 2>/dev/null || true
}

x265_ci_version_from_latest_tag() {
  local latest_tag="${1:-}"
  local head_tag
  local head_hash
  local version
  local orig_tag
  local rest
  local distance

  test -n "$latest_tag"
  head_tag=$(x265_describe_numeric_tag)
  if [ -z "$head_tag" ] && [ -f .git/shallow ]; then
    for deepen in 32 128 512 2048; do
      echo "Deepening checkout by $deepen commits for CI version tag discovery" >&2
      git fetch --tags --deepen="$deepen" origin "${GITHUB_REF}"
      head_tag=$(x265_describe_numeric_tag)
      if [ -n "$head_tag" ]; then
        break
      fi
    done
    if [ -z "$head_tag" ] && [ -f .git/shallow ]; then
      echo "Falling back to full history for CI version tag discovery" >&2
      git fetch --tags --unshallow origin
      head_tag=$(x265_describe_numeric_tag)
    fi
  fi

  head_hash=$(git rev-parse --short HEAD)
  if [ -z "$head_tag" ]; then
    version="${latest_tag}-g${head_hash}"
  elif [[ "$head_tag" != *-* ]]; then
    version="${head_tag#M}-g${head_hash}"
  else
    orig_tag=${head_tag%%-*}
    rest=${head_tag#*-}
    distance=${rest%%-*}
    version="${orig_tag#M}+${distance}-g${head_hash}"
  fi

  test -n "$version"
  printf '%s\n' "$version"
}

x265_package_version_for_event() {
  local release_version="${1:-}"
  local ci_version="${2:-}"
  local version

  if [ "${GITHUB_EVENT_NAME:-}" = 'workflow_dispatch' ] || [[ "${GITHUB_REF:-}" == refs/tags/* ]]; then
    version="$release_version"
  else
    version="$ci_version"
  fi

  test -n "$version"
  printf '%s\n' "$version"
}

#!/usr/bin/env bash
set -euo pipefail

find_preinstalled_cmake4() {
  local candidate version

  for candidate in \
    "${ANDROID_SDK_ROOT:-}/cmake"/*/bin/cmake \
    "${ANDROID_HOME:-}/cmake"/*/bin/cmake \
    /usr/local/bin/cmake \
    /usr/bin/cmake; do
    [ -x "$candidate" ] || continue
    version=$("$candidate" --version | sed -nE 's/^cmake version ([0-9]+(\.[0-9]+)+).*$/\1/p' | head -1)
    [ -n "$version" ] || continue
    if [[ "$version" == 4.* ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  return 1
}

ensure_cmake4() {
  local cmake_path
  if cmake_path=$(find_preinstalled_cmake4); then
    export PATH="$(dirname "$cmake_path"):$PATH"
    echo "Using preinstalled CMake: $cmake_path"
    return 0
  fi

  python -m venv "$RUNNER_TEMP/cmake-venv"
  "$RUNNER_TEMP/cmake-venv/bin/python" -m pip install 'cmake>=4.0,<5'
  export PATH="$RUNNER_TEMP/cmake-venv/bin:$PATH"
  echo "Installed fallback CMake into $RUNNER_TEMP/cmake-venv"
}

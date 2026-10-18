#!/usr/bin/env bash
#
# Run by "git release" after the release X.Y.Z is pushed. Can also be run by hand:
#
#   ./post-release.sh 2.0.13
#
# The theme repositories next to this one build on the blog-site image. Their Dockerfile (FROM ...) and
# __version__ are set to the new version. The changes are NOT committed: commit them in the theme
# repositories once the CI has built the image ghcr.io/g10f/blog-site:<version>.
#
# A theme repository is a git repository next to this one whose Dockerfile builds on the blog-site
# image. A theme repository with a file .skip-release is skipped.

set -euo pipefail

IMAGE=ghcr.io/g10f/blog-site

fail() {
  echo "error: $1" >&2
  exit 1
}

version=${1:-}
if [[ ! $version =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  fail "usage: $0 X.Y.Z"
fi

# all paths are relative to the repository root
cd "$(dirname "$0")"

for theme_dir in ../*/; do
  theme_dir=${theme_dir%/}
  if [ ! -d "$theme_dir/.git" ] || ! grep -q "^FROM ${IMAGE//./\\.}:" "$theme_dir/Dockerfile" 2>/dev/null; then
    continue  # not a theme repository
  fi
  if [ -f "$theme_dir/.skip-release" ]; then
    echo "skipped $theme_dir (.skip-release present)"
    continue  # theme opted out of release bumps
  fi

  sed -i "s#^FROM ${IMAGE//./\\.}:.*#FROM $IMAGE:$version#" "$theme_dir/Dockerfile"
  # the version file of the theme: the tracked Python file with a line __version__ = '...'
  git -C "$theme_dir" grep -l -E "^__version__ = " -- '*.py' | while read -r version_file; do
    sed -i "s/^__version__ = .*/__version__ = '$version'/" "$theme_dir/$version_file"
  done
  echo "updated $theme_dir (not committed)"
done

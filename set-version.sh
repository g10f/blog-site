#!/bin/bash
VERSION=1.5.6

sed -i "s/__version__ =.*/__version__ = '${VERSION}'/" apps/blogsite/__init__.py

sed -i "s/FROM ghcr\.io\/g10f\/blog-site:.*/FROM ghcr\.io\/g10f\/blog-site:${VERSION}/" ../blog-michal-theme/Dockerfile
sed -i "s/__version__ =.*/__version__ = '${VERSION}'/" ../blog-michal-theme/michal_theme/__init__.py

sed -i "s/FROM ghcr\.io\/g10f\/blog-site:.*/FROM ghcr\.io\/g10f\/blog-site:${VERSION}/" ../afd-blog/Dockerfile
sed -i "s/__version__ =.*/__version__ = '${VERSION}'/" ../afd-blog/afd_theme/__init__.py


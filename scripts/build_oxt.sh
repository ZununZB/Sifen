#!/usr/bin/env bash
# Empaqueta la extensión como .oxt (un .zip con la estructura requerida por
# el Administrador de Extensiones de LibreOffice).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="$ROOT_DIR/dist"
OUT_FILE="$DIST_DIR/sifen-libre.oxt"

mkdir -p "$DIST_DIR"
rm -f "$OUT_FILE"

cd "$ROOT_DIR"
zip -r "$OUT_FILE" \
  description.xml \
  META-INF \
  registry \
  src \
  -x "**/__pycache__/*" "**/*.pyc"

echo "Extensión generada en: $OUT_FILE"
echo "Instálala desde LibreOffice: Herramientas > Administrar extensiones > Agregar..."

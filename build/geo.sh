#!/usr/bin/env bash
# Rebuild simplified map shapes from the NCES boundary file. Needs: npx mapshaper.
set -euo pipefail
ZIP=$(ls fetch/raw/edge_boundaries__*.zip | head -1)
TMP=$(mktemp -d); unzip -q "$ZIP" -d "$TMP"; SHP=$(find "$TMP" -name "*.shp" | head -1)
OUT=build/geo; mkdir -p $OUT; cd "$TMP"
npx -y mapshaper@0.7 "$SHP" -each 'id=GEOID, l=MTFCC=="G5400"?"e":MTFCC=="G5410"?"s":"u"' -filter-fields id,l \
  -simplify 2% keep-shapes -split l -o format=geojson precision=0.001 id-field=id
npx -y mapshaper@0.7 -i u.json e.json combine-files -merge-layers -o base.json format=geojson precision=0.001
# Lighter copy for the national view (zoomed out): fewer points, loads and draws faster
npx -y mapshaper@0.7 base.json -filter-fields id -simplify 10% keep-shapes -o base_lo.json format=geojson precision=0.005
npx -y mapshaper@0.7 "$SHP" -each 'st=GEOID.slice(0,2)' -dissolve st -simplify 1% -filter-fields st -o states.json format=geojson precision=0.002
cd - >/dev/null; cp "$TMP"/base.json "$TMP"/base_lo.json "$TMP"/s.json "$TMP"/states.json $OUT/
echo "map shapes: $(ls -la $OUT)"

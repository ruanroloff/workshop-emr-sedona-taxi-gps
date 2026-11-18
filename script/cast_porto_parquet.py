import geopandas as gpd
from pyrosm import OSM

osm = OSM("porto.osm.pbf")

# --- Administrative boundaries / named places (polygons) ---
boundaries = osm.get_boundaries()           # admin areas (parishes, city)
landuse    = osm.get_landuse()              # parks, residential, etc.
pois       = osm.get_pois()                 # points of interest

# Keep polygons only, build a unified "places" table
import pandas as pd

def to_places(gdf, type_col, type_val=None):
    gdf = gdf[gdf.geometry.type.isin(["Polygon", "MultiPolygon"])].copy()
    gdf = gdf.to_crs("EPSG:4326")
    out = pd.DataFrame({
        "place_name": gdf.get("name", "unknown"),
        "place_type": gdf[type_col] if type_col in gdf else type_val,
        "geometry_wkt": gdf.geometry.to_wkt(),
    })
    return out[out["place_name"].notna()]

places = pd.concat([
    to_places(boundaries, "admin_level", "boundary"),
    to_places(landuse,    "landuse"),
], ignore_index=True)

places = places.reset_index().rename(columns={"index": "place_id"})
places.to_parquet("porto_places_wkt.parquet", index=False)
print(f"OK. {len(places)} places exported")

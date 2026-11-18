# Porto Taxi GPS Spatial Analytics

This project analyzes taxi GPS trajectories in Porto, Portugal, using AWS EMR,
Apache Spark, Apache Sedona, and Amazon S3. It demonstrates a spatial data lake
architecture that transforms raw taxi trajectories into route geometries,
combines them with Porto places from OpenStreetMap (OSM), and produces spatial
insights such as frequently crossed places, 200-meter traffic-density cells,
and merged route corridors.

## Project architecture

The analysis follows a medallion-style lakehouse pipeline:

```text
Porto taxi CSV + Porto OSM places
                |
                v
          BRONZE layer
  Valid trajectories without missing
  data or fewer than two GPS points
                |
                v
          SILVER layer
  GPS arrays converted to LineStrings,
  invalid/short routes removed, routes
  simplified, places converted to geometries
                |
                v
           GOLD layer
  Spatial joins, pass-through rankings,
  200 m density grid, merged routes,
  and top-place aggregates
```

The notebooks and AWS paths are organized as follows:

| Notebook | Purpose | Main output |
| --- | --- | --- |
| `notebook/00-bronze-taxi.ipynb` | Reads the taxi CSV, parses `POLYLINE`, filters bad trips, and creates the Bronze table | `bronze/porto_trips_parsed.parquet` |
| `notebook/01-silver-taxi.ipynb` | Builds route `LineString` geometries, filters and simplifies routes, and processes OSM places | `silver/routes_simplified.geoparquet` and `silver/places.parquet` |
| `notebook/02-gold-taxi.ipynb` | Performs spatial joins and aggregates, identifies popular places, and generates a heatmap | `gold/heatmat.parquet` and `gold_top_places` |
| `notebook/hello.ipynb` | Verifies that Apache Sedona is installed and callable in Spark | No data output |

## Repository contents

```text
data/
  porto_taxi.csv              Taxi trajectories supplied as a Kaggle dataset
  porto_places_wkt.parquet    Porto boundaries/land-use place polygons in WKT
emr/
  conf/emr_sedona_conf.json   Spark configuration for Apache Sedona
  script/emr_init_sedona.sh   Bootstrap script that installs Sedona jars and Python packages
notebook/
  00-bronze-taxi.ipynb
  01-silver-taxi.ipynb
  02-gold-taxi.ipynb
  hello.ipynb
script/
  extract_porto_portogual.sh  Extracts the Porto bounding box from a Portugal OSM PBF
  cast_porto_parquet.py       Converts OSM boundaries and land-use polygons to WKT Parquet
read.me.txt                   Original project notes
```

## Dataset

### Porto taxi trajectories

The taxi file contains 1,710,670 rows and the following relevant fields:

| Field | Description |
| --- | --- |
| `TRIP_ID` | Unique trip identifier |
| `CALL_TYPE` | How the ride was requested |
| `ORIGIN_CALL` | Customer call identifier, when applicable |
| `ORIGIN_STAND` | Taxi stand identifier, when applicable |
| `TAXI_ID` | Taxi identifier |
| `TIMESTAMP` | Unix timestamp for the trip |
| `DAY_TYPE` | Trip day category |
| `MISSING_DATA` | Whether GPS points are flagged as missing |
| `POLYLINE` | JSON-style array of `[longitude, latitude]` GPS points |

The source is the Kaggle **PKDD 15: Predict Taxi Service Trajectory** competition
dataset:

- https://www.kaggle.com/c/pkdd-15-predict-taxi-service-trajectory-i

### Porto places

Place data is derived from Portugal OpenStreetMap data:

- https://download.geofabrik.de/europe/portugal.html

The included `porto_places_wkt.parquet` file contains place names and types,
plus polygon geometries serialized in WKT. The extraction script limits OSM data
to the Porto-area bounding box:

```text
-8.75, 41.05, -8.40, 41.30
```

## Analysis performed

The notebooks include:

- Parsing raw taxi polylines into Spark arrays and route geometries.
- Removing empty, missing, invalid, and routes shorter than 10 meters.
- Simplifying route geometries with a 0.0001-degree Douglas-Peucker tolerance.
- Finding places intersected by the largest number of distinct taxi routes.
- Filtering place results by OSM place type.
- Creating an approximately 200-meter grid from route GPS points.
- Counting total GPS observations and distinct trips in each grid cell.
- Merging the routes that pass through each place.
- Aggregating the busiest place types and place names for a Gold/Athena table.

## Practical AWS setup

### 1. Create S3 buckets

Create separate locations for temporary workshop data, the data lake, and the
warehouse. The repository notebooks currently use these example bucket names:

```text
workshop-sedona-tmp
workshop-sedona-datalake
workshop-sedona-warehouse
```

Replace them with your own bucket names where noted in the notebooks if those
buckets are unavailable in your AWS account.

### 2. Upload source data

Upload the two source datasets to S3:

```bash
aws s3 cp data/porto_taxi.csv s3://workshop-sedona-tmp/data/porto/
aws s3 cp data/porto_places_wkt.parquet s3://workshop-sedona-datalake/bronze/
```

Upload the EMR configuration if you configure the cluster through AWS CLI or
CloudFormation:

```bash
aws s3 cp emr/conf/emr_sedona_conf.json s3://workshop-sedona-tmp/emr/
```

### 3. Create the EMR cluster

Configure the cluster with Apache Spark and Jupyter/Jupyter Enterprise Gateway
or JupyterHub support. The bootstrap script installs the Sedona and GeoTools
libraries and the required Python packages:

```bash
emr/script/emr_init_sedona.sh
```

The bootstrap downloads:

- Apache Sedona Spark shaded JAR `1.9.1`
- GeoTools wrapper JAR `1.9.1-33.5`
- `apache-sedona==1.9.1`
- Python packages including Pandas, GeoPandas, Shapely, KeplerGL, and Pydeck

The Spark configuration in `emr/conf/emr_sedona_conf.json` enables:

- Sedona Kryo serialization
- Sedona Spark SQL extensions
- Sedona visualization extensions
- The Sedona JARs distributed to YARN

Also verify that the EMR cluster role can read and write the configured S3
buckets, and that notebook access is authorized.

### 4. Run the notebooks

Upload or open the notebooks on the EMR/Jupyter environment. Run them in this
order:

1. `hello.ipynb` to confirm the Sedona and Spark installation.
2. `00-bronze-taxi.ipynb` to parse and clean taxi trajectories.
3. `01-silver-taxi.ipynb` to build route and place geometries.
4. `02-gold-taxi.ipynb` to calculate insights and create Gold outputs.

The notebook paths are AWS S3 paths. Update them if you use different buckets,
regions, prefixes, or database names.

## Rebuilding Porto place data locally

The place Parquet file can be regenerated from an OSM PBF export.

Install local tools for OSM extraction and the Python conversion script:

```bash
brew install osmium-tool
python3 -m pip install pandas geopandas pyrosm pyarrow
```

Download `portugal-latest.osm.pbf` from Geofabrik, then run:

```bash
./script/extract_porto_portogual.sh
cp porto.osm.pbf script/porto.osm.pbf
cd script
python3 cast_porto_parquet.py
```

The extraction command produces `porto.osm.pbf`, and the Python script produces
`porto_places_wkt.parquet` in the current directory.

## Gold/Athena configuration

The Gold notebook writes an example table with:

```text
Database: workshop-sedona
Table:    gold_top_places
Bucket:   workshop-sedona-warehouse
Location: s3://workshop-sedona-warehouse/warehouse/`workshop-sedona`/gold_top_places/
```

Create and configure the corresponding Glue database and S3 location in your AWS
account before running the final `saveAsTable` cell.

## Important notebook behavior

- The Bronze notebook removes trips whose `MISSING_DATA` value is not `False`
  and routes with fewer than two GPS points.
- The Silver notebook processes only `df_trips.limit(10000)` for route
  transformation. The 10,000-row limit is an exploration/demo setting, not a
  complete portfolio limit; remove or parameterize it for production-scale
  analysis.
- The 200-meter heatmap uses `0.002` degrees for longitude and latitude.
- The Gold notebook enables a Sedona global KDB-tree spatial index.
- The notebook that saves merged Gold routes is commented out. The heatmap and
  top-place aggregate are the enabled Gold outputs.
- The repository contains AWS-generated notebook output and sample cluster
  identifiers. Replace these environment-specific values when rerunning it.

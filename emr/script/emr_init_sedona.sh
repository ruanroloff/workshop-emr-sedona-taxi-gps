#!/bin/bash

# EMR clusters only have ephemeral local storage. It does not really matter where we store the jars.
sudo mkdir /jars

# Download Sedona jar
sudo curl -o /jars/sedona-spark-shaded-4.0_2.13-1.9.1.jar "https://repo1.maven.org/maven2/org/apache/sedona/sedona-spark-shaded-4.0_2.13/1.9.1/sedona-spark-shaded-4.0_2.13-1.9.1.jar"

# Download GeoTools jar
sudo curl -o /jars/geotools-wrapper-1.9.1-33.5.jar "https://repo1.maven.org/maven2/org/datasyslab/geotools-wrapper/1.9.1-33.5/geotools-wrapper-1.9.1-33.5.jar"

# Install necessary python libraries
sudo python3 -m pip install pandas
sudo python3 -m pip install shapely
sudo python3 -m pip install geopandas
sudo python3 -m pip install keplergl==0.3.2
sudo python3 -m pip install pydeck==0.8.0
sudo python3 -m pip install attrs matplotlib descartes apache-sedona==1.9.1
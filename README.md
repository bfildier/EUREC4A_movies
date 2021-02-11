# EUREC$^4$A/ATOMIC flight overview movies
Scripts to generate movies of GOES16 imagery with overlays of flight tracks and soundings.

![Snapshot animation](./docs/imgs/snapshot.png)

## Installation
```
# Install package requirements
pip install -r requirements.txt

# Install requirements of eurec4a-intake
pip install -r https://raw.githubusercontent.com/observingClouds/eurec4a-intake/master/requirements.txt

# Clone directory
git clone https://github.com/bfildier/EUREC4A_movies
```
## Creating the images
GOES16 satellite images are created with
```
python create_EUREC4A_movie.py -y 2020 -m 2 -d 5
```
## Creating the movie
Based on the images created above
```
python scripts/make_movie_GOES_opendap.py -d 20200205 --start_time 10:00 --stop_time 10:10
```
overlays the GOES16 images with flight trajectories and sounding trajectories.

Note: The images need to be created first and must exists for the requested time

## Configuration
The configuration of the movies/images is done by the config-yaml files in `./config/`

- Output directories and output are defined in `./config/output_user.yaml`
- Selection of channel and colormap depending on day-time can be adapted in `./config/design.yaml` by adding specific time sections:
    ```
    satellite:
      defaults:
        colormap: terrain
      timespecific:
        "00:00-10:59":
          colormap: RdBu_r
          channel: 13
          vmin: 260
          vmax: 302
        "11:00-20:59":
          colormap: RdBu_r
          channel: 2
          vmin: None
          vmax: None
        "21:00-23:59":
          colormap: RdBu_r
          channel: 13
          vmin: 260
          vmax: 302
    ``` 
  If time in not within specified time ranges, the default values are used.
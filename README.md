To generate movie with GOES image and HALO dropsondes:


# 1. Download dropsondes data on AERIS 

. use the following command

wget -r -nH --no-parent https://observations.ipsl.fr/aeris/eurec4a-data/AIRCRAFT/HALO/AVAP-DROPSONDES/2020/

# 2. Edit scripts/movie_params.py

. sondedir: path to the directory storing dropsonde data. The directory tree is the same as the AERIS system.

. goesdir: where you want to store GOES images. 

. outputdir: where you want to store your movies.

. date_str: in format 'YYYY-MM-DD'

. any other parameter you want to change.

# 3. Run python scripts/download_GOES_images.py to download images from Worldview.

# 4. Run python scripts/make_movie_GOES_dropsondes.py to generate movie.

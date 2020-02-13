To generate movie with GOES image and HALO dropsondes:

1. Edit scripts/movie_params.py

. sondedir: path to the directory storing dropsonde data. The directory tree is the same as the NAS system used in the ops center during the campaign.

. goesdir: where you want to store GOES images. 

. outputdir: where you want to store your movies.

. date_str: in format 'YYYY-MM-DD'

. any other parameter you want to change.

2. Run python scripts/download_GOES_images.py to download images from Worldview.
3. Run python scripts/make_movie_GOES_dropsondes.py to generate movie.

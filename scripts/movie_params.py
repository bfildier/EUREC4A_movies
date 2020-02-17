import numpy as np
import matplotlib.pyplot as plt

# GOES variable
goes_varid = 'GOES-East_ABI_Band2_Red_Visible_1km'

# I/O directories
sondedir="/run/media/ludo/DATA/google-drive/Thèse/EUREC4a/Data/aeris/eurec4a-data/AIRCRAFT/HALO/AVAP-DROPSONDES/2020"
#'/Users/bfildier/Data/EUREC4A/Measurements/HALO'
goesdir ='/run/media/ludo/DATA/google-drive/Thèse/EUREC4a/github/EUREC4A_movies/images/GOES'
outputdir ='/run/media/ludo/DATA/google-drive/Thèse/EUREC4a/github/EUREC4A_movies/movies'

# aircraft altitude
altmax = 11000 # (m)

# HALO circle
lon_center, lat_center = -57.717,13.3
lon_pt_circle, lat_pt_circle = -57.245,14.1903
r_circle = np.sqrt((lon_pt_circle-lon_center)**2+(lat_pt_circle-lat_center)**2)

# Image box
lonmin,lonmax = -60,-55
dlon = lonmin-lonmax
latmin,latmax = 11.5,15
dlat = latmin-latmax
width = 1125
height = int(width*dlat/dlon)

# time range
date_str = "2020-01-24"
start_time = "10:00"
end_time = "22:00"

# movie format
dpi = 150
asp_ratio = dlat/dlon
w_inches = 10
h_inches = w_inches*asp_ratio
# how many times real speed is increased 
# (600 is about 2 dropsondes appearing per second in the movie)
speed_factor = 600 
delta_t = 60 # time increment to update frames, in s

# fading of dropsonde display
dt_fade = 40 # (mn)

# color choice
cmap = plt.cm.terrain
col_top = 'w'
col_bottom = cmap(0)

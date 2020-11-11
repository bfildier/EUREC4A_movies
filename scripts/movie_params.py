import numpy as np
import matplotlib.pyplot as plt
import getpass

# I/O directories
if getpass.getuser() == "bfildier":
  sondedir='/Users/bfildier/Data/EUREC4A/merged/sondes/'
  goesdir='/Users/bfildier/Code/analyses/EUREC4A/EUREC4A_movies/images/GOES16'
  platformdir='/Users/bfildier/Data/EUREC4A/tracks/'
  outputdir='/Users/bfildier/Code/analyses/EUREC4A/EUREC4A_movies/movies/'
elif getpass.getuser() == "ludo":
  sondedir="/media/ludo/DATA/google-drive/Thèse/EUREC4a/github/Input/Products/"
  goesdir ='../images/ciclad'
  platformdir = "/media/ludo/DATA/google-drive/Thèse/EUREC4a/github/Input/"
  outputdir ='../movies/'
  outputdir_images = '../images/ciclad'
else:
  sondedir = '../data/dropsondes'
  platformdir = '../data/tracks'
  goesdir = '/scratch/local1/m300408/GOES16animation/images'
  image_file_fmt = 'GOES16__{channel}__%Y%m%d_%H%M.png'
  outputdir = '../movies'
  pass # ADD YOUR DIRECTORIES HERE


# HALO aircraft altitude
altmax = 11000 # (m)

# HALO circle
lon_center, lat_center = -57.717,13.3
lon_pt_circle, lat_pt_circle = -57.245,14.1903
r_circle = np.sqrt((lon_pt_circle-lon_center)**2+(lat_pt_circle-lat_center)**2)

# GOES16 data
GOES16_var_night = 'C13'  # channel variable to use during nighttime (e.g. C13, temp_11_0um_nom)
GOES16_var_day = 'C13'   # channel variable to use during daytime (e.g. C02, refl_0_65um_nom)

# Image box
lonmin,lonmax = -60,-55
dlon = lonmin-lonmax
latmin,latmax = 11.5,15
dlat = latmin-latmax
width = 1125
height = int(width*dlat/dlon)

# time range
start_time = "10:30"
end_time = "21:30"

# start_time = "00:00"
# end_time = "23:59"

# platforms to show (if any)
platform_names = ['ATR','HALO']
track_colors = ['palegoldenrod','palegreen']
platform_colors = ['goldenrod','green']
draw_circle = 'HALO' not in platform_names # shown HALO circle iff HALO track is not shown

# movie format
dpi = 150
asp_ratio = dlat/dlon
w_inches = 10
h_inches = w_inches*asp_ratio
# how many times real speed is increased 
# (600 is about 2 dropsondes appearing per movie second)
speed_factor = 600 
delta_t = 60 # time increment to update frames, in s

# fading of dropsonde display
dt_fade = 40 # (mn real clock)

# color choice
cmap = plt.cm.terrain
col_top = 'w'
col_bottom = cmap(0)
# col_bottom = 'b'

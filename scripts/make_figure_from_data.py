from netCDF4 import Dataset
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
import glob, os
import matplotlib.ticker as ticker
import argparse

def get_files(year=2020, month=2, day=5):
    
    str_month="{0:0=2d}".format(month)
    str_day="{0:0=2d}".format(day)
    str_day=str(year)+"_"+str_month+"_"+str_day
    list_files=[]
    path = "../satellite_data/ciclad/"
    path_dir = os.path.join(path, str_day)
                            
    with os.scandir(path_dir) as entries:
        for entry in entries:
            if entry.is_file():
                path_file = os.path.join(path_dir, entry.name)
                list_files.append(path_file)
    
    return list_files

def make_figure(path_file):
    
    # path = os.path.join(path_dir,"clavrx_goes16_2020_022_2348_BARBADOS-2KM-FD.level2.nc")
    file = xr.open_dataset(path_file)
    file = file.where(file.scan_lines_along_track_direction < 498, drop=True)

    if(file.START_TIME < 11 or file.START_TIME > 21):
        colormap="Greys"
        channel = "temp_11_0um_nom"
    else:
        colormap="Greys_r"
        channel = "refl_0_65um_nom"
    
    
    fig, ax = plt.subplots(1, 1)

    fig.subplots_adjust(left=0, bottom=0, right=1, top=1, wspace=None, hspace=None)

   
    # ax.pcolormesh((file["refl_2_10um_nom"].values)**(1/6), cmap=colormap)
    alpha=1/6
    ax.pcolormesh(file["longitude"],file["latitude"],(file[channel].values)**(alpha), cmap=colormap)
    ax.set_xlim([-60,-55])
    ax.set_ylim([11.5, 15])
    ax.axis('off')
    
    str_day = os.path.split(os.path.split(path_file)[0])[1]
    output_dir = os.path.join("../images/ciclad", str_day)
    os.makedirs(output_dir, exist_ok=True)    
    
    output_file = os.path.split(path_file)[1]
    output_file = os.path.splitext(output_file)[0]+'.jpg'
    output_file = output_file.replace("_BARBADOS-2KM-FD.level2", "")    
    output_file = os.path.join(output_dir, output_file)
    
    fig.savefig(output_file)
    
    plt.close(fig)

       
if __name__ == "__main__":
    
    # Specified beforehand
    from movie_params import *

    # Arguments to be used if want to change options while executing script
    parser = argparse.ArgumentParser(description="Transform ciclad .nc data into satellite images")
    parser.add_argument("-y","--year", default=2020,help="Year, YYYY")
    parser.add_argument("-m","--month", default=2, help="Month, M")
    parser.add_argument("-d","--day", default=5, help="Day, D")
    args = parser.parse_args()
    year = args.year
    month = args.month
    day = args.day
    
    files = get_files(year, month, day)
    for file in files:
        make_figure(file)

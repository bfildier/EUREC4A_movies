# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""

# load modules
import numpy as np
import xarray as xr
import os,sys,glob
from datetime import datetime,timedelta
import pandas as pd
import argparse

#%% Main script

if __name__ == "__main__":

#%% 
    
    # Specified beforehand
    from movie_params import *
    
    # Command-line arguments 
    parser = argparse.ArgumentParser(description="Show common dates to all platforms")
    parser.add_argument("-p","--platforms", nargs='+',help="Sequence of platform names")
    args = parser.parse_args()
    
    # get measurement dates for all platforms
    dates_all = []
    for platform in args.platforms:
        
        print('get %s dates'%platform)
        
        # load
        filename = 'EUREC4A_%s_Track_v1.1.nc'%platform
        track = xr.open_dataset(os.path.join(platformdir,filename))
        # get dates
        dates = [pd.to_datetime(str(track.time.values[i])).strftime('%Y-%m-%d') for i in range(track.time.size)]
        # remove duplicates
        dates = list(set(dates))
        # save
        dates_all.append(dates)
    
    # get intersection
    dates_intersect = set(dates_all[0])
    for i in range(1,len(dates_all)):
        dates_intersect = dates_intersect.intersection(set(dates_all[i]))
    
    # sort dates
    dates_intersect = list(dates_intersect)   
    dates_intersect.sort()
    
    # show
    print(dates_intersect)
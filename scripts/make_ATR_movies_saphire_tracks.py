#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Oct 22 10:55:23 2021

@author: bfildier

Generate movies for the ATR flights + dropsondes, zooming on the ATR+HALO circle area. 
Flights with segments after 23:59 UTC are extended to the next day to have 1 movie per flight.
Tracks are retrieved from the Saphire track files.

Select the design_ATR.yml config file as design.yml for the correct movie setup.
"""

import os,glob
import xarray as xr

load_images=False
create_movies=True

workdir = os.path.dirname(os.path.realpath(__file__))
# workdir = '/Users/bfildier/Code/analyses/EUREC4A/EUREC4A_movies/scripts'
repodir = os.path.dirname(workdir)
trackdir = os.path.join(repodir,'input/EUREC4A_Core_1Hz_v2')
track_files = glob.glob(os.path.join(trackdir,'*.nc'))
track_files.sort()

def getFlightName(track_file):
    
    flight_number = track_file[-11:-9]
    flight_name = 'RF%s'%flight_number
    
    return flight_name

def getTimeBounds(track):
    
    start_date = str(track.time.values[0])[:10].replace('-','')
    start_time = str(track.time.values[0])[11:16]
    stop_date = str(track.time.values[-1])[:10].replace('-','')
    stop_time = str(track.time.values[-1])[11:16]

    return start_date, start_time, stop_date, stop_time


for track_file in track_files:
    
    if '12_L2' not in track_file:
        continue
 
    filename = track_file.split('/')[-1]
    track = xr.open_dataset(track_file)
    
    flight_name = getFlightName(filename)
    time_bounds = start_date, start_time, stop_date, stop_time = getTimeBounds(track)
    
    print()
    print('--- Flight %s ---'%flight_name)
    print()
    print('From %s @ %s'%time_bounds[:2])
    print('to %s @ %s'%time_bounds[2:])
    print()

    if load_images:
        print(' - Load images for ATR region for flight %s'%flight_name)
        print()
        if stop_date == start_date:        
            os.system('python ./scripts/make_images_opendap.py -d %s --start_time %s --stop_time %s'%(start_date,start_time,stop_time))
        else:
            os.system('python ./scripts/make_images_opendap.py -d %s --start_time %s --stop_time %s'%(start_date,start_time,'23:59'))
            os.system('python ./scripts/make_images_opendap.py -d %s --start_time %s --stop_time %s'%(stop_date,'00:00',stop_time))
        print()
    if create_movies:
        print('- Create ATR movie for flight %s'%flight_name)
        print()
        os.system('python ./scripts/make_movie_opendap.py -d %s --stop_date %s --start_time %s --stop_time %s -l %s -t %s'%(start_date,stop_date,start_time,stop_time,flight_name,track_file))
        print()

print('All done my friend.')

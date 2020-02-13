# by Ludovic Touze-Peiffer
# thanks to Hauke Schulz for showing his initial method

import urllib.request
import datetime
from calendar import monthrange
import os
import argparse

if __name__ == "__main__":

    ##-- import movie parameters

    from movie_params import *

    ##-- load arguments if present

    # Arguments to be used if want to change options while executing script
    parser = argparse.ArgumentParser(description="Downloads GOES images for movie")
    parser.add_argument("--date", type=str, default=date_str,help="Flight date, YYY-MM-DD")
    parser.add_argument("--goes_varid",type=str,default=goes_varid,
        help='GOES variable ID')
    args = parser.parse_args()

    # Define ouput path
    path_dir = os.path.join(goesdir,"%s/%s"%(args.goes_varid,args.date))
    os.makedirs(path_dir,exist_ok=True)

    # Define dates
    start_date = datetime.datetime.strptime(args.date+start_time,"%Y-%m-%d%H:%M")
    end_date = datetime.datetime.strptime(args.date+end_time,"%Y-%m-%d%H:%M")
    delta = datetime.timedelta(minutes=10)
    
    # Loop over all times
    while start_date <= end_date:

        str_date = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        lon_lat = str(latmin)+','+str(lonmin)+ ',' + str(latmax)+','+str(lonmax)
        
        # define download url
        url = ('https://wvs.earthdata.nasa.gov/api/v1/snapshot?'+
        'REQUEST=GetSnapshot&TIME='+
        str_date+
        '&BBOX='+
        lon_lat+
        '&CRS=EPSG:4326&LAYERS='+
        args.goes_varid+
        ','+
        'Reference_Labels,Reference_Features&WRAP=x,x,x&FORMAT=image/jpeg&WIDTH='+
        str(width)+
        '&HEIGHT='+
        str(height)+
        '&ts=1580766913339')

        # save
        save_str = os.path.join(path_dir,'%s.jpg'%str_date)
        urllib.request.urlretrieve(url, save_str)
        
        # increment
        start_date += delta
    

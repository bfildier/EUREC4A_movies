#!/bin/bash

# by Ludovic Touze-Peiffer


daylist=(20200202)
wdir=${PWD%/*}
len=${#daylist[@]} ## Use bash for loop
start_day=16
end_day=21
mod_min=10

for (( iday=0; iday<$len; iday++)); do

	day="${daylist[iday]}" 
	echo ${day}

#Download GOES data in netcdf format

#Download IR pictures during the night
	channel=13
	odir=$wdir/satellite_data/GOES16/$day/channel$channel
	mkdir -p $odir
	for (( hour=0; hour<$start_day; hour++)); do		
		python download_GOES16.py -d $day -k $channel -o ${odir}/GOES16_{channel}_{N1}N-{N2}N_{E1}E-{E2}E_%Y%m%d_%H%M.nc -t $hour $mod_min
	done


#Download IR pictures during the day
	channel=02
	odir=$wdir/satellite_data/GOES16/$day/channel$channel
	mkdir -p $odir
	for (( hour=$start_day; hour<$end_day; hour++)); do		
		python download_GOES16.py -d $day -k $channel -o ${odir}/GOES16_{channel}_{N1}N-{N2}N_{E1}E-{E2}E_%Y%m%d_%H%M.nc -t $hour $mod_min
	done
	

#Download IR pictures during the night
	channel=13
	odir=$wdir/satellite_data/GOES16/$day/channel$channel
	for (( hour=$end_day; hour<24; hour++)); do	
		python download_GOES16.py -d $day -k $channel -o ${odir}/GOES16_{channel}_{N1}N-{N2}N_{E1}E-{E2}E_%Y%m%d_%H%M.nc -t $hour $mod_min
	done

#Make figures from GOES data

	python make_figure_from_data.py -d $day	
	
#Make movie

	python make_movie_GOES_all_sondes.py --date=${day} 

done

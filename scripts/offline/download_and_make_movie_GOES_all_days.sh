#!/bin/bash

# by Ludovic Touze-Peiffer


#daylist=(20200115)
#daylist=(20200117)
#daylist=(20200203)
#daylist=(20200124)

#daylist=(20200119 20200120 20200121 20200122 20200123 20200124 20200125 20200126 20200127 20200128 20200129 20200130 20200131 20200201 20200202 20200203 20200204 20200205 20200206 20200207 20200208 20200209 20200210 20200211 20200212 20200213 20200214 20200215 20200216 20200217 20200218 20200219 20200220)
#daylist=(20200119 20200122 20200123 20200124 20200126 20200128 20200130 20200131 20200202 20200203 20200204 20200205 20200207 20200209 20200210 20200211 20200213 20200215)
#daylist=(20200202)
daylist=(20200205)
wdir=${PWD%/*}
len=${#daylist[@]} ## Use bash for loop
#start_day=1
#end_day=1
#mod_min=60
#len=1

for (( iday=0; iday<$len; iday++)); do

	day="${daylist[iday]}" 
	echo ${day}

##Download GOES data in netcdf format
#
##Download IR pictures during the night
	#channel=13
	#odir=$wdir/satellite_data/GOES16/$day/channel$channel
	#mkdir -p $odir
	#for (( hour=0; hour<$start_day; hour++)); do		
	#	python download_GOES16.py -d $day -k $channel -o ${odir}/GOES16_{channel}_{N1}N-{N2}N_{E1}E-{E2}E_%Y%m%d_%H%M.nc -t $hour $mod_min
	#done


#Download VIS pictures during the day
	#channel=02
	#odir=$wdir/satellite_data/GOES16/$day/channel$channel
	#mkdir -p $odir
	#for (( hour=$start_day; hour<$end_day; hour++)); do		
	#	python download_GOES16.py -d $day -k $channel -o ${odir}/GOES16_{channel}_{N1}N-{N2}N_{E1}E-{E2}E_%Y%m%d_%H%M.nc -t $hour $mod_min
	#done
	#

#Downloa##d IR pictures during the night
	#channel=13
	#odir=$wdir/satellite_data/GOES16/$day/channel$channel
	#for (( hour=$end_day; hour<24; hour++)); do	
	#	python download_GOES16.py -d $day -k $channel -o ${odir}/GOES16_{channel}_{N1}N-{N2}N_{E1}E-{E2}E_%Y%m%d_%H%M.nc -t $hour $mod_min
	#done

#Make figures from GOES data

#	python make_figure_from_data.py -d $day	
	
#Make movie

	python make_movie_GOES.py --date=${day} 

done

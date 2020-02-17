#!/bin/bash

# by Ludovic Touze-Peiffer


daylist=(2020-01-22 2020-01-24 2020-01-26 2020-01-28 2020-01-30 2020-01-31 2020-02-02 2020-02-05 2020-02-07 2020-02-09 2020-02-11 2020-02-13)

wdir=${PWD%/*}
satellite=GOES-East_ABI_Band2_Red_Visible_1km
idir=${wdir}/images/GOES/$satellite
odir=${wdir}/movies/$satellite


#download GOES images
for iday in {0..11} ; do

	day="${daylist[iday]}" 
	echo ${day}
	idir_day=${idir}/${day}
	
	#Download GOES image
	if [ -z "$(ls -A ${idir_day})" ]; then
		python download_GOES_images.py --date=${day} 
	else
		echo $idir_day" already exists"
	fi
	
	#Make movie
	if [ -z "$(ls -A ${odir}/*${day}*)" ]; then
		python make_movie_GOES_dropsondes.py --date=${day} 
	else
		echo "movie "${idir_day}" already exists"
	fi

done

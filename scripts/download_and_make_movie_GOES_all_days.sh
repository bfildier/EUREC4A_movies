#!/bin/bash

# by Ben Fildier and Ludovic Touze-Peiffer
# Uses radiative transfer code by Robert Pincus to calculate
# radiative profiles from HALO dropsonde data


daylist=(2020-01-19 2020-01-24 2020-01-26 2020-01-28 2020-01-30 2020-01-31 2020-02-02 2020-02-05 2020-02-07 2020-02-09 2020-02-11 2020-02-13)

wdir=${PWD%/*}
satellite=GOES-East_ABI_Band2_Red_Visible_1km
idir=${wdir}/images/GOES/$satellite
odir=${wdir}/movies/$satellite


#download GOES images
for iday in {0..12} ; do

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

#make movie


#	cd $sdir
#
#	for ifile in `ls ${idir_day}/*PQC.nc ${idir_day}/processed/*PQC.nc`; do 
#
#		filename=${ifile##*\/}	
#		echo ${filename}
#		echo 'Combining sonde with background '$ifile
#		mkdir -p ${odir_day}
#
#		python combine_reference_and_sonde_profiles.py --sonde_file=${ifile} --out_dir=${odir_day} 
#
#		echo " "	
#	done
#
#	for ofile in `ls ${odir_day}/*.nc`; do
#		echo 'Compute radiation profile '$ofile
#		${cdir}/sonde_radiation $ofile
#		echo " "
#	done	


#ulimit -s unlimited
#sonde_path=${1%\/*}
#sonde_filename=${1##*\/}
#echo 'processing sonde '$sonde_filename
#rad_filename=${sonde_filename%*.nc}'_rad.nc'
#
## Merge dropsonde profiles with standard atmosphere profiles
#echo 'merging sounding and reference profiles in new file '$rad_filename
#
## Compute radiative profles
#echo "compute radiative profiles and append them to ${rad_filename}" 
#../code/sonde_radiation ${rad_filename}
#
##echo "move ${rad_filename} to ${sonde_path}"
#mv ${rad_filename} ${sonde_path}/

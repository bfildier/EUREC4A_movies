""" Download GOES16 raw data
regrid it to equidistant lat/lon grid
and crop to specific region.

Raw data is only temporarily stored.

USAGE EXAMPLE:
python download_GOES16.py -k 13 -r 10 30 -64 -20 -d 20190519
"""

import os
import sys
import os.path
import numpy as np
import time
import argparse
import subprocess
import configparser
from configparser import ExtendedInterpolation
import datetime
from datetime import datetime as dt
import tempfile
import glob
import gcsfs
from tqdm import tqdm
import requests
import satpy
import pyresample
from satpy import Scene
from pyresample.geometry import AreaDefinition
import xarray as xr
import pandas as pd
import gc
import logging
from movie_params import *

global verbose


# ====================================================
# General MPI-BCO settings:
# ====================================================
def load_configuration(configuration_file=None):
    """
    Loads the configuration file PATH.ini.
    1. If provided load configuration_file
    2. Attempt to load from home directory
    3. Attempt to load from relative path inside BCO-git structure

    Args:
        configuration_file: optional: complete path to the configuration file.

    Returns:
        instance of ConfigParser class with extended interpolation.
    """
    dir_path = os.path.dirname(os.path.realpath(__file__))
    if not isinstance(configuration_file, str):
        if os.path.isfile(os.getenv("HOME") + "/PATH.ini"):
            configuration_file = os.getenv("HOME") + "/PATH.ini"

        if not os.path.isfile(configuration_file):
            raise FileNotFoundError(
                "No Configuration File 'PATH.ini' found. Please create one in your home directory "
                "or provide the path via the argument parsing -c.")
        else:
            logging.info("Using configuration file: %s" % configuration_file)

    config = configparser.ConfigParser(interpolation=ExtendedInterpolation())
    config.read(configuration_file)
    return config


def get_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-c', '--configfile', metavar="PATH.ini", help='Provide a PATH.ini configuration file. \n'
                                                                       'If not provided it will be searched for at:\n'
                                                                       '1. ~/PATH.ini\n'
                                                                       '2. ../../../PATH.ini', required=False)
    parser.add_argument('-o', '--outputfile', metavar="/path/to/outputfile_{channel}_%Y%m%d_%H%M.nc",
                        required=False, help='Provide filename of output. If several timestamps are selected, it is'
                                             'recommended to provide a filename format, otherwise the file is over'
                                             'written each time. Valid formaters are %%Y, %%m, %%d, {N1}, {N2}, {E1},'
                                             '{E2}, {channel}.')

    parser.add_argument('-z', '--compression', metavar="COMPRESSION_LEVEL",
                        help="Set the Level of compression for the output (1-9)",
                        required=False, default=8, type=int)

    parser.add_argument('-d', '--date', metavar="YYYYMMDD", help='Provide the desired date or date range to be processed. '
                                                                 'Format: YYYYMMDD or YYYYMMDD-YYYYMMDD',
                        required=True, default=None)

    parser.add_argument('-r', '--region', nargs='+', metavar="lat0 lat1 lon0 lon1",
                        help='Provide the region for the output', required=False,
                       default=[latmin,latmax,lonmin,lonmax])

    parser.add_argument('-k', '--channel', metavar="1..16", help='Provide the channel of the ABI',
                        required=True)

    parser.add_argument('-p', '--product', metavar="ABI-L2-AODF", help='Product of GOES16',
                        required=False, default='ABI-L1b-RadF')

    parser.add_argument('-t', '--timesteps', metavar='12 60', help='Provide mod_hour and mod_minute who restrict the '
                                                                    'files to be downloaded in time. (0 0) for latest image', required=False,
                        default=[1,10], nargs=2, type=int)

    parser.add_argument('-g', '--googletoken', metavar="token", help='In case the download does not work for anonymous'
                                                                      'provide a token or path to a google credential'
                                                                      'file, see https://gcsfs.readthedocs.io/en/latest/'
                                                                      'index.html#credentials. The JSON file created by'
                                                                      'gsutil (has to be installed separatly) at ~/.con'
                                                                      'fig/gcloud/legacy_credentials/$USER/adc.json has'
                                                                      'been tested successfully.'
                                                                      'In order to get this file the command `gcloud '
                                                                      'auth login` might need to be executed.',
                        required=False, default='anon')

    parser.add_argument('-v', '--verbose', metavar="DEBUG", help='Set the level of verbosity [DEBUG, INFO, WARNING, ERROR]',
                        required=False, default="INFO")

    args = vars(parser.parse_args())

    return args


def setup_logging(verbose):
    assert verbose in ["DEBUG", "INFO", "WARNING", "ERROR"]
    logging.basicConfig(
        level=logging.getLevelName(verbose),
        format="%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s",
        handlers=[
            logging.FileHandler(f"{__file__}.log"),
            logging.StreamHandler()
        ])


def get_tmp_dir():
    """
    Creates a temporary folder at the systems default location for temporary files.

    Returns:
        Sets Class variables:
        - self.tmpdir_obj: tempfile.TemporaryDirectory
        - self.tmpdir: string containing the path to the folder
    """
    tmpdir_obj = tempfile.TemporaryDirectory()
    tmpdir = tmpdir_obj.name
    print(tmpdir)
    return tmpdir, tmpdir_obj


def find_remote_files(product, date, channel, fs):
    """
    Find satellite files on the remote server,
    that fit the requirements set by user e.g.
    channel, date, product

    Returns
    -------
    files : list
        List of remote file addresses
    """
    if 'L1' in product:
        files = [fs.glob('gcp-public-data-goes-16/' + product + '/' + str(date.year) + '/' +
                         '{0:03g}'.format(int(date.strftime('%j'))) + '/*/*M[36]C' + str(channel) + '*.nc')]
    elif 'L2' in product:
        files = [fs.glob('gcp-public-data-goes-16/' + product + '/' + str(date.year) + '/' +
                         '{0:03g}'.format(int(date.strftime('%j'))) + '/*/*' + str(product) + '*M[36]' + '*.nc')]

    files = [y for x in files for y in x]

    return files


def filter_filelist(files: list, hour_mod: int = 12, min_mod: int = 60) -> list:
    """
    Filter filelist of remote filenames
    by temporal resolution.
    This reduces the number of filenames
    depending on the resolution requested.

    Input
    -----
    files : list
        List of file download addresses

    hour_mod : int
        Restricting the hours that are downloaded
        by the calculation hour % hour_mod == 0.
        E.g. if hour_mod == 3: 0,3,6,...21 UTC are
        downloaded. If hour_mod == 12: 0, 12 UTC
        are downloaded.

    min_mod : int
        Same as hour_mod, but for minutes.
        Set it to 1 to download all available minutes
        within the hours selected by hour_mod.
        Set it to 60 to only download HH:00 UTC.

    Returns
    -------
    files : list
        List of remote file addresses
    """
    files_restricted = []
    if hour_mod == 0 and min_mod == 0:
        files_restricted.append(sorted(files)[-1])
    else:
        for file in files:
            hour = int(file.split("_")[3][8:10])
            minute = int(file.split("_")[3][10:12])
            if hour == hour_mod and minute % min_mod == 0:
                files_restricted.append(file)
                logging.debug(f'Remote file added: {file}')
            else:
                logging.debug(f'Remote file ignored: {file}')
    logging.info('Files to be downloaded has been reduced from {} to {}'.format(len(files), len(files_restricted)))
    return files_restricted


def download_remote_files(output_dir, files):
    """
    Download remote satellite files
    """
    logging.debug(f"Try to download files: {files}")

    for file in tqdm(files):
        file_local = file.split("/")[-1]
        file_local = output_dir + file_local

        if os.path.isfile(file_local):
            logging.info("Raw file {} exists locally".format(file_local))
            continue
        else:
            # Download file

            url = "https://storage.googleapis.com/" + file
            remote_file = requests.get(url)
            open(file_local, 'wb').write(remote_file.content)


def define_output_area(lat0, lon0, lat1, lon1):
    """
    Create area object with the area and projection
    of interest.

    Input
    -----
    lat0, lon0, lat1, lon1 : float
        Extent of area of interest.
        This area defines the output.

    Note
    ----
    The resolution is currently fixed to about
    1 km. The factor 1/110 has to be adapted otherwise.
    """
    area_out = AreaDefinition.from_extent(area_id='EUREC4A_Upstream',
                                          projection={'a': '6378144.0', 'b': '6356759.0',
                                                      'lat_0': '0.00', 'lat_ts': '50.00',
                                                      'lon_0': '-60.00', 'proj': 'eqc'},
                                          shape=[np.abs(lon1 - lon0) / (1 / 110), np.abs(lat1 - lat0) / (1 / 110)],
                                          area_extent=[lon0, lat0, lon1, lat1], units='deg')
    return area_out


def write_netcdf(resampled_data, lons, lats, original_filename, channel, outputfile, netcdf_attrs, compression):
    time = resampled_data.attrs['start_time']
    var_attrs = resampled_data.attrs
    import copy
    attrs_ = copy.copy(var_attrs)
    for key, value in attrs_.items():
        if value is None or type(value) != 'str':
            del var_attrs[key]

    goes16_sat_xr = xr.Dataset()

    goes16_sat_xr[channel] = xr.DataArray(resampled_data.values[None, :, :], dims=['time', 'lat', 'lon'])
    goes16_sat_xr[channel].encoding = {"zlib": True, "complevel": compression, "_FillValue": np.nan}
    goes16_sat_xr[channel].attrs = var_attrs

    goes16_sat_xr['lat'] = lats[:, 0]
    goes16_sat_xr['lat'].attrs['standard_name'] = 'latitude'
    goes16_sat_xr['lat'].attrs['units'] = 'degree_north'
    goes16_sat_xr['lon'] = lons[0, :]
    goes16_sat_xr['lon'].attrs['standard_name'] = 'longitude'
    goes16_sat_xr['lon'].attrs['units'] = 'degree_east'

    goes16_sat_xr['time'] = [time.replace(tzinfo=datetime.timezone.utc).timestamp()]
    goes16_sat_xr['time'].attrs["standard_name"] = "time"
    goes16_sat_xr['time'].attrs["units"] = "seconds since 1970-1-1 0:00:00 UTC"
    goes16_sat_xr['time'].attrs["axis"] = "T"
    goes16_sat_xr['time'].attrs["calendar"] = "gregorian"

    goes16_sat_xr.attrs = netcdf_attrs
    goes16_sat_xr.attrs['source'] = original_filename

    outputfile = dt.strftime(time, outputfile)

    goes16_sat_xr.to_netcdf(outputfile, unlimited_dims={'time':True})

def check_numpy_compatibility():
    """
    With numpy version 1.16.3 and higher,
    pickle objects are not allowed to be
    loaded at default.
    This causes an issue with the current version
    of satpy using caches during resample.
    An issue is posted at
    https://github.com/pytroll/satpy/issues/785.

    Note: remove this check if the issue is
    solved! The cache increases the speed.

    Returns
    -------
    boolean
        False: not compatible;
        True: probably compatible;
    """
    def get_digits(string):
        """
        Returns digits of string
        by removing all other characters
        """
        digit_str= ''.join(filter(lambda x: x.isdigit(), string))
        return digit_str

    main, sub, patch = np.__version__.split('.')
    main = int(get_digits(main))*1000
    sub = int(get_digits(sub))*10
    patch = int(get_digits(patch))
    logging.info(f'Version number of numpy is {main+sub+patch}')
    if main+sub+patch >= 1163: # 1.16.3 --> 1000+160+3
        return False
    else:
        return True


def date_input2dates(date_str):
    if len(date_str) == 8:
        # single date
        date_obj = dt.strptime(date_str, "%Y%m%d")
        return date_obj
    elif len(date_str) == 17:
        # date range
        start_date_str, stop_date_str = date_str.split('-')
        f = lambda s: dt.strptime(s, "%Y%m%d")
        start_date_obj = f(start_date_str)
        stop_date_obj = f(stop_date_str)
        dates = pd.date_range(start_date_obj, stop_date_obj, freq='D')
        return dates
    else:
        raise ValueError


def main():
    args = get_args()

    product = args['product']
    if 'L2' in product:
        reader = 'abi_l2_nc'
        channel = args['channel']
    elif 'L1' in product:
        reader = 'abi_l1b'
        channel = args["channel"]

    date_str = args["date"]
    dates = date_input2dates(date_str)

    verbose = args["verbose"]
    region = args["region"]
    token = args["googletoken"]
    setup_logging(verbose)
    setup_logging(verbose)
    logging.info("Set up logging.")

    if args["outputfile"] is not None:
        outputfile = args["outputfile"]
    else:
        config = load_configuration(args["configfile"])
        logging.info('Using outputfile and path defined in config')
        outputfile = config["DOWNLOAD_GOES16"]["OUTPUT_FILE"]

    outputfile = outputfile.replace('{N1}',str(region[0]))
    outputfile = outputfile.replace('{N2}',str(region[1]))
    outputfile = outputfile.replace('{E1}',str(region[2]))
    outputfile = outputfile.replace('{E2}',str(region[3]))
    outputfile = outputfile.replace('{channel}', args["channel"])

    output_path = os.path.dirname(outputfile)
    if not os.path.isdir(output_path):
        logging.info(f"Directory {output_path} does not exist, needs to be created:")
        os.makedirs(output_path)
    else:
        logging.info(f"Directory {output_path} already exists!")

    try:
        git_module_version = subprocess.check_output(["git", "describe"]).strip().decode()
    except:
        logging.warning("Could not find git hash.", exc_info=True)
        git_module_version = "--"

    tmpdir, tmpdir_obj = get_tmp_dir()

    try:
        fs = gcsfs.GCSFileSystem(project='gcp-public-data-goes-16/' + product + '/', token=token)
    except:
        logging.error('Connection not successful', exc_info=True)


    logging.info('Start downloading raw data to temporary directory {}'.format(tmpdir))
    if isinstance(dates, datetime.date):
        files_2_download = find_remote_files(product, dates, channel, fs)
    elif isinstance(dates, pd.DatetimeIndex):
        files_2_download = []
        for date in dates:
            files_2_download.extend(find_remote_files(product, date, channel, fs))
    if args['timesteps'] is not None:
        mod_hour, mod_minute = args['timesteps']
        files_2_download = filter_filelist(files_2_download, mod_hour, mod_minute)

    download_remote_files(tmpdir + '/', files_2_download)

    logging.info('Start regridding and cropping data')

    netcdf_attrs = dict(title='Geostationary satellite imagery from GOES16 on regular grid',
                        description='GOES16 satellite data regridded on a regular '
                                    'grid',
                        converted_by='Hauke Schulz (hauke.schulz@mpimet.mpg.de)',
                        institution='Max Planck Institute for Meteorology, Hamburg, Germany',
                        Conventions='CF-1.7',
                        python_version="{} (with pyresample version: {}; satpy: {})".format(sys.version,
                                                                                            pyresample.__version__,
                                                                                            satpy.__version__),
                        creation_date=time.asctime(),
                        created_with=os.path.basename(__file__) + " with its last modification on " +
                                     time.ctime(os.path.getmtime(os.path.realpath(__file__))),
                        version=git_module_version)

    lat_min, lat_max, lon_min, lon_max = np.array(args['region'], dtype='float')

    if 'L1' in product:
        channel = "C{0:0>2}".format(args['channel'])
    elif 'L2' in product:
        pass

    files_local = sorted(glob.glob(tmpdir + '/*'))

    logging.info('Local files: {}'.format(files_local))
    area_out = define_output_area(lat_min, lon_min, lat_max, lon_max)
    lons, lats = area_out.get_lonlats()
    for f_i, f in tqdm(enumerate(files_local)):
        logging.info('Loading scene')
        input_sat_scene = Scene(reader=reader, filenames=[f])
        input_sat_scene.load([channel])
        logging.info('Resampling scene')
        if check_numpy_compatibility():
            output_region_scene = input_sat_scene.resample(area_out, cache_dir='./')
        else:
            output_region_scene = input_sat_scene.resample(area_out)
        resampled_data = output_region_scene.datasets[channel]
        logging.info('Write output to netcdf')
        write_netcdf(resampled_data, lons, lats, files_2_download[f_i], channel, outputfile, netcdf_attrs, args["compression"])
        input_sat_scene.unload()
        output_region_scene.unload()
        del input_sat_scene
        del output_region_scene
        del resampled_data
        gc.collect()

    tmpdir_obj.cleanup()

if __name__ == '__main__':
    main()

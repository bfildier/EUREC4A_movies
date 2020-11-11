import glob, os
import datetime as dt
import argparse
import tqdm
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr


def get_files(year=2020, month=2, day=5, input_file_fmt=None):
    date = dt.datetime(year, month, day)
    files = sorted(glob.glob(date.strftime(input_file_fmt)))
    
    return files

def make_figure(path_file, source='ciclad'):
    """
    Create images from datafiles

    Converts the satellite data (netcdf) to images
    that are used as a basis for the movies or could
    be used as still images.

    :param path_file: source file containing satellite data
    :param source: type of source to use: ciclad (default), local
    :return:
    """
    assert source in ['ciclad', 'local'], 'Source unknown, please choose between ciclad, local'
    if source == 'ciclad':
    
        # path = os.path.join(path_dir,"clavrx_goes16_2020_022_2348_BARBADOS-2KM-FD.level2.nc")
        ds_sat = xr.open_dataset(path_file)
        ds_sat = ds_sat.where(ds_sat.scan_lines_along_track_direction < 498, drop=True)

        if(ds_sat.START_TIME < 11 or ds_sat.START_TIME > 21):
            colormap="Greys"
            channel = GOES16_var_night
        else:
            colormap="Greys_r"
            channel = GOES16_var_day


        fig, ax = plt.subplots(1, 1)

        fig.subplots_adjust(left=0, bottom=0, right=1, top=1, wspace=None, hspace=None)


        # ax.pcolormesh((file["refl_2_10um_nom"].values)**(1/6), cmap=colormap)
        alpha=1/6
        ax.pcolormesh(ds_sat["longitude"],ds_sat["latitude"],(ds_sat[channel].values)**(alpha), cmap=colormap)
        ax.set_xlim([lonmin, lonmax])
        ax.set_ylim([latmin, latmax])
        ax.axis('off')

        str_day = os.path.split(os.path.split(path_file)[0])[1]
        output_dir = os.path.join(goesdir, str_day)
        os.makedirs(output_dir, exist_ok=True)

        output_file = os.path.split(path_file)[1]
        output_file = os.path.splitext(output_file)[0]
        output_file = output_file.replace("_BARBADOS-2KM-FD.level2", "")
        output_file = output_file[:-3]+'.jpg'
        output_file = output_file.replace("clavrx_OR_ABI-L1b-RadF-M6C01_G16", "GOES16")

        output_file = os.path.join(output_dir, output_file)

        fig.savefig(output_file)

        plt.close(fig)

    elif source == 'local':
        ds_sat = xr.open_dataset(path_file)
        # Select only region of interest defined in movie_params.py
        ds_sat_sel = ds_sat.sel(lon=slice(lonmin,lonmax),
                                lat=slice(latmax, latmin))

        if (ds_sat_sel.time.dt.hour < 11 or ds_sat_sel.time.dt.hour > 21):
            colormap = "Greys"
            cmin, cmax = (260, 300)
            channel = GOES16_var_night
        else:
            colormap = "Greys"
            cmin, cmax = (270, 300)
            channel = GOES16_var_day

        # Drop times where no data is available at the center of the requested domain
        # ds_sat_sel = ds_sat_sel.where(np.isnan(ds_sat_sel.sel(lon=lonmin+dlon/2,
        #                                           lat=latmin+dlat/2,
        #                                           method='nearest')[channel].values),
        #                       drop=True)

        fig, ax = plt.subplots(1, 1)

        fig.subplots_adjust(left=0, bottom=0, right=1, top=1, wspace=None, hspace=None)

        ax.pcolormesh(ds_sat_sel["lon"].values,
                      ds_sat_sel["lat"].values,
                      ds_sat_sel[channel].squeeze().values, cmap=colormap,
                      vmin=cmin, vmax=cmax)
        ax.set_xlim([lonmin, lonmax])
        ax.set_ylim([latmin, latmax])
        ax.axis('off')

        output_dir = goesdir
        os.makedirs(output_dir, exist_ok=True)

        output_file = str(ds_sat_sel.squeeze().time.dt.strftime(image_file_fmt).values)
        try:
            output_file = output_file.format(channel=channel)
        except:
            pass

        output_file = os.path.join(output_dir, output_file)

        fig.savefig(output_file)

        plt.close(fig)

       
if __name__ == "__main__":
    
    # Specified beforehand
    from movie_params import *

    # Arguments to be used if want to change options while executing script
    parser = argparse.ArgumentParser(description="Transform ciclad .nc data into satellite images")
    parser.add_argument("-y","--year", default=2020,help="Year, YYYY", type=int)
    parser.add_argument("-m","--month", default=2, help="Month, M", type=int)
    parser.add_argument("-d","--day", default=5, help="Day, D", type=int)
    parser.add_argument("-i", "--input", default='../satellite_data/ciclad/%Y_%m_%d/*.nc',
                        help="Input filename format of netCDF4 files")
    parser.add_argument("-s", "--source", default='ciclad',
                        help="Source of files (ciclad or local)")  # datafiles differ depending on the source
    args = parser.parse_args()
    year = args.year
    month = args.month
    day = args.day
    input_file_fmt = args.input
    source = args.source
    
    files = get_files(year, month, day, input_file_fmt)
    for file in tqdm.tqdm(files):
        make_figure(file, source = source)

"""
Main script to create EUREC4A movies
"""
import os, sys
import datetime as dt
import argparse
import tqdm
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
sys.path.append('.')
sys.path.append('./scripts/')
import helpers as h
from omegaconf import OmegaConf
from intake import open_catalog

import movie_params as mp

def get_timeperiod_cfg(timerange):
    """
    Get time period from string

    Input
    -----
    timerange : str
      Time range in format HHMM-HHMM
    """
    s_time_str, e_time_str = timerange.split('-')
    start_time = dt.datetime.strptime(s_time_str, '%H:%M').time()
    end_time = dt.datetime.strptime(e_time_str, '%H:%M').time()
    return start_time, end_time

def check_range(time, timeranges):
    """
    Check if time is in any timerange
    """
    for t, t_range in enumerate(timeranges):
        if time >= t_range[0] and time <= t_range[1]:
            return t

    return None


def make_figure(ds, cfg_general=None, cfg_specific=None):
    # Select only region of interest defined in movie_params.py
    lonmin = cfg_general.output.domain.lonmin
    lonmax = cfg_general.output.domain.lonmax
    latmin = cfg_general.output.domain.latmin
    latmax = cfg_general.output.domain.latmax
    try:
        vmin = eval(cfg_specific.vmin)
    except TypeError:
        vmin = cfg_specific.vmin
    try:
        vmax = eval(cfg_specific.vmax)
    except TypeError:
        vmax = cfg_specific.vmax

    fig, ax = plt.subplots(1, 1)
    fig.subplots_adjust(left=0, bottom=0, right=1, top=1, wspace=None, hspace=None)

    if ds is not None:
        ds_sel = ds.sel(lon=slice(lonmin, lonmax),
                        lat=slice(latmax, latmin))

        var = [*ds_sel.squeeze().data_vars.keys()][0]  # first variable in dataset
        ax.pcolormesh(ds_sel["lon"].values,
                      ds_sel["lat"].values,
                      ds_sel[var].squeeze().values,
                      cmap=plt.cm.__dict__[cfg_specific.colormap],
                      vmin=vmin, vmax=vmax, shading="nearest")
    ax.set_xlim([lonmin, lonmax])
    ax.set_ylim([latmin, latmax])
    ax.axis('off')

    return fig

def export_figure(fig, filename):
    fig.savefig(output_file)
    plt.close(fig)

if __name__ == "__main__":
    # Specified beforehand
    from movie_params import *

    # Arguments to be used if want to change options while executing script
    parser = argparse.ArgumentParser(description="Transform satellite data into images")
    parser.add_argument("-d", "--date", default='20200205', help="Date, YYYYMMDD", type=str)
    parser.add_argument("-s", "--source", default='opendap',
                        help="Source of files (opendap)")
    parser.add_argument("-o", "--overwrite", default=False, help="overwriting existing local images", type=bool)
    args = parser.parse_args()
    source = args.source

    assert source == 'opendap', 'Currently only opendap is supported'
    cfg_design = OmegaConf.load("./config/design.yaml")
    cfg_access = OmegaConf.load("./config/access_opendap.yaml")
    cfg_output = OmegaConf.load("./config/output_user.yaml")
    cat = open_catalog(cfg_access.catalog)
    date = dt.datetime.strptime(args.date, '%Y%m%d')

    catalog_entry_1 = cat.satellites.sat.GOES16_regridded(date=date)
    catalog_entry_2_CH02 = cat.satellites.sat.GOES16_latlongrid_CH02_10min
    catalog_entry_2_CH13 = cat.satellites.sat.GOES16_latlongrid_CH13_10min
    t_res = cfg_design.output.images['temporal_resolution_min']
    times = pd.date_range(date,date+dt.timedelta(days=1),freq=f'{t_res}T')

    # Load all available satellite images lazy
    datasets = {}
    fmt = 'CH{ch:02d}_{res:02d}min'
    datasets[fmt.format(ch=13, res=1)] = catalog_entry_1(channel=13, date=date).to_dask()
    datasets[fmt.format(ch=2, res=1)] = catalog_entry_1(channel=2, date=date).to_dask()
    datasets[fmt.format(ch=13, res=10)] = catalog_entry_2_CH13.to_dask()
    datasets[fmt.format(ch=2, res=10)] = catalog_entry_2_CH02.to_dask()

    design_setup = cfg_design.satellite.defaults

    time_ranges_str = [*cfg_design.satellite.timespecific.keys()]
    time_ranges = np.empty((len(time_ranges_str),2),dtype=object)
    for t, t_range in enumerate(time_ranges_str):
        time_ranges[t,:] = get_timeperiod_cfg(t_range)


    for time in tqdm.tqdm(times):
        design_setup_ = design_setup.copy()

        t_range = check_range(time.time(), time_ranges)
        cfg_key = time_ranges_str[t_range]
        if cfg_key is not None:
            design_setup_.update(cfg_design.satellite.timespecific[cfg_key])
        channel = design_setup_.channel

        output_dir = cfg_output.output.images.directory
        os.makedirs(output_dir, exist_ok=True)
        filename = os.path.join(output_dir, cfg_output.output.images.file_fmt)
        output_file = str(time.strftime(filename))

        if os.path.exists(output_file) and not args.overwrite:
            continue

        # Check if highest temporal res is available otherwise fallback to lower resolution or None
        try:
            data = datasets[fmt.format(ch=channel, res=1)].sel(time=time, tolerance=dt.timedelta(minutes=1), method='nearest')
        except KeyError: # Data not available at high resolution
            try:
                data = datasets[fmt.format(ch=channel, res=10)].sel(time=time, tolerance=dt.timedelta(minutes=6),
                                                                   method='nearest')
            except KeyError:
                data = None

        fig = make_figure(data, cfg_general=cfg_design, cfg_specific=design_setup_)

        export_figure(fig, output_file)

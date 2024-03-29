# by Benjamin Fildier & Ludovic Touze-Peiffer

# General
import numpy as np
import os,sys,glob
import datetime as dt
import logging
from omegaconf import OmegaConf
# Remove warning
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
# Read arguments
import argparse
# Load data
import xarray as xr
import pandas as pd
from PIL import Image
# Display
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.ticker as ticker
from matplotlib.patches import Circle, Wedge
import matplotlib.colors as colors
import matplotlib.cm as cmx
import matplotlib.lines as mlines
from intake import open_catalog
from functools import partial


def loadImage(dtime, cfg, verbose=False):
    """Load GOES image closest to given time
    Arguments:
    - dtime: datetime object
    """

    goes_temporal_res = 1  # temporal resolution in minutes
    # pick time of goes_timestep
    hr_goes = dtime.hour
    min_goes = np.round(dtime.minute/goes_temporal_res)*goes_temporal_res  # round min to closest goes_timestep
    hr_goes += int((min_goes/60))  # increment if round to next hour
    min_goes = int(min_goes%60)
    dtime_goes = dt.datetime(year=dtime.year,
                             month=dtime.month,
                             day=dtime.day,
                             hour=hr_goes,
                             minute=min_goes)
    
    # path of image
    nameroot = dtime_goes.strftime('%Y%j%H%M')
    path = cfg.output.images.directory
    filename = os.path.join(path, cfg.output.images.file_fmt)
    filename = dtime_goes.strftime(filename)
    filename = glob.glob(os.path.join( filename))

    assert len(filename) == 1, 'No or too many files found for requested time ({})'.format(filename)
    fullpath = filename[0]
   
    if verbose:
        logging.info('load image %s.jpg' % nameroot)
    
    # load and return image
    return Image.open(fullpath)

def loadSondes(dtime, catalog):
    """Load sondes for the day as a list of xarrays"""
    datasets = {}
    for platform in ['bco', 'meteor', 'ms_merian', 'ronbrown', 'atalante_vaisala']:
        datasets[platform] = catalog.radiosondes[platform].to_dask()
    # Preparing merging of radiosoundings and dropsondes
    radiosondes = xr.concat(datasets.values(), dim="sounding")
    radiosondes = radiosondes.set_coords(["launch_time","platform_id"])
    radiosondes = radiosondes.rename({"platform_id": "platform",
                                      "sounding_id": "sounding"
                                      })
    del radiosondes['flight_time']
    dropsondes = catalog.dropsondes.JOANNE.level3.to_dask()
    dropsondes = dropsondes.set_coords("platform")
    radios_at_droplevel = radiosondes.sel(alt=dropsondes.alt, method='nearest')
    allsondes = xr.concat([radios_at_droplevel.p.compute(), dropsondes.p.compute()], dim="sounding")

    # all sondes for the specific day
    allsondes = allsondes.swap_dims({'sounding': 'launch_time'}).sortby('launch_time')
    sondes_of_day = allsondes.sel(launch_time=slice(dtime.date()+dt.timedelta(hours=0),
                                                    dtime.date()+dt.timedelta(hours=24)))
                                 
    return sondes_of_day

def loadPlatform(dtime, platform_name, catalog, ATR_track_file=None):
    """Load track data for platform"""

    if platform_name == 'ATR' and ATR_track_file is not None: # use user-prescribed track file (from Saphire) because the ATR tracks are slightly wrong for 2020-01-26
        platform = xr.open_dataset(ATR_track_file)
    else: # use intake catalog
        platform_track = catalog[platform_name].track.to_dask()
        platform = platform_track.sel(time=slice(dtime,dtime+dt.timedelta(days=1,hours=2)))
    
    return platform

def getMatchingSondes(allsondes,dtime,dt_fade,nfill=None,verbose=False):
    
    """Returns a list of sondes in xarray format, to be displayed.

    Arguments:
    - allsondes: list of all sondes already loaded
    - dtime: datetime object, current time
    - dt_fade: time window (mn) to fade out sondes that reached the surface
    - nfill: output list lf nfill elements. Default is None (unconstrained size)
    - verbose: 
    
    Returns:
    - sondes: list of xarray objects"""
    
    sondes = []
    
    # window for fading out sonde display
    delta_fade = dt.timedelta(minutes=dt_fade)
   
    number_sondes = len(allsondes.launch_time)
    
    for i in range(number_sondes):
        sonde = allsondes.isel(launch_time=i)
        
        launch_time = dt.datetime.strptime(str(sonde.launch_time.values)[:16],
                                           '%Y-%m-%dT%H:%M')

        # If sonde currently falling or fell in the past dt_fade mn
        if launch_time <= dtime < launch_time + delta_fade:
                
            if verbose:
                logging.debug('keep ',launch_time)
                
            # Then load sonde data and store it
            sondes.append(sonde)
    
    # fill list of nfill elements with empty sonde objects
    if nfill is None:
        return sondes
    elif nfill > len(sondes):
        return sondes+[None]*(nfill-len(sondes))
    else:
        return sondes[:nfill]


def initSondeObj(cfg):
    """Creates a patch to be displayed on the figure, and updated at each time step"""
   
    return Circle((cfg.HALO_circle.lon_center,cfg.HALO_circle.lat_center),
                  0.02,linewidth=2,ec='w',fc='w',alpha=0)


def getSondeObj(dtime, sonde, scalarMap, cfg, col_fading='darkorange', gettime=True):
    """Creates a new patch based on dropsonde data. Not for display, but to 
    communicate its position, color and transparency to patches already plotted."""
    
    # default value
    if sonde is None:
        logging.debug("no sonde")
        return initSondeObj(cfg)
        
    # position of sonde at current time
    if len(sonde.dropna(dim="alt").alt) == 0:
        # Sonde is empty
        return
    lon_sonde = sonde.lon.dropna(dim="alt").values[0]
    lat_sonde = sonde.lat.dropna(dim="alt").values[0]

    time_sonde = dt.datetime.strptime(str(sonde.launch_time.values)[:16],
                                                '%Y-%m-%dT%H:%M')

    delta_fade = dt.timedelta(minutes=cfg.output.movies.dt_fade)
    alpha = (((time_sonde+delta_fade)-dtime)/(delta_fade))**3  # to the power 3 for better display
    if alpha > 1: alpha = 1  # correct for cases where alpha>1 due to time rounding errors

    if sonde.platform == "HALO" or sonde.platform == "P3":
        fc = ec = 'b'
        if alpha < 1:
            fc = ec = 'b'
    else:
        fc = ec = 'r'

    # create and return patch
    return Circle((lon_sonde,lat_sonde),0.03,linewidth=2,ec=ec,fc=fc,alpha=alpha)


def getPlatform(platform, platform_col='lemonchiffon', track_col='gold'):
    
    if 'lon' in list(platform.coords):
        x, y = np.array([platform.lon[:], platform.lat[:]])
    elif 'LONGITUDE' in list(platform.coords):
        x, y = np.array([platform.LONGITUDE[:], platform.LATITUDE[:]])
# old version
#    line = mlines.Line2D(x, y, lw=5., alpha=1, color=track_col,
#                         marker="o",ms=7, markevery=[0],
#                         mfc=platform_col,mec=platform_col)
    line = mlines.Line2D(x, y, lw=2., alpha=1, color=track_col,
                         marker="o",ms=10, markevery=[0],
                         mfc=platform_col,mec=platform_col)
    
    return line


def getLaunchTime(sonde=None):

    if sonde is None:
        return ''
    else:
        return str(sonde.launch_time.values)[11:16]


def showTime(ax, dtime, cfg, title=''):
    """Display time (and movie title if there is one) on figure axes ax"""

    t = ax.text(0, 1,
                dtime.strftime('%Y-%m-%d\n%H:%M UTC\n'+title), ha='left', va='top',
                color='white',fontsize=30, transform=ax.transAxes)

    return t


def initFigure(goes_im, cfg, draw_circle=True):
    """Initialize figure"""
    # Calculate figure dimensions( Attention! Needs to be the same
    # as those during the image creation process, because there is
    # no other geometric reference in the images
    dlat = np.abs(cfg.output.domain.latmax - cfg.output.domain.latmin)
    dlon = np.abs(cfg.output.domain.lonmax - cfg.output.domain.lonmin)
    asp_ratio = dlat / dlon
    w_inches = cfg.output.movies.w_inches
    h_inches = w_inches * asp_ratio
    #if h_inches % 2 != 0:
    #    h_inches = h_inches // 2 * 2
    #if w_inches % 2 != 0:
    #    w_inches = w_inches // 2 * 2

    fig = plt.figure()
    fig.set_size_inches(w_inches, h_inches, True)
    fig.subplots_adjust(left=0, bottom=0, right=1, top=1, wspace=None, hspace=None)
    ax = fig.gca()

    im = ax.imshow(goes_im,aspect=1)
    im.set_extent([cfg.output.domain.lonmin,
                   cfg.output.domain.lonmax,
                   cfg.output.domain.latmin,
                   cfg.output.domain.latmax])

    # add HALO circle
    if draw_circle:
        r_circle = np.sqrt((cfg.HALO_circle.lon_pt_circle - cfg.HALO_circle.lon_center) ** 2 +
                           (cfg.HALO_circle.lat_pt_circle - cfg.HALO_circle.lat_center) ** 2)
        circ = Circle((cfg.HALO_circle.lon_center,
                       cfg.HALO_circle.lat_center),
                      r_circle, linewidth=2,
                      ec=cfg.output.movies.color_top,
                      fill=False)
        ax.add_patch(circ)

    # add grid
    ax.xaxis.set_major_locator(ticker.MultipleLocator(0.5))
    ax.yaxis.set_major_locator(ticker.MultipleLocator(0.5))
    ax.grid(color='w', linestyle='-', linewidth=0.3)

    # remove axes
    ax.xaxis.set_ticklabels([])
    ax.xaxis.set_ticks_position('none')
    ax.yaxis.set_ticklabels([])
    ax.yaxis.set_ticks_position('none')

    return fig, ax, im


def initSondeDisplay(ax, allsondes, cfg, title='', n_sondeobj=30):

    # create and show sonde objects at start time
    sonde_objs = []
    time_objs = []
    for i_sonde in range(n_sondeobj):
        sonde_obj = initSondeObj(cfg)
        # show
        ax.add_patch(sonde_obj)
        time_obj = ax.text(cfg.HALO_circle.lon_center,cfg.HALO_circle.lat_center,'',
                color='w',alpha=1,fontsize=18)
        # store
        sonde_objs.append(sonde_obj)
        time_objs.append(time_obj)

    # init current time
    t_main = showTime(ax, start, cfg, title)
    
    return t_main, time_objs, sonde_objs


def updateText(t, pos='', text='', col='', alpha=''):
    """Update text displayed on image in text object t"""

    t.set_text(text)
    t.set_position(pos)
    t.set_color(col)
    t.set_alpha(alpha)


def updateSondeObj(obj, pos=(0,0), fc='w', ec='w', alpha=1.):
    """Update patch (i.e. sonde) properties for patch object obj"""

    obj.center = pos
    obj.set_fc(fc)
    obj.set_ec(ec)
    obj.set_alpha(alpha)


def updatePlatformObj(obj, platform, dtime):
    """Update line and patch (i.e. trajectory and platform) properties for patch object obj"""

    dtime_str = dtime.strftime('%Y-%m-%d %H:%M')
        
    ts = pd.to_datetime(platform.time.values[:]) 
    df = ts.strftime('%Y-%m-%d %H:%M')

    matching_time = np.where(df.values[:] == dtime_str)[0]

    if matching_time.size != 0:
        matching_time = matching_time[0]
                
    obj.set_markevery([matching_time])


def makeMovie(s_time, e_time, cfg, movie_name, movie_label, ATR_track_file, verbose=False):
    """Generate animation"""

    n_sondeobj = 30

    # colorscale falling dropsondes
    cNorm = colors.Normalize(vmin=0, vmax=cfg.soundings.alt_max)
    scalarMap = cmx.ScalarMappable(norm=cNorm,
                                   cmap=plt.cm.__dict__[cfg.soundings.colormap])

    # Initialize intake catalog
    cat = open_catalog(cfg.catalog)
    
    # Load first GOES image
    goes_im = loadImage(s_time, cfg_merged)

    # Load all sondes
    allsondes = loadSondes(s_time, cat)

    # Load platforms
    platforms = {}
    for platform_name in cfg.platforms.incl_platforms:
        logging.debug(f"Loading platform: {platform_name}")
        platforms[platform_name] = loadPlatform(start.date(),platform_name, cat,ATR_track_file=ATR_track_file)
    
    # -- initialize figure
    # figure
    fig, ax, im = initFigure(goes_im, cfg_merged, draw_circle=cfg_merged.output.movies.draw_HALO_circle)
    # sondes and times
    t_main, time_objs, sonde_objs = initSondeDisplay(ax, allsondes, cfg_merged, title=movie_label, n_sondeobj=n_sondeobj)
    
    # platform(s)
    platform_objs = {}
    for platform_name in platforms.keys():
        if len(platforms[platform_name].time) == 0:
            logging.warning(f"No track found for {platform_name} on this day")
            continue
        # get platform data
        platform_obj = getPlatform(platforms[platform_name],
                                   platform_col=cfg.platforms[platform_name].platform_color,
                                   track_col=cfg.platforms[platform_name].track_color)
        # store
        platform_objs[platform_name] = platform_obj
        # show
        ax.add_line(platform_obj)

    # -- define movie loop
    def updateImage(i, cfg):
        
        # update current time
        dtime = s_time + i*dt_delta
        if verbose and dtime.minute%10 == 0:
            print('... %s ...'%dtime.strftime('%Y-%m-%d %H:%M'))
        
        # update main time display
        t_main.set_text(dtime.strftime('%Y-%m-%d\n%H:%M UTC\n'+movie_label))
        
        # update GOES image if necessary
        goes_im = loadImage(dtime, cfg)
        im.set_data(goes_im)
        
        # update platform objects
        for platform_name, platform_obj in platform_objs.items():
            updatePlatformObj(platform_obj, platforms[platform_name], dtime)
        
        # update sondes
        show_sondes = False
        if cfg.output.movies.show_sondes:
            for i_sonde, sonde in zip(range(n_sondeobj),
                                     getMatchingSondes(allsondes, dtime, cfg.output.movies.dt_fade,
                                                       nfill=n_sondeobj)):

                launch_time = getLaunchTime(sonde)
                sonde_obj = getSondeObj(dtime, sonde, scalarMap,
                                        col_fading=cfg.output.movies.color_bottom,
                                        cfg=cfg)

                if sonde_obj is None:
                    continue

                # update patch
                updateSondeObj(sonde_objs[i_sonde],
                               pos=sonde_obj.center,
                               fc=sonde_obj.get_fc(),
                               ec=sonde_obj.get_ec(),
                               alpha=sonde_obj.get_alpha())
                # update time
                lon_sonde, lat_sonde = sonde_obj.center
                updateText(time_objs[i_sonde],
                           pos=(lon_sonde+0.05, lat_sonde+0.05),
                           text=launch_time,
                           col=sonde_obj.get_fc(),
                           alpha=sonde_obj.get_alpha())
        
        return [im]
    
    # -- make movie
    # create
    updateImage_ = partial(updateImage, cfg=cfg_merged)
    ani = animation.FuncAnimation(fig, updateImage_, Nt,
                                  interval=cfg.output.movies.speed_factor/delta_t,
                                  blit=True)
    writer = animation.writers['ffmpeg'](fps=cfg.output.movies.speed_factor/delta_t,
                                         metadata={"comment":f"created on {dt.datetime.now().strftime('%Y%m%d %H:%M')}"}
                                         )
    
    # save
    outputdir = cfg.output.movies.directory
    os.makedirs(outputdir, exist_ok=True)

    moviefile = os.path.join(outputdir, '%s.mp4'%(movie_name))
    print(cfg.output.movies.dpi)
    ani.save(moviefile, writer=writer, dpi=cfg.output.movies.dpi)
    
    plt.close()
    
    return ani


if __name__ == "__main__":
    # Arguments to be used if want to change options while executing script
    parser = argparse.ArgumentParser(description="Generates movie showing sondes and platforms over GOES images")
    parser.add_argument("-d","--start_date", required=True, default=None,help="Date, YYYYMMDD")
    parser.add_argument("--stop_date",required=False, default=None,help="End Date, YYYYMMDD")
    parser.add_argument("-s", "--start_time", required=False, default="00:00", help="start time of movie in HHMM")
    parser.add_argument("-e", "--stop_time", required=False, default="23:59", help="end time of movie in HHMM")
    parser.add_argument("-v", "--verbose", required=False, default=True, help="Verbosity of script")
    parser.add_argument("-l", "--movie_label", required=False, default='', help="Movie title to be added below the date and in the movie name")
    parser.add_argument("-t", "--ATR_track_file", required=False, default=None, help="Manual entry of track file to use, if different from the intake catalog")
    args = parser.parse_args()
    date_str = str(args.start_date)
    if args.stop_date is None:
        stop_date_str = date_str
    else:
        stop_date_str = str(args.stop_date)

    cfg_design = OmegaConf.load("./config/design.yaml")
    cfg_access = OmegaConf.load("./config/access_opendap.yaml")
    cfg_output = OmegaConf.load("./config/output_user.yaml")
    cfg_merged = OmegaConf.merge(cfg_design,cfg_access,cfg_output)
    cfg_merged._parents = OmegaConf.merge(cfg_design,cfg_access,cfg_output)

    # -- movie
    # define time objects
    start = dt.datetime.strptime(date_str+args.start_time,'%Y%m%d%H:%M')
    stop = dt.datetime.strptime(stop_date_str+args.stop_time,'%Y%m%d%H:%M')
    delta_t = cfg_design.output.movies.delta_t
    dt_delta = dt.timedelta(seconds=delta_t)
    Nt = int((stop-start).seconds/delta_t)

    movie_name = start.strftime('%Y-%m-%d')
    if args.movie_label != '':
        movie_name = "%s_%s"%(movie_name,args.movie_label)

    if args.verbose:
        print()
        print('-- Show sondes and platforms on GOES images --')
        print()
        print("Flight day %s" % date_str)
        print("Platforms: %s" % (', '.join(cfg_merged.platforms.incl_platforms)))
        print("Time increment: %2.1f min" % (dt_delta.seconds/60))
        print('Number of frames:', Nt)
        print('Start movie at %s' % start)
        print('Movie name: %s'%movie_name)
        print('Movie label: %s'%args.movie_label)
        print()

    # make movie
    makeMovie(start, stop, cfg_merged, movie_name, args.movie_label, args.ATR_track_file, verbose=args.verbose)

    if args.verbose:
        print()
        print('Done :)')

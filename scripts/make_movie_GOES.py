# by Benjamin Fildier & Ludovic Touze-Peiffer

# General
import numpy as np
import os,sys,glob
import datetime as dt
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
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.ticker as ticker
from matplotlib.patches import Circle, Wedge
import matplotlib.colors as colors
import matplotlib.cm as cmx
import matplotlib.lines as mlines
from matplotlib.patches import Patch
from matplotlib.lines import Line2D


def loadImage(dtime, channel='C13', verbose=False):
    """Load GOES image closest to given time
    Arguments:
    - dtime: datetime object
    """
    
    date_str = dtime.strftime('%Y_%m_%d')
    goes_temporal_res = 1  # temporal resolution in minutes
    # pick time of goes_timestep
    hr_goes = dtime.hour
    min_goes = round(dtime.minute/goes_temporal_res)*goes_temporal_res  # round min to closest goes_timestep
    hr_goes += int((min_goes/60)) # increment if round to next hour
    min_goes = min_goes%60
    dtime_goes = dt.datetime(year=dtime.year,
                                   month=dtime.month,
                                   day=dtime.day,
                                   hour=hr_goes,
                                   minute=min_goes)
    
    # path of image
    nameroot = dtime_goes.strftime('%Y%j%H%M')
    file_fmt = dtime_goes.strftime(image_file_fmt)
    filename = file_fmt.format(channel=channel)
    file = glob.glob(os.path.join(goesdir, filename))

    assert len(file) == 1, 'No or too many files found for requested time ({})'.format(os.path.join(goesdir, filename))
    fullpath = file[0]
   
    if verbose:
        print('load image %s.jpg'%nameroot)
    
    # load and return image
    return Image.open(fullpath)

def loadSondes(dtime):
    """Load sondes for the day as a list of xarrays"""
    
    path_allsondes = os.path.join(sondedir,"all_sondes.nc")
    
    allsondes = xr.open_dataset(path_allsondes)
     
    #all sondes for the specific day
    allsondes = allsondes.swap_dims({'sounding': 'launch_time'}).sortby('launch_time')
    sondes_of_day = allsondes.sel(launch_time=slice(dtime.date()+dt.timedelta(hours=0),
                                                    dtime.date()+dt.timedelta(hours=24)))
                                 
    return sondes_of_day

def loadPlatform(dtime, platform_name):
    """Load track data for platform"""

    filename = "EUREC4A_%s_Track_v1.2.nc"%platform_name
    
    path_platform = os.path.join(platformdir,filename)
    platform = xr.open_dataset(path_platform)
    
    str_date = dtime.strftime("%Y-%m-%d")
    platform = platform.sel(time=str_date)
    
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
        #.dropna(dim="gpsalt",subset=["time"])
        
        launch_time = dt.datetime.strptime(str(sonde.launch_time.values)[:16],
                                                '%Y-%m-%dT%H:%M')

        # If sonde currently falling or fell in the past dt_fade mn
        if launch_time <= dtime and launch_time + delta_fade > dtime:
                
            if verbose:
                print('keep ',launch_time)
                
            # Then load sonde data and store it
            sondes.append(sonde)
    
    # fill list of nfill elements with empty sonde objects
    if nfill is None:
        return sondes
    elif nfill > len(sondes):
        return sondes+[None]*(nfill-len(sondes))
    else:
        return sondes[:nfill]

def initSondeObj():
    """Creates a patch to be displayed on the figure, and updated at each time step"""
   
    return Circle((lon_center,lat_center),0.02,linewidth=2,ec='w',fc='w',alpha=0)

def getSondeObj(dtime,sonde,scalarMap,col_fading='darkorange',gettime=True):
    """Creates a new patch based on dropsonde data. Not for display, but to 
    communicate its position, color and transparency to patches already plotted."""
    
    ## default value
    if sonde is None:
     #   print("no sonde")
        return initSondeObj()
    
    ## otherwise define patch with correct position, color and transparency

    # earlier get index in sonde lifetime that matches current time
    dtime_str = dtime.strftime('%Y-%m-%dT%H:%M')

#     t_inds = np.arange(0,sonde.time.size,int(sonde.time.size/15)) # use time subindices to speed up the code
       
#     sonde_times = np.array([dt.datetime.utcfromtimestamp(sonde.time[t_inds[i]].values).strftime("%Y-%m-%dT%H:%M")\
#                              for i in range(len(t_inds))]) 
    
    
#     matching_times = np.where(sonde_times == dtime_str)[0]
    
#     if matching_times.size == 0: # no matching time, sonde on the ground
#         falling = False
#         i_dtime = 0
#     else:
#         falling = True
#         i_dtime = t_inds[matching_times[-1]]
        
    # position of sonde at current time
    try:
        lon_sonde = sonde.longitude.dropna(dim="height").values[0]
        lat_sonde = sonde.latitude.dropna(dim="height").values[0]
    except:
        lon_sonde = sonde.lon.dropna(dim="alt").values[0]
        lat_sonde = sonde.lat.dropna(dim="alt").values[0]

    time_sonde = launch_time = dt.datetime.strptime(str(sonde.launch_time.values)[:16],
                                                '%Y-%m-%dT%H:%M')
    

#     alt_sonde = sonde.alt.values[i_dtime]
#     time_sonde = dt.datetime.utcfromtimestamp(sonde.time.values[i_dtime])
#    # print("time_sonde" + str(time_sonde))
#     launch_time = dt.datetime.strptime(str(sonde.launch_time.values)[:16],'%Y-%m-%dT%H:%M')
#    # print("launch_time" +str(launch_time))
#     last_time = dt.datetime.utcfromtimestamp(sonde.time.values[0])
#   #  print("last_time" + str(last_time))
    
#     # choose color based on height
#     fc = ec = scalarMap.to_rgba(alt_sonde)
    delta_fade = dt.timedelta(minutes=dt_fade)
    alpha = (((time_sonde+delta_fade)-dtime)/(delta_fade))**3 # to the power 3 for better display
    if alpha > 1: alpha = 1 # correct for cases where alpha>1 due to time rounding errors
    
        
    if (sonde.platform == "HALO" or sonde.platform == "P3"):
        fc=ec='b'
        if alpha < 1:
            fc=ec='b'
    else:
        fc=ec='r'
    
#     # color in darkorange if the sonde reached the ocean
#     if dtime > last_time:
#         fc = ec = col_fading
#     # fix color for when sonde is just being launched
#     if dtime == launch_time:
#         fc = ec = col_top
    
#     if not falling:
#         # fade out coefficient
#         delta_fade = dt.timedelta(minutes=dt_fade)
#         alpha = (((time_sonde+delta_fade)-dtime)/(delta_fade))**3 # to the power 3 for better display
#         if alpha > 1: alpha = 1 # correct for cases where alpha>1 due to time rounding errors
    
    # create and return patch
    return Circle((lon_sonde,lat_sonde),0.03,linewidth=2,ec=ec,fc=fc,alpha=alpha)

def getPlatform(dtime, platform, platform_col='lemonchiffon',track_col='gold'):
    
    x, y = np.array([platform.lon[:], platform.lat[:]])
    # line = mlines.Line2D(x, y, lw=2., alpha=1, color=platform_col, marker="o",ms=10, markevery=[0])
    line = mlines.Line2D(x, y, lw=1., alpha=1, color=track_col, marker="o",ms=7, markevery=[0],mfc=platform_col,mec=platform_col)
    
    return line

def getLaunchTime(sonde=None):

    if sonde is None:
        return ''
    else:
        return str(sonde.launch_time.values)[11:16]

def showTime(ax,dtime):
    """Display time on figure axes ax"""

    t = ax.text(lonmin+0.1,latmax-0.45,dtime.strftime('%Y-%m-%d\n%H:%M UTC'),
            color='white',fontsize=30)

    return t

def initFigure(goes_im,draw_circle=True):

    fig = plt.figure()
    fig.set_size_inches(w_inches, h_inches, True)
    fig.subplots_adjust(left=0, bottom=0, right=1, top=1, wspace=None, hspace=None)
    ax = fig.gca()

    im = ax.imshow(goes_im,aspect=1)
    im.set_extent([lonmin,lonmax,latmin,latmax])

    # add HALO circle
    if draw_circle:
        circ = Circle((lon_center,lat_center),r_circle,linewidth=2,ec=col_top,fill=False)
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

    
#     legend_elements = [Line2D([0], [0], marker='o', color='y', label='Platform',
#                           markerfacecolor='g', markersize=10),
#                    Line2D([0], [0], marker='o', color='w', label='inside cold pool',
#                           markerfacecolor='b', markersize=10),
#                    Line2D([0], [0], marker='o', color='w', label='outside cold pool',
#                           markerfacecolor='r', markersize=10)
#                    ]

# Create the figure
#     ax.legend(handles=legend_elements, loc='upper right', labelspacing=2, framealpha=1)
    # show colorbar
#     x,y,w,h = ax.get_position().bounds
#     c_map_ax = fig.add_axes([x+0.9*w, y+0.05*h, 0.008*w, 0.5*h])
#     cbar = mpl.colorbar.ColorbarBase(c_map_ax, cmap=cmap, orientation = 'vertical')
#     cbar.ax.set_ylabel('z(km)',fontsize=20,color='w') # cbar legend
#     h_values = np.linspace(0,altmax,6)
#     cbar.ax.set_yticklabels(['%1.1f'%(v/1000) for v in h_values],fontsize=15) # set ticklabels
#     cbar.ax.tick_params(axis='y',colors='w') # set tick color in white

    return fig, ax, im

def initSondeDisplay(ax,allsondes,n_sondeobj=30):

    # create and show sonde objects at start time
    sonde_objs = []
    time_objs = []
    for i_sonde in range(n_sondeobj):
        sonde_obj = initSondeObj()
        # show
        ax.add_patch(sonde_obj)
        time_obj = ax.text(lon_center,lat_center,'',
                color='w',alpha=1,fontsize=18)
        # store
        sonde_objs.append(sonde_obj)
        time_objs.append(time_obj)

    # init current time
    t_main = showTime(ax,start)

    return t_main, time_objs, sonde_objs

def updateText(t,pos='',text='',col='',alpha=''):
    """Update text displayed on image in text object t"""

    t.set_text(text)
    t.set_position(pos)
    t.set_color(col)
    t.set_alpha(alpha)

def updateSondeObj(obj,pos=(0,0),fc='w',ec='w',alpha=1.):
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

    matching_time = np.where(df.values[:]==dtime_str)[0]

    if(matching_time.size != 0):
        matching_time=matching_time[0]
                
    obj.set_markevery([matching_time])

def makeMovie(verbose=False):
    """Generate animation"""

    n_sondeobj = 30

    # colorscale falling dropsondes
    cNorm = colors.Normalize(vmin=0, vmax=altmax)
    scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=cmap)

    ##-- initialize data
    
    # Load first GOES image
    goes_im = loadImage(start)
    # current_image_time = imageNameRoot(start)

    # Load all sondes
    allsondes = loadSondes(start)
    Nsondes = len(allsondes)

    # Load platforms
    platforms = []
    for platform_name in platform_names:
        platforms.append(loadPlatform(start,platform_name))
    
    ##-- initialize figure
    
    # figure
    fig, ax, im = initFigure(goes_im,draw_circle=draw_circle)
    # sondes and times
    t_main, time_objs, sonde_objs = initSondeDisplay(ax,allsondes,n_sondeobj=n_sondeobj)    
    
    # platform(s)
    platform_objs = []
    for platform,platform_color,track_color in zip(platforms,platform_colors,track_colors):
    
        # get platform data
        platform_obj = getPlatform(start,
                                    platform,
                                    platform_col=platform_color,
                                    track_col=track_color)
        # store
        platform_objs.append(platform_obj)
        # show
        ax.add_line(platform_obj)

    ##-- define movie loop

    def updateImage(i):
        
        # update current time
        dtime = start + i*dt_delta
        if verbose and dtime.minute%10 == 0:
            print('... %s ...'%dtime.strftime('%Y-%m-%d %H:%M'))
        
        # update main time display
        t_main.set_text(dtime.strftime('%Y-%m-%d\n%H:%M UTC'))
        
        # update GOES image if necessary
        goes_im = loadImage(dtime)
        im.set_data(goes_im)
        
        # update platform objects
        for platform,platform_obj in zip(platforms,platform_objs):
            updatePlatformObj(platform_obj, platform, dtime)
        
        # update sondes
        for i_sonde,sonde in zip(range(n_sondeobj),getMatchingSondes(allsondes,dtime,dt_fade,nfill=n_sondeobj)):

            # sonde = sondes[i_sonde]
            # sonde = sondes[i_sonde]
            launch_time = getLaunchTime(sonde)
            sonde_obj = getSondeObj(dtime,sonde,scalarMap,col_fading=col_bottom)

            # update patch
            updateSondeObj(sonde_objs[i_sonde],
                            pos=sonde_obj.center,
                            fc=sonde_obj.get_fc(),
                            ec=sonde_obj.get_ec(),
                            alpha=sonde_obj.get_alpha())
            # update time
            lon_sonde,lat_sonde = sonde_obj.center
            updateText(time_objs[i_sonde],
                        pos=(lon_sonde+0.05,lat_sonde+0.05),
                        text=launch_time,
                        col=sonde_obj.get_fc(),
                        alpha=sonde_obj.get_alpha())
        
        return [im]
    
    ##-- make movie
   
    
    # create
    ani = animation.FuncAnimation(fig,updateImage,Nt,interval=speed_factor/delta_t,blit=True)
    writer = animation.writers['ffmpeg'](fps=speed_factor/delta_t)
    
    # save

    os.makedirs(outputdir,exist_ok=True)

    moviefile = os.path.join(outputdir,'%s.mp4'%(start.strftime('%Y-%m-%d')))
    ani.save(moviefile,writer=writer,dpi=dpi)
    
    plt.close()
    
    return ani


if __name__ == "__main__":
    
    ##-- import movie parameters

    # Specified beforehand
    from movie_params import *

    # Arguments to be used if want to change options while executing script
    parser = argparse.ArgumentParser(description="Generates movie showing sondes and platforms over GOES images")
    parser.add_argument("-d","--date", required=True, default=None,help="Date, YYYYMMDD")
    args = parser.parse_args()
    date_str = str(args.date)

    ##-- movie

    # define time objects
    start = dt.datetime.strptime(date_str+start_time,'%Y%m%d%H:%M')
    end = dt.datetime.strptime(date_str+end_time,'%Y%m%d%H:%M')
    dt_delta = dt.timedelta(seconds=delta_t)
    Nt = int((end-start).seconds/delta_t)

    verbose = True
    if verbose:

        print()
        print('-- Show sondes and platforms on GOES images --')
        print()
        print("Flight day %s"%date_str)
        print("Platforms: %s"%(', '.join(platform_names)))
        print("Time increment: %2.1f min"%(dt_delta.seconds/60))
        print('Number of frames:',Nt)
        print('Start movie at %s'%start_time)
        print()

    # make movie
    makeMovie(verbose=verbose)

    if verbose:
        print()
        print('Done :)')

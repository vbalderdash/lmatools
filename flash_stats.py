import glob
import os

import numpy as np

from lmatools.io import read_flashes
from lmatools.density_to_files import coroutine


def bin_center(bins):
    return (bins[:-1] + bins[1:]) / 2.0
    

def energy_plot_setup(fig=None, subplot=111, bin_unit='km'):
    """ Create an energy spectrum plot with a 5/3 slope line and an spare line
        to be used for plotting the spectrum. The spare line is intially located
        on top of the 5/3 line 
        If fig is specified, the spectrum axes will be created on that figure
        in the subplot position given by subplot.
        
        Returns 
    """    
    if fig is None:
        import matplotlib.pyplot as plt
        fig = plt.figure()
    
    spectrum_ax = fig.add_subplot(subplot)
    spectrum_ax.set_xlabel('Flash width ($\sqrt{A_h}$, %s)' % (bin_unit,))
    spectrum_ax.set_ylabel('$E(l) \mathrm{(m^2 s^{-2} km^{-1})}$')
    spectrum_ax.set_xlim(10**-1, 10**2)
    spectrum_ax.set_ylim(10**0, 10**8)
    spectrum_ax.set_yscale('log')
    spectrum_ax.set_xscale('log')
    
    #1e-2 to 1e4
    min_pwr = -2
    max_pwr = 4
    delta_pwr = 0.1
    powers = np.arange(min_pwr, max_pwr+delta_pwr, delta_pwr)
    flash_1d_extent = 10**powers
    wavenumber = (2*np.pi)/flash_1d_extent
    inertialsubrange = 10**6 * (wavenumber)**(-5.0/3.0)
    
    spectrum_line_artist = spectrum_ax.loglog(flash_1d_extent, inertialsubrange, 'r')[0]
    fivethirds_line_artist = spectrum_ax.loglog(flash_1d_extent, inertialsubrange, 'k')[0]
    
    return fig, spectrum_ax, fivethirds_line_artist, spectrum_line_artist


def calculate_energy_from_area_histogram(histo, bin_edges, duration, scaling_constant=1.0):
    flash_1d_extent = bin_center(np.sqrt(bin_edges))    
    bin_widths = np.sqrt(bin_edges[1:] - bin_edges[:-1])    
    # This should give   s^-2                 m^2                      km^-1   =  m s^-2 km^-1
    specific_energy = (histo/duration * flash_1d_extent*1000.0)**2.0 / (bin_widths) # flash_1d_extent #bin_widths
    specific_energy *= 1.0
    return flash_1d_extent, specific_energy

def plot_energy_from_area_histogram(histo, bin_edges, bin_unit='km', save=False, fig=None, color_cycle_length=1, color_map='gist_earth', duration=600.0):
    """ Histogram for flash width vs. count """
    duration=float(duration)
    
    fig, spectrum_ax, fivethirds_line_artist, spectrum_artist = energy_plot_setup()
    spectrum_ax.set_title(save.split('/')[-1].split('.')[0])
    
    flash_1d_extent, specific_energy = calculate_energy_from_area_histogram(histo, bin_edges, duration)
    spectrum_artist.set_data(flash_1d_extent, specific_energy)
    
    if save==False:
        plt.show()
    else:
        # ax.set_title(save)
        fig.savefig(save)
        fig.clf()
    


@coroutine
def histogram_for_parameter(parameter, bin_edges, target=None):
    """ General coroutine that accepts a named numpy array with field parameter
        and calcualtes a histogram using bin_edges. Target is sent histogram, edges.
    """
    while True:
        a = (yield)
        histo, edges = np.histogram(a[parameter], bins=bin_edges)
        if target is not None:
            target.send((histo, edges))

@coroutine
def events_flashes_receiver(target=None):
    """ Passes along only flashes """
    while True:
        events, flashes = (yield)
        if target is not None:
            target.send(flashes)


@coroutine
def histogram_accumulate_plot(plotter, histo_array=None, save=False, fig=None):
    bin_edges=None
    try:
        while True:        
            histo, edges = (yield) 
            
            if bin_edges is None:
                bin_edges = edges
            else:
                assert (bin_edges == edges).all()
            
            if histo_array is None:
                histo_array  = histo
            else:
                histo_array += histo
    except GeneratorExit:
        plotter(histo_array, bin_edges, save=save, fig=fig)
        

    
def footprint_stats(h5_filenames, save=False, fig=None, min_points=10):
    
    # start_time = datetime(2009,6,10, 20,0,0)
    # end_time   = datetime(2009,6,10, 21,0,0)

    #1e-2 to 1e4
    min_pwr = -2
    max_pwr = 4
    delta_pwr = 0.1
    powers = np.arange(min_pwr, max_pwr+delta_pwr, delta_pwr)
    footprint_bin_edges = 10**powers

    plotter = plot_energy_from_area_histogram
    
    histogram_plot = histogram_accumulate_plot(plotter, save=save, fig=fig)
    histogrammer=histogram_for_parameter('area', footprint_bin_edges, target=histogram_plot)
    ev_fl_rx = events_flashes_receiver(target=histogrammer)
    read_flashes(h5_filenames, ev_fl_rx, min_points=min_points)
    
if __name__ == '__main__':
    # '/data/20090610/data'
    # min_points = 10

    # --- All times (6+ hours), .15 s and 3 km ---
    # h5_filenames = glob.glob('29may-thresh-0.15_dist-3000.0/LYL*.flash.h5')
    # h5_filenames += glob.glob('30may-thresh-0.15_dist-3000.0/LYL*.flash.h5')
    # h5_filenames = glob.glob('30may-thresh-0.15_dist-3000.0/LYL*0130*.flash.h5')

    # h5_filenames = glob.glob('/Users/ebruning/code/McCaul Flash/test20040529/fixed-area-run/thresh-0.15_dist-3000.0/LYL*.flash.h5')
        
    # footprint_stats(h5_filenames, min_points=min_points)

    # --- 0130 - 0140 UTC, range of different space/time criteria ---
    if True:
        import matplotlib.pyplot as plt
        
        fig = plt.figure()
        
        min_points = (10,)
        time_critera = (0.15,)
        distance_critera = (3000.0,)

        filename_template = '/Users/ebruning/code/McCaul Flash/test20040529/fixed-area-run-expandedtime/thresh-{0}_dist-{1}/LYL*.flash.h5'
        for dpt in min_points:
            for dt in time_critera:
                for dx in distance_critera:
                    pattern = filename_template.format(dt,dx)
                    print pattern
                    h5_filenames = glob.glob(pattern)
                    for h5_file in h5_filenames:
                        file_basename = os.path.split(h5_file)[-1].split('.')[:-3][0]
                        figure_file = '/Users/ebruning/code/McCaul Flash/test20040529/fixed-area-run-expandedtime/thresh-{0}_dist-{1}/histos/{2}-footprint_histogram-{3}pts.pdf'.format(dt,dx,file_basename,dpt)
                        # print figure_file
                        footprint_stats([h5_file], save=figure_file, fig=fig, min_points=dpt)
                # break
            # break
    
    # To open all figures in Preview, you can use a pattern like so from sh/bash
    # open thresh-0.{05,1,15,2,25}_dist*/footprint_histogram-10pts.pdf
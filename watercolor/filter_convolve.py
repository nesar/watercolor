# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/06_filter_convolve.ipynb.

# %% auto 0
__all__ = ['data_str', 'FILTER_DIR', 'load_filter', 'load_indiv_filter_all', 'clip_bandpass_vals', 'load_survey_filters',
           'sed_to_mock_phot']

# %% ../nbs/06_filter_convolve.ipynb 3
import numpy as np
from scipy.interpolate import interp1d as interp1d
from .ssp_interpolation import spec_ssp_lookup

from .load_sps_library import load_fsps_spectral_library, load_fsps_age_metallicity
from .load_sps_library import STELLAR_LIBRARY_DIR

from .load_sim_stellar_catalog import load_hacc_galaxy_data
from .load_sim_stellar_catalog import GALS_FILE
from .load_sim_stellar_catalog import Z_SOLAR_PADOVA, H0

from .calculate_csp import calc_fluxes_for_galaxy

# %% ../nbs/06_filter_convolve.ipynb 9
data_str = ['LSST', 'cosmos', 'SPHEREx'][0]
# dataIn = 'filter_specifics/' + data_str + '_only.txt'
FILTER_DIR = '../watercolor/data/filter_specifics/'
# FILTER_NAMES = pkg_resources.resource_stream("watercolor", FILTER_DIR).name

# %% ../nbs/06_filter_convolve.ipynb 10
def load_filter(dirIn:str=FILTER_DIR # Input directory of the filters 
                              ) -> tuple: #wavelength, transmission co-effecients 
    
    glob.glob()
    spec_flux = np.load(pkg_resources.resource_stream("watercolor", FILTER_DIR + "ssp_spec_flux_lines.npy"))
    spec_wave = np.load(pkg_resources.resource_stream("watercolor", FILTER_DIR + "ssp_spec_wave.npy"))
    print('Library shape: ', spec_flux.shape) 
    print('Wavelength shape: ', spec_wave.shape)
    return spec_flux, spec_wave

# %% ../nbs/06_filter_convolve.ipynb 12
def load_indiv_filter_all(filtfile, norm=True):
    
    if ('SPHEREx' in filtfile):
        bandpass_name = filtfile.split('.dat')[0].split('/')[-1]
        x = np.loadtxt(filtfile)
    else:
        bandpass_name = filtfile.split('.npy')[0].split('/')[-1]
        x = np.load(filtfile)
    
    nonz = (x[:,1] != 0.)
    bandpass_wav = x[nonz,0]*1e-4
    bandpass_val = x[nonz,1]

    if norm:
        bandpass_val /= np.sum(bandpass_val)

    cenwav = np.dot(bandpass_wav, bandpass_val)
    # cenwav = np.dot(x[nonz,0], x[nonz,1])

    return bandpass_wav, bandpass_val, cenwav, bandpass_name




# %% ../nbs/06_filter_convolve.ipynb 13
def clip_bandpass_vals(bandpass_wavs, bandpass_vals):
    all_clip_bandpass_wav, all_clip_bandpass_vals = [], []

    for b in range(len(bandpass_wavs)):
        nonz_bandpass_val = (bandpass_vals[b] > 0)
        clip_bandpass_wav = bandpass_wavs[b][nonz_bandpass_val]
        clip_bandpass_vals = bandpass_vals[b][nonz_bandpass_val]
        all_clip_bandpass_wav.append(clip_bandpass_wav)
        all_clip_bandpass_vals.append(clip_bandpass_vals)

    return all_clip_bandpass_wav, all_clip_bandpass_vals

# %% ../nbs/06_filter_convolve.ipynb 14
def load_survey_filters(filtdir='data/spherex_filts/', to_um=True):

    ''' 
    Loads files, returns list of central wavelengths and list of wavelengths/filter responses. 
    Converts wavelengths to microns unless otherwise specified.
    '''
    if ('SPHEREx' in filtdir):
        
        bandpass_wavs, bandpass_vals, central_wavelengths, bandpass_names = [], [], [], []
        bband_idxs = np.arange(1, 7)
    
        for bandidx in bband_idxs:
            # filtfiles = glob.glob(filtdir+'SPHEREx_band'+str(bandidx)+'*.dat')
            filtfiles = glob.glob(filtdir+'*'+str(bandidx)+'*.dat')

            for filtfile in filtfiles:

                bandpass_wav, bandpass_val, cenwav, bandpass_name = load_indiv_filter_all(filtfile)
                bandpass_names.append(bandpass_name)

                bandpass_wavs.append(bandpass_wav)
                bandpass_vals.append(bandpass_val)
                central_wavelengths.append(cenwav)
    
    else:
        bandpass_wavs, bandpass_vals, central_wavelengths, bandpass_names = [], [], [], []
    

        filtfiles = glob.glob(filtdir+'*.npy')
        for filtfile in filtfiles:            

            bandpass_wav, bandpass_val, cenwav, bandpass_name = load_indiv_filter_all(filtfile)
            bandpass_names.append(bandpass_name)

            bandpass_wavs.append(bandpass_wav)
            bandpass_vals.append(bandpass_val)
            central_wavelengths.append(cenwav)
        

    return np.array(central_wavelengths), np.array(bandpass_wavs), np.array(bandpass_vals), np.array(bandpass_names)

# %% ../nbs/06_filter_convolve.ipynb 15
def sed_to_mock_phot(central_wavelengths, sed_um_wave, sed_mJy_flux, 
                     bandpass_wavs, bandpass_vals, interp_kind='linear', plot=True, clip_bandpass=True):
    # central wavelengths in micron
    if clip_bandpass:
        all_clip_bandpass_wav, all_clip_bandpass_vals = clip_bandpass_vals(bandpass_wavs, bandpass_vals)

    sed_interp = interp1d(sed_um_wave,
                          sed_mJy_flux,
                          kind=interp_kind,
                          bounds_error=False, 
                          fill_value = 0.0)

    band_fluxes = np.zeros_like(central_wavelengths)

    for b, bandpass_wav in enumerate(bandpass_wavs):
        # fluxes in mJy
        if clip_bandpass:
            band_fluxes[b] = np.dot(all_clip_bandpass_vals[b], sed_interp(all_clip_bandpass_wav[b]))
        else:
            band_fluxes[b] = np.dot(bandpass_vals[b], sed_interp(bandpass_wav))

    flux = 1e3*band_fluxes # uJy
    appmag_ext = -2.5*np.log10(flux)+23.9

    if plot:

        wav_um = np.array(central_wavelengths)

        plt.figure(figsize=(12, 4))
        plt.title('sed uJy flux')
        plt.plot(sed_um_wave, 1e3*sed_mJy_flux, color='k', zorder=5, alpha=0.5)
        plt.scatter(wav_um, flux, color='r', label='bandpass-convolved fluxes', s=30)
        # plt.ylim(0, 1.2*np.max(flux))
        plt.xlabel('um', fontsize=16)
        plt.ylabel('uJy', fontsize=16)
        plt.xlim(wav_um.min()*0.8, wav_um.max()*1.2)
        plt.tick_params(labelsize=14)
        plt.legend()
        plt.show()

    return flux, appmag_ext, band_fluxes

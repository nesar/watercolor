# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/06_filter_convolve.ipynb.

# %% auto 0
__all__ = ['ALL_FILTER_DIR', 'load_indiv_filter_all', 'clip_bandpass_vals', 'load_survey_filters', 'sed_to_mock_phot']

# %% ../nbs/06_filter_convolve.ipynb 3
import numpy as np
import glob
from scipy.interpolate import interp1d as interp1d
from .ssp_interpolation import spec_ssp_lookup

from .load_sps_library import load_fsps_spectral_library, load_fsps_age_metallicity
from .load_sps_library import STELLAR_LIBRARY_DIR

from .load_sim_stellar_catalog import load_hacc_galaxy_data
from .load_sim_stellar_catalog import GALS_FILE
from .load_sim_stellar_catalog import Z_SOLAR_PADOVA, H0

from .calculate_csp import calc_fluxes_for_galaxy

# %% ../nbs/06_filter_convolve.ipynb 8
ALL_FILTER_DIR = '../watercolor/data/filter_specifics/'

# %% ../nbs/06_filter_convolve.ipynb 10
def load_indiv_filter_all(filtfile:str=ALL_FILTER_DIR+'LSST', # Individual filter files 
                          norm:bool=True #Bandpass normalization condition
                         )->tuple: #Wavelengths, bandpass values, central wavelengths, filter name
    
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

# %% ../nbs/06_filter_convolve.ipynb 11
def clip_bandpass_vals(bandpass_wavs:np.float32=None, 
                       bandpass_vals:np.float32=None
                      )->tuple: #Clipped bandpass wavelengths, clipped bandpass values
    all_clip_bandpass_wav, all_clip_bandpass_vals = [], []

    for b in range(len(bandpass_wavs)):
        nonz_bandpass_val = (bandpass_vals[b] > 0)
        clip_bandpass_wav = bandpass_wavs[b][nonz_bandpass_val]
        clip_bandpass_vals = bandpass_vals[b][nonz_bandpass_val]
        all_clip_bandpass_wav.append(clip_bandpass_wav)
        all_clip_bandpass_vals.append(clip_bandpass_vals)

    return all_clip_bandpass_wav, all_clip_bandpass_vals

# %% ../nbs/06_filter_convolve.ipynb 12
def load_survey_filters(filtdir:str=ALL_FILTER_DIR+'LSST', #Input directory with all filter definitions
                        to_um:bool=True, #True/False to convert wavelengths to microns
                       )->tuple: #Central wavelengths, Bandpass wavelengths, Bandpass values, filter names 

    if ('SPHEREx' in filtdir):
        
        bandpass_wavs, bandpass_vals, central_wavelengths, bandpass_names = [], [], [], []
        
        # bandpass_wavs = np.array([], dtype=object)
        # bandpass_vals = np.array([], dtype=object)
        # central_wavelengths = np.array([], dtype=object)
        # bandpass_names = np.array([], dtype=object)
        
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
                
                # np.append(bandpass_names, bandpass_name)
                # np.append(bandpass_wavs, bandpass_wav)
                # np.append(bandpass_vals, bandpass_val)
                # np.append(central_wavelengths, cenwav)
    
    else:
        bandpass_wavs, bandpass_vals, central_wavelengths, bandpass_names = [], [], [], []
        
        # bandpass_wavs = np.array([], dtype=np.float64)
        # bandpass_vals = np.array([], dtype=np.float64)
        # central_wavelengths = np.array([], dtype=np.float64)
        # bandpass_names = np.array([], dtype=object)
    

        filtfiles = glob.glob(filtdir+'*.npy')
        for filtfile in filtfiles:            

            bandpass_wav, bandpass_val, cenwav, bandpass_name = load_indiv_filter_all(filtfile)
            
            # print(bandpass_wav)
            # print(bandpass_val)
            # print(cenwav)
            # print(bandpass_name)
            
            bandpass_names.append(bandpass_name)
            bandpass_wavs.append(bandpass_wav)
            bandpass_vals.append(bandpass_val)
            central_wavelengths.append(cenwav)
            
            # np.append(bandpass_names, bandpass_name)
            # np.append(bandpass_wavs, bandpass_wav)
            # np.append(bandpass_vals, bandpass_val)
            # np.append(central_wavelengths, cenwav)
        
    return central_wavelengths, bandpass_wavs, bandpass_vals, bandpass_names
    # return np.array(central_wavelengths, dtype=np.float64), np.array(bandpass_wavs, dtype=np.float64), np.array(bandpass_vals, dtype=np.float64), np.array(bandpass_names, dtype=object)

# %% ../nbs/06_filter_convolve.ipynb 13
def sed_to_mock_phot(central_wavelengths:np.array=None, # Central wavelengths
                     sed_um_wave:np.array=None, # SED wavelengths (in microns)
                     sed_mJy_flux:np.array=None, # SED fluxes (in mJy)
                     bandpass_wavs:np.array=None, # Bandpass wavelenths
                     bandpass_vals:np.array=None, # Bandspass values
                     bandpass_names:np.array=None, #Names of the bandpasses
                     interp_kind:str='linear', # Interpolation type
                     plot:bool=True, # Plotting SEDs with filter convolution
                     clip_bandpass:bool=True #Clip bandpass condition
                    )->tuple: # Fluxes, Apparent magnitudes, Band fluxes
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

        # plt.figure(figsize=(12, 4))
        f, a = plt.subplots(2, 1, figsize=(14, 6), sharex=True, gridspec_kw={'height_ratios': [2, 1]})
        a[0].set_title('sed uJy flux')
        a[0].plot(sed_um_wave, 1e3*sed_mJy_flux, color='k', zorder=5, alpha=0.5)
        a[0].scatter(wav_um, flux, color='r', label='bandpass-convolved fluxes', s=30)
        # plt.ylim(0, 1.2*np.max(flux))
        a[0].set_ylabel('uJy', fontsize=16)
        a[0].set_xlim(wav_um.min()*0.8, wav_um.max()*1.2)
        # plt.tick_params(labelsize=14)
        # plt.legend()
        
        
        a[1].set_title('Filter transmissions')
        for central_idx in range(wav_um.shape[0]):
            a[1].plot(bandpass_wavs[central_idx], bandpass_vals[central_idx], label=bandpass_names[central_idx])
        
        a[1].set_xlabel('um', fontsize=16)
        plt.show()

    return flux, appmag_ext, band_fluxes

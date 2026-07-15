import scipy
import numpy as np
import matplotlib.pyplot as plt
from glob import glob

#-------------------------------
# Peak and phase extraction code
#-------------------------------

def extract_peaks(fname, plot=False):
	# Read in wave file
    fs, y = scipy.io.wavfile.read(fname)
	# Separate channels
    y_mic = y[:,0] / np.max(np.abs(y[:,0]))
    y_met = y[:,1] / np.max(np.abs(y[:,1]))
	# Find peaks in each channel
	# This code relies on a few heuristics, so will likely need to be updated slightly, but
	# it works on all of the cued sub04 trials, at least
    pks, pmb = scipy.signal.find_peaks(np.abs(y_mic), height = 10 * scipy.stats.mstats.gmean(np.abs(y_mic[np.abs(y_mic) > 0])), 
                                  distance = fs * 0.3)
    metpks, metpmb = scipy.signal.find_peaks(np.abs(y_met), height = 10 * scipy.stats.mstats.gmean(np.abs(y_mic[np.abs(y_mic) > 0])), 
                                  distance = fs * 0.3)
	# This confirms that the peaks were properly detected
    if plot:
        fig, ax = plt.subplots()
        ax.plot(y_mic)
        for pk in pks:
            ax.axvline(pk, c='k', ls='--', alpha=0.2)
	# Convert the peak heights into decibels
	# Note that since the audio was normalized, these decibel ratings will all be much higher
    pkheights = 10 * np.log10(pmb['peak_heights'])
    return pks, metpks, pkheights, y_mic

def extract_phases(pks, metpks, y_mic):
    # Construct (linear) phase curve, wrapped into [-pi,pi]
    ph = [np.linspace(0, 2 * np.pi, x + 1) for x in np.diff(metpks)]
    ph_total = np.concatenate([tph[range(len(tph)-1)] for tph in ph])
    ph_total = np.angle(np.exp(1j*np.concatenate((np.zeros(min(metpks)), ph_total, 2*np.pi*np.ones(y_mic.shape[0] - max(metpks))))))
    # Map peak times onto phase curve
    tap_phases = ph_total[pks]
    return tap_phases

#------------------------------------
# Example with sub04
#------------------------------------
# Change the file path here to match wherever your files are store.
# This should point to the folder containing the audio recordings:
base_dir = '../save/'
# and this is the subject ID:
subj = 'sub04'
fnames_cued = glob('%s/%s/test/*_cued.wav' % (base_dir, subj))
for fname in fnames_cued:
	# Change the True argument to False if you don't want to see all the plots
    pks, metpks, pkheights, y_mic = extract_peaks(fname, True)
    print(len(pks))
    print(len(metpks))
    tap_phases = extract_phases(pks, metpks, y_mic)
    fig, ax = plt.subplots()
    ax.scatter(pks, pkheights)
    ax.plot(pks, pkheights)
    #plt.show()
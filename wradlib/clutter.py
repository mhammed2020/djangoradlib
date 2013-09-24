#-------------------------------------------------------------------------------
# Name:         clutter
# Purpose:
#
# Authors:      Maik Heistermann, Stephan Jacobi and Thomas Pfaff
#
# Created:      26.10.2011
# Copyright:    (c) Maik Heistermann, Stephan Jacobi and Thomas Pfaff 2011
# Licence:      The MIT License
#-------------------------------------------------------------------------------
#!/usr/bin/env python
"""
Clutter Identification
^^^^^^^^^^^^^^^^^^^^^^

.. autosummary::
   :nosignatures:
   :toctree: generated/

   filter_gabella
   filter_gabella_a
   filter_gabella_b
   histo_cut
   classify_echo_fuzzy

"""
import numpy as np
import scipy.ndimage as ndi
import wradlib.dp as dp
import wradlib.util as util

def filter_gabella_a(img, wsize, tr1, cartesian=False, radial=False):
    r"""First part of the Gabella filter looking for large reflectivity
    gradients.

    This function checks for each pixel in `img` how many pixels surrounding
    it in a window of `wsize` are by `tr1` smaller than the central pixel.

    Parameters
    ----------
    img : array_like
        radar image to which the filter is to be applied
    wsize : int
        Size of the window surrounding the central pixel
    tr1 : float
        Threshold value
    cartesian : boolean
        Specify if the input grid is Cartesian or polar
    radial : boolean
        Specify if only radial information should be used

    Returns
    -------
    output : array_like
        an array with the same shape as `img`, containing the filter's results.

    See Also
    --------
    filter_gabella_b : the second part of the filter
    filter_gabella : the complete filter

    Examples
    --------
    TODO: provide a correct example here

    >>> a=[1,2,3]
    >>> print [x + 3 for x in a]
    :w
[4, 5, 6]
    >>> print "a\n\nb"
    a
    b

    """
    nn = wsize // 2
    count = -np.ones(img.shape,dtype=int)
    range_shift = range(-nn,nn+1)
    azimuth_shift = range(-nn,nn+1)
    if radial:
        azimuth_shift = [0]
    for sa in azimuth_shift:
        refa = np.roll(img,sa,axis=0)
        for sr in range_shift:
            refr = np.roll(refa,sr,axis=1)
            count += ( img - refr < tr1 )
    count[:,0:nn] = wsize**2
    count[:,-nn:] = wsize**2
    if cartesian :
        count[0:nn,:] = wsize**2
        count[-nn:,:] = wsize**2
    return(count)

def filter_gabella_b(img, thrs=0.):
    r"""Second part of the Gabella filter comparing area to circumference of
    contiguous echo regions.



    Parameters
    ----------
    img : array_like
    thrs : float
        Threshold below which the field values will be considered as no rain

    Returns
    -------
    output : array_like
        contains in each pixel the ratio between area and circumference of the
        meteorological echo it is assigned to or 0 for non precipitation pixels.

    See Also
    --------
    filter_gabella_a : the first part of the filter
    filter_gabella : the complete filter

    Examples
    --------
    TODO: provide a correct example here

    >>> a=[1,2,3]
    >>> print [x + 3 for x in a]
    [4, 5, 6]
    >>> print "a\n\nb"
    a
    b

    """
    conn = np.ones((3,3))
    # create binary image of the rainfall field
    binimg = img > thrs
    # label objects (individual rain cells, so to say)
    labelimg, nlabels = ndi.label(binimg, conn)
    # erode the image, thus removing the 'boundary pixels'
    binimg_erode = ndi.binary_erosion(binimg, structure=conn)
    # determine the size of each object
    labelhist, edges = np.histogram(labelimg,
                                    bins=nlabels+1,
                                    range=(-0.5, labelimg.max()+0.5))
    # determine the size of the eroded objects
    erodelabelhist, edges = np.histogram(np.where(binimg_erode, labelimg, 0),
                                         bins=nlabels+1,
                                         range=(-0.5, labelimg.max()+0.5))
    # the boundary is the difference between these two
    boundarypixels = labelhist - erodelabelhist
    # now get the ratio between object size and boundary
    ratio = labelhist.astype(np.float32) / boundarypixels
    # assign it back to the objects
    # first get the indices
    indices = np.digitize(labelimg.ravel(), edges)-1
    # then produce a new field with the ratios in the right place
    result = ratio[indices.ravel()].reshape(img.shape)

    return result

def filter_gabella(img, wsize=5, thrsnorain=0., tr1=6., n_p=6, tr2=1.3, rm_nans=True, radial = False, cartesian = False):
    r"""Clutter identification filter developed by Gabella [Gabella2002]_ .

    This is a two-part identification algorithm using echo continuity and
    minimum echo area to distinguish between meteorological (rain) and non-
    meteorological echos (ground clutter etc.)

    Parameters
    ----------
    img : array_like
    wsize : int
        Size of the window surrounding the central pixel
    thrsnorain : float
    tr1 : float
    n_p : int
    thr2 : float
    rm_nans : boolean
        True replaces nans with Inf
        False takes nans into acount
    radial : boolean
        True to use radial information only in filter_gabella_a.
    cartesian : boolean
        True if cartesian data are used, polar assumed if False.

    Returns
    -------
    output : array
        boolean array with pixels identified as clutter set to True.

    See Also
    --------
    filter_gabella_a : the first part of the filter
    filter_gabella_b : the second part of the filter

    References
    ----------
    .. [Gabella2002] Gabella, M. & Notarpietro, R., 2002.
        Ground clutter characterization and elimination in mountainous terrain.
        In Proceedings of ERAD. Delft: Copernicus GmbH, pp. 305-311.
        Available at: http://www.copernicus.org/erad/online/erad-305.pdf
        [Accessed Oct 27, 2010].

    Examples
    --------
    TODO: provide a correct example here

    >>> a=[1,2,3]
    >>> print [x + 3 for x in a]
    [4, 5, 6]
    >>> print "a\n\nb"
    a
    b

    """
    bad = np.isnan(img)
    if rm_nans:
        img = img.copy()
        img[bad] = np.Inf
    ntr1 = filter_gabella_a(img, wsize, tr1, cartesian, radial)
    if not rm_nans:
        f_good = ndi.filters.uniform_filter((~bad).astype(float),size=wsize)
        f_good[f_good == 0] = 1e-10
        ntr1 = ntr1/f_good
        ntr1[bad] = n_p
    clutter1 = (ntr1 < n_p)
    ratio = filter_gabella_b(img, thrsnorain)
    clutter2 = ( np.abs(ratio) < tr2 )
    return ( clutter1 | clutter2 )

def histo_cut(prec_accum):
    r"""Histogram based clutter identification.

    This identification algorithm uses the histogram of temporal accumulated
    rainfall. It iteratively detects classes whose frequency falls below a
    specified percentage (1% by default) of the frequency of the class with the
    biggest frequency and remove the values from the dataset until the changes
    from iteration to iteration falls below a threshold. This algorithm is able
    to detect static clutter as well as shadings. It is suggested to choose a
    representative time periode for the input precipitation accumulation. The
    recommended time period should cover one year.

    Parameters
    ----------
    prec_accum : array_like
        spatial array containing rain accumulation

    Returns
    -------
    output : array
        boolean array with pixels identified as clutter/shadings set to True.

    """

    prec_accum = np.array(prec_accum)

    # initialization of data bounds for clutter and shade definition
    lower_bound = 0
    upper_bound = prec_accum.max()

    # predefinitions for the first iteration
    lower_bound_before = -51
    upper_bound_before = -51

    # iterate as long as the difference between current and last iteration doesn't fall below the stop criterion
    while ((abs(lower_bound - lower_bound_before) > 1) or (abs(upper_bound - upper_bound_before) > 1)):

        # masks for bins with sums over/under the data bounds
        upper_mask = (prec_accum <= upper_bound).astype(int)
        lower_mask = (prec_accum >= lower_bound).astype(int)
        # NaNs in place of masked bins
        prec_accum_masked = np.where((upper_mask * lower_mask) == 0, np.nan,prec_accum) # Kopie der Datenmatrix mit Nans an Stellen, wo der Threshold erreicht wird

        # generate a histogram of the valid bins with 50 classes
        (n, bins) = np.histogram(prec_accum_masked[np.isfinite(prec_accum_masked)].ravel(), bins = 50)
        # get the class with biggest occurence
        index=np.where(n == n.max())
        index= index[0]

        # separeted stop criterion check in case one of the bounds is already robust
        if (abs(lower_bound - lower_bound_before) > 1):
        # get the index of the class which underscores the occurence of the biggest class by 1%,
        #beginning from the class with the biggest occurence to the first class
           for i in range(index, -1, -1):
                if (n[i] < (n[index] * 0.01)): break
        if (abs(upper_bound - upper_bound_before) > 1):
            # get the index of the class which underscores the occurence of the biggest class by 1%,
            #beginning from the class with the biggest occurence to the last class
            for j in range(index, len(n)):
                if (n[j] < (n[index] * 0.01)): break

        lower_bound_before = lower_bound
        upper_bound_before = upper_bound
        # update the new boundaries
        lower_bound = bins[i]
        upper_bound = bins[j + 1]

    return np.isnan(prec_accum_masked)


def classify_echo_fuzzy(dat,
                        weights = {"zdr":0.4, "rho":0.4, "phi":0.4, "dop":0.3, "map":0.5},
                        trpz    = {"zdr":[0.7,1.0,9999,9999],
                                   "rho":[0.1,0.15,9999,9999],
                                   "phi":[15,20,10000,10000],
                                   "dop":[-0.2,-0.1,0.1,0.2],
                                   "map":[1,1,9999,9999]},
                        thresh  = 0.5):
    """Fuzzy echo classification and clutter identification based on polarimetric moments.

    The implementation is based on [Vulpiani2012]_. At the moment, it only distinguishes
    between metorological and non-meteorological echos.

    For each decision variable and radar bin, the algorithm uses trapezoidal
    functions in order to define the membership to the non-meteorological echo class.
    Based on pre-defined weights, a linear combination of the different degrees
    of membership is computed. The echo is assumed to be non-meteorological in case
    the linear comination exceeds a threshold.

    At the moment, the following decision variables are required:

        - Differential reflectivity (zdr)

        - Correlation coefficient (rho)

        - Differential phase (phidp)

        - Doppler velocity (dop)

        - Static clutter map (map)

    Parameters
    ----------
    dat : dictionary of arrays
       Contains the data of the decision variables. The shapes of the arrays should
       be (..., number of beams, number of gates) and the shapes need to be identical.
    weights : dictionary of floats
       Defines the weights of the decision variables.
    trpz : dictionary of lists of floats
       Contains the arguments of the trapezoidal membership functions for ecah decision variable
    thresh : float
       Threshold below which membership in non-meteorological membership class is assumed.

    Returns
    -------
    output : boolean array of same shape input arrays marking the occurence of non-meteorological echos.

    References
    ----------
    .. [Vulpiani2012] Vulpiani, G., M. Montopoli, L. D. Passeri, A. G. Gioia,
       P. Giordano, F. S. Marzano, 2012: On the Use of Dual-Polarized C-Band Radar
       for Operational Rainfall Retrieval in Mountainous Areas.
       J. Appl. Meteor. Climatol., 51, 405-425.

    """
    # Check the inputs
    keys = ["zdr","rho","phi","dop","map"]
    assert np.all(np.in1d(keys, dat.keys()    )), "Argument dat of classify_echo_fuzzy must be a dictionary with keywords %r." % (keys,)
    assert np.all(np.in1d(keys, weights.keys())), "Argument weights of classify_echo_fuzzy must be a dictionary with keywords %r." % (keys,)
    shape = None
    for key in keys:
        if not dat[key]==None:
            if shape==None:
                shape=dat[key].shape
            else:
                assert dat[key].shape==shape, "Arrays of the decision variables have an inconsistent shape."
        else:
            print "WARNING: Missing decision variable: %s" % key

    # Replace missing data by NaN
    dummy = np.zeros(shape)*np.nan
    for key in dat.keys():
        if dat[key]==None:
            dat[key] = dummy

    # membership in meteorological class for each variable
    q_dop = 1. - util.trapezoid(dat["dop"]            , trpz["dop"][0], trpz["dop"][1], trpz["dop"][2], trpz["dop"][3])
    q_zdr = 1. - util.trapezoid(dp.texture(dat["zdr"]), trpz["zdr"][0], trpz["zdr"][1], trpz["zdr"][2], trpz["zdr"][3])
    q_rho = 1. - util.trapezoid(dp.texture(dat["phi"]), trpz["phi"][0], trpz["phi"][1], trpz["phi"][2], trpz["phi"][3])
    q_phi = 1. - util.trapezoid(dp.texture(dat["rho"]), trpz["rho"][0], trpz["rho"][1], trpz["rho"][2], trpz["rho"][3])
    q_map = 1. - util.trapezoid(dat["map"]            , trpz["map"][0], trpz["map"][1], trpz["map"][2], trpz["map"][3])

    # create weight arrays which are zero where the data is NaN
    # This way, each pixel "adapts" to the local data availability
    w_dop = _weight_array(q_dop, weights["dop"])
    w_zdr = _weight_array(q_zdr, weights["zdr"])
    w_rho = _weight_array(q_rho, weights["rho"])
    w_phi = _weight_array(q_phi, weights["phi"])
    w_map = _weight_array(q_map, weights["map"])

    # remove NaNs from data
    q_dop = np.nan_to_num(q_dop)
    q_zdr = np.nan_to_num(q_zdr)
    q_rho = np.nan_to_num(q_rho)
    q_phi = np.nan_to_num(q_phi)
    q_map = np.nan_to_num(q_map)

    # Membership in meteorological class after combining all variables
    Q = ((q_map * w_map) + (q_dop * w_dop) + (q_zdr * w_zdr) + (q_rho * w_rho) + (q_phi * w_phi)) \
        / (w_map + w_dop + w_zdr + w_rho + w_phi)

    # flag low quality
    return np.where(Q < thresh, True, False)


def _weight_array(data, weight):
    """
    Generates weight array where valid values have the weight value and NaNs have 0 weight value.
    """
    w_array = weight * np.ones(np.shape(data))
    w_array[np.isnan(data)] = 0.
    return w_array


if __name__ == '__main__':
    print 'wradlib: Calling module <clutter> as main...'

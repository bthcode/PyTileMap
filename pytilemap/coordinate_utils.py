#!/usr/bin/env python

import numpy as np
import math


class WGS84:
    def __init__(self):
        self.a = 6378137.0
        self.b = 6356752.314245
        self.f = 1.0 / 298.257223563
        self.e2 = 1.0 - (1 - self.f) ** 2

def lla2ecef(lla, wgs84=WGS84()):
    """Convert Lat/Lon/Height to ECEF

    Parameters
    ----------
        lla: float[3]
            lat rad, lon rad, alt meters
        wgs84: WGS84
            wgs84 ellipsoid suas_model
    Returns
    -------
        float[3]
            xyz meters ECEF
    """
    ecef = list(range(len(lla)))

    # sines and cosines
    clat = np.cos(lla[0])
    slat = np.sin(lla[0])
    clon = np.cos(lla[1])
    slon = np.sin(lla[1])

    # normal
    tmp = wgs84.e2 * (slat * slat)
    nlat = wgs84.a / np.sqrt(1 - tmp)

    # x, y, z
    tmp = (nlat + lla[2]) * clat
    ecef[0] = tmp * clon
    ecef[1] = tmp * slon
    ecef[2] = (nlat * (1 - wgs84.e2) + lla[2]) * slat

    return ecef


# end lla2ecef


def ecef2lla(ecef_vec, wgs84=WGS84(), max_iterations=10):
    """Convert an ECEF coord to an Lat/Lon/Height coord

    Parameters
    ----------
        ecef_vec: float[3]
            x,y,z in meters ECEF
        wgs84: WGS84
            wgs 84 params struct
        max_iterations: int
            maximum attemps to search for coordinates

    Returns
    -------
        float[3]
             lat rad, lon rad, height meters above elipsoid

    Note
    ----
        This function is iterative and may have performance implications
    """

    # X,Y,Z from ecef_vec
    X = ecef_vec[0]
    Y = ecef_vec[1]
    Z = ecef_vec[2]

    RSQ = (X * X) + (Y * Y)
    alt = wgs84.e2 * Z

    for iteration in range(max_iterations):
        ZP = Z + alt
        clat = np.sqrt(RSQ + (ZP**2))
        slat = ZP / float(clat)
        tmp = wgs84.e2 * slat**2
        nlat = wgs84.a / np.sqrt(1 - tmp)
        alt_tmp = nlat * wgs84.e2 * slat
        if np.sqrt((alt - alt_tmp) ** 2) < 1e-7:
            break
        alt = alt_tmp

    lat = np.arctan2(ZP, np.sqrt(RSQ))
    lon = np.arctan2(Y, X)
    alt = clat - nlat
    return lat, lon, alt


# end ecef2lla







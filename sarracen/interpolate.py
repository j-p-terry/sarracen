import numpy as np
import pandas as pd
from numpy import ndarray
from pandas import DataFrame

from sarracen import SarracenDataFrame
from sarracen.kernels import BaseKernel


def interpolate2D(data: SarracenDataFrame,
                  x: str,
                  y: str,
                  target: str,
                  kernel: BaseKernel,
                  pixwidthx: float,
                  pixwidthy: float,
                  xmin: float = 0,
                  ymin: float = 0,
                  pixcountx: int = 480,
                  pixcounty: int = 480):
    """
    Interpolates particle data in a SarracenDataFrame across two directional axes to a 2D
    grid of pixels.

    :param data: The particle data, in a SarracenDataFrame.
    :param x: The column label of the x-directional axis.
    :param y: The column label of the y-directional axis.
    :param target: The column label of the target smoothing data.
    :param kernel: The kernel to use for smoothing the target data.
    :param pixwidthx: The width that each pixel represents in particle data space.
    :param pixwidthy: The height that each pixel represents in particle data space.
    :param xmin: The starting x-coordinate (in particle data space).
    :param ymin: The starting y-coordinate (in particle data space).
    :param pixcountx: The number of pixels in the output image in the x-direction.
    :param pixcounty: The number of pixels in the output image in the y-direction.
    :return: The output image, in a 2-dimensional numpy array.
    """
    if pixwidthx <= 0:
        raise ValueError("pixwidthx must be greater than zero!")
    if pixwidthy <= 0:
        raise ValueError("pixwidthy must be greater than zero!")
    if pixcountx <= 0:
        raise ValueError("pixcountx must be greater than zero!")
    if pixcounty <= 0:
        raise ValueError("pixcounty must be greater than zero!")

    if kernel.ndims != 2:
        raise ValueError("Kernel must be two-dimensional!")

    image = np.zeros((pixcounty, pixcountx))

    # iterate through all particles
    for i, particle in data.iterrows():
        # dimensionless weight
        # w_i = m_i / (rho_i * (h_i) ** 2)
        weight = particle['m'] / (particle['rho'] * particle['h'] ** 2)

        # skip particles with 0 weight
        if weight <= 0:
            continue

        # kernel radius scaled by the particle's 'h' value
        radkern = kernel.radkernel * particle['h']
        term = weight * particle[target]
        hi1 = 1 / particle['h']
        hi21 = hi1 ** 2

        part_x = particle[x]
        part_y = particle[y]

        # determine the min/max x&y coordinates affected by this particle
        ipixmin = int(np.rint((part_x - radkern - xmin) / pixwidthx))
        jpixmin = int(np.rint((part_y - radkern - ymin) / pixwidthy))
        ipixmax = int(np.rint((part_x + radkern - xmin) / pixwidthx))
        jpixmax = int(np.rint((part_y + radkern - ymin) / pixwidthy))

        # ensure that the min/max x&y coordinates remain within the bounds of the image
        if ipixmin < 0:
            ipixmin = 0
        if ipixmax > pixcountx:
            ipixmax = pixcountx
        if jpixmin < 0:
            jpixmin = 0
        if jpixmax > pixcounty:
            jpixmax = pixcounty

        # precalculate differences in the x-direction (optimization)
        dx2i = np.zeros(pixcountx)
        for ipix in range(ipixmin, ipixmax):
            dx2i[ipix] = ((xmin + (ipix + 0.5) * pixwidthx - part_x) ** 2) * hi21

        # traverse horizontally through affected pixels
        for jpix in range(jpixmin, jpixmax):
            # determine differences in the y-direction
            ypix = ymin + (jpix + 0.5) * pixwidthy
            dy = ypix - part_y
            dy2 = dy * dy * hi21

            for ipix in range(ipixmin, ipixmax):
                # calculate contribution at i, j due to particle at x, y
                q2 = dx2i[ipix] + dy2
                wab = kernel.w(np.sqrt(q2))

                # add contribution to image
                image[jpix][ipix] += term * wab

    return image


def interpolate2DCross(data: SarracenDataFrame,
                       x: str,
                       y: str,
                       target: str,
                       kernel: BaseKernel,
                       x1: float = 0,
                       y1: float = 0,
                       x2: float = 1,
                       y2: float = 1,
                       pixcount: int = 500) -> ndarray:
    """
    Interpolates particle data in a SarracenDataFrame across two directional axes to a 1D
    cross-section line.

    :param data: The particle data, in a SarracenDataFrame.
    :param x: The column label of the x-directional axis.
    :param y: The column label of the y-directional axis.
    :param target: The column label of the target smoothing data.
    :param kernel: The kernel to use for smoothing the target data.
    :param x1: The starting x-coordinate of the cross-section line. (in particle data space)
    :param y1: The starting y-coordinate of the cross-section line. (in particle data space)
    :param x2: The ending x-coordinate of the cross-section line. (in particle data space)
    :param y2: The ending y-coordinate of the cross-section line. (in particle data space)
    :param pixcount: The number of pixels in the output over the entire cross-sectional line.
    :return: The interpolated output, in a 1-dimensional numpy array.
    """
    if np.isclose(y2, y1) and np.isclose(x2, x1):
        raise ValueError('Zero length cross section!')

    if pixcount <= 0:
        raise ValueError('pixcount must be greater than zero!')

    if kernel.ndims != 2:
        raise ValueError("Kernel must be two-dimensional!")

    output = np.zeros(pixcount)

    # determine the slope of the cross-section line
    gradient = 0
    if not np.isclose(x2, x1):
        gradient = (y2 - y1) / (x2 - x1)
    yint = y2 - gradient * x2

    # determine the fraction of the line that one pixel represents
    xlength = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    pixwidth = xlength / pixcount
    xpixwidth = (x2 - x1) / pixcount

    # filter out particles with 0 weight
    term = data[target] * data['m'] / (data['rho'] * data['h'] ** 2)
    filter_weight = term / data[target] > 0

    # the intersections between the line and a particle's 'smoothing circle' are
    # found by solving a quadratic equation with the below values of a, b, and c.
    # if the determinant is negative, the particle does not contribute to the
    # cross-section, and can be removed.
    aa = 1 + gradient ** 2
    bb = 2 * gradient * (yint - data[y][filter_weight]) - 2 * data[x][filter_weight]
    cc = data[x][filter_weight] ** 2 + data[y][filter_weight] ** 2 \
         - 2 * yint * data[y][filter_weight] + yint ** 2 \
         - (kernel.radkernel * data['h'][filter_weight]) ** 2
    det = bb ** 2 - 4 * aa * cc

    # create a filter for particles that do not contribute to the cross-section
    filter_det = det >= 0
    det = np.sqrt(det[filter_det])
    cc = None

    # the starting and ending x coordinates of the lines intersections with a particle's smoothing circle
    xstart = ((-bb[filter_det] - det) / (2 * aa)).clip(lower=x1, upper=x2)
    xend = ((-bb[filter_det] + det) / (2 * aa)).clip(lower=x1, upper=x2)
    bb, det = None, None

    # the start and end distances which lie within a particle's smoothing circle.
    rstart = np.sqrt((xstart - x1) ** 2 + ((gradient * xstart + yint) - y1) ** 2)
    rend = np.sqrt((xend - x1) ** 2 + (((gradient * xend + yint) - y1) ** 2))
    xstart, xend = None, None

    # the maximum and minimum pixels that each particle contributes to.
    ipixmin = np.rint(rstart / pixwidth).clip(lower=0, upper=pixcount)
    ipixmax = np.rint(rend / pixwidth).clip(lower=0, upper=pixcount)
    rstart, rend = None, None

    # iterate through the indices of all non-filtered particles
    for i in filter_det.to_numpy().nonzero()[0]:
        # determine contributions to all affected pixels for this particle
        xpix = x1 + (np.arange(int(ipixmin[i]), int(ipixmax[i])) + 0.5) * xpixwidth
        ypix = gradient * xpix + yint
        dy = ypix - data[y][i]
        dx = xpix - data[x][i]

        q2 = (dx * dx + dy * dy) * (1 / (data['h'][i] * data['h'][i]))
        wab = kernel.w(np.sqrt(q2))

        # add contributions to output total, transformed by minimum/maximum pixels
        output[int(ipixmin[i]):int(ipixmax[i])] += (wab * term[i])

    return output

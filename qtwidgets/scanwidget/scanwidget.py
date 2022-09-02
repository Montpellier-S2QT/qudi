# -*- coding: utf-8 -*-
"""
This module contains a GUI component to define a dockable widget
to display a 2D scan image.

Qudi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Qudi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

import os
import pyqtgraph as pg
import numpy as np

from qtpy import QtWidgets
from qtpy import uic

from gui.colordefs import QudiPalettePale as palette
from qtwidgets.scanwidget.scanplotwidget import ScanImageItem


class ScanWidget(QtWidgets.QDockWidget):
    """ Widget containing a ScanPlotWidget to display the image and
    a colorbar, as well as a scanline and additionnal data treatment tools.
    """

    def __init__(self, data, line, title, name, unit, extent,
                 cmap_name, plane_fit=False, line_correction=False):
        """ Widget creation.
        @param 2D ndarray: image data
        @param 2D ndarray: scanline data, 1st column x, 2nd column y
        @param str title: title of the DockWidget
        @param str name: name of the displayed quantity (colorbar label)
        @param str unit
        @param list extent: [[x_min, x_max], [y_min, y_max]]
        @param str cmap_name (should be in the cdict of colordefs.py)
        @param bool plane_fit: display or not the plane fit correction tool
        @param bool line_correction: display or not the line correction combobox
        """

        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_scanwidget.ui')

        # Load it
        super(ScanWidget, self).__init__()
        uic.loadUi(ui_file, self)

        # sets the title
        self.setWindowTitle(title)
        self.plane_fit_applied = False
        self.line_correction_applied = False
        self.cursorCheckBox.clicked.connect(self.toggle_cursor)
        self.raw_data = data
        self.raw_line = line
        self.line_coords = np.linspace(extent[0][0], extent[0][1], np.size(self.raw_data, axis=1))
        
        # creates additional buttons if needed
        if plane_fit:
            self.planeFitCheckBox = QtWidgets.QCheckBox()
            self.planeFitCheckBox.setText('Plane fit')
            self.dataCorrLayout.addWidget(self.planeFitCheckBox)
            self.planeFitCheckBox.clicked.connect(self.refresh_image)
        if line_correction:
            self.lineCorrComboBox = QtWidgets.QComboBox()
            self.lineCorrComboBox.addItems([' ', 'Average', 'Median', 'Median diff', 'Median div'])
            self.dataCorrLayout.addWidget(self.lineCorrComboBox)
            self.lineCorrComboBox.currentIndexChanged.connect(self.refresh_image)

        self.scanline = pg.PlotDataItem(line, pen=pg.mkPen(palette.c1))
        self.scanlineView.addItem(self.scanline)
        self.scanlineView.setLabel('bottom', 'Position', units='m')
        self.scanlineView.setLabel('left', name, units=unit)

        self.image = ScanImageItem(image=data, axisOrder='row-major')
        self.image.set_image_extent(extent)
        self.image_widget.addItem(self.image)
        self.image_widget.setAspectLocked(True)
        self.image_widget.setLabel('bottom', 'X position', units='m')
        self.image_widget.setLabel('left', 'Y position', units='m')

        self.colorbar.set_image(self.image)
        self.colorbar.set_label(name, unit)
        self.colorbar.set_colormap(cmap_name)
        
        
    def apply_plane_fit(self, data):
        """ Corrects the data with a plane fit (or removes the correction).

        @param 2d ndarray data
        """
        if self.planeFitCheckBox.isChecked():
            self.plane_fit_applied = True
            output = plane_fit(data.copy())
            return output
        else:
            self.plane_fit_applied = False
            return data


    def apply_line_correction(self, data):
        """ Corrects the data by aligning the scan lines.

        @param 2d ndarray data
        """
        if self.lineCorrComboBox.currentText() == ' ':
            self.line_correction_applied = False
            return data
        else:
            self.line_correction_applied = True
            if self.lineCorrComboBox.currentText() == 'Average':
                output = subtract_average(data.copy())
            elif self.lineCorrComboBox.currentText() == 'Median':
                output = median(data.copy())
            elif self.lineCorrComboBox.currentText() == 'Median diff':
                output = median_diff(data.copy())
            elif self.lineCorrComboBox.currentText() == 'Median div':
                output = median_div(data.copy())
            else:
                return data
            return output

    
    def refresh_image(self, state=None, data=None, line=None):
        """ Refresh both the image and the colorbar, applying the correction if requested.
        @param int state of the clicked checkbox (not useful but passed by the signal)
        @param 2d ndarray data
        @param 2d ndarray line (2 columns, position and data)
        NB: the line is not plotted corrected.
        """
        if data is not None:
            self.raw_data = data.copy()
            
        if line is not None:
            self.raw_line = line.copy()
            
        new_data = None
        if self.plane_fit_applied:
            new_data = self.apply_plane_fit(self.raw_data)
        if self.line_correction_applied:
            new_data = self.apply_line_correction(self.raw_data)
        if new_data is None:
            new_data = self.raw_data.copy()
            
        self.image.setImage(image=new_data)
        self.colorbar.refresh_image()
        self.scanline.setData(x = self.line_coords, y = self.raw_line)
        return

    
    def toggle_cursor(self, is_active):
        """ Activates or not the ROI and the cursor. """
        if is_active:
            pass
        else:
            return

        
    def refresh_scan_area(self, extent):
        """ Changes the XY coordinates of the scan. """
        pass


# A few basic data processing functions
def subtract_average(data, mean_to_zero=True, direction='row'):
    """
    Data correction function. Substract to the values of each row or columns
    their mean value.
    
    @param 2D ndarray data: the 2D-ndarray to correct
    @param bool mean_to_zero: if True, after use of this function, the mean value
    of each row (resp. col) is zero. If False, the original mean value of
    the image is set again at the end
    @param str direction: 'row' or 'col', default 'row'
    
    @return 2D ndarray data, after correction
    """
    m = np.mean(data)
    if direction == 'row':
        data = data - np.mean(data, axis=1, keepdims=True)
    elif direction == 'col':
        data = data - np.mean(data, axis=0, keepdims=True)
    else:
        print('Unknown scan direction !')
        return
    if not mean_to_zero:
        data = data - np.mean(data) + m
    return data


def median_diff(data, direction='row'):
    """
    Data correction function. Substract to the value of each row or column the median of
    differences between their neighboring rows or columns.

    @param 2D ndarray data: the 2D-ndarray to correct
    @param str direction: 'row' or 'col', default 'row'
    
    @return 2D ndarray data, after correction
    """
    if direction == 'row':
        for i in range(1, np.size(data, axis=0)):
            med_diff = np.median(data[i, :]-data[i-1, :])
            data[i, :] = data[i, :] - med_diff
    elif direction == 'col':
        for i in range(1, np.size(data, axis=1)):
            med_diff = np.median(data[:, i]-data[:, i-1])
            data[:, i] = data[:, i] - med_diff
    else:
        print('Unknown scan direction !')
        return
    return data


def median(data, direction='row'):
    """
    Data correction function. Substract to each row or column the value of their median.
    
    @param 2D ndarray data: the 2D-ndarray to correct
    @param str direction: 'row' or 'col', default 'row'
    
    @return 2D ndarray data, after correction
    """
    if direction == 'row':
        for i in range(0, np.size(data, axis=0)):
            med = np.median(data[i, :])
            data[i, :] = data[i, :] - med
    elif direction == 'col':
        for i in range(0, np.size(data, axis=1)):
            med = np.median(data[:, i])
            data[:, i] = data[:, i] - med
    else:
        print('Unknown scan direction !')
        return
    return data


def median_div(data, direction='row'):
    """
    Data correction function. Divide each row or column by the value of their median.
    
    @param 2D ndarray data: the 2D-ndarray to correct
    @param str direction: 'row' or 'col', default 'row'
    
    @return 2D ndarray data, after correction
    """
    if direction == 'row':
        for i in range(0, np.size(data, axis=0)):
            med = np.median(data[i, :])
            data[i, :] = data[i, :]/med
    elif direction == 'col':
        for i in range(0, np.size(data, axis=1)):
            med = np.median(data[:, i])
            data[:, i] = data[:, i]/med
    else:
        print('Unknown scan direction !')
        return
    return data


# Equation of a plane from 2 array of coordinates x,y
def plane(x, y, a, b, c):
    return a*x+b*y+c


# Compute the difference between a 2D array zz and the plane
# with parameters a, b, c in params
def errorfunc_plane(params, *args):
    zz = args[0]
    xx = args[1]
    yy = args[2]
    out = zz-plane(xx, yy, *params)
    return out.flatten()


def plane_fit(array):
    """
    Data correction function. Fits a plane to the data and subtracts it.
    
    @param 2D ndarray array: the 2D-ndarray to correct
    
    @return 2D ndarray array, after correction
    """
    # pb with incomplete pictures,
    # we need to fit only the part containing data.
    clean = array[~np.isnan(array).any(axis=1), :]
    N = np.size(clean, axis=0)
    M = np.size(clean, axis=1)
    xx, yy = np.meshgrid(np.arange(M), np.arange(N))
    result = leastsq(errorfunc_plane, [1, 1, 1], args=(clean, xx, yy))
    pfit = result[0]
    zz = clean-plane(xx, yy, *pfit)
    # back to initial shape
    output = np.nan*np.ones(array.shape)
    # start missing
    if np.isnan(array).any(axis=1)[0]:
        i = 0
        while np.isnan(array).any(axis=1)[i]:
            i = i+1
        output[i:, :] = zz
    # end missing
    elif np.isnan(array).any(axis=1)[-1]:
        n = np.size(array, axis=0)-1
        i = n
        while np.isnan(array).any(axis=1)[i]:
            i = i-1
        output[:i+1, :] = zz
    else:
        output = zz
    return output


from skimage.transform import pyramid_gaussian
from skimage.transform import pyramid_expand
from skimage.io import imread
import matplotlib.pyplot as plt
import numpy as np
import imutils
import cv2
import argparse as ap
import config as cfg
import sys


def getWindowDims(image, winSize=[cfg.winSize, cfg.winSize], stride=[cfg.stride,cfg.stride]):
    # This function returns the bounding boxes for each window in the given image
    windows = []

    for y in xrange(0, image.shape[0]-winSize[0], stride[0]):
        for x in xrange(0, image.shape[1]-winSize[1], stride[1]):
            windows.append([x, y, winSize[0], winSize[1]]) # row, col, width, height

    return windows

def extractSubWindows(image, windows, transformer):
    # This function extracts the subwindows and puts it in the format required by caffe for batch processing.
    # Each window is of the same size

    subWindows = np.zeros(np.array([len(windows), 3, windows[0][2], windows[0][3]]))
    for i in xrange(0, len(windows)):
        x = windows[i][0]
        y = windows[i][1]
        w = windows[i][2]
        h = windows[i][3]
        subWindows[i] = transformer.preprocess('data', image[y:y+h, x:x+w])

    return subWindows

def extractSubImages(image, windows):
    subWindows = np.zeros(np.array([len(windows), windows[0][2], windows[0][3], 3]))
    for i in xrange(0, len(windows)):
        x = windows[i][0]
        y = windows[i][1]
        w = windows[i][2]
        h = windows[i][3]
        subWindows[i] = image[y:y+h, x:x+w]

    return subWindows

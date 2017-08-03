

import sys
import os
import numpy as np
import matplotlib.pyplot as plt
import PIL
from PIL import Image, ImageDraw, ImageFont
import argparse
import cv2
import copy, time, math
from . import config

sys.path.insert(0, os.path.join(config.caffe_root, 'python'))
import caffe

from nms import nms_max, nms_average
from helperModules import *
from Clustering import *
from windowExtractor import *


class componentDetector(object):

    def __init__(self, component="ic", mode="GPU"):
        self.componentClass = component
        self.mode = mode
        self.modelpath = os.path.join(config.modelpath, self.componentClass)
        #print self.modelpath
        self.model = os.path.join(self.modelpath, 'model_' + self.componentClass + '.caffemodel')
        self.prototxt = os.path.join(self.modelpath, 'deploy.prototxt')
        self.fullConvProto = os.path.join(self.modelpath, 'fullConv_' + self.componentClass + '.prototxt')
        self.meanfile = os.path.join(self.modelpath, 'mean_' + self.componentClass + '.npy')
        self.winSize = config.winSize

        # load the full conv net
        self.net_full_conv = loadNet(self.prototxt, self.fullConvProto, self.model, self.mode)
        # reshape the data layer to match the size of the image
        #self.net_full_conv.blobs['data'].reshape(1,3,self.winSize, self.winSize)
        # load the transformer
        self.transformer = loadTransformer(self.net_full_conv, self.meanfile, (self.winSize, self.winSize))


    def detectfast(self, image, minComponentSize):
        # check if the image exists
        if os.path.exists(image):
            # load the image
            img = caffe.io.load_image(image)
            # compute scale
            scale = math.ceil(227.0 / int(minComponentSize))
            # scale the image
            ims = caffe.io.resize_image(img, (int(img.shape[0]*scale), int(img.shape[1]*scale)))
            # load the transformer
            self.transformer = loadTransformer(self.net_full_conv, self.meanfile, (ims.shape[0], ims.shape[1]))
            # send image for detection
            out = self.net_full_conv.forward_all(data=np.asarray([self.transformer.preprocess('data', ims)]))
            # extract the heat map
            outprob = out['prob'][0,1]
            # generate bounding boxes
            boxes = generateBoundingBox(outprob, scale)
            # convert boxes to np array for nms
            boxes_nms = np.array(boxes)
            # perform non-maximum suppression
            true_boxes = nms_max(boxes_nms, overlapThresh=0.3)
            # validate the boxes for boundary conditions
            true_boxes = validateBoxes(true_boxes, [img.shape[0], img.shape[1]])
            # cluster the boxes
            clusters = clusterBoxes(true_boxes)
            fCluster = getAvgClusterBoxes(clusters)
            # perform validation again
            nBoxes = validateBoxes(fCluster, [img.shape[0], img.shape[1]])
            # get enclosing boxes
            nBoxes = enclosingBoxes(nBoxes)
            return nBoxes
        else:
            print("Image not found")


    def detect(self, image, minComponentSize):
        # check if the image exists:
            if os.path.exists(image):
                # load the image
                img = caffe.io.load_image(image)
                # compute scale
                scale = math.ceil(227.0 / int(minComponentSize))
                # scale the image
                ims = caffe.io.resize_image(img, (int(img.shape[0]*scale), int(img.shape[1]*scale)))
                # sliding window
                total_boxes = []

                print("Computing bounding boxes")
                start1 = time.time()
                for (x,y,imw) in sliding_window(ims, (515, 515), (minComponentSize, minComponentSize)):
                    # pass the image window to the classifier network
                    out = self.net_full_conv.forward_all(data=np.asarray([self.transformer.preprocess('data', imw)]))

                    # get the probability matrix associated with class 1 (IC here)
                    outprob = out['prob'][0,1]

                    # generate the bounding boxes based on the heat map
                    boxes = generateBoundingBox(outprob, 1)

                    # convert boxes to np array for nms
                    boxes_nms = np.array(boxes)

                    # perform non-maximum suppression
                    true_boxes = nms_max(boxes_nms, overlapThresh=cfg.overlapThresh)

                    # if there are any boxes returned scale them according to the original image
                    if (np.any(true_boxes)):
                        #plotHeatmap(scaleImg, outprob, "Heat Map")
                        scaled_boxes = copy.deepcopy(true_boxes)
                        for i, box in enumerate(scaled_boxes):
                            scaled_boxes[i][0] += x
                            scaled_boxes[i][1] += y
                            scaled_boxes[i][2] += x
                            scaled_boxes[i][3] += y
                        #drawBoundingBoxes(ims, scaled_boxes, "Scaled Image")
                        for i, box in enumerate(scaled_boxes):
                            true_boxes[i][0] = scaled_boxes[i][0] / scale
                            true_boxes[i][1] = scaled_boxes[i][1] / scale
                            true_boxes[i][2] = scaled_boxes[i][2] / scale
                            true_boxes[i][3] = scaled_boxes[i][3] / scale
                        total_boxes.extend(true_boxes)

                end1 = time.time()
                #print "Total time take for this image: " % (end1-start1)

                print("Performing Non-Maxima Suppression")
                # perform nms for the entire set of boxes
                boxes_nms = np.array(total_boxes)
                true_boxes = nms_max(boxes_nms, overlapThresh=0.2)

                print("Clustering bounding boxes")
                # Cluster the overlapping bounding boxes
                clusters = clusterBoxes(true_boxes)
                fCluster = getAvgClusterBoxes(clusters)

                print("Finding enclosing boxes")
                # group enclosed boxes
                finalBoxes = enclosingBoxes(fCluster)

                return finalBoxes

                #draw the Bounding boxes on top of the image
                #drawBoundingBoxes(im, finalBoxes, "Final Image")
            else:
                print("Image not found")

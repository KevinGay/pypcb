import sys, os
from copy import deepcopy
import cv2
import numpy as np
import itertools as it
import numpy.matlib
import itertools as it

def initClusters(b):
    listsoflists = []

    for i in xrange(0, len(b)):
        listsoflists.append([b[i]])

    return listsoflists

def intersection(r1, r2):
    # finds the intersection of all pairs of rectangles from clusters r1 and r2
    # r1 and r2 are lists
    rs1 = np.array(r1)
    rs2 = np.array(r2)

    xa1 = rs1[:,0]
    ya1 = rs1[:,1]
    xa2 = rs1[:,2]
    ya2 = rs1[:,3]

    xb1 = rs2[:,0]
    yb1 = rs2[:,1]
    xb2 = rs2[:,2]
    yb2 = rs2[:,3]

    xx1 = [np.maximum(i,j) for i,j in it.product(xa1, xb1)]
    xx1 = np.array(xx1)
    xx1 = xx1.reshape(len(xa1), len(xb1))

    yy1 = [np.maximum(i,j) for i,j in it.product(ya1, yb1)]
    yy1 = np.array(yy1)
    yy1 = yy1.reshape(len(ya1), len(yb1))

    xx2 = [np.minimum(i,j) for i,j in it.product(xa2, xb2)]
    xx2 = np.array(xx2)
    xx2 = xx2.reshape(len(xa2), len(xb2))

    yy2 = [np.minimum(i,j) for i,j in it.product(ya2, yb2)]
    yy2 = np.array(yy2)
    yy2 = yy2.reshape(len(ya2), len(yb2))

    w = np.maximum(0, xx2 - xx1)
    h = np.maximum(0, yy2 - yy1)

    intersection = w * h

    area1 = (xa2-xa1) * (ya2-ya1)
    area2 = (xb2-xb1) * (yb2-yb1)

    area1a = np.tile(area1, (len(area2),1))
    area2a = np.tile(area2, (len(area1),1))

    area1a = area1a.T

    #tarea = area1a + area2a - intersection
    tarea = np.minimum(area1a, area2a)

    iou = np.divide(intersection,tarea)

    #print "intersection"
    #print intersection
    #print "area"
    #print tarea

    return iou

def clusterBoxes(boxlist):

    # Initialize clusters
    clusts = initClusters(boxlist)

    threshold = 0.01
    tclusts = clusts
    finalCluster = []
    more = 1
    blacklist = []
    while (more == 1):
        tempclust = []
        for i in xrange(0, len(tclusts)):
            if i in blacklist:
                continue
            else:
                c1 = tclusts[i]
                c = deepcopy(c1)
                for j in xrange(0, len(tclusts)):
                    if i == j:
                        continue
                    else:
                        c2 = tclusts[j]
                        inter = intersection(c1, c2)
                        # Check if any iou is greater than the threshold
                        #print inter, (inter >= threshold).sum()
                        count = (inter >= threshold).sum()

                        # if the count is greater than zero then merge the clusters
                        if count > 0:
                            c = c + c2
                            blacklist.append(j)
                tempclust.append(c)
        if len(tempclust) == len(tclusts): # this means that no clusters were merged in the current iteration
            more = 0
            finalCluster = deepcopy(tempclust)
        else:
            more = 1
            tclusts = deepcopy(tempclust)
            blacklist = []

    #clusts = []
    #for c in finalCluster:
    #    if c not in clusts:
    #        clusts.append(c)

    return finalCluster


def getAvgClusterBoxes(cluster):
    boxes = []
    for clust in cluster:
        k = np.array(clust)
        m = np.mean([min(k[:,0]), np.mean(k[:,0])])
        n = np.mean([min(k[:,1]), np.mean(k[:,1])])
        box = [min(k[:,0]), min(k[:,1]), max(k[:,2]), max(k[:,3]), np.mean(k[:,4])]
        #box = [m, n, max(k[:,2]), max(k[:,3]), np.mean(k[:,4])]
        boxes.append(box)
    return boxes


def validateBoxes(boxes, imgSize):
    # checks for the boundary conditions for the boxes with the image
    nBoxes = []
    for i in xrange(0, len(boxes)):
        box = boxes[i]
        if (box[0] > 0 and box[0] < imgSize[1] and box[1] > 0 and box[1] < imgSize[0]):

            if (box[2] > 0 and box[2] < imgSize[1] and box[3] > 0 and box[3] < imgSize[0]):
                nBoxes.append(box)
    return nBoxes

def enclosed(a,b):
    # checks whether b is enclosed in a or not

    # add and subtract to top left and bottom right corners to avoid checking special cases
    k = deepcopy(b)
    k[0] = k[0] + 1
    k[1] = k[1] + 1
    k[2] = k[2] - 1
    k[3] = k[3] - 1

    if (k[0] > a[0] and k[1] > a[1] and k[2] < a[2] and k[3] < a[3]):
        return True
    else:
        return False

def enclosingBoxes(meanCluster):
    clust = []
    isE = np.zeros([len(meanCluster),1])
    #isN = np.zeros([len(meanCluster),1])
    for i in xrange(0, len(meanCluster)):
        a = meanCluster[i]
        for j in xrange(0, len(meanCluster)):
            if i != j:
                b = meanCluster[j]
                if (enclosed(a,b) is True):
                    isE[j] = 1
                    #isN[i] = 1

    for i in xrange(0, len(meanCluster)):
        if (isE[i] == 0):
            clust.append(meanCluster[i])
    return clust

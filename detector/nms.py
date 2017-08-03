import sys
import os
import numpy as np
import PIL


def match_score(b1, b2):
    # sum of the distance between centers of the two bounding
    # boxes and the intersection area of the boxes

    # calculate the centers
    xc1 = (b1[0]+b1[2]) / 2
    yc1 = (b1[1]+b1[3]) / 2
    xc2 = (b2[0]+b2[2]) / 2
    yc2 = (b2[1]+b2[3]) / 2

    dist = sqrt( (xc2 - xc1)**2 + (yc2 - yc1)**2 )

    dx = min(b1[2], b2[2]) - max(b1[0], b2[0])
    dy = min(b1[3], b2[3]) - max(b1[1], b2[1])
    if (dx >= 0) and (dy >= 0):
        area = dx*dy
    else:
        area = 0

    return dist+area

#def box_merge(b1, b2):


def combine_boxes(boxes, overlapThresh=0.07):
    # Combines boxes across scales
    if len(boxes) == 0:
        return []

    # Bs - set of bounding boxes predicted by the regressor network
    # for each class in Cs across all spatial locations at scale s
    # In our case it the boxes variable itself



def nms_max(boxes, overlapThresh=0.3):
    if len(boxes) == 0:
        return []
    #print len(boxes)
    # initialize the list of picked indexes
    pick = []
    # grab the coordinates of the bounding boxes
    x1 = boxes[:,0]
    y1 = boxes[:,1]
    x2 = boxes[:,2]
    y2 = boxes[:,3]
    # compute the area of the bounding boxes and sort the bounding
    # boxes by the bottom-right y-coordinate of the bounding box
    area = (x2 - x1 + 1) * (y2 - y1 + 1)
    idxs = np.argsort(boxes[:,4])

    # keep looping while some indexes still remain in the indexes
    # list
    while len(idxs) > 0:
        # grab the last index in the indexes list and add the
        # index value to the list of picked indexes
        last = len(idxs) - 1
        i = idxs[last]
        pick.append(i)

        # find the largest (x, y) coordinates for the start of
        # the bounding box and the smallest (x, y) coordinates for the end of the bounding box
        xx1 = np.maximum(x1[i], x1[idxs[:last]])
        yy1 = np.maximum(y1[i], y1[idxs[:last]])
        xx2 = np.minimum(x2[i], x2[idxs[:last]])
        yy2 = np.minimum(y2[i], y2[idxs[:last]])

        # compute the width and height of the bounding box
        w = np.maximum(0, xx2 - xx1 + 1)
        h = np.maximum(0, yy2 - yy1 + 1)

        # area of i.
        area_i = np.maximum(0, x2[i] - x1[i] + 1) * np.maximum(0, y2[i] - y1[i] + 1)
        area_array = np.zeros(len(idxs) - 1)
        area_array.fill(area_i)

        # compute the ratio of overlap
        overlap = (w * h) / (area[idxs[:last]]  - w * h + area_array)

        # delete all indexes from the index list that have
        idxs = np.delete(idxs, np.concatenate(([last],np.where(overlap > overlapThresh)[0])))

    # return only the bounding boxes that were picked using the integer data type
    return boxes[pick]


def nms_average(boxes, overlapThresh=0.2):
    result_boxes = []
    if len(boxes) == 0:
        return []

    # initialize the list of picked indexes
    pick = []

    # grab the coordinates of the bounding boxes
    x1 = boxes[:,0]
    y1 = boxes[:,1]
    x2 = boxes[:,2]
    y2 = boxes[:,3]

    # compute the area of the bounding boxes and sort the bounding
    # boxes by the bottom-right y-coordinate of the bounding box
    area = (x2 - x1 + 1) * (y2 - y1 + 1)
    idxs = np.argsort(boxes[:,4])

    # keep looping while some indexes still remain in the indexes
    # list
    while len(idxs) > 0:
        # grab the last index in the indexes list and add the index value to the list of picked indexes
        last = len(idxs) - 1
        i = idxs[last]
        pick.append(i)

        # find the largest (x, y) coordinates for the start of the bounding box
        # and the smallest (x, y) coordinates for the end of the bounding box
        xx1 = np.maximum(x1[i], x1[idxs[:last]])
        yy1 = np.maximum(y1[i], y1[idxs[:last]])
        xx2 = np.minimum(x2[i], x2[idxs[:last]])
        yy2 = np.minimum(y2[i], y2[idxs[:last]])

        # compute the width and height of the bounding box
        w = np.maximum(0, xx2 - xx1 + 1)
        h = np.maximum(0, yy2 - yy1 + 1)

        # area of i.
        area_i = np.maximum(0, x2[i] - x1[i] + 1) * np.maximum(0, y2[i] - y1[i] + 1)
        area_array = np.zeros(len(idxs) - 1)
        area_array.fill(area_i)

        # compute the ratio of overlap
        overlap = (w * h) / (area[idxs[:last]])

        delete_idxs = np.concatenate(([last],np.where(overlap > overlapThresh)[0]))
        # print "delete_idxs:", delete_idxs
        xmin = 10000
        ymin = 10000
        xmax = 0
        ymax = 0
        ave_prob  = 0
        width = x2[i] - x1[i] + 1
        height = y2[i] - y1[i] + 1

        for idx in delete_idxs:
            #print "min and max:", xmin, ymin, xmax, ymax
            ave_prob += boxes[idxs[idx]][4]
            if(boxes[idxs[idx]][0] < xmin):
                xmin = boxes[idxs[idx]][0]
            if(boxes[idxs[idx]][1] < ymin):
                ymin = boxes[idxs[idx]][1]
            if(boxes[idxs[idx]][2] > xmax):
                xmax = boxes[idxs[idx]][2]
            if(boxes[idxs[idx]][3] > ymax):
                ymax = boxes[idxs[idx]][3]
        if(x1[i] - xmin >  0.1 * width):
            xmin = x1[i] - 0.1 * width
        if(y1[i] - ymin > 0.1 * height):
            ymin = y1[i] - 0.1 * height
        if(xmax - x2[i]> 0.1 * width):
            xmax = x2[i]  + 0.1 * width
        if( ymax - y2[i] > 0.1 * height):
            ymax = y2[i] + 0.1 * height

        result_boxes.append([xmin, ymin, xmax, ymax, ave_prob / len(delete_idxs)])

        # delete all indexes from the index list that have
        idxs = np.delete(idxs, delete_idxs)

    # return only the bounding boxes that were picked using the integer data type
    return result_boxes

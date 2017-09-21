
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

sys.path.insert(0, cfg.caffe_root + 'python')
import caffe


# Compute the scales for which the image should be resized
# need the image as argument to get its size

def computeScale(img, mins, maxs):
    scales = []

    min = 0
    max = 0
    if (img.shape[0] > img.shape[1]):
        min = img.shape[1]
        max = img.shape[0]
    else:
        min = img.shape[0]
        max = img.shape[1]

    upScaleCount = 227 / mins

    for i in xrange(1, upScaleCount):
        scales.append(cfg.upscaleFactor*i)

    if (maxs >= 150 and min > 515 and max > 515): # the max IC size must be reduced to 150 so as to get it detected in a 227x227 window
        downscaleCount = maxs / 150
        for i in xrange(1, downscaleCount):
            scales.append(pow(cfg.downscaleFactor, i))

    return scales


def computeScales(img, mins, maxs):
    scales = []
    min = 0
    max = 0
    if (img.shape[0] > img.shape[1]):
        min = img.shape[1]
        max = img.shape[0]
    else:
        min = img.shape[0]
        max = img.shape[1]

    x = mins
    while (x < 227):
        scales.append(227.0/x)
        x = x + 60 # increment the size of the IC by 10 and then find the scaling factor to enlarge it to the size of 227

    y = maxs
    while (y >= 227 and min > 515 and max > 515):
        scales.append(227.0/y)
        y = y - 60

    return scales



"""
def computeScales(img):
    scales = []

    min = 0
    max = 0
    if (img.shape[0] > img.shape[1]):
        min = img.shape[1]
        max = img.shape[0]
    else:
        min = img.shape[0]
        max = img.shape[1]

    # check the min and max IC sizes to decide on the number of upscales and downscales
    # assumes that both coordinates are equal (ICs are square shaped) later to be changed to adapt to rectangular ICs
    upScaleCount = 227 / cfg.min_ic_size[0]

    for i in xrange(1, upScaleCount):
        scales.append(cfg.upscaleFactor*i)

    # get the min size of the image and multiply it with the factor
    min = min * cfg.downscaleFactor
    factor_count = 1

    while (min >= 227): # the 227 is the size of input to Alexnet
        scales.append(pow(cfg.downscaleFactor, factor_count))
        min = min * cfg.downscaleFactor
        factor_count += 1

    return scales
"""


def sliding_window(image, window_size, step_size):
    '''
    This function returns a patch of the input image `image` of size equal
    to `window_size`. The first image returned top-left co-ordinates (0, 0)
    and are increment in both x and y directions by the `step_size` supplied.
    So, the input parameters are -
    * `image` - Input Image
    * `window_size` - Size of Sliding Window
    * `step_size` - Incremented Size of Window
    The function returns a tuple -
    (x, y, im_window)
    where
    * x is the top-left x co-ordinate
    * y is the top-left y co-ordinate
    * im_window is the sliding window image
    '''
    for y in xrange(0, image.shape[0], step_size[1]):
        for x in xrange(0, image.shape[1], step_size[0]):
            yield (x, y, image[y:y + window_size[1], x:x + window_size[0]])




def generateBoundingBox(featureMap, scale):
    # return bounding box locations (xmin, ymin, xmax, ymax)
    #print featureMap.shape[0], featureMap.shape[1], scale
    bbox = []
    stride = cfg.stride
    cellSizeX = cfg.cellSizeX
    cellSizeY = cfg.cellSizeY
    #stride = 30 # These two numbers play a role in picking the bounding box region
    #cellSize = 227 # This number is equal to the input size for the network - changing it will cause absurd results
    for (x,y), prob in np.ndenumerate(featureMap):
        if (prob >= 0.97):
            #print "denumerate: ", y, x, stride, scale, cellSize, prob
            bbox.append([float(stride*y)/scale, float(stride*x)/scale, float(stride*y + cellSizeY - 1)/scale, float(stride*x + cellSizeX - 1)/scale, prob])
    return bbox

def processHeatMaps(out, windows, scale):
    n = len(out)
    boxs = []

    for i in xrange(0,n-1):
        outprob = out[i,1]

        # the offset of the subwindow in the scaled image
        x = windows[i][0]
        y = windows[i][1]

        # generate the bounding boxes
        boxes = generateBoundingBox(outprob, 1) # add the scale after adding the sub-window offset

        if (np.any(boxes)):
            boxes_nms = np.array(boxes)
            true_boxes = nms_max(boxes_nms, overlapThresh=cfg.overlapThresh)
            true_boxes = nms_average(true_boxes, 0.05)
            scaled_boxes = copy.deepcopy(true_boxes)
            for j, box in enumerate(true_boxes):
                scaled_boxes[j][0] += x
                scaled_boxes[j][1] += y
                scaled_boxes[j][2] += x
                scaled_boxes[j][3] += y

                # scale the dimensions to match with the original image
                scaled_boxes[j][0] /= scale
                scaled_boxes[j][1] /= scale
                scaled_boxes[j][2] /= scale
                scaled_boxes[j][3] /= scale

            boxs.extend(scaled_boxes)

    return boxs

def parse_args():
    parser = argparse.ArgumentParser(description='Test a Gender recognition CNN network')
    parser.add_argument('--gpu', dest='gpu_id', help='GPU id to use',
            default=0, type=int)
    parser.add_argument('--proto', dest='prototxt',
                        help='deploy prototxt file defining the network',
                        default=None, type=str)
    parser.add_argument('--model', dest='caffemodel',
                        help='model to test',
                        default=None, type=str)
    parser.add_argument('--meanfile', dest='meanfilename',
			help='mean binaryproto filename',
			default=None, type=str)
    parser.add_argument('--imagelist', dest='imagelist',
			help='image list text filename',
			default=None, type=str)

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()
    return args


def plotHeatmap(img, outprob, title):
    plt.title(title)
    plt.subplot(1,2,1)
    plt.imshow(img)
    plt.subplot(1,2,2)
    plt.imshow(outprob)
    plt.show()

def drawFinalBoxes(img, boxes, title):
    plt.title(title)
    plt.imshow(img)
    currentAxis = plt.gca()
    for box in boxes[:]:
        #print box[0], box[1], box[2], box[3], box[4]
        currentAxis.add_patch(plt.Rectangle((box[0], box[1]), box[2]-box[0], box[3]-box[1], fill=False, edgecolor='r', linewidth=3))
    plt.show()

def drawBoundingBoxes(img, boxes, title):
    plt.title(title)
    plt.imshow(img)
    currentAxis = plt.gca()
    for box in boxes[:]:
        #print box[0], box[1], box[2], box[3], box[4]
        score = "{0:.2f}".format(box[4])
        plt.text(box[0], box[1]-5, str(score), fontsize=10, color='r', weight='extra bold')
        #plt.Rectangle((box[0], box[1]), box[2]-box[0], box[3]-box[1], fill=False, edgecolor='r', linewidth=3)
        #currentAxis.add_patch(plt.text(box[0], box[1], str(score), fontsize=20))
        currentAxis.add_patch(plt.Rectangle((box[0], box[1]), box[2]-box[0], box[3]-box[1], fill=False, edgecolor='r', linewidth=2))
    plt.show()

def loadNet(deployProto, fullConvProto, caffeModel, mode='CPU'):
    if mode == "GPU":
        caffe.set_mode_gpu()
    else:
        caffe.set_mode_cpu()

    net = caffe.Net(deployProto, caffeModel, caffe.TEST)
    fc_params = {pr: (net.params[pr][0].data, net.params[pr][1].data) for pr in cfg.params}

    #for fc in params:
    #    print '{} weights are {} dimensional and biases are {} dimensional'.format(fc, fc_params[fc][0].shape, fc_params[fc]    [1].shape)

    net_full_conv = caffe.Net(fullConvProto, caffeModel, caffe.TEST)

    params_full_conv = ['fc6-conv', 'fc7-conv', 'fc8-conv']

    conv_params = {pr: (net_full_conv.params[pr][0].data, net_full_conv.params[pr][1].data) for pr in params_full_conv}

    #for conv in params_full_conv:
    #    print '{} weights are {} dimensional and biases are {} dimensional'.format(conv, conv_params[conv][0].shape, conv_params[conv][1].shape)

    for pr, pr_conv in zip(cfg.params, params_full_conv):
        conv_params[pr_conv][0].flat = fc_params[pr][0].flat # flat unrolls the arrays
        conv_params[pr_conv][1][...] = fc_params[pr][1]

    #net_full_conv.save(netFullConvModel)
    return net_full_conv


def loadTransformer(net_full_conv, meanFile, reshapeSize=(515, 515)):
    # reshape the data layer to match the size of the image
    net_full_conv.blobs['data'].reshape(1, 3, reshapeSize[0], reshapeSize[1])
    transformer = caffe.io.Transformer({'data': net_full_conv.blobs['data'].data.shape})
    transformer.set_mean('data', np.load(meanFile).mean(1).mean(1))
    transformer.set_transpose('data', (2,0,1))
    transformer.set_channel_swap('data', (2,1,0))
    transformer.set_raw_scale('data', 255.0)
    return transformer


def getMean(meanBinaryProto):
    proto_data = open(meanBinaryProto, "rb").read()
    blob = caffe.proto.caffe_pb2.BlobProto()
    blob.ParseFromString(proto_data)
    arr = np.array( caffe.io.blobproto_to_array(blob) )
    mean = arr[0]
    np.save('./mean.npy', mean)
    return mean

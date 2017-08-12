import os
import sys

caffe_root = '/data0/mahaling/TEXT/CTPN/caffe/'

import numpy as np

class Config:
    MEAN=np.float32([102.9801, 115.9465, 122.7717])
    TEST_GPU_ID=0
    SCALE=600
    MAX_SCALE=1000

    LINE_MIN_SCORE=0.7
    TEXT_PROPOSALS_MIN_SCORE=0.7
    TEXT_PROPOSALS_NMS_THRESH=0.3
    MAX_HORIZONTAL_GAP=50
    TEXT_LINE_NMS_THRESH=0.3
    MIN_NUM_PROPOSALS=2
    MIN_RATIO=1.2
    MIN_V_OVERLAPS=0.7
    MIN_SIZE_SIM=0.7
    TEXT_PROPOSALS_WIDTH=16
    NET_FILE="models/deploy.prototxt"
    MODEL_FILE="models/ctpn_trained_model.caffemodel"

    MIN_CONTOUR_AREA=100

    FONT_MODEL="models/font_model.caffemodel"
    FONT_MEANFILE="models/mean.npy"
    FONT_PROTO="models/font_deploy.prototxt"
    FONT_DIMS=32
    FONT_LBLFILE="models/fontLabels.txt"

def init():
    sys.path.insert(0, caffe_root + 'python')
init()

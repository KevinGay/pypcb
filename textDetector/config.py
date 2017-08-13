import os
import sys


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

    MODELPATH = os.path.dirname(__file__)

    NET_FILE=os.path.join(MODELPATH, "models/ctpn_deploy.prototxt")
    MODEL_FILE=os.path.join(MODELPATH, "models/ctpn_trained_model.caffemodel")

    MIN_CONTOUR_AREA=100

    FONT_MODEL=os.path.join(MODELPATH, "models/font_model.caffemodel")
    FONT_MEANFILE=os.path.join(MODELPATH, "models/font_mean.npy")
    FONT_PROTO=os.path.join(MODELPATH, "models/font_deploy.prototxt")
    FONT_DIMS=32
    FONT_LBLFILE=os.path.join(MODELPATH, "models/fontLabels.txt")

    caffe_root = '/data0/mahaling/TEXT/CTPN/caffe/'


def init():
    c = Config()
    if '/usr/local/caffe/python' in sys.path:
        sys.path.remove('/usr/local/caffe/python')
    sys.path.insert(0, c.caffe_root + 'python')
init()

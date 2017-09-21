
import os
import sys

min_ic_size = (50,50)
max_ic_size = (350, 350)

minSize = 30
maxSize = 350

stride = 32
cellSizeX = 227
cellSizeY = 227
winSize = 515 # This one is the size of the subwindow from a sliding window approach

downscaleFactor = 0.793700526
upscaleFactor = 1.2
overlapThresh = 0.3

params = ['fc6', 'fc7', 'fc8']
params_full_conv = ['fc6-conv', 'fc7-conv', 'fc8-conv']

defaultComponent = "ic"

modelpath = 'models/'
modelpath = os.path.join(os.path.dirname(__file__),'models')
componentPath = os.path.join(modelpath, defaultComponent)
model = os.path.join(componentPath, 'model_' + defaultComponent + '.caffemodel')
prototxt = os.path.join(componentPath, 'deploy.prototxt')
fullConvProto = os.path.join(componentPath, 'fullConv_' + defaultComponent + '.prototxt')
meanfile = os.path.join(componentPath, 'mean_' + defaultComponent + '.npy')


caffe_root = '/data0/mahaling/TEXT/CTPN/caffe/'

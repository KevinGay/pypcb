
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

# model parameters and files
caffeModel = 'models/pcb_ic_tight.caffemodel'
deployProto = 'models/pcb_ic_tight_deploy.prototxt'
fullConvProto = 'models/pcb_ic_tight_full_conv.prototxt'
params = ['fc6', 'fc7', 'fc8']
params_full_conv = ['fc6-conv', 'fc7-conv', 'fc8-conv']
netFullConvModel = 'models/pcbu_full_conv.caffemodel'
meanFile = 'models/mean_IC.npy'
meanBinaryProto = 'models/mean_IC.binaryproto'

caffe_root = '/home/mahaling/Libraries/caffe/'


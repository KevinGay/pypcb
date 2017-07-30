
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

defaultComponent = "ic"

modelpath = 'models/' + defaultComponent
model = os.path.join(modelpath, 'model_' + defaultComponent + '.caffemodel')
prototxt = os.path.join(modelpath, 'deploy.prototxt')
fullConvProto = os.path.join(modelpath, 'fullConv_' + defaultComponent + '.prototxt')
meanfile = os.path.join(modelpath, 'mean_' + defaultComponent + '.npy')


caffe_root = '/home/mahaling/Libraries/caffe/'

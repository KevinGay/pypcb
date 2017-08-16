from config import Config as cfg
from detectors import TextDetector, TextProposalDetector
from other import draw_boxes, resize_im, CaffeModel


import sys
if '/usr/local/caffe/python' in sys.path:
    sys.path.remove('/usr/local/caffe/python')
sys.path.insert(0, cfg.caffe_root + 'python')
import cv2, os, caffe
import os
import numpy as np
from timer import Timer


class TextRecognizer():
    """
    Recognizes text from a given image
    """
    def __init__(self, mode):
        if mode == "GPU":
            caffe.set_mode_gpu()
            caffe.set_device(cfg.TEST_GPU_ID)
        else:
            caffe.set_mode_cpu()

        netfile = cfg.NET_FILE
        modelfile = cfg.MODEL_FILE

        # initialize the detectors
        self.text_proposals_detector=TextProposalDetector(CaffeModel(netfile, modelfile))
        self.text_detector = TextDetector(self.text_proposals_detector)
        self.timer = Timer()

        self.char_classifier = caffe.Classifier(cfg.FONT_PROTO,
                                                cfg.FONT_MODEL,
                                                mean=np.load(cfg.FONT_MEANFILE).mean(1).mean(1),
                                                channel_swap=(2,1,0),
                                                raw_scale=255,
                                                image_dims=(cfg.FONT_DIMS, cfg.FONT_DIMS))
        with open(cfg.FONT_LBLFILE, 'r') as f:
            self.fontLabels = [x.strip() for x in f]

    def detectText(self, image):
        """
        Detects text from the image given its path
        Returns a list of bounding boxes
        """
        if os.path.exists(image):
            img = cv2.imread(image)

            self.timer.tic()
            im, f=resize_im(img, cfg.SCALE, cfg.MAX_SCALE)
            text_lines = self.text_detector.detect(im)
            print("Time: %f"%self.timer.toc())
            return text_lines, f
        else:
            print("Image not found")

    def extractText(self, image, boundingBoxes):
        """
        Extracts the text from a given image using the bounding boxes
        Input - image name and the bounding boxes list
        Output - extracted text images
        """
        extractedText = []
        if os.path.exists(image):
            img = cv2.imread(image)
            for box in boundingBoxes:
                text = img[int(box[1]):int(box[3]),int(box[0]):int(box[2])]
                extractedText.append(text)
        else:
            print("Image not found")
        return extractedText

    def extractCharacters(self, image):
        """
        Extracts characters from a given "text" image
        Input - "image" opencv image
        """
        extractedChars = []
        if image.shape[2] == 3:
            imgGray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            imgGray = image

        # Otsu's Thresholding
        newRet,binaryThreshold = cv2.threshold(imgGray,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)

        # dilation
        rectkernel = cv2.getStructuringElement(cv2.MORPH_RECT,(5,5))
        rectdilation = cv2.dilate(binaryThreshold, rectkernel, iterations = 1)
        outputImage = image.copy()
        npaContours, npaHierarchy = cv2.findContours(rectdilation.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for num, npaContour in enumerate(npaContours):
            if cv2.contourArea(npaContour) > cfg.MIN_CONTOUR_AREA:
                [intX, intY, intW, intH] = cv2.boundingRect(npaContour)
                cv2.rectangle(outputImage,(intX, intY),(intX+intW,intY+intH),(0, 0, 255),2)
                # Get subimage of word and find contours of that word
                imgROI = binaryThreshold[intY:intY+intH, intX:intX+intW]
                subContours, subHierarchy = cv2.findContours(imgROI.copy(),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)

                for n, subContour in enumerate(subContours):
                    [pointX, pointY, width, height] = cv2.boundingRect(subContour)
                    imr = image[intY+pointY:intY+pointY+height, intX+pointX:intX+pointX+width]
                    extractedChars.append(imr)
        return extractedChars

    def recognizeCharacters(self, charList):
        """
        Character classification module
        charList - list of character images
        """
        outList = []
        pred = self.char_classifier.predict(charList)
        detectedChars = []
        for p in pred:
            x = self.fontLabels[p.argmax()]
            detectedChars.append(x)
        #detectedChars = [self.fontLabels[x] for i,p in enumerate(pred) x = self.fontLabels.index(p.argmax)]
        #indexes = [x for i,x in enumerate(self.fontLabels) if x == self.fontLabels[pred[0].argmax()]]
        return detectedChars

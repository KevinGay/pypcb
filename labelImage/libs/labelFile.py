try:
    from PyQt5.QtGui import QImage
except ImportError:
    from PyQt4.QtGui import QImage

from base64 import b64encode, b64decode
try:
    from libs.pascal_voc_io import PascalVocWriter, XML_EXT
except ImportError:
    from pascal_voc_io import PascalVocWriter, XML_EXT
import json
import os.path
import sys

class LabelFileError(Exception):
    pass

class LabelFile(object):
    """
    This class controls the saving and loading of XML label files.
    """

    suffix = XML_EXT

    def __init__(self, filename=None):
        """
        Create a labelFile object.
        :param filename: The name of the label file.
        """
        self.shapes = ()
        self.imagePath = None
        self.imageData = None
        if filename is not None:
            self.load(filename)

    def load(self, filename):
        """
        Load information from a file into the instance variables
        :param filename: 
        :return: 
        """
        try:
            with open(filename, 'rb') as f:
                data = json.load(f)
                imagePath = data['imagePath']
                imageData = b64decode(data['imageData'])
                lineColor = data['lineColor']
                fillColor = data['fillColor']
                shapes = ((s['label'], s['points'], s['line_color'], s['fill_color'])\
                        for s in data['shapes'])
                # Only replace data after everything is loaded.
                self.shapes = shapes
                self.imagePath = imagePath
                self.imageData = imageData
                self.lineColor = lineColor
                self.fillColor = fillColor
        except Exception as e:
            raise LabelFileError(e)

    def save(self, filename, shapes, imagePath, imageData, lineColor=None, fillColor=None):
        """
        Save a XML file.
        :param filename: The name to save the file with. 
        :param shapes: The shapes to save to the XML file.
        :param imagePath: The path to the image that the annotations correspond to.
        :param imageData: The data about the image, including the width, height, and depth.
        :param lineColor: The line color that is saved with the boxes.
        :param fillColor: The fill color that is saved with the boxes.
        """
        try:
            with open(filename, 'wb') as f:
                json.dump(dict(
                    shapes=shapes,
                    lineColor=lineColor, fillColor=fillColor,
                    imagePath=imagePath,
                    imageData=b64encode(imageData)),
                    f, ensure_ascii=True, indent=2)
        except Exception as e:
            raise LabelFileError(e)

    def savePascalVocFormat(self, filename, shapes, imagePath, imageData, lineColor=None, fillColor=None, databaseSrc=None):
        """
        Save a XML in pascal Voc format.
        :param filename: The name to save the file with.
        :param shapes: The shapes to save to the XML file.
        :param imagePath: The path to the image that the annotations correspond to.
        :param imageData: The data about the image, including the width, height, and depth.
        :param lineColor: The line color that is saved with the boxes.
        :param fillColor: The fill color that is saved with the boxes.
        :param databaseSrc: The source of the database that the annotations are located.
        """
        imgFolderPath = os.path.dirname(imagePath)
        imgFolderName = os.path.split(imgFolderPath)[-1]
        imgFileName = os.path.basename(imagePath)
        imgFileNameWithoutExt = os.path.splitext(imgFileName)[0]

        # Read from file path because self.imageData might be empty if saving to
        # Pascal format
        image = QImage()
        image.load(imagePath)
        imageShape = [image.height(), image.width(), 1 if image.isGrayscale() else 3]
        writer = PascalVocWriter(imgFolderName, imgFileNameWithoutExt,\
                                 imageShape, localImgPath=imagePath)
        bSave = False
        for shape in shapes:
            points = shape['points']
            label = shape['label']
            bndbox = LabelFile.convertPoints2BndBox(points)
            writer.addBndBox(bndbox[0], bndbox[1], bndbox[2], bndbox[3], label)
            bSave = True

        if bSave:
            writer.save(targetFile = filename)
        return

    @staticmethod
    def isLabelFile(filename):
        """
        Returns true if the filename has the same suffix as the class variable "suffix".
        :param filename: The filename to test.
        """
        fileSuffix = os.path.splitext(filename)[1].lower()
        return fileSuffix == LabelFile.suffix

    @staticmethod
    def convertPoints2BndBox(points):
        """
        Given points, convert them into a bounding box (xmin, xmax, ymin, ymax).
        :param points: The points to convert.
        :return: The xmin, xmax, ymin, and ymax that correspond to the given points.
        """
        xmin = float('inf')
        ymin = float('inf')
        xmax = float('-inf')
        ymax = float('-inf')
        for p in points:
            x = p[0]
            y = p[1]
            xmin = min(x,xmin)
            ymin = min(y,ymin)
            xmax = max(x,xmax)
            ymax = max(y,ymax)

        # Martin Kersner, 2015/11/12
        # 0-valued coordinates of BB caused an error while
        # training faster-rcnn object detector.
        if (xmin < 1):
            xmin = 1

        if (ymin < 1):
            ymin = 1

        return (int(xmin), int(ymin), int(xmax), int(ymax))

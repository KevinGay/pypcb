#!/usr/bin/python
# -*- coding: utf-8 -*-


try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
except ImportError:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *

try:
    from libs.lib import distance
except ImportError:
    from lib import distance

DEFAULT_LINE_COLOR = QColor(0, 255, 0, 128)
DEFAULT_FILL_COLOR = QColor(255, 0, 0, 128)
DEFAULT_SELECT_LINE_COLOR = QColor(255, 255, 255)
DEFAULT_SELECT_FILL_COLOR = QColor(0, 128, 255, 155)
DEFAULT_VERTEX_FILL_COLOR = QColor(0, 255, 0, 255)
DEFAULT_HVERTEX_FILL_COLOR = QColor(255, 0, 0)

class Shape(object):
    """
    This class represents an annotation bounding box and contains methods for altering them.
    """
    P_SQUARE, P_ROUND = range(2)

    MOVE_VERTEX, NEAR_VERTEX = range(2)

    ## The following class variables influence the drawing
    ## of _all_ shape objects.
    line_color = DEFAULT_LINE_COLOR
    fill_color = DEFAULT_FILL_COLOR
    select_line_color = DEFAULT_SELECT_LINE_COLOR
    select_fill_color = DEFAULT_SELECT_FILL_COLOR
    vertex_fill_color = DEFAULT_VERTEX_FILL_COLOR
    hvertex_fill_color = DEFAULT_HVERTEX_FILL_COLOR
    point_type = P_ROUND
    point_size = 8
    scale = 1.0

    def __init__(self, label=None, line_color=None):
        """
        Create a bounding  box.
        :param label: The label that is associated with the bounding box.
        :param line_color: The line color that is associated with the bounding box.
        """
        self.label = label
        self.points = []
        self.fill = False
        self.selected = False

        self._highlightIndex = None
        self._highlightMode = self.NEAR_VERTEX
        self._highlightSettings = {
            self.NEAR_VERTEX: (4, self.P_ROUND),
            self.MOVE_VERTEX: (1.5, self.P_SQUARE),
            }

        self._closed = False

        if line_color is not None:
            # Override the class line_color attribute
            # with an object attribute. Currently this
            # is used for drawing the pending line a different color.
            self.line_color = line_color

    def close(self):
        """
        Close the shape after the user is done drawing it. 
        """
        self._closed = True

    def reachMaxPoints(self):
        """
        :return: True if there are at least 4 points in the shape. False otherwise. 
        """
        if len(self.points) >=4:
            return True
        return False

    def addPoint(self, point):
        """
        Add a point to the shape.
        :param point: The point to add to the shape.
        """
        if self.points and point == self.points[0]:
            self.close()
        else:
            self.points.append(point)

    def popPoint(self):
        """
        :return: The last value in the list of points. 
        """
        if self.points:
            return self.points.pop()
        return None

    def isClosed(self):
        """
        :return: True if the shape is closed. False otherwise. 
        """
        return self._closed

    def setOpen(self):
        """
        Open the shape.
        """
        self._closed = False

    def paint(self, painter):
        """
        Paint the shape using QPen and the given painter
        :param painter: The QPainter.
        """
        if self.points:
            color = self.select_line_color if self.selected else self.line_color
            pen = QPen(color)
            # Try using integer sizes for smoother drawing(?)
            pen.setWidth(max(1, int(round(2.0 / self.scale))))
            painter.setPen(pen)

            line_path = QPainterPath()
            vrtx_path = QPainterPath()

            line_path.moveTo(self.points[0])
            # Uncommenting the following line will draw 2 paths
            # for the 1st vertex, and make it non-filled, which
            # may be desirable.
            #self.drawVertex(vrtx_path, 0)

            for i, p in enumerate(self.points):
                line_path.lineTo(p)
                self.drawVertex(vrtx_path, i)
            if self.isClosed():
                line_path.lineTo(self.points[0])

            painter.drawPath(line_path)
            painter.drawPath(vrtx_path)
            painter.fillPath(vrtx_path, self.vertex_fill_color)
            if self.fill:
                color = self.select_fill_color if self.selected else self.fill_color
                painter.fillPath(line_path, color)

    def drawVertex(self, path, i):
        """
        Draw the vertex of the shape. 
        :param path: 
        :param i: 
        """
        d = self.point_size / self.scale
        shape = self.point_type
        point = self.points[i]
        if i == self._highlightIndex:
            size, shape = self._highlightSettings[self._highlightMode]
            d *= size
        if self._highlightIndex is not None:
            self.vertex_fill_color = self.hvertex_fill_color
        else:
            self.vertex_fill_color = Shape.vertex_fill_color
        if shape == self.P_SQUARE:
            path.addRect(point.x() - d / 2, point.y() - d / 2, d, d)
        elif shape == self.P_ROUND:
            path.addEllipse(point, d / 2.0, d / 2.0)
        else:
            assert False, "unsupported vertex shape"

    def nearestVertex(self, point, epsilon):
        """
        :param point: The point to compare with all vertices.
        :param epsilon: The epsilon value.
        :return: Return the point that is nearest the the given point. 
        """
        for i, p in enumerate(self.points):
            if distance(p - point) <= epsilon:
                return i
        return None

    def containsPoint(self, point):
        """
        :param point: The point 
        :return: Returns True if the shape contains the given point. False otherwise.
        """
        return self.makePath().contains(point)

    def makePath(self):
        """
        :return: The QPainterPath of the drawn shape.
        """
        path = QPainterPath(self.points[0])
        for p in self.points[1:]:
            path.lineTo(p)
        return path

    def boundingRect(self):
        """
        Draws the bounding rectangle using the QPainterPath
        """
        return self.makePath().boundingRect()

    def moveBy(self, offset):
        """
        Move the shape by the given offset.
        :param offset: The number of pixels to move the shape.
        """
        self.points = [p + offset for p in self.points]

    def moveVertexBy(self, i, offset):
        """
        Move the specified vertex with the given offset.
        :param i: The index of the vertex to move.
        :param offset: The number of pixels to move the vertex.
        """
        self.points[i] = self.points[i] + offset

    def highlightVertex(self, i, action):
        """
        Highlight a vertex using the given action (usually when the user mouses over it).
        :param i: The index of the vertex to move.
        :param action: The action to perform.
        """
        self._highlightIndex = i
        self._highlightMode = action

    def highlightClear(self):
        """
        Clear the highlighting.
        """
        self._highlightIndex = None

    def copy(self):
        """
        Copy this shape.
        :return: Return a copy of this shape.
        """
        shape = Shape("%s" % self.label )
        shape.points= [p for p in self.points]
        shape.fill = self.fill
        shape.selected = self.selected
        shape._closed = self._closed
        if self.line_color != Shape.line_color:
            shape.line_color = self.line_color
        if self.fill_color != Shape.fill_color:
            shape.fill_color = self.fill_color
        return shape

    def __len__(self):
        """
        :return: Return the amount of points in this shape. 
        """
        return len(self.points)

    def __getitem__(self, key):
        return self.points[key]

    def __setitem__(self, key, value):
        self.points[key] = value


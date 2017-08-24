import sys

qt4 = False

try:
    from PyQt4.QtCore import QString
    qt4 = True
except:
    qt4 = False

def ustr(x):
    """
    py2/py3 unicode helper.
    :param x: The string to be converted.
    :return: The converted string.
    """
    if sys.version_info < (3, 0, 0):
        if type(x) == str:
            return x.decode('utf-8')
        if qt4 and type(x) == QString:
            return unicode(x)
        return x
    else:
        return x  # py3
import qtpy
from enum import Enum

''' Handle Minor API Variations Between PyQt5, Pyside6 and Pyside2 '''

__all__ = [
    "getQVariantValue",
    "wheelAngleDelta",
]

def getQVariantValue(variant):
    '''Extract python object from network response'''
    if qtpy.API_NAME in ['PySide6', 'PyQt5']:
        return variant
    else:
        return variant.toPyObject()
        

if qtpy.API_NAME in ['PySide6', 'PyQt5']:
    def wheelAngleDelta(wheelEvent):
        return wheelEvent.angleDelta().y()
    from qtpy.QtCore import QStandardPaths
    def getCacheFolder():
        return QStandardPaths.writableLocation(QStandardPaths.CacheLocation)
else:
    def wheelAngleDelta(wheelEvent):
        return wheelEvent.delta()

    from qtpy.QtGui import QDesktopServices

    def getCacheFolder():
        return QDesktopServices.storageLocation(QDesktopServices.CacheLocation)

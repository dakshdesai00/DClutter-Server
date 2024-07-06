import sys
sys.path.append("..")
from models.fileModel import fileModel
from models.folderModel import folderModel
from redis_om import Migrator
import os

Migrator().run()

def searchFromName(name):
    folders = folderModel.find(folderModel.folder == name).all()
    if os.path.splitext(name)[1] != "":
        files = fileModel.find((fileModel.fileName == os.path.splitext(name)[0]) &
            (fileModel.fileType== os.path.splitext(name)[1])).all()
    else:
        files = fileModel.find(fileModel.fileName == name).all()
    return {
        "files":files,
        "folders": folders
    }

def searchFromFileType(fileType):
    files = fileModel.find(fileModel.fileType == fileType).all()
    return {
        "files":files,
        "folder":[]
    }

def searchFromLastModifiedTime(timeStr):
    files = fileModel.find(fileModel.lastModified == timeStr).all()
    return {
        "files":files,
        "folder":[]
    }

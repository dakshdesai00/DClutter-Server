import sys
from redis_om.model.model import NotFoundError
sys.path.append("..")
from models.fileModel import fileModel
from models.folderModel import folderModel
import os
import shutil
from distutils.dir_util import copy_tree
from functions.fileSystemInRedis import makeFileList

def cutFileTo(parentId,fileId):
    try:
        newParentFolder = folderModel.get(parentId)
        file = fileModel.get(fileId)
        oldParentFolder = folderModel.get(file.parentId)
        file.parentId = parentId
        oldPath = file.path
        newPath = newParentFolder.path+ "/" + os.path.split(oldPath)[1]
        file.path = newPath
        newParentFolder.files.append(file.pk)
        oldParentFolder.files.remove(file.pk)
        oldParentFolder.save()
        newParentFolder.save()
        file.save()
        shutil.move(oldPath,newPath)
        return "Cut Paste done successfully"
    except NotFoundError:
        return "File or folder not found"

def cutFolderTo(parentId,folderId,isCut):
    try:
        newParentFolder = folderModel.get(parentId)
        folder = folderModel.get(folderId)
        oldParentFolder = folderModel.get(folder.parentId)
        if newParentFolder != oldParentFolder:
            oldParentFolder.subDirectory.remove(folder.pk)
            newParentFolder.subDirectory.append(folder.pk)
            folder.parentId = parentId
            oldPath = folder.path
            newPath = newParentFolder.path +"/"+os.path.split(oldPath)[1]
            folder.path = newPath
            oldParentFolder.save()
            newParentFolder.save()
            folder.save()
            if isCut == False:
                shutil.move(oldPath,newPath)
            for fileId in folder.files:
                file = fileModel.get(fileId)
                file.path = newPath + "/" +file.fileName + file.fileType
                file.save()
            for folderId in folder.subDirectory:
                cutFolderTo(folderId=folderId,parentId=folder.pk,isCut=True)
        elif newParentFolder == oldParentFolder:
            oldPath = folder.path
            newPath = newParentFolder.path + "/" + os.path.split(oldPath)[1]
            folder.path = newPath
            newParentFolder.save()
            folder.save()
            if isCut == False:
                shutil.move(oldPath,newPath)
            for fileId in folder.files:
                file = fileModel.get(fileId)
                file.path = newPath + "/" +file.fileName + file.fileType
                file.save()
            for folderId in folder.subDirectory:
                cutFolderTo(folderId=folderId,parentId=folder.pk,isCut=True)
    except NotFoundError:
        return "Folder not found"

def copyFileTo(parentId,fileId):
    try:
        newParentFolder = folderModel.get(parentId)
        newFile = fileModel.get(fileId)
        shutil.copy(newFile.path,newParentFolder.path)
        newFile.parentId = parentId
        newFile.path = newParentFolder.path + "/" + newFile.fileName + newFile.fileType
        newParentFolder.files.append(newFile.pk)
        # newFile.backups=[] NEED TO FIND ITS ALTERNATIVE
        newParentFolder.save()
        newFile.save()
        return "Copy paste done successfully"
    except NotFoundError:
        return "File or folder not found"

def copyFolderTo(parentId,folderId):
    try:
        folder = folderModel.get(folderId)
        newParentFolder = folderModel.get(parentId)
        newPath = newParentFolder.path + "/" + folder.folder
        copy_tree(folder.path,newPath)
        newParentFolder.subDirectory.append(makeFileList(path=newPath,parentId=parentId).pk)
        newParentFolder.save()
        return "Copy paste done successfully"
    except NotFoundError:
        return "File or folder not found"

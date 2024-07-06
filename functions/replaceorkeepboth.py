import sys
from redis_om import NotFoundError
sys.path.append("..")
import os
from models.fileModel import fileModel
from models.folderModel import folderModel
from functions.addFile import addFile,addFolder
from functions.rename import renameFile,renameFolder
from functions.deleteFile import deleteFile,deleteFolder

def replaceFile(oldFileId,content,lastModified,size,newFileName):
    try:
        oldFile = fileModel.get(oldFileId)
        path = oldFile.path
        parentId = oldFile.parentId
        fileName = oldFile.fileName+oldFile.fileType
        if fileName == newFileName:
            deleteFile(oldFileId)
            return addFile(parentId=parentId,fileName=fileName,lastModified=lastModified,content=content,size=size)
        else:
            print("Original file and new file are diffrent")
    except NotFoundError:
        print("Old file not found")

def replaceFolder(oldFolderId,content,zipFolderName):
    try:
        oldFolder = folderModel.get(oldFolderId)
        parentId = oldFolder.parentId
        newName = os.path.splitext(zipFolderName)[0]
        if newName==oldFolder.folder:
            deleteFolder(oldFolderId,isDeleted=False)
            return addFolder(parentId=parentId,content=content,zipFolderName=zipFolderName)
        else:
            print("Original folder and new folder are diffrent")
    except NotFoundError:
        print("Old folder not found")

def keepBothFile(oldFileId,content,lastModified,size,newFileName):
    try:
        oldFile = fileModel.get(oldFileId)
        path = oldFile.path
        parentId = oldFile.parentId
        fileName = oldFile.fileName+oldFile.fileType
        if newFileName==fileName:
            renameFile(id=oldFileId,newName=oldFile.fileName+"_1")
            return addFile(parentId=parentId,fileName=(oldFile.fileName+"_2"+oldFile.fileType),lastModified=lastModified,size=size,content=content)
        else:
            print("Original file and new file are diffrent")
    except NotFoundError:
        print("Old file not found")

def keepBothFolder(oldFolderId,content,zipFolderName):
    try:
        oldFolder = folderModel.get(oldFolderId)
        parentId = oldFolder.parentId
        newName = os.path.splitext(zipFolderName)[0]
        if newName == oldFolder.folder:
            renameFolder(id = oldFolderId,newName=oldFolder.folder + "_1")
            newFolderId= addFolder(parentId=parentId,zipFolderName=zipFolderName,content=content)
            renameFolder(id=newFolderId,newName=oldFolder.folder+"_2")
            return newFolderId
        else:
            print("Original folder and new folder are diffrent")
    except NotFoundError:
        print("Old folder not found")

import sys
sys.path.append("..")
from redis_om.model.model import NotFoundError
from functions.fileSystemInRedis import makeFileList
from models.fileModel import fileModel
from models.folderModel import folderModel
import zipfile
import os

def addFile(parentId,fileName,lastModified,size,content):
    fileSplit = os.path.splitext(fileName)
    try:
        parentFolder = folderModel.get(parentId)
        path = os.path.join(parentFolder.path,fileName)
        if os.path.exists(path):
            return "File already exists use replace or keep both option"
        else:
            file = fileModel(
                fileName = fileSplit[0],
                lastModified = lastModified,
                size = size,
                fileType = fileSplit[1],
                parentId = parentId,
                path=path,
                type="File"
            )
            parentFolder.files.append(file.pk)
            parentFolder.save()
            file.save()
            with open(path,"wb") as f:
                f.write(content)
            return file.pk
    except NotFoundError:
        print("Operation failed!! parent folder not found")

def createFolder(parentId,folderName):
    try:
        parentFolder = folderModel.get(parentId)
        newPath = os.path.join(parentFolder.path,folderName)
        if os.path.exists(newPath):
            return "Folder already exists use replace or keep both option"
        else:
            newFolder = folderModel(
                folder = folderName,
                path = newPath,
                files = [],
                subDirectory = [],
                parentId = parentId
            )
            parentFolder.subDirectory.append(newFolder.pk)
            newFolder.save()
            parentFolder.save()
            os.mkdir(newPath)
            return newFolder.pk
    except NotFoundError:
        print("Operation failed!! parent folder not found")

def addFolder(parentId,zipFolderName,content):
    try:
        parentFolder = folderModel.get(parentId)
        zipPath = parentFolder.path + "/" + zipFolderName
        folderName = os.path.splitext(zipFolderName)[0]
        if os.path.exists(parentFolder.path+"/"+folderName):
            return "Folder already exists use replace or keep both option"
        else:
            with open(zipPath,"wb") as f:
                f.write(content)
            with zipfile.ZipFile(zipPath, 'r') as zip_ref:
                zip_ref.extractall(parentFolder.path)
            os.remove(zipPath)
            folder = makeFileList(parentFolder.path+"/"+folderName,parentFolder.pk)
            parentFolder.subDirectory.append(folder.pk)
            parentFolder.save()
            return folder.pk
    except NotFoundError:
        print("Parent folder not found")

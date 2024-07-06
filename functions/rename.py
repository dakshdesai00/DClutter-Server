import os
import sys
from redis_om.model.model import NotFoundError
sys.path.append('..')
from models.fileModel import fileModel
from models.folderModel import folderModel

def renameFile(id,newName):
    try:
        file = fileModel.get(id)
        file.fileName = newName
        path = os.path.split(file.path)
        newPath = os.path.join(path[0],newName+'.'+path[1].split('.')[-1])
        oldPath = file.path
        file.path = newPath
        os.rename(oldPath,newPath)
        file.save()
        return "done"
    except:
        return "File that is being tried to be renamed is not found"
def renameFolder(id,newName,hasRenamed = False):
    try:
        folder = folderModel.get(id)
        folder.folder = newName
        newPath = folderModel.get(folder.parentId).path + "/" + newName
        oldPath = folder.path
        folder.path = newPath
        folder.save()
        if hasRenamed == False:
            os.rename(oldPath,newPath)
        for fileId in folder.files:
            file = fileModel.get(fileId)
            file.path = newPath + "/" +file.fileName + file.fileType
            file.save()
        for folderId in folder.subDirectory:
            renameFolder(id = folderId,newName=folderModel.get(folderId).folder,hasRenamed=True)
        return "done"
    except NotFoundError:
        return "Folder that is being tried to be renamed is not found"

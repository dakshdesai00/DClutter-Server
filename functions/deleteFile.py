import sys
from redis_om.model.model import NotFoundError
sys.path.append("..")
from models.fileModel import fileModel
from models.folderModel import folderModel
import os
import shutil

def deleteFile(id):
    try:
        file = fileModel.get(id)
        parentFolder = folderModel.get(file.parentId)
        parentFolder.files.remove(id)
        parentFolder.save()
        fileModel.delete(id)
        os.remove(file.path)
        return "done"
    except NotFoundError:
        return "File not found"
def deleteFolder(id,isDeleted=False):
    try:
        folder = folderModel.get(id)
        parentFolder = folderModel.get(folder.parentId)
        parentFolder.subDirectory.remove(id)
        parentFolder.save()
        if isDeleted is False:
            shutil.rmtree(folder.path)
        for folders in folder.subDirectory:
            deleteFolder(folders,isDeleted=True)
        for files in folder.files:
            try:
                file = fileModel.get(files)
                parentFolder = folderModel.get(file.parentId)
                parentFolder.files.remove(files)
                parentFolder.save()
                fileModel.delete(files)
            except NotFoundError:
                print("File not found")
        folderModel.delete(id)

        return "done"
    except NotFoundError:
        return "Folder not found"

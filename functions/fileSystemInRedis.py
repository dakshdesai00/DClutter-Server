import os
import sys
import time
sys.path.append('..')
from models.fileModel import fileModel
from models.folderModel import folderModel

def makeFileList(path,parentId):
    parent,folder = os.path.split(path)
    children = os.listdir(path)
    mainFolder = folderModel(
        folder = folder,
        path = path,
        files = [],
        subDirectory = [],
        parentId = parentId,
        type = "Folder"
    )
    for child in children:
        child_path = os.path.join(path,child)
        if os.path.isdir(child_path):

            res = makeFileList(child_path,mainFolder.pk)
            mainFolder.subDirectory.append(res.pk)


        else:
            fileSplit = os.path.splitext(child)
            file = fileModel(
                fileName = fileSplit[0],
                path = child_path,
                lastModified = time.ctime(os.path.getmtime(child_path)),
                size = os.path.getsize(child_path),
                fileType = fileSplit[1],
                parentId = mainFolder.pk,
                type = "File"
            )
            file.save()
            mainFolder.files.append(file.pk)
    mainFolder.save()
    return mainFolder

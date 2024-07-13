import datetime
import sys
from fastapi import FastAPI, UploadFile, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from redis_om import NotFoundError, Migrator
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from models.fileModel import fileModel
from models.folderModel import folderModel
from models.userModel import userModel
from functions.deleteFile import deleteFile, deleteFolder
from functions.addFile import addFile, addFolder, createFolder
from functions.rename import renameFile, renameFolder
from functions.search import (
    searchFromName,
    searchFromFileType,
    searchFromLastModifiedTime,
)
from functions.fileSystemInRedis import makeFileList
from functions.moveFile import copyFileTo, copyFolderTo, cutFileTo, cutFolderTo
from starlette.formparsers import MultiPartParser
from fastapi.responses import FileResponse
from functions.replaceorkeepboth import (
    keepBothFile,
    keepBothFolder,
    replaceFile,
    replaceFolder,
)
import os
import shutil
from dotenv import load_dotenv
import inquirer
from yaspin import yaspin
import pyfiglet
from yaspin.spinners import Spinners
import subprocess
import socket, errno
from functions.fileSystemInRedis import makeFileList
import uvicorn
import atexit
import signal
import string
import random

load_dotenv()

SecretKey = (
    os.getenv("SecretKey")
    if type(os.getenv("SecretKey")) == str
    else "randomstrthatcanbeputhere"
)
AlgorithmToHash = "HS256"
AcessTokenExpiresInMinutes = 30
MaxSizeInMemory = os.getenv("MaxSizeInMemory")
MultiPartParser.max_file_size = (
    (int(MaxSizeInMemory) if type(MaxSizeInMemory) == str else 1) * 1024 * 1024
)
Migrator().run()

pwdContext = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2Scheme = OAuth2PasswordBearer(tokenUrl="token")


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


def verifyPassword(plainPass, hashPass):
    return pwdContext.verify(plainPass, hashPass)


def hashPass(plainPass):
    return pwdContext.hash(plainPass)


def getUser(userName):
    if not userModel.find(userModel.userName == userName).all():
        return None
    else:
        return userModel.find(userModel.userName == userName).all()[0]


def authUser(userName, password):
    user = getUser(userName)
    if not user:
        return False
    if not verifyPassword(plainPass=password, hashPass=user.hashedPassword):
        return False

    return user


def createUser(
    userName: str, userEmail: str, plainPassword: str, disabled: bool, folderId: str
):
    if not userModel.find(userModel.userName == userName).all():
        user = userModel(
            userName=userName,
            userEmail=userEmail,
            hashedPassword=hashPass(plainPassword),
            disabled=disabled,
            folderId=folderId,
        )
        user.save()
        return user
    else:
        return "User exists"


def createAccessToken(data: dict, expiresDelta: datetime.timedelta | None = None):
    toEncode = data.copy()
    if expiresDelta:
        expire = datetime.datetime.utcnow() + expiresDelta
    else:
        expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=10080)
    toEncode.update({"exp": expire})
    encodeed_jwt = jwt.encode(toEncode, SecretKey, algorithm=AlgorithmToHash)
    return encodeed_jwt


async def getCurrentUser(token: str = Depends(oauth2Scheme)):

    credentialException = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Cannot authenticate",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SecretKey, algorithms=[AlgorithmToHash])
        username = payload.get("sub")
        if username is None:
            raise credentialException
        tokenData = TokenData(username=username)
    except JWTError:
        raise credentialException
    user = getUser(userName=username)
    if user is None:
        raise credentialException
    return user


async def getCurrentUserActive(currentUser: userModel = Depends(getCurrentUser)):
    if currentUser.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return currentUser


app = FastAPI(title="DClutter Server")


@app.post("/token", response_model=Token)
async def loginForAccessToken(formData: OAuth2PasswordRequestForm = Depends()):
    user = authUser(userName=formData.username, password=formData.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect data",
            headers={"WWW-Authenticate": "Bearer"},
        )
    accessTokenExpires = datetime.timedelta(minutes=AcessTokenExpiresInMinutes)
    accessToken = createAccessToken(
        data={"sub": user.userName}, expiresDelta=accessTokenExpires
    )
    return {"access_token": accessToken, "token_type": "bearer"}


@app.get("/{folderId}")
async def openFolder(
    folderId: str, curentUser: userModel = Depends(getCurrentUserActive)
):
    try:
        folder = folderModel.get(folderId)
        folderStructure = {
            "folder": folder.folder,
            "path": folder.path,
            "parentId": folder.parentId,
            "subDirectory": [],
            "files": [],
        }
        for subDirectory in folder.subDirectory:
            subDirectoryDetails = {
                "folder": folderModel.get(subDirectory).folder,
                "id": subDirectory,
                "parentId": folder.pk,
            }
            folderStructure["subDirectory"].append(subDirectoryDetails)
        for file in folder.files:
            folderStructure["files"].append(fileModel.get(file))
        return folderStructure
    except NotFoundError:
        return "Folder not found"


@app.delete("/deletefile/{id}")
async def deleteFileRequest(
    id: str, curentUser: userModel = Depends(getCurrentUserActive)
):
    return deleteFile(id)


@app.delete("/deletefolder/{id}")
async def deleteFolderRequest(
    id: str, curentUser: userModel = Depends(getCurrentUserActive)
):
    return deleteFolder(id)


@app.post("/addfile/{parentId}")
async def addFileRequest(
    parentId: str,
    file: UploadFile,
    curentUser: userModel = Depends(getCurrentUserActive),
):
    data = await file.read()
    return addFile(
        parentId=parentId,
        fileName=file.filename,
        lastModified=datetime.datetime.now().isoformat(),
        size=file.size,
        content=data,
    )


@app.post("/replacefile/{parentId}")
async def replaceFileRequest(
    oldFileId: str,
    file: UploadFile,
    curentUser: userModel = Depends(getCurrentUserActive),
):
    data = await file.read()
    return replaceFile(
        oldFileId=oldFileId,
        size=file.size,
        content=data,
        lastModified=datetime.datetime.now().isoformat(),
        newFileName=file.filename,
    )


@app.post("/keepbothfile/{parentId}")
async def keepBothFileRequest(
    oldFileId: str,
    file: UploadFile,
    curentUser: userModel = Depends(getCurrentUserActive),
):
    data = await file.read()
    return keepBothFile(
        oldFileId=oldFileId,
        size=file.size,
        content=data,
        lastModified=datetime.datetime.now().isoformat(),
        newFileName=file.filename,
    )


@app.post("/keepbothfolder/{parentId}")
async def keepBothFolderRequest(
    oldFolderId: str,
    file: UploadFile,
    curentUser: userModel = Depends(getCurrentUserActive),
):
    data = await file.read()
    return keepBothFolder(
        oldFolderId=oldFolderId, content=data, zipFolderName=file.filename
    )


@app.post("/replacefolder/{parentId}")
async def replaceFolderRequest(
    oldFolderId: str,
    file: UploadFile,
    curentUser: userModel = Depends(getCurrentUserActive),
):
    data = await file.read()
    return replaceFolder(
        oldFolderId=oldFolderId, content=data, zipFolderName=file.filename
    )


@app.post("/addfolder/{parentId}")
async def addFolderRequest(
    parentId: str,
    file: UploadFile,
    curentUser: userModel = Depends(getCurrentUserActive),
):
    data = await file.read()
    return addFolder(parentId=parentId, content=data, zipFolderName=file.filename)


@app.post("/createfolder/{parentId}")
async def createFolderRequest(
    parentId: str,
    folderName: str,
    curentUser: userModel = Depends(getCurrentUserActive),
):
    return createFolder(parentId=parentId, folderName=folderName)


@app.put("/renamefile/{id}")
async def renameFileRequest(
    id: str, newName: str, curentUser: userModel = Depends(getCurrentUserActive)
):
    return renameFile(id=id, newName=newName)


@app.put("/renamefolder/{id}")
async def renameFolderRequest(
    id: str, newName: str, curentUser: userModel = Depends(getCurrentUserActive)
):
    return renameFolder(id=id, newName=newName)


@app.get("/searchbyname/{name}")
async def searchByNameRequest(
    name: str, curentUser: userModel = Depends(getCurrentUserActive)
):
    return searchFromName(name)


@app.get("/searchbyfiletype/{type}")
async def searchByTypeRequest(
    type: str, curentUser: userModel = Depends(getCurrentUserActive)
):
    return searchFromFileType(type)


@app.get("/searchbytime/{time}")
async def searchByTimeRequest(
    time: str, curentUser: userModel = Depends(getCurrentUserActive)
):
    return searchByTimeRequest(time)


@app.put("/cutpastefile/{parentId}")
async def cutPasteFileRequest(
    parentId: str, fileId: str, curentUser: userModel = Depends(getCurrentUserActive)
):
    return cutFileTo(parentId=parentId, fileId=fileId)


@app.put("/cutpastefolder/{parentId}")
async def cutPasteFolderRequest(
    parentId: str, folderId: str, curentUser: userModel = Depends(getCurrentUserActive)
):
    msg = cutFolderTo(parentId=parentId, folderId=folderId, isCut=False)
    if msg is None:
        return "Done"
    else:
        return msg


@app.put("/copypastefile/{parentId}")
async def copyPasteFileRequest(
    parentId: str, fileId: str, curentUser: userModel = Depends(getCurrentUserActive)
):
    return copyFileTo(parentId=parentId, fileId=fileId)


@app.put("/copypastefolder/{parentId}")
async def copyPasteFolderRequest(
    parentId: str, folderId: str, curentUser: userModel = Depends(getCurrentUserActive)
):
    return copyFolderTo(parentId=parentId, folderId=folderId)


@app.get("/getfilebyid/{id}")
async def getFileByIdRequest(
    id: str, curentUser: userModel = Depends(getCurrentUserActive)
):
    try:
        file = fileModel.get(id)
        return FileResponse(file.path)
    except NotFoundError:
        return "File does not exist"


def deleteTempZipFolder(path: str):
    os.remove(path)


@app.get("/getfolderbyid/{id}")
async def downloadFolderByIdRequest(
    id: str,
    background_tasks: BackgroundTasks,
    curentUser: userModel = Depends(getCurrentUserActive),
):
    tempFile = str(
        "".join(random.choices(string.ascii_lowercase + string.digits, k=15))
    )
    try:
        folder = folderModel.get(id)
        parentFolderPath = folderModel.get(folder.parentId).path
        shutil.make_archive(
            base_name=tempFile,
            root_dir=folder.path,
            format="zip",
        )
        path = folder.path + "/" + tempFile + ".zip"
        background_tasks.add_task(deleteTempZipFolder, path)
        return FileResponse(path)

    except NotFoundError:
        return "Folder does not exist"


pid = -1


def exit_handler():
    if pid != -1:
        os.kill(pid, signal.SIGTERM)


def kill_handler(*args):
    if pid != -1:
        os.kill(pid, signal.SIGTERM)


atexit.register(exit_handler)
signal.signal(signal.SIGINT, kill_handler)
signal.signal(signal.SIGTERM, kill_handler)


def deleteUserRequest():
    questions = [
        inquirer.Text(
            "userName",
            message="Enter username",
        ),
        inquirer.Password("password", message="Enter password"),
    ]
    answers = inquirer.prompt(questions)
    if answers != None:
        userName = answers["userName"]
        password = answers["password"]
        if userName != "" and password != "":
            user = authUser(userName=userName, password=password)
            if user == False:
                print("Wrond password")
            else:
                id = user.pk
                user.delete(id)
                print("User deleted")
        else:
            print("Enter details again")
    else:
        print("Enter details again")


def updateUserPassRequest():
    questions = [
        inquirer.Text(
            "userName",
            message="Enter username",
        ),
        inquirer.Password("oldpassword", message="Enter old password"),
        inquirer.Password("newpassword", message="Enter new password"),
    ]
    answers = inquirer.prompt(questions)
    if answers != None:
        userName = answers["userName"]
        oldpassword = answers["oldpassword"]
        newpassword = answers["newpassword"]
        if userName != "" and oldpassword != "" and newpassword != "":
            user = authUser(userName=userName, password=oldpassword)
            if user == False:
                print("Wrond password")
            else:
                newhashPass = hashPass(newpassword)
                user.hashedPassword = newhashPass
                user.save()
                print("User password changed")
        else:
            print("Enter details again")
    else:
        print("Enter details again")


def disableUserRequest():
    questions = [
        inquirer.Text(
            "userName",
            message="Enter username",
        ),
        inquirer.Password("password", message="Enter password"),
    ]
    answers = inquirer.prompt(questions)
    if answers != None:
        userName = answers["userName"]
        password = answers["password"]
        if userName != "" and password != "":
            user = authUser(userName=userName, password=password)
            if user == False:
                print("Wrond old password")
            else:
                user.disabled = True
                user.save()
                print("User disabled")
        else:
            print("Enter details again")
    else:
        print("Enter details again")


def createUserRequest():
    questions = [
        inquirer.Text(
            "userName",
            message="Enter username",
        ),
        inquirer.Text("userEmail", message="Enter useremail"),
        inquirer.Password("password", message="Enter password"),
    ]
    answers = inquirer.prompt(questions)
    if answers != None:
        userName = answers["userName"]
        userEmail = answers["userEmail"]
        password = answers["password"]
        if userName != "" and userEmail != "" and password != "":
            try:
                parentFolder = folderModel.find(folderModel.parentId == "parent").all()[
                    0
                ]
                result = createUser(
                    userName=answers["userName"],
                    userEmail=answers["userEmail"],
                    plainPassword=answers["password"],
                    disabled=False,
                    folderId=parentFolder.pk,
                )
                if result == "User exists":
                    print("User exists")
                else:
                    print("User created")
            except NotFoundError:
                print("error")

        else:
            print("Enter details again")

    else:
        print("Enter details again")


def makeFileListRequest():
    questions = [
        inquirer.Path(
            "folderPath",
            message="Enter folder path to make it a remote share",
            path_type=inquirer.Path.DIRECTORY,
        ),
    ]
    pathAnswer = inquirer.prompt(questions)
    if pathAnswer != None:
        if os.path.exists(pathAnswer["folderPath"]):
            with yaspin(Spinners.dots, text="Indexing file system") as sp:
                global parentFolderId
                parentFolderId = makeFileList(pathAnswer["folderPath"], "parent").pk
                sp.ok("✅")
        else:
            print("Path entered does not exists\n")
            makeFileListRequest()


if __name__ == "__main__":

    if os.path.exists(os.getcwd() + "/.config"):
        serverPort: int
        with open(".config", "r+") as file:
            serverPort = int(file.read())
        if os.name == "nt":
            os.system("cls")
        else:
            os.system("clear")
        dclutterText = pyfiglet.figlet_format("DClutter Server", font="big")
        print(dclutterText)
        pid = subprocess.Popen(
            ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", f"{serverPort}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        ).pid
        print(f"Server is running on port {serverPort} with pid of {pid}")
        questions = [
            inquirer.List(
                "operations",
                message="What do you want to do?",
                choices=[
                    "Create User Account",
                    "Update Password of an Account",
                    "Disable an Account",
                    "Delete an Account",
                    "Quit",
                ],
            ),
        ]
        while True:
            answers = inquirer.prompt(questions)
            if answers != None:
                if answers["operations"] == "Create User Account":
                    createUserRequest()
                elif answers["operations"] == "Update Password of an Account":
                    updateUserPassRequest()
                elif answers["operations"] == "Disable an Account":
                    disableUserRequest()
                elif answers["operations"] == "Delete an Account":
                    deleteUserRequest()
                elif answers["operations"] == "Quit":
                    sys.exit()
    else:
        if os.name == "nt":
            os.system("cls")
        else:
            os.system("clear")
        HOST = "localhost"
        serverPort: int
        quitPrompt = ""
        parentFolderId = ""
        dclutterText = pyfiglet.figlet_format("DClutter Server", font="big")
        print(dclutterText)
        makeFileListRequest()

        questions = [
            inquirer.Text(
                "userName",
                message="Enter username",
            ),
            inquirer.Text("userEmail", message="Enter useremail"),
            inquirer.Password("password", message="Enter password"),
        ]
        while True:
            if quitPrompt != "q":
                answers = inquirer.prompt(questions)
                if answers != None:
                    userName = answers["userName"]
                    userEmail = answers["userEmail"]
                    password = answers["password"]
                    if userName != "" and userEmail != "" and password != "":
                        result = createUser(
                            userName=answers["userName"],
                            userEmail=answers["userEmail"],
                            plainPassword=answers["password"],
                            disabled=False,
                            folderId=parentFolderId,
                        )
                        if result == "User exists":
                            print("User exists")
                        else:
                            print("User created")
                    else:
                        print("Enter details again")
                        continue
                else:
                    print("Enter details again")
                    continue
                print(
                    "Enter q if you want to quit or press enter to continue creating users."
                )
                quitPrompt = input("")
            elif quitPrompt == "q":

                break

        questions = [
            inquirer.Text(
                "ServerPort",
                message="Enter port to run server? (4 digit integer)",
            )
        ]

        while True:
            answers = inquirer.prompt(questions)
            if answers != None:
                try:
                    serverPort = int(answers["ServerPort"])
                    with yaspin(Spinners.dots, text="Starting server") as sp:
                        if serverPort > 999 & serverPort < 10000:
                            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            try:
                                sock.bind((HOST, serverPort))
                                sock.close()
                                with open(".config", "w+") as file:
                                    file.write(str(serverPort))
                                pid = subprocess.Popen(
                                    [
                                        "uvicorn",
                                        "main:app",
                                        "--host",
                                        "0.0.0.0",
                                        "--port",
                                        f"{serverPort}",
                                    ],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                ).pid
                                print(f"\nFile server started at {serverPort}")
                                break
                            except socket.error as e:
                                if e.errno == errno.EADDRINUSE:
                                    print("\nPort is already in use", serverPort)
                                    print("Try diffrent port")
                                else:
                                    print(
                                        f"\n****Port: {serverPort} cannot be acessed****"
                                    )
                                    print("Try diffrent port")
                                continue
                        else:
                            print("Enter a 4 digit integer")
                            continue
                except ValueError:
                    print("Enter a 4 digit integer")
                    continue
        if os.name == "nt":
            os.system("cls")
        else:
            os.system("clear")
        print(dclutterText)
        questions = [
            inquirer.List(
                "operations",
                message="What do you want to do?",
                choices=[
                    "Create User Account",
                    "Update Password of an Account",
                    "Disable an Account",
                    "Delete an Account",
                    "Quit",
                ],
            ),
        ]
        while True:
            answers = inquirer.prompt(questions)
            if answers != None:
                if answers["operations"] == "Create User Account":
                    createUserRequest()
                elif answers["operations"] == "Update Password of an Account":
                    updateUserPassRequest()
                elif answers["operations"] == "Disable an Account":
                    disableUserRequest()
                elif answers["operations"] == "Delete an Account":
                    deleteUserRequest()
                elif answers["operations"] == "Quit":
                    sys.exit()

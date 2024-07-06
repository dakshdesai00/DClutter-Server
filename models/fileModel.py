from typing import Optional
from redis_om import (
    Field,
    JsonModel,
    get_redis_connection
)
import sys
import os
from dotenv import load_dotenv
sys.path.append("..")
load_dotenv()
port = os.getenv("DBPORT")
print(port)
redis = get_redis_connection(port = int(port)) if type(port) == str else get_redis_connection(port = 6379)

class fileModel(JsonModel):
    fileName:str = Field(index=True)
    path:str
    lastModified: str = Field(index=True)
    size: int
    fileType: str = Field(index=True)
    type :str = Field(index=True)
    parentId:str = Field(index=True)
    class Meta:
            database = redis

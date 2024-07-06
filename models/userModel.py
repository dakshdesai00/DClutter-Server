from redis_om import Field, JsonModel,get_redis_connection
import sys
import os
from dotenv import load_dotenv
sys.path.append("..")
load_dotenv()
port = os.getenv("DBPORT")
print(port)
redis = get_redis_connection(port = int(port)) if type(port) == str else get_redis_connection(port = 6379)
class userModel(JsonModel):
    userName:str = Field(index=True)
    userEmail:str
    hashedPassword:str
    disabled:bool
    folderId:str
    class Meta:
            database = redis

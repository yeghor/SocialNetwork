# SocialNetwork project
This is my the most **serious** project.

It is prototype of social network like Twitter _(now X)_. 

Stack of this project includes:
- fastAPI
- Pydantic
- SQLalchemy *(PostgresSQL)* - As a main database. 
- Redis - For storing short living data, like: JWTs, viewed posts excluding, temporary image urls _(when using the local storage)_. _Async_
- ChromaDD - For user posts feed related to his history. 
- AioBotocore - For **AWS S3**.
- etc.

Project architecture complete with following SOLID principles, also it is asynchronous and easy to develop/expand.

Work with images *(user avatars, post pictures) impemented by using **S3** *(AioBotocore)* or **LocalStorage**. Can be shosen in `.env` file.

Interactions with `/media` router in LocalStorage all the same as in **S3** implementation.

Authorization handeled with password hashing and two JWT tokens:
- Refresh token - long termed. Used to refresh access token.
- Acces token - short termed.

Post interactions include basic CRUD operations like:
- Creating post
- Post editing
- Post deleting
- etc.

And advanced popularity rate system. Post popularity depends on user activity. This guarantees that user feed will always be **fresh**.

User feed contain mixed posts: *(proportions can be setted in `.env` file)*
- History related
- Unrelevant popular posts - Just fresh and popular posts
- Following posts - Post from users you follow to

# Usage
Requirements - Docker, Python 3.12.0 or higher.
To run this application, follow these steps:

## Backend 
**Copy the repository:**
```bash
git clone https://github.com/yeghor/SocialNetwork.git
```

**Setup python virtual environment _(optional)_**
```bash
cd SocialNetwork/Backend
python -m venv myenv

# On Windows
myenv\Scripts\activate.bat

# On Mac
cd myenv
source bin/activate
cd ..
```
---
**Install requirements:**
```bash
pip install -r requirements.txt
pip install python-magic-bin==0.4.14
```
---
**Open `.env` file and choose image storage**
```env
USE_S3 = "False" # Set to 'False' to use local storage
```
To use S3, you need to setup your AWS S3 buckets and enter their names in `.env` file
```env
USE_S3 = "True"

S3_BUCKET_NAME = "socialnetwork2025"
S3_BUCKET_NAME_TEST = "socialnetwork2025test"
```
Then you have to configure your AWS credentials _(secret key)_ through AWS CLI. Follow steps: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-quickstart.html
---
**Run Redis, ChromaDB, PostgresSQL using docker:**
```bash
docker run --name postgres_container -e POSTGRES_USER=database -e POSTGRES_PASSWORD=password -e POSTGRES_DB=database -p 5432:5432 -d postgres
docker run -d --name redis -p 6379:6379 redis
docker run -v ./chroma-data:/data -p 8000:8000 chromadb/chroma
```
---
**Run the application:**
```bash
uvicorn main:app --reload
```

## Frontend

  **To be continued...**

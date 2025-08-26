# SocialNetwork project
This is my the most **serious** project.

It is a prototype of social network similar to Twitter _(now X)_. 

Stack of this project includes:
- fastAPI
- Pydantic
- SQLalchemy *(PostgreSQL)* - As a main database. 
- Redis - For storing short living data, like: JWTs, viewed posts excluding, temporary image urls _(when using the local storage)_. _Async_
- ChromaDD - For user posts feed related to his history. 
- AioBotocore - For **AWS S3**.
- etc.

Project architecture complete with following SOLID principles, also it is asynchronous and easy to develop/expand.

Work with images (user avatars, post pictures) impemented by using **S3** *(AioBotocore)* or **LocalStorage**. Can be shosen in `.env` file.

Interactions with `/media` router in LocalStorage all the same as in **S3** implementation.

Authorization handeled with password hashing and two JWT tokens:
- Refresh token - long termed. Used to refresh access token.
- Access token - short termed.

Post interactions include basic CRUD operations.
And advanced popularity rate system. Post popularity depends on user activity. It guarantees that user feed will always be **fresh**.

User feed contain mixed posts: *(proportions can be setted in `.env` file)*
- History related
- Unrelevant popular posts - Just fresh and popular posts
- Following posts - Post from users you follow to

This project has `docker-compose.yml` file, so it is allow you to start the application executing only one command.

# Usage
Requirements - Docker, Python 3.12.0 or higher.
To run this application, follow these steps:

**Copy the repository:**
```bash
git clone https://github.com/yeghor/SocialNetwork.git
```

**Move to repository directory:**
```bash
cd SocialNetwork
```

**Run `docker-compose.yml`**
```bash
docker compose up
```

Acces your backend application by this URL:
Https://0.0.0.0:8800/docs

## Frontend

  **To be continued...**

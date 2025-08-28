# Social Network project
This is my most **serious** project.

It is a prototype of a social network similar to Twitter _(now X)_. 

**Stack of this project includes:**
- fastAPI
- Pydantic
- SQLalchemy *(PostgreSQL)* - As a main database. 
- Redis - For storing short-lived data, like: JWTs, viewed posts excluding temporary image URLs _(when using the local storage)_. _Async_
- ChromaDB - For user posts feed related to their history. 
- AioBotocore - For **AWS S3**.

**Features:**
- **Architecture** built on SOLID principles, also it is fully asynchronous and easy to _develop_/_expand_.
- **Images** support user avatars and post pictures. Storage can be chosen in `.env` file (**AWS S3** via **AioBotocore**, **Local Storage**)

- **Authorization** handled with password hashing and two JWT tokens:
  - **Refresh** token - long termed. Used to refresh access token.
  - **Access** token - short termed.
- **Feed** unique to every user. It works by post popularity rate and chromaDB semantic search
  - **Popularity rate** is a dynamic field in each post, value depends on user activity. The rate is secured from fake activity abusing.
  - **ChromaDB Semantic Search** provides vectorized search to find relevant posts to user view history.
  The feed contains mixed posts _(proportions can be seted in `.env` file)_
    - **History related** _(Semantic Search)_
    - **Unrelated**, but popular and fresh posts
    - **Following posts** from users you follow to _(If no follows - returns **Unrelated**)_

This project has a `docker-compose.yml` file, so it allows you to start the application by executing only one line.

Also the project has basic **CI** _(Implemented with GitHub actions)_ that runs tests on every **push**.

**Next step**: Implement fronted, notifications

# Usage

> Requirements - Docker, Python 3.12.0 or higher.
> 
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
---

In case you managed to run the application **not** using `docker-compose`. 

**Change** HOST variables values in `.env` file to `localhost`!
Example:
```env
REDIS_HOST = "localhost" # from redis_db
CHROMADB_HOST = "localhost" # from "chromadb_db"
DB_HOST = "localhost" # from "postgres_db"
```
---

**Acces** your backend application by this URL:
[https://0.0.0.0:8800/docs](http://127.0.0.1:8800/)

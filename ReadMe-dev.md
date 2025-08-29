## Local image storage
This application suport choice using between S3 and Local storage to store images.

#### Local images naming:
- Post: {PostId}-{ImageNumber}.png/jpg
- User: {UserId}.png/jpg

Filenames **must** be unique

## Dependencies
Required pips on Windows:
pip install python-magic-bin==0.4.14

### AWS CLI
If this error: The AWS Access Key Id you provided does not exist in our records.
Update your AWS CLI

## Tests
Tests can be only in `backend` directory, due to import issues. 
Sonn will be fixed

## Debug mode

The `DEBUG` variable in the `.env` file controls how the application handles exceptions:

- `DEBUG=True` — when an exception is raised, you will see the full stack trace. Exceptions are not written to the log file.  
- `DEBUG=False` — the application raises client-safe FastAPI `HTTPException`s and records them in the `.log` file.
## Local image storage
This application suport choice using between S3 and Local storage to store images.

#### Local images naming:
- Post: {PostId}-{ImageNumber}.png/jpg
- User: {UserId}.png/jpg

Filenames **must** be unique

If libmagic module not found - pip install python-magic-bin==0.4.14

Required pips:
pip install python-magic-bin==0.4.14
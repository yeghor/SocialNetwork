import mimetypes

# Example MIME types
mime_type_text = "text/plain"
mime_type_jpeg = "image/jpeg"
mime_type_pdf = "application/pdf"
mime_type_unknown = "application/x-some-custom-type"

# Guess extensions
extension_text = mimetypes.guess_extension(mime_type_text)
extension_jpeg = mimetypes.guess_extension(mime_type_jpeg)
extension_pdf = mimetypes.guess_extension(mime_type_pdf)
extension_unknown = mimetypes.guess_extension(mime_type_unknown)

print(f"Extension for '{mime_type_text}': {extension_text}")
print(f"Extension for '{mime_type_jpeg}': {extension_jpeg}")
print(f"Extension for '{mime_type_pdf}': {extension_pdf}")
print(f"Extension for '{mime_type_unknown}': {extension_unknown}")

import glob


print(glob.glob("test*", root_dir="backend/media/prod_media/posts"))
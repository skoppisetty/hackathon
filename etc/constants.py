IMAGE_LICENSES = {
  "CC0": ["CC0", "(Public Domain)", "http://creativecommons.org/publicdomain/zero/1.0/", "http://mirrors.creativecommons.org/presskit/buttons/80x15/png/publicdomain.png"],
  "CC BY": ["CC BY", "(Attribution)", "http://creativecommons.org/licenses/by/4.0/", "http://mirrors.creativecommons.org/presskit/buttons/80x15/png/by.png"],
  "CC BY-SA": ["CC BY-SA", "(Attribution-ShareAlike)", "http://creativecommons.org/licenses/by-sa/4.0/", "http://mirrors.creativecommons.org/presskit/buttons/80x15/png/by-sa.png"],
  "CC BY-NC": ["CC BY-NC", "(Attribution-Non-Commercial)", "http://creativecommons.org/licenses/by-nc/4.0/", "http://mirrors.creativecommons.org/presskit/buttons/80x15/png/by-nc.png"],
  "CC BY-NC-SA": ["CC BY-NC-SA", "(Attribution-NonCommercial-ShareAlike)", "http://creativecommons.org/licenses/by-nc-sa/4.0/", "http://mirrors.creativecommons.org/presskit/buttons/80x15/png/by-nc-sa.png"]
};

ALLOWED_FILES = '(.*?)\.(jpg|jpeg|tiff|tif)$'
'''
Regex of allowed files. Will be matched case-insensitively.
'''

EXTENSION_MEDIA_TYPES = {
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".tiff": "image/tiff",
  ".tif": "image/tiff",
}

INPUT_CSV_FIELDNAMES = (
  "idigbio:OriginalFileName", "idigbio:MediaGUID"
)

G_DEFAULT_CSV_OUTPUT_NAME = 'media_records.csv'

IMAGES_TABLENAME = 'imagesV9_0_2'
BATCHES_TABLENAME = 'batchesV9_0_2'

IMAGE_CSV_NAME = "image.csv"
STUB_CSV_NAME = "stub.csv"
ZIP_NAME = "iDigBio_output.zip"

class FieldNameException(Exception):
  def __init__(self, msg, reason=''):
    Exception.__init__(self, msg)
    self.reason = reason

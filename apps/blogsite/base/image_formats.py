# image_formats.py
from django.utils.translation import gettext_lazy as _
from wagtail.images.formats import Format, register_image_format, unregister_image_format

# unregister_image_format
# register_image_format(Format('thumbnail', 'Thumbnail', 'richtext-image thumbnail', 'max-120x120'))
unregister_image_format('fullwidth')
unregister_image_format('left')
unregister_image_format('right')
register_image_format(Format('fullwidth', _('Full width'), 'rounded img-fluid w-sm-100', 'width-2000'))
register_image_format(Format('left', _('Left-aligned'), 'float-sm-start p-sm-2 img-fluid w-sm-50', 'width-1000'))
register_image_format(Format('right', _('Right-aligned'), 'float-sm-end p-sm-2 img-fluid w-sm-50', 'width-1000'))

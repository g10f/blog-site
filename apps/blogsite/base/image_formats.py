# image_formats.py
from django.utils.translation import gettext_lazy as _
from wagtail.images.formats import Format, register_image_format, unregister_image_format

#unregister_image_format
#register_image_format(Format('thumbnail', 'Thumbnail', 'richtext-image thumbnail', 'max-120x120'))
unregister_image_format('fullwidth')
unregister_image_format('left')
unregister_image_format('right')
register_image_format(Format('fullwidth', _('Full width'), 'richtext-image full-width', 'width-800'))
register_image_format(Format('left', _('Left-aligned'), 'float-md-start rounded img-fluid', 'width-1000'))
register_image_format(Format('right', _('Right-aligned'), 'float-md-end rounded img-fluid', 'width-1000'))

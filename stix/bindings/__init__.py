# Copyright (c) 2017, The MITRE Corporation. All rights reserved.
# See LICENSE.txt for complete terms.

import collections

from lxml import etree as etree_
import mixbox.xml

from xml.sax import saxutils
import re
import base64
from datetime import datetime, tzinfo, timedelta


TypeInfo = collections.namedtuple("TypeInfo", ('ns', 'typename'))

CDATA_START = "<![CDATA["
CDATA_END = "]]>"

ExternalEncoding = 'utf-8'
Tag_pattern_ = re.compile(r'({.*})?(.*)')

# These are only used internally
_tzoff_pattern = re.compile(r'(\+|-)((0\d|1[0-3]):[0-5]\d|14:00)$')
_Tag_strip_pattern_ = re.compile(r'\{.*\}')


def get_type_info(node):
    """Returns a ``TypeInfo`` object for `node`.

    This is accomplished by parsing the ``xsi:type`` attribute found on
    `node`.

    Args:
        node: An lxml.etree element object.

    Raises:
        KeyError: If `node` does not have an ``xsi:type`` attribute.

    """
    xsi_type = node.attrib[mixbox.xml.TAG_XSI_TYPE]
    typeinfo = xsi_type.split(":")

    if len(typeinfo) == 2:
        prefix, typename = typeinfo
    else:
        typename = typeinfo
        prefix = None

    ns = node.nsmap[prefix]
    return TypeInfo(ns=ns, typename=typename)


#: A mapping of namespace/type information to binding classes.
_BINDING_EXTENSION_MAP = {}


def add_extension(cls):
    """Adds the binding class `cls` to the ``_EXTENSION_MAP``.

    This enables the lookup and instantiation of classes during parse when
    ``xsi:type`` attributes are encountered.

    """
    typeinfo = TypeInfo(ns=cls.xmlns, typename=cls.xml_type)
    _BINDING_EXTENSION_MAP[typeinfo] = cls


def register_extension(cls):
    """Class decorator for registering a binding class as an implementation of
    an xml type.

    Classes must have ``xmlns`` and ``xml_type`` class attributes to be
    registered.

    """
    add_extension(cls)
    return cls


def lookup_extension(typeinfo, default=None):
    """Looks up the binding class for `typeinfo`, which is a namespace/typename
    pairing.

    Args:
        typeinfo: An lxml Element node or a stix.bindings.TypeInfo namedtuple.
        default: A binding class that will be returned if typeinfo is an
            Element without an xsi:type attribute.

    Returns:
        A binding class that has been registered for the namespace and typename
        found on `typeinfo`.

    """
    if not isinstance(typeinfo, TypeInfo):
        if has_xsi_type(typeinfo):
            typeinfo = get_type_info(typeinfo)
        elif default:
            return default

    if typeinfo in _BINDING_EXTENSION_MAP:
        return _BINDING_EXTENSION_MAP[typeinfo]

    fmt = "No class implemented or registered for XML type '{%s}%s'"
    error = fmt % (typeinfo.ns, typeinfo.typename)
    raise NotImplementedError(error)


def has_xsi_type(node):
    """Returns ``True`` if `node` does not have an xsi:type attribute.

    """
    return mixbox.xml.TAG_XSI_TYPE in node.attrib


def _cast(typ, value):
    if typ is None or value is None:
        return value
    return typ(value)


def showIndent(lwrite, level, pretty_print=True):
    if pretty_print:
        lwrite('    ' * level)


def quote_attrib(text):
    if not text:
        return ''

    return saxutils.quoteattr(text)


def find_attr_value_(attr_name, node):
    attrs = node.attrib
    attr_parts = attr_name.split(':')
    value = None
    if len(attr_parts) == 1:
        value = attrs.get(attr_name)
    elif len(attr_parts) == 2:
        prefix, name = attr_parts
        namespace = node.nsmap.get(prefix)
        if namespace is not None:
            value = attrs.get('{%s}%s' % (namespace, name, ))
    return value


def raise_parse_error(node, msg):
    msg = '%s (element %s/line %d)' % (msg, node.tag, node.sourceline)
    raise GDSParseError(msg)


def quote_xml(text):
    if not text:
        return ''

    if text.startswith(CDATA_START):
        return text

    return saxutils.escape(text)


def get_all_text_(node):
    if node.text is not None:
        text = node.text
    else:
        text = ''
    for child in node:
        if child.tail is not None:
            text += child.tail
    return text


def parsexml_(*args, **kwargs):
    if 'parser' not in kwargs:
        # Use the lxml ElementTree compatible parser so that, e.g.,
        # we ignore comments.
        kwargs['parser'] = etree_.ETCompatXMLParser(huge_tree=True)
    return etree_.parse(*args, **kwargs)


class GDSParseError(Exception):
    pass


class _FixedOffsetTZ(tzinfo):

    def __init__(self, offset, name):
        self.__offset = timedelta(minutes=offset)
        self.__name = name

    def utcoffset(self, dt):
        return self.__offset

    def tzname(self, dt):
        return self.__name

    def dst(self, dt):
        return None


class GeneratedsSuper(object):

    def gds_format_string(self, input_data, input_name=''):
        return input_data

    def gds_validate_string(self, input_data, node, input_name=''):
        return input_data

    def gds_format_base64(self, input_data, input_name=''):
        return base64.b64encode(input_data)

    def gds_validate_base64(self, input_data, node, input_name=''):
        return input_data

    def gds_format_integer(self, input_data, input_name=''):
        return '%d' % int(input_data)

    def gds_validate_integer(self, input_data, node, input_name=''):
        return input_data

    def gds_format_integer_list(self, input_data, input_name=''):
        return '%s' % input_data

    def gds_validate_integer_list(self, input_data, node, input_name=''):
        values = input_data.split()
        for value in values:
            try:
                fvalue = float(value)
            except (TypeError, ValueError) as exp:
                raise_parse_error(node, 'Requires sequence of integers')
        return input_data

    def gds_format_float(self, input_data, input_name=''):
        return '%f' % input_data

    def gds_validate_float(self, input_data, node, input_name=''):
        return input_data

    def gds_format_float_list(self, input_data, input_name=''):
        return '%s' % input_data

    def gds_validate_float_list(self, input_data, node, input_name=''):
        values = input_data.split()
        for value in values:
            try:
                fvalue = float(value)
            except (TypeError, ValueError) as exp:
                raise_parse_error(node, 'Requires sequence of floats')
        return input_data

    def gds_format_double(self, input_data, input_name=''):
        return '%e' % input_data

    def gds_validate_double(self, input_data, node, input_name=''):
        return input_data

    def gds_format_double_list(self, input_data, input_name=''):
        return '%s' % input_data

    def gds_validate_double_list(self, input_data, node, input_name=''):
        values = input_data.split()
        for value in values:
            try:
                fvalue = float(value)
            except (TypeError, ValueError) as exp:
                raise_parse_error(node, 'Requires sequence of doubles')
        return input_data

    def gds_format_boolean(self, input_data, input_name=''):
        return ('%s' % input_data).lower()

    def gds_validate_boolean(self, input_data, node, input_name=''):
        return input_data

    def gds_format_boolean_list(self, input_data, input_name=''):
        return '%s' % input_data

    def gds_validate_boolean_list(self, input_data, node, input_name=''):
        values = input_data.split()
        for value in values:
            if value not in ('true', '1', 'false', '0'):
                msg = ('Requires sequence of booleans '
                       '("true", "1", "false", "0")')
                raise_parse_error(node, msg)
        return input_data

    def gds_validate_datetime(self, input_data, node, input_name=''):
        return input_data

    def gds_format_datetime(self, input_data, input_name=''):
        if isinstance(input_data, str):
            return input_data
        if input_data.microsecond == 0:
            _svalue = input_data.strftime('%Y-%m-%dT%H:%M:%S')
        else:
            _svalue = input_data.strftime('%Y-%m-%dT%H:%M:%S.%f')
        if input_data.tzinfo is not None:
            tzoff = input_data.tzinfo.utcoffset(input_data)
            if tzoff is not None:
                total_seconds = tzoff.seconds + (86400 * tzoff.days)
                if total_seconds == 0:
                    _svalue += 'Z'
                else:
                    if total_seconds < 0:
                        _svalue += '-'
                        total_seconds *= -1
                    else:
                        _svalue += '+'
                    hours = total_seconds // 3600
                    minutes = (total_seconds - (hours * 3600)) // 60
                    _svalue += '{0:02d}:{1:02d}'.format(hours, minutes)
        return _svalue

    def gds_parse_datetime(self, input_data, node, input_name=''):
        tz = None
        if input_data[-1] == 'Z':
            tz = _FixedOffsetTZ(0, 'GMT')
            input_data = input_data[:-1]
        else:
            results = _tzoff_pattern.search(input_data)
            if results is not None:
                tzoff_parts = results.group(2).split(':')
                tzoff = int(tzoff_parts[0]) * 60 + int(tzoff_parts[1])
                if results.group(1) == '-':
                    tzoff *= -1
                tz = _FixedOffsetTZ(tzoff, results.group(0))
                input_data = input_data[:-6]
        if len(input_data.split('.')) > 1:
            dt = datetime.strptime(input_data, '%Y-%m-%dT%H:%M:%S.%f')
        else:
            dt = datetime.strptime(input_data, '%Y-%m-%dT%H:%M:%S')
        return dt.replace(tzinfo=tz)

    def gds_validate_date(self, input_data, node, input_name=''):
        return input_data

    def gds_format_date(self, input_data, input_name=''):
        _svalue = input_data.strftime('%Y-%m-%d')
        if input_data.tzinfo is not None:
            tzoff = input_data.tzinfo.utcoffset(input_data)
            if tzoff is not None:
                total_seconds = tzoff.seconds + (86400 * tzoff.days)
                if total_seconds == 0:
                    _svalue += 'Z'
                else:
                    if total_seconds < 0:
                        _svalue += '-'
                        total_seconds *= -1
                    else:
                        _svalue += '+'
                    hours = total_seconds // 3600
                    minutes = (total_seconds - (hours * 3600)) // 60
                    _svalue += '{0:02d}:{1:02d}'.format(hours, minutes)
        return _svalue

    def gds_parse_date(self, input_data, node, input_name=''):
        tz = None
        if input_data[-1] == 'Z':
            tz = _FixedOffsetTZ(0, 'GMT')
            input_data = input_data[:-1]
        else:
            results = _tzoff_pattern.search(input_data)
            if results is not None:
                tzoff_parts = results.group(2).split(':')
                tzoff = int(tzoff_parts[0]) * 60 + int(tzoff_parts[1])
                if results.group(1) == '-':
                    tzoff *= -1
                tz = _FixedOffsetTZ(tzoff, results.group(0))
                input_data = input_data[:-6]
        return datetime.strptime(input_data, '%Y-%m-%d').replace(tzinfo=tz)

    def gds_str_lower(self, instring):
        return instring.lower()

    def get_path_(self, node):
        path_list = []
        self.get_path_list_(node, path_list)
        path_list.reverse()
        path = '/'.join(path_list)
        return path

    def get_path_list_(self, node, path_list):
        if node is None:
            return
        tag = _Tag_strip_pattern_.sub('', node.tag)
        if tag:
            path_list.append(tag)
        self.get_path_list_(node.getparent(), path_list)

    def get_class_obj_(self, node, default_class=None):
        class_obj1 = default_class
        if 'xsi' in node.nsmap:
            classname = node.get('{%s}type' % node.nsmap['xsi'])
            if classname is not None:
                names = classname.split(':')
                if len(names) == 2:
                    classname = names[1]
                class_obj2 = globals().get(classname)
                if class_obj2 is not None:
                    class_obj1 = class_obj2
        return class_obj1

    def gds_build_any(self, node, type_name=None):
        return None


__all__ = [
    '_cast',
    'TypeInfo',
    'add_extension',
    'etree_',
    'get_type_info',
    'has_xsi_type',
    'lookup_extension',
    'register_extension',
    'showIndent',
    'quote_attrib',
    'ExternalEncoding',
    'Tag_pattern_',
    'find_attr_value_',
    'raise_parse_error',
    'GeneratedsSuper',
    'quote_xml',
    'get_all_text_',
    'parsexml_',
    'CDATA_START',
    'CDATA_END'
]

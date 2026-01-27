# -*- coding: utf-8 -*-
import os
import sys
import time
from datetime import date, datetime, timedelta, tzinfo
from itertools import chain, product
import pytest
import six

from scrapy_rss.utils import (format_rfc822, is_strict_subclass, get_full_class_name,
                              deprecated_module, deprecated_class, deprecated_func)


class A0:
    def foo(self):
        pass
    class B0:
        def bar(self):
            pass

class C0(A0):
    pass

class D0(C0):
    pass


@pytest.mark.parametrize("dt,timezone_offset,valid", chain(
    product([
        date.today(),
        datetime.now(),
        datetime(2000, 1, 1, 0, 0, 0),
        datetime(2010, 12, 28, 1, 1, 1),
        datetime(2020, 12, 28, 23, 59, 59),
    ],
    [-10, 0, 10] if sys.version_info[0:2] >= (3,) and sys.version_info[0:2] <= (3, 3)
        else [-10, -4, -1, 0, 2, 5, 10],
    [True]
), [
    ('Fri, 01 Dec 2000 23:59:59 +0000', None, True),
    ('Fri, 01 Dec 2000 23:59:59 -0500', None, True),
    ('invalid date', None, False),
    ('Fri, 31 Nov 2000 23:59:59 +0000', None, False),
    ('Sat, 32 Dec 2000 23:59:59 +0000', None, False),
    ('Fri, 01 Dec 2000 24:59:59 +0000', None, False),
    ('Fri, 01 Dec 2000 23:60:59 +0500', None, False),
    ('Fri, 01 Dec 2000 23:59:60 +0500', None, False),
    ('Fri, 01 Dem 2000 23:59:59 +0500', None, False),
    ('Fri, 01 Dec 2000 23:59:59 +050', None, False),
    ('Fri, 01 Dec 200 23:59:59 +0000', None, False),
]))
def test_format_rfc822(dt, timezone_offset, valid):
    class TzOffset(tzinfo):
        def __init__(self, name, offset):
            self._name = name
            self._offset = timedelta(seconds=offset.total_seconds())

        def utcoffset(self, dt):
            return self._offset

        def dst(self, dt):
            return timedelta(0)

        def tzname(self, dt):
            return self._name

        def fromutc(self, dt):
            return dt + self._offset

    weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    if timezone_offset is not None:
        tz = TzOffset('Etc/GMT{:+}'.format(-timezone_offset), timedelta(hours=timezone_offset))
    else:
        tz = None
    if isinstance(dt, datetime):
        dt = dt.replace(tzinfo=tz)
        expected = ('{}, {:02} {} {} {:02}:{:02}:{:02} {:+03}00'
                    .format(weekdays[dt.weekday()], dt.day, months[dt.month - 1], dt.year,
                            dt.hour, dt.minute, dt.second, timezone_offset))
        if valid:
            actual = format_rfc822(dt)
        else:
            with pytest.raises(ValueError):
                format_rfc822(dt)
            return

    elif isinstance(dt, date):
        old_os_tz = os.environ.get('TZ', None)
        try:
            os.environ['TZ'] = tz.tzname(None)
            time.tzset()
            if valid:
                actual = format_rfc822(dt)
            else:
                with pytest.raises(ValueError):
                    format_rfc822(dt)
                return
        finally:
            if old_os_tz:
                os.environ['TZ'] = old_os_tz
            else:
                del os.environ['TZ']
            time.tzset()
        expected = ('{}, {:02} {} {} 00:00:00 {:+03}00'
                    .format(weekdays[dt.weekday()], dt.day, months[dt.month - 1], dt.year,
                            timezone_offset))
    else:
        expected = dt
        if valid:
            actual = format_rfc822(dt)
        else:
            with pytest.raises(ValueError):
                format_rfc822(dt)
            return
    assert actual == expected

@pytest.mark.parametrize("tz_offset,tz_name",
                         ((n, 'Etc/GMT{:+}'.format(-n) if abs(n) >= 10 or n == 0
                              else {-1: 'Atlantic/Cape_Verde', 2: 'Europe/Kaliningrad'}[n])
                          for n in  [-10, -1, 0, 2, 10]))
def test_tzlocal(tz_offset, tz_name):
    from scrapy_rss.utils import get_tzlocal

    old_os_tz = os.environ.get('TZ', None)
    try:
        os.environ['TZ'] = tz_name
        time.tzset()
        dt_tz = datetime.now(get_tzlocal())
        dt_naive = datetime.now()
        actual_offset = dt_tz.tzinfo.utcoffset(dt_naive)
        expected_offset = timedelta(seconds=60*60*tz_offset)
    finally:
        if old_os_tz:
            os.environ['TZ'] = old_os_tz
        else:
            del os.environ['TZ']
        time.tzset()
    assert actual_offset == expected_offset


@pytest.mark.parametrize("cls,base_cls,expected", [
    (int, int, False),
    (int, float, False),
    (float, int, False),
    (A0, A0, False),
    (C0, A0, True),
    (A0, C0, False),
    (D0, A0, True),
    (D0, C0, True),
])
def test_is_strict_subclass(cls, base_cls, expected):
    assert is_strict_subclass(cls, base_cls) == expected


@pytest.mark.parametrize("obj,expected_name",[
    (int, 'int'),
    (str, 'str'),
    (get_full_class_name, 'scrapy_rss.utils.get_full_class_name'),
    (datetime, 'datetime.datetime'),
    (A0, 'tests.test_utils.A0'),
    (A0.foo, 'tests.test_utils.A0.foo' if six.PY3 else 'tests.test_utils.foo'),
    (A0.B0, 'tests.test_utils.A0.B0' if six.PY3 else 'tests.test_utils.B0'),
    (A0.B0.bar, 'tests.test_utils.A0.B0.bar' if six.PY3 else 'tests.test_utils.bar'),
])
def test_get_full_class_name(obj, expected_name):
    actual = get_full_class_name(obj)
    assert actual == expected_name


def test_get_full_class_name_with_bad_object():
    with pytest.raises(TypeError, match='object does not have __name__'):
        get_full_class_name(None)


def test_deprecated_module():
    with pytest.warns(DeprecationWarning):
        deprecated_module('Message')


def test_deprecated_class():
    @deprecated_class('Message')
    class A(object):
        pass

    with pytest.warns(DeprecationWarning):
        A()

    with pytest.raises(TypeError, match='Unsupported reason type'):
        @deprecated_class
        class B:
            pass


def test_deprecated_func():
    @deprecated_func('Message')
    def func_a():
        pass

    with pytest.warns(DeprecationWarning):
        func_a()

    with pytest.raises(TypeError, match='Unsupported reason type'):
        @deprecated_func
        def func_b():
            pass


if __name__ == '__main__':
    pytest.main()

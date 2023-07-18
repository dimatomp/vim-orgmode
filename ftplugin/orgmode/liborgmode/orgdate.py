# -*- coding: utf-8 -*-
u"""
    OrgDate
    ~~~~~~~~~~~~~~~~~~

    This module contains all date/time/timerange representations that exist in
    orgmode.

    There exist three different kinds:

    * OrgDate: is similar to a date object in python and it looks like
      '2011-09-07 Wed'.

    * OrgDateTime: is similar to a datetime object in python and looks like
      '2011-09-07 Wed 10:30'

    * OrgTimeRange: indicates a range of time. It has a start and and end date:
      * <2011-09-07 Wed>--<2011-09-08 Fri>
      * <2011-09-07 Wed 10:00-13:00>

    All OrgTime oblects can be active or inactive.
"""

import datetime
import re
from dateutil.relativedelta import relativedelta

from orgmode.py3compat.encode_compatibility import *
from abc import abstractmethod

# <2011-09-12 Mon>
_DATE_REGEX = re.compile(r"(?<!-)<(\d\d\d\d)-(\d\d)-(\d\d) [A-Z]\w\w>(?!-)", re.UNICODE)
# <2011-09-12 Mon +1w>
_DATE_REGEX_REPEATED = re.compile(r"<(\d\d\d\d)-(\d\d)-(\d\d) [A-Z]\w\w \+([1-9])(d|wd|w|m|wm)>", re.UNICODE)
# [2011-09-12 Mon]
_DATE_PASSIVE_REGEX = re.compile(r"\[(\d\d\d\d)-(\d\d)-(\d\d) [A-Z]\w\w\]", re.UNICODE)

# <2011-09-12 Mon 10:20>
_DATETIME_REGEX = re.compile(
    r"(?<!-)<(\d\d\d\d)-(\d\d)-(\d\d) [A-Z]\w\w (\d{1,2}):(\d\d)>(?!-)", re.UNICODE)
# <2011-09-12 Mon 10:20 +1w>
_DATETIME_REGEX_REPEATED = re.compile(
    r"<(\d\d\d\d)-(\d\d)-(\d\d) [A-Z]\w\w (\d{1,2}):(\d\d) \+([1-9])(d|wd|w|m|wm)>", re.UNICODE)
# [2011-09-12 Mon 10:20]
_DATETIME_PASSIVE_REGEX = re.compile(
    r"(?<!-)\[(\d\d\d\d)-(\d\d)-(\d\d) [A-Z]\w\w (\d{1,2}):(\d\d)\](?!-)", re.UNICODE)

_DATETIMERANGE_PASSIVE_REGEX = re.compile(
    # <2011-09-12 Mon 10:00>--
    r"\[(\d\d\d\d)-(\d\d)-(\d\d) [A-Z]\w\w (\d\d):(\d\d)\]--"
    # <2011-09-12 Mon 11:00>
    "\[(\d\d\d\d)-(\d\d)-(\d\d) [A-Z]\w\w (\d\d):(\d\d)\]", re.UNICODE)

# <2011-09-12 Mon>--<2011-09-13 Tue>
_DATERANGE_REGEX = re.compile(
    # <2011-09-12 Mon>--
    r"<(\d\d\d\d)-(\d\d)-(\d\d) [A-Z]\w\w>--"
    # <2011-09-13 Tue>
    r"<(\d\d\d\d)-(\d\d)-(\d\d) [A-Z]\w\w>", re.UNICODE)
# <2011-09-12 Mon 10:00>--<2011-09-12 Mon 11:00>
_DATETIMERANGE_REGEX = re.compile(
    # <2011-09-12 Mon 10:00>--
    r"<(\d\d\d\d)-(\d\d)-(\d\d) [A-Z]\w\w (\d\d):(\d\d)>--"
    # <2011-09-12 Mon 11:00>
    r"<(\d\d\d\d)-(\d\d)-(\d\d) [A-Z]\w\w (\d\d):(\d\d)>", re.UNICODE)
# <2011-09-12 Mon 10:00--12:00>
_DATETIMERANGE_SAME_DAY_REGEX = re.compile(
    r"<(\d\d\d\d)-(\d\d)-(\d\d) [A-Z]\w\w (\d\d):(\d\d)-(\d\d):(\d\d)>", re.UNICODE)


def get_orgdates(data):
    u"""
    Parse the given data (can be a string or list). Return an OrgDate if data
    contains a string representation of an OrgDate; otherwise return None.

    data can be a string or a list containing strings.
    active can be boolean if either active or inactive date is requested or None if any date is fine
    """
    # TODO maybe it should be checked just for iterable? Does it affect here if
    # in base __getitem__(slice(i,j)) doesn't return a list but userlist...
    if isinstance(data, list):
        return ((date, line) for idx, line in enumerate(data) for date in _text2orgdate(line))
    return ((date, data) for date in _text2orgdate(data))


def _text2orgdate(string, active=None):
    u"""
    Transform the given string into an OrgDate.
    Return an OrgDate if data contains a string representation of an OrgDate;
    otherwise return None.

    active can be boolean if either active or inactive date is requested or None if any date is fine
    """
    # handle active datetime with same day
    for result in re.finditer(_DATETIMERANGE_SAME_DAY_REGEX, string):
        try:
            (syear, smonth, sday, shour, smin, ehour, emin) = \
                [int(m) for m in result.groups()]
            start = datetime.datetime(syear, smonth, sday, shour, smin)
            end = datetime.datetime(syear, smonth, sday, ehour, emin)
            yield OrgTimeRange(True, start, end)
        except BaseException:
            return

    # handle active datetime range
    for result in re.finditer(_DATETIMERANGE_REGEX, string):
        try:
            tmp = [int(m) for m in result.groups()]
            (syear, smonth, sday, shour, smin, eyear, emonth, eday, ehour, emin) = tmp
            start = datetime.datetime(syear, smonth, sday, shour, smin)
            end = datetime.datetime(eyear, emonth, eday, ehour, emin)
            yield OrgTimeRange(True, start, end)
        except BaseException:
            return

    # handle active date range
    for result in re.finditer(_DATERANGE_REGEX, string):
        try:
            tmp = [int(m) for m in result.groups()]
            syear, smonth, sday, eyear, emonth, ehour = tmp
            start = datetime.date(syear, smonth, sday)
            end = datetime.date(eyear, emonth, ehour)
            yield OrgTimeRange(True, start, end)
        except BaseException:
            return

    # handle active repeated datetime
    for result in re.finditer(_DATETIME_REGEX_REPEATED, string):
        try:
            year, month, day, hour, minutes, period = [int(m) for m in result.groups()[:-1]]
            unit = result.groups()[-1]
            yield OrgRepeatedDateTime(True, year, month, day, hour, minutes, period, unit)
        except BaseException:
            return

    # handle active datetime
    for result in re.finditer(_DATETIME_REGEX, string):
        try:
            year, month, day, hour, minutes = [int(m) for m in result.groups()]
            yield OrgDateTime(True, year, month, day, hour, minutes)
        except BaseException:
            return

    # handle passive datetime range
    for result in re.finditer(_DATETIMERANGE_PASSIVE_REGEX, string):
        try:
            tmp = [int(m) for m in result.groups()]
            (syear, smonth, sday, shour, smin, eyear, emonth, eday, ehour, emin) = tmp
            start = datetime.datetime(syear, smonth, sday, shour, smin)
            end = datetime.datetime(eyear, emonth, eday, ehour, emin)
            yield OrgTimeRange(False, start, end)
        except BaseException:
            return

    # handle passive datetime
    for result in re.finditer(_DATETIME_PASSIVE_REGEX, string):
        try:
            year, month, day, hour, minutes = [int(m) for m in result.groups()]
            yield OrgDateTime(False, year, month, day, hour, minutes)
        except BaseException:
            return

    # handle passive dates
    for result in re.finditer(_DATE_PASSIVE_REGEX, string):
        try:
            year, month, day = [int(m) for m in result.groups()]
            yield OrgDate(False, year, month, day)
        except BaseException:
            return

    # handle active repeated dates
    for result in re.finditer(_DATE_REGEX_REPEATED, string):
        try:
            year, month, day, period = [int(m) for m in result.groups()[:-1]]
            unit = result.groups()[-1]
            yield OrgRepeatedDate(True, year, month, day, period, unit)
        except BaseException:
            return

    # handle active dates
    for result in re.finditer(_DATE_REGEX, string):
        try:
            year, month, day = [int(m) for m in result.groups()]
            yield OrgDate(True, year, month, day)
        except BaseException:
            return

class OrgRepeatedTimeBase:
    def __init__(self, period, unit):
        self.period = period
        self.unit = unit

    def _advance(self):
        date = self.date()
        raw_date = datetime.date(date.year, date.month, date.day)
        if self.unit[-1] == 'd':
            next = raw_date + datetime.timedelta(days=self.period)
            if len(self.unit) == 2 and next.weekday() > 4:
                next += datetime.timedelta(days=7 - next.weekday())
        elif self.unit[-1] == 'w':
            next = raw_date + datetime.timedelta(days=7 * self.period)
        elif self.unit[-1] == 'm':
            next = raw_date + relativedelta(months=self.period)
            if len(self.unit) == 2 and next.weekday() != self.weekday():
                farther_next = next + datetime.timedelta(days=(self.weekday() - next.weekday() + 7) % 7)
                next = farther_next if farther_next.month == next.month else next - datetime.timedelta(days=(next.weekday() - self.weekday() + 7) % 7)
        return next

    @abstractmethod
    def next(self): pass

    @abstractmethod
    def date(self): pass

    def _period_str(self):
        return '+%d%s' % (self.period, self.unit)

class OrgDate(datetime.date):
    u"""
    OrgDate represents a normal date like '2011-08-29 Mon'.

    OrgDates can be active or inactive.

    NOTE: date is immutable. That's why there needs to be __new__().
    See: http://docs.python.org/reference/datamodel.html#object.__new__
    """
    def __init__(self, active, year, month, day):
        self.active = active
        pass

    def __new__(cls, active, year, month, day):
        return datetime.date.__new__(cls, year, month, day)

    def __unicode__(self):
        u"""
        Return a string representation.
        """
        if self.active:
            return self.strftime(u'<%Y-%m-%d %a>')
        else:
            return self.strftime(u'[%Y-%m-%d %a]')

    def __str__(self):
        return u_encode(self.__unicode__())

    def timestr(self):
        return '--:--'
    
    def latest_time(self):
        return datetime.datetime.combine(self, datetime.time(23, 59))

    def date(self):
        return self

    def strftime(self, fmt):
        return u_decode(datetime.date.strftime(self, u_encode(fmt)))

class OrgRepeatedDate(OrgDate, OrgRepeatedTimeBase):
    u"""
    OrgRepeatedDate represents a repeated date like '2011-08-29 Mon +1w'.

    OrgRepeatedDates can be active or inactive.

    NOTE: date is immutable. That's why there needs to be __new__().
    See: http://docs.python.org/reference/datamodel.html#object.__new__
    """
    def __init__(self, active, year, month, day, period, unit):
        OrgDate.__init__(self, active, year, month, day)
        OrgRepeatedTimeBase.__init__(self, period, unit)
        pass

    def __new__(cls, active, year, month, day, period, unit):
        return OrgDate.__new__(cls, active, year, month, day)

    def __unicode__(self):
        u"""
        Return a string representation.
        """
        if self.active:
            return self.strftime(u'<%Y-%m-%d %a ' + self._period_str() + '>')
        else:
            return self.strftime(u'[%Y-%m-%d %a ' + self._period_str() + ']')

    def date(self):
        return OrgDate(self.active, self.year, self.month, self.day)

    def next(self):
        next = self._advance()
        return OrgRepeatedDate(self.active, next.year, next.month, next.day, self.period, self.unit)

class OrgDateTime(datetime.datetime):
    u"""
    OrgDateTime represents a normal time like '2011-08-29 Mon 11:00'.

    OrgDateTime can be active or inactive.

    NOTE: datetime is immutable. That's why there needs to be __new__().
    See: http://docs.python.org/reference/datamodel.html#object.__new__
    """

    def __init__(self, active, year, month, day, hour, mins):
        self.active = active

    def __new__(cls, active, year, month, day, hour, minute):
        return datetime.datetime.__new__(cls, year, month, day, hour, minute)

    def __unicode__(self):
        u"""
        Return a string representation.
        """
        if self.active:
            return self.strftime(u'<%Y-%m-%d %a %H:%M>')
        else:
            return self.strftime(u'[%Y-%m-%d %a %H:%M]')

    def __str__(self):
        return u_encode(self.__unicode__())

    def timestr(self):
        return self.strftime('%H:%M')

    def date(self):
        return OrgDate(self.active, self.year, self.month, self.day)

    def strftime(self, fmt):
        return u_decode(datetime.datetime.strftime(self, u_encode(fmt)))

class OrgRepeatedDateTime(OrgDateTime, OrgRepeatedTimeBase):
    u"""
    OrgDateTimeRepeated represents a repeated time like '2011-08-29 Mon 11:00'.

    OrgDateTimeRepeated can be active or inactive.

    NOTE: datetime is immutable. That's why there needs to be __new__().
    See: http://docs.python.org/reference/datamodel.html#object.__new__
    """

    def __init__(self, active, year, month, day, hour, mins, period, unit):
        OrgDateTime.__init__(self, active, year, month, day, hour, mins)
        OrgRepeatedTimeBase.__init__(self, period, unit)

    def __new__(cls, active, year, month, day, hour, minute, period, unit):
        return OrgDateTime.__new__(cls, active, year, month, day, hour, minute)

    def __unicode__(self):
        u"""
        Return a string representation.
        """
        if self.active:
            return self.strftime(u'<%Y-%m-%d %a %H:%M ' + self._period_str() + '>')
        else:
            return self.strftime(u'[%Y-%m-%d %a %H:%M ' + self._period_str() + ']')
    
    def next(self):
        next = self._advance()
        return OrgRepeatedDateTime(self.active, next.year, next.month, next.day, self.hour, self.minute, self.period, self.unit)

class OrgTimeRange(object):
    u"""
    OrgTimeRange objects have a start and an end. Start and ent can be date
    or datetime. Start and end have to be the same type.

    OrgTimeRange objects look like this:
    * <2011-09-07 Wed>--<2011-09-08 Fri>
    * <2011-09-07 Wed 20:00>--<2011-09-08 Fri 10:00>
    * <2011-09-07 Wed 10:00-13:00>
    """

    def __init__(self, active, start, end):
        u"""
        stat and end must be datetime.date or datetime.datetime (both of the
        same type).
        """
        super(OrgTimeRange, self).__init__()
        self.start = start
        self.end = end
        self.active = active

        self.verbose = False

    def __unicode__(self):
        u"""
        Return a string representation.
        """
        # active
        if self.active:
            # datetime
            if isinstance(self.start, datetime.datetime):
                # if start and end are on same the day
                if self.start.year == self.end.year and\
                    self.start.month == self.end.month and\
                    self.start.day == self.end.day:
                    return u"<%s-%s>" % (
                        self.start.strftime(u'%Y-%m-%d %a %H:%M'),
                        self.end.strftime(u'%H:%M'))
                else:
                    return u"<%s>--<%s>" % (
                        self.start.strftime(u'%Y-%m-%d %a %H:%M'),
                        self.end.strftime(u'%Y-%m-%d %a %H:%M'))
            # date
            if isinstance(self.start, datetime.date):
                return u"<%s>--<%s>" % (
                    self.start.strftime(u'%Y-%m-%d %a'),
                    self.end.strftime(u'%Y-%m-%d %a'))
        # inactive
        else:
            if isinstance(self.start, datetime.datetime):
                # if start and end are on same the day
                if not self.verbose and self.start.year == self.end.year and\
                    self.start.month == self.end.month and\
                    self.start.day == self.end.day:
                    return u"[%s-%s]" % (
                        self.start.strftime(u'%Y-%m-%d %a %H:%M'),
                        self.end.strftime(u'%H:%M'))
                else:
                    return u"[%s]--[%s]" % (
                        self.start.strftime(u'%Y-%m-%d %a %H:%M'),
                        self.end.strftime(u'%Y-%m-%d %a %H:%M'))
            if isinstance(self.start, datetime.date):
                return u"[%s]--[%s]" % (
                    self.start.strftime(u'%Y-%m-%d %a'),
                    self.end.strftime(u'%Y-%m-%d %a'))

    def __str__(self):
        return u_encode(self.__unicode__())

    def duration(self):
        return self.end - self.start

    def str_duration(self):
        duration = self.duration()
        hours, minutes = divmod(duration.total_seconds(), 3600)
        return u'%d:%02d' % (hours, minutes // 60)

# -*- coding: utf-8 -*-

u"""
    agendafilter
    ~~~~~~~~~~~~~~~~

    AgendaFilter contains all the filters that can be applied to create the
    agenda.


    All functions except filter_items() in the module are filters. Given a
    heading they return if the heading meets the criteria of the filter.

    The function filter_items() can combine different filters and only returns
    the filtered headings.
"""
from datetime import date
from datetime import time
from datetime import datetime
from datetime import timedelta
from orgmode.liborgmode.orgdate import OrgRepeatedTimeBase 

try:
    from itertools import ifilter as filter
except:
    pass


def filter_items(headings, filters):
    u""" Filter the given headings.

    Args:
        headings (list): Contains headings
        filters (list): Filters that will be applied. All functions in
            this module (except this function) are filters.

    Returns:
        filter iterator: Headings which were not filtered.

    Examples:
        >>> filtered = filter_items(headings, [contains_active_date,
                contains_active_todo])
    """
    filtered = headings
    for f in filters:
        filtered = filter(f, filtered)
    return filtered


def is_within_week(heading):
    u""" Test if headings date is within a week

    Returns:
        bool: True if the date in the deading is within a week in the future (or
            older False otherwise.
    """
    if contains_active_date(heading):
        next_week = datetime.combine(date.today() + timedelta(days=8), time(0, 0))
        if heading.active_date < next_week:
            return True


def is_within_week_and_active_todo(heading):
    u"""
    Returns:
        bool: True if heading contains an active TODO and the date is within a
            week.
    """
    return is_within_week(heading) and contains_active_todo(heading)


def is_repeated(heading):
    if contains_active_date(heading):
        return isinstance(heading.active_date, OrgRepeatedTimeBase)

allowed_tags_for_rescheduling = {'p1', 'p2', 'p3'}

def is_reschedulable(heading):
    return (set(heading.get_all_tags()) & allowed_tags_for_rescheduling) and not is_repeated(heading)

def contains_active_todo(heading):
    u"""

    Returns:
        bool: True if heading contains an active TODO.
    """
    # TODO make this more efficient by checking some val and not calling the
    # function
    # TODO why is this import failing at top level? circular dependency...
    from orgmode._vim import ORGMODE
    active = []
    for act in ORGMODE.get_document().get_todo_states():
        active.extend(act[0])
    return heading.todo in active


def contains_active_date(heading):
    u"""

    Returns:
        bool: True if heading contains an active date.
    """
    return not(heading.active_date is None)

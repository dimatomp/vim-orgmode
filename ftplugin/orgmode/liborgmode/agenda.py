# -*- coding: utf-8 -*-

u"""
    Agenda
    ~~~~~~~~~~~~~~~~~~

    The agenda is one of the main concepts of orgmode. It allows to
    collect TODO items from multiple org documents in an agenda view.

    Features:
    * filtering
    * sorting
"""

from orgmode.liborgmode.agendafilter import filter_items
from orgmode.liborgmode.agendafilter import is_within_week_and_active_todo
from orgmode.liborgmode.agendafilter import contains_active_todo
from orgmode.liborgmode.agendafilter import contains_active_date
from orgmode.liborgmode.agendafilter import is_repeated
from orgmode.liborgmode.agendafilter import is_within_week
from orgmode.liborgmode.agendafilter import is_reschedulable
from orgmode.liborgmode.orgdate import OrgDateTime, OrgTimeRange
from orgmode.liborgmode.headings import GeneratedHeading
import datetime

def date_to_datetime(orgtime):
    if orgtime is None or isinstance(orgtime, OrgDateTime):
        return orgtime
    if isinstance(orgtime, OrgTimeRange):
        return orgtime.start

    # It is an OrgDate. OrgDate cannot be compared with datetime-based Org* values by 
    # default, so it will be converted in such a way that:
    # * OrgDate value of _today_ will be displayed after today's passed events and before
    #   today's upcoming scheduled events.
    # * OrgDate value of a past day will be displayed after all other items of the same
    #   day.
    # * OrgDate value of a future day will be displayed before all other items of the same
    #   day.
    now = datetime.datetime.now()
    today = now.date()
    if today > orgtime:
        return orgtime.latest_time()
    time_to_add = now.time() if today == orgtime else datetime.time(0, 0)
    return datetime.datetime.combine(orgtime, time_to_add)

def agenda_sorting_key(heading):
    return date_to_datetime(heading.active_date)

class RepeatedHeading(GeneratedHeading): pass

class RescheduledHeading(GeneratedHeading):
    def __init__(self, level=1, title=u'', tags=None, todo=None, body=None, active_date=None, deadline=None, derived_from=None):
        super().__init__(level, title, tags, todo, body, active_date, deadline, derived_from)
        self.rescheduled_date = None

def detect_reschedulable_heading(h):
    return h.copy(including_children=False, cls=RescheduledHeading) if is_reschedulable(h) else h

class AgendaManager(object):
    u"""Simple parsing of Documents to create an agenda."""
    # TODO Move filters in this file, they do the same thing

    def __init__(self):
        super(AgendaManager, self).__init__()

    def get_todo(self, documents):
        u"""
        Get the todo agenda for the given documents (list of document).
        """
        filtered = []
        for document in iter(documents):
            # filter and return headings
            filtered.extend(filter_items(document.all_headings(),
                                [contains_active_todo]))
        return sorted(filtered, key=agenda_sorting_key)

    def _generate_repeated_items(self, headings, until_condition):
        for h in list(filter_items(headings, [is_repeated])):
            h = h.copy(including_children=False, cls=RepeatedHeading)
            h.active_date = h.active_date.next()
            while until_condition(h):
                headings.append(h)
                h = h.copy(including_children=False, cls=RepeatedHeading)
                h.active_date = h.active_date.next()

    def get_active_todo(self, documents):
        u"""
        Get the agenda for the given documents (list of document).
        """
        filtered = []
        for document in iter(documents):
            # filter and return headings
            c_filtered = filter_items(document.all_headings(),
                                [contains_active_todo, contains_active_date])
            c_filtered = list(map(detect_reschedulable_heading, c_filtered))
            max_date = max(map(agenda_sorting_key, c_filtered))
            self._generate_repeated_items(c_filtered, lambda h: agenda_sorting_key(h) < max_date)
            filtered += c_filtered
            
        return sorted(filtered, key=agenda_sorting_key)

    def get_next_week_and_active_todo(self, documents):
        u"""
        Get the agenda for next week for the given documents (list of
        document).
        """
        filtered = []
        for document in iter(documents):
            # filter and return headings
            c_filtered = list(filter_items(document.all_headings(),
                                [is_within_week_and_active_todo]))
            self._generate_repeated_items(c_filtered, is_within_week)
            filtered += c_filtered
            
        return sorted(filtered, key=agenda_sorting_key)

    def get_timestamped_items(self, documents):
        u"""
        Get all time-stamped items in a time-sorted way for the given
        documents (list of document).
        """
        filtered = []
        for document in iter(documents):
            # filter and return headings
            filtered.extend(filter_items(document.all_headings(),
                                [contains_active_date]))
        return sorted(filtered, key=agenda_sorting_key)

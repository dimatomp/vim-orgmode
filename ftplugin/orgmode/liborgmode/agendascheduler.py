from orgmode.liborgmode.agenda import RescheduledHeading
from orgmode.liborgmode.agenda import agenda_sorting_key
from orgmode.liborgmode.agenda import date_to_datetime
from orgmode.liborgmode.agendafilter import is_reschedulable
from orgmode._vim import echom

from datetime import date, timedelta

def toggle_rescheduling(h):
    if not isinstance(h, RescheduledHeading):
        echom('Not reschedulable')
        return
    h.rescheduled_date = None if h.rescheduled_date else h.active_date

class SchedulingConfig:
    def __init__(self, allowed_tags_for_weekdays, story_points, max_capacity, holidays):
        self.allowed_tags_for_weekdays = allowed_tags_for_weekdays
        self.story_points = story_points
        self.max_capacity = max_capacity
        self.holidays = holidays

bufname_configs = {
    'rakuten': SchedulingConfig(
        ({'rfb'}, {'indirect', 'learn'}, {'rfb'}, {'idlite', 'indirect', 'learn'}, {'rfb'}, set(), set()),
        { 'p1': (1, 1), 'p2': (2, 2), 'p3': (3, 3), 'mtg': (0, 1)},
        (7, 12),
        [(date(2023, 8, 1), date(2023, 8, 16)), (date(2023, 8, 23), date(2023, 9, 3))]
    ),
    'personal': SchedulingConfig(
        (None, None, None, None, None, None, None),
        {'1p': (1,), '2p': (2,), '3p': (3,)},
        (4,),
        [(date(2023, 8, 1), date(2023, 8, 16)), (date(2023, 8, 23), date(2023, 9, 3))]
    )
}

class AgendaScheduler:
    def __init__(self, bufname):
        self.config = bufname_configs[bufname]

    def reschedule_items(self, all_items):
        active_dates_for_rescheduling = [h.active_date.date() for h in all_items if get_rescheduled_date(h)]
        if not active_dates_for_rescheduling: return
        min_active_date = min(active_dates_for_rescheduling)

        def has_to_be_rescheduled(item):
            return get_rescheduled_date(item) or self.is_not_available_for_scheduling(item.active_date.date())

        urgent_item_dates_for_rescheduling = [h.active_date.date() for h in all_items if has_to_be_rescheduled(h) and h.get_parent_deadline()]
        min_urgent_date = urgent_item_dates_for_rescheduling and min(urgent_item_dates_for_rescheduling)

        def is_to_be_rescheduled(item):
            return is_reschedulable(item) and (
                urgent_item_dates_for_rescheduling and item.get_parent_deadline() and item.active_date.date() > min_urgent_date
                or has_to_be_rescheduled(item))

        available_capacity = self.compute_available_capacity(filter(lambda h: not is_to_be_rescheduled(h), all_items), min_active_date, lambda h: h.active_date, self.config.max_capacity)
        urgent_items = list(sorted(filter(lambda h: is_to_be_rescheduled(h) and h.get_parent_deadline(), all_items), key=lambda h: (date_to_datetime(h.get_parent_deadline()), agenda_sorting_key(h))))
        self.do_reschedule(urgent_items, available_capacity)
        
        items_scheduled_so_far = filter(lambda h: not is_to_be_rescheduled(h) or h.get_parent_deadline(), all_items)
        available_capacity = self.compute_available_capacity(sorted(items_scheduled_so_far, key=lambda h: date_to_datetime(get_new_date(h))), min_active_date, get_new_date, self.config.max_capacity)
        non_urgent_items = list(filter(lambda h: is_to_be_rescheduled(h) and not h.get_parent_deadline(), all_items))
        self.do_reschedule(non_urgent_items, available_capacity)

    def can_be_rescheduled_to(self, item, target_date):
        active_date = item.active_date.date().raw()
        allowed_tags = self.config.allowed_tags_for_weekdays[target_date.weekday()]
        return (allowed_tags is None or set(item.get_all_tags()) & allowed_tags) \
            and (active_date != target_date or item.get_parent_deadline() and not get_rescheduled_date(item)) \
            and (target_date != date.today() or active_date < target_date) \
            and (not item.get_parent_deadline() or item.get_parent_deadline().date().raw() >= target_date)

    def do_reschedule(self, items, available_capacity):
        try:
            from taskplanner import TaskPlanner
            planner = TaskPlanner()
            capacities = [capacity for _, capacity in available_capacity]
            planner.addDays(*capacities)
            for item in items:
                story_points = sum(max(self.config.story_points[t]) if t in self.config.story_points else 0 for t in item.get_all_tags())
                available_days = [i for i, (date, _) in enumerate(available_capacity) if self.can_be_rescheduled_to(item, date)]
                planner.addTask(story_points, available_days)
            solution = planner.planSchedule()
            for item, dayIdx in zip(items, solution):
                item.rescheduled_date = get_new_date(item).assign_new_date(available_capacity[dayIdx][0]) if dayIdx != -1 else None
        except ImportError:
            raise Exception("Please install task planning library from https://github.com/dimatomp/cpy-task-planner")

    def is_not_available_for_scheduling(self, datetime):
        return datetime < date.today() or self.config.allowed_tags_for_weekdays[datetime.weekday()] == set() or list(filter(lambda holiday: holiday[0] <= datetime <= holiday[1], self.config.holidays))

    def compute_available_capacity(self, fixed_items, min_active_date, get_date_func, max_capacity):
        available_capacity = []
        for item in fixed_items:
            item_date = get_date_func(item).date().raw()
            if item_date <= min_active_date: continue
            while not available_capacity or available_capacity[-1][0] < item_date:
                new_date = available_capacity[-1][0] + timedelta(days=1) if available_capacity else item_date
                capacity = [0] * len(max_capacity) if self.is_not_available_for_scheduling(new_date) else list(max_capacity)
                available_capacity.append((new_date, capacity))
            capacity = available_capacity[-1][1]
            for tag in item.get_all_tags():
                if tag not in self.config.story_points:
                    continue
                for i, sp in enumerate(self.config.story_points[tag]):
                    capacity[i] -= sp
        for i in range(31):
            new_date = available_capacity[-1][0] + timedelta(days=1)
            capacity = [0] * len(max_capacity) if self.is_not_available_for_scheduling(new_date) else list(max_capacity)
            available_capacity.append((new_date, capacity))
        return [(date, max(0, min(cap))) for date, cap in available_capacity]

def get_new_date(h):
    return get_rescheduled_date(h) or h.active_date

def get_rescheduled_date(h):
    if isinstance(h, RescheduledHeading):
        return h.rescheduled_date

def get_better_solution(a, b):
    for i, j in zip(a, b):
        if i < j:
            return a
        elif i > j:
            return b
    return a if len(a) > len(b) else b
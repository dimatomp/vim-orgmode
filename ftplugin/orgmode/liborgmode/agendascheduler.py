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

allowed_tags_for_weekdays = (
    {'rfb'},
    {'indirect', 'learn'},
    {'rfb'},
    {'idlite'},
    {'rfb'},
    set(),
    set()
)

story_points = {
    'p1': (1, 1),
    'p2': (2, 2),
    'p3': (3, 3),
    'mtg': (0, 1),
    '1p': (1,),
    '2p': (2,),
    '3p': (3,)
}

holidays = [
    (date(2023, 8, 1), date(2023, 8, 16)),
    (date(2023, 8, 23), date(2023, 9, 3)),
]

max_capacity = {
    'rakuten': (7, 12),
    'personal': (4,)
}

def reschedule_items(all_items, bufname):
    min_active_date = min(h.active_date.date() for h in all_items if get_rescheduled_date(h))

    def has_to_be_rescheduled(item):
        return get_rescheduled_date(item) or is_not_available_for_scheduling(item.active_date.date())

    urgent_item_dates_for_rescheduling = [h.active_date.date() for h in all_items if has_to_be_rescheduled(h) and h.get_parent_deadline()]
    min_urgent_date = urgent_item_dates_for_rescheduling and min(urgent_item_dates_for_rescheduling)

    def is_to_be_rescheduled(item):
        return is_reschedulable(item) and (
            urgent_item_dates_for_rescheduling and item.get_parent_deadline() and item.active_date.date() > min_urgent_date
            or has_to_be_rescheduled(item))

    available_capacity = compute_available_capacity(filter(lambda h: not is_to_be_rescheduled(h), all_items), min_active_date, lambda h: h.active_date, max_capacity[bufname])
    urgent_items = list(sorted(filter(lambda h: is_to_be_rescheduled(h) and h.get_parent_deadline(), all_items), key=lambda h: (date_to_datetime(h.get_parent_deadline()), agenda_sorting_key(h))))
    do_reschedule(urgent_items, available_capacity)
    
    items_scheduled_so_far = filter(lambda h: not is_to_be_rescheduled(h) or h.get_parent_deadline(), all_items)
    available_capacity = compute_available_capacity(sorted(items_scheduled_so_far, key=lambda h: date_to_datetime(get_new_date(h))), min_active_date, get_new_date, max_capacity[bufname])
    non_urgent_items = list(filter(lambda h: is_to_be_rescheduled(h) and not h.get_parent_deadline(), all_items))
    do_reschedule(non_urgent_items, available_capacity)

def can_be_rescheduled_to(item, target_date):
    active_date = item.active_date.date().raw()
    return (set(item.get_all_tags()) & allowed_tags_for_weekdays[target_date.weekday()]) \
        and (active_date != target_date or item.get_parent_deadline() and not get_rescheduled_date(item)) \
        and (target_date != date.today() or active_date < target_date)

def get_better_solution(a, b):
    for i, j in zip(a, b):
        if i < j:
            return a
        elif i > j:
            return b
    return a if len(a) > len(b) else b

def do_reschedule(items, available_capacity):
    solution_for_prev_day = [[]] * (len(items) + 1)
    item_story_points = [sum(max(story_points[t]) if t in story_points else 0 for t in h.get_all_tags()) for h in items]
    for date, capacity in available_capacity:
        if len([i for i in solution_for_prev_day if len(i) == len(items)]): break
        solution = [solution_for_prev_day[:] for i in range(capacity + 1)]
        best_solution = solution_for_prev_day
        for i, h in enumerate(items):
            if not can_be_rescheduled_to(h, date): continue
            for j, s in enumerate(solution[item_story_points[i]:]):
                candidate = solution[j][i] + [(i, date)]
                s[i + 1] = get_better_solution(s[i + 1], candidate)
                best_solution[i + 1] = get_better_solution(best_solution[i + 1], s[i + 1])
        solution_for_prev_day = best_solution
    best_solution = []
    for s in solution_for_prev_day:
        best_solution = get_better_solution(best_solution, s)
    for i, date in best_solution:
        item = items[i]
        item.rescheduled_date = get_new_date(item).assign_new_date(date) if date != item.active_date.date().raw() else None
        if item.get_parent_deadline() and date_to_datetime(get_new_date(item)) > date_to_datetime(item.get_parent_deadline()):
            echom('Could not reschedule an item with fixed deadline: ' + item.title)

def is_not_available_for_scheduling(datetime):
    return datetime < date.today() or list(filter(lambda holiday: holiday[0] <= datetime <= holiday[1], holidays))

def compute_available_capacity(fixed_items, min_active_date, get_date_func, max_capacity):
    available_capacity = []
    for item in fixed_items:
        item_date = get_date_func(item).date().raw()
        if item_date <= min_active_date: continue
        while not available_capacity or available_capacity[-1][0] < item_date:
            new_date = available_capacity[-1][0] + timedelta(days=1) if available_capacity else item_date
            capacity = [0] * len(max_capacity) if is_not_available_for_scheduling(new_date) else list(max_capacity)
            available_capacity.append((new_date, capacity))
        capacity = available_capacity[-1][1]
        for tag in item.get_all_tags():
            if tag not in story_points:
                continue
            for i, sp in enumerate(story_points[tag]):
                capacity[i] -= sp
    return [(date, max(0, min(cap))) for date, cap in available_capacity]

def get_new_date(h):
    return get_rescheduled_date(h) or h.active_date

def get_rescheduled_date(h):
    if isinstance(h, RescheduledHeading):
        return h.rescheduled_date
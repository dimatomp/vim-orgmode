# -*- coding: utf-8 -*-

from datetime import date
import os
import glob

import vim

from orgmode._vim import ORGMODE, get_bufnumber, get_bufname, echoe, echom
from orgmode import settings
from orgmode.keybinding import Keybinding, Plug, Command
from orgmode.menu import Submenu, ActionEntry, add_cmd_mapping_menu

from orgmode.py3compat.encode_compatibility import *
from orgmode.py3compat.unicode_compatibility import *
from orgmode.py3compat.py_py3_string import *

from orgmode.liborgmode.orgdate import OrgDate

from orgmode.liborgmode.agendascheduler import toggle_rescheduling
from orgmode.liborgmode.agendascheduler import get_rescheduled_date
from orgmode.liborgmode.agendascheduler import reschedule_items

class Agenda(object):
    u"""
    The Agenda Plugin uses liborgmode.agenda to display the agenda views.

    The main task is to format the agenda from liborgmode.agenda.
    Also all the mappings: jump from agenda to todo, etc are realized here.
    """

    def __init__(self):
        u""" Initialize plugin """
        object.__init__(self)
        # menu entries this plugin should create
        self.menu = ORGMODE.orgmenu + Submenu(u'Agenda')

        # key bindings for this plugin
        # key bindings are also registered through the menu so only additional
        # bindings should be put in this variable
        self.keybindings = []

        # commands for this plugin
        self.commands = []

    @classmethod
    def _switch_to(cls, bufname, vim_commands=None):
        u"""
        Swicht to the buffer with bufname.

        A list of vim.commands (if given) gets executed as well.

        TODO: this should be extracted and imporved to create an easy to use
        way to create buffers/jump to buffers. Otherwise there are going to be
        quite a few ways to open buffers in vimorgmode.
        """
        cmds = [
            u'botright split org:%s' % bufname,
            u'setlocal buftype=nofile',
            u'setlocal modifiable',
            u'setlocal nonumber',
            # call opendoc() on enter the original todo item
            u'nnoremap <silent> <buffer> <CR> :exec "%s ORGMODE.plugins[u\'Agenda\'].opendoc()"<CR>' % VIM_PY_CALL,
            u'nnoremap <silent> <buffer> <TAB> :exec "%s ORGMODE.plugins[u\'Agenda\'].opendoc(switch=True)"<CR>' % VIM_PY_CALL,
            u'nnoremap <silent> <buffer> <S-CR> :exec "%s ORGMODE.plugins[u\'Agenda\'].opendoc(split=True)"<CR>' % VIM_PY_CALL,
            # statusline
            u'setlocal statusline=Org\\ %s' % bufname]
        if vim_commands:
            cmds.extend(vim_commands)
        for cmd in cmds:
            vim.command(u_encode(cmd))

    @classmethod
    def _get_agendadocuments(self):
        u"""
        Return the org documents of the agenda files; return None if no
        agenda documents are defined.

        TODO: maybe turn this into an decorator?
        """
        # load org files of agenda
        agenda_files = settings.get(u'org_agenda_files', u',')
        if not agenda_files or agenda_files == ',':
            echoe(
                u"No org_agenda_files defined. Use :let "
                u"g:org_agenda_files=['~/org/index.org'] to add "
                u"files to the agenda view.")
            return
        return self._load_agendafiles(agenda_files)

    @classmethod
    def _load_agendafiles(self, agenda_files):
        # glob for files in agenda_files
        resolved_files = []
        for f in agenda_files:
            f = glob.glob(os.path.join(
                os.path.expanduser(os.path.dirname(f)),
                os.path.basename(f)))
            resolved_files.extend(f)

        agenda_files = [os.path.realpath(f) for f in resolved_files]

        # load the agenda files into buffers
        for agenda_file in agenda_files:
            vim.command(u_encode(u'badd %s' % agenda_file.replace(" ", "\\ ")))

        # determine the buffer nr of the agenda files
        agenda_nums = [get_bufnumber(fn) for fn in agenda_files]

        # collect all documents of the agenda files and create the agenda
        return [ORGMODE.get_document(i) for i in agenda_nums if i is not None]

    @classmethod
    def toggle_rescheduling(cls):
        row = vim.current.window.cursor[0]
        heading = cls.line2doc[row]
        toggle_rescheduling(heading)
        bufnr = heading.document.bufnr
        reschedule_items(list(filter(lambda h: h.document.bufnr == bufnr, cls.line2doc.values())), cls.get_short_bufname(bufnr))
        vim.command(u_encode(u'setlocal modifiable'))
        for row, heading in cls.line2doc.items():
            vim.current.buffer[row - 1] = cls.format_agenda_item(heading)
        vim.command(u_encode(u'setlocal nomodifiable'))

    @classmethod
    def apply_rescheduling(cls):
        for item in cls.line2doc.values():
            new_date = get_rescheduled_date(item)
            if not new_date: continue
            item.derived_from.body = [s.replace(unicode(item.active_date), unicode(new_date)) for s in item.derived_from.body]
            item.derived_from.set_dirty_body()
            item.document.write_heading(item.derived_from)
        vim.command(u_encode(u"quit"))
        echom('Updated active dates')

    @classmethod
    def opendoc(cls, split=False, switch=False):
        u"""
        If you are in the agenda view jump to the document the item in the
        current line belongs to. cls.line2doc is used for that.

        :split: if True, open the document in a new split window.
        :switch: if True, switch to another window and open the the document
            there.
        """
        row, _ = vim.current.window.cursor
        try:
            heading = cls.line2doc[row]
            bufnr = heading.document.bufnr
            bufname = get_bufname(bufnr)
            destrow = heading.start
        except:
            return

        # reload source file if it is not loaded
        if get_bufname(bufnr) is None:
            vim.command(u_encode(u'badd %s' % bufname))
            bufnr = get_bufnumber(bufname)
            tmp = cls.line2doc[row]
            cls.line2doc[bufnr] = tmp
            # delete old endry
            del cls.line2doc[row]

        if split:
            vim.command(u_encode(u"sbuffer %s" % bufnr))
        elif switch:
            vim.command(u_encode(u"wincmd w"))
            vim.command(u_encode(u"buffer %d" % bufnr))
        else:
            vim.command(u_encode(u"buffer %s" % bufnr))
        vim.command(u_encode(u"normal! %dgg <CR>" % (destrow + 1)))

    @classmethod
    def list_next_week(cls):
        agenda_documents = cls._get_agendadocuments()
        if not agenda_documents:
            return
        cls.list_next_week_for(agenda_documents)

    @classmethod
    def list_all_agenda(cls):
        agenda_documents = cls._get_agendadocuments()
        if not agenda_documents:
            return
        cls.list_active_todo(agenda_documents)

    @classmethod
    def list_next_week_for_buffer(cls):
        agenda_documents = vim.current.buffer.name
        loaded_agendafiles = cls._load_agendafiles([agenda_documents])
        cls.list_next_week_for(loaded_agendafiles)
    
    @classmethod
    def list_active_todo(cls, agenda_documents):
        raw_agenda = ORGMODE.agenda_manager.get_active_todo(
            agenda_documents)

        # if raw_agenda is empty, return directly
        if not raw_agenda:
            vim.command('echom "All caught-up. No agenda or active todo next week."')
            return

        # create buffer at bottom
        cmd = [
            u'setlocal filetype=orgagenda',
            u'nnoremap <silent> <buffer> L :exec "%s ORGMODE.plugins[u\'Agenda\'].toggle_rescheduling()"<CR>' % VIM_PY_CALL,
            u'nnoremap <silent> <buffer> A :exec "%s ORGMODE.plugins[u\'Agenda\'].apply_rescheduling()"<CR>' % VIM_PY_CALL ]
        cls._switch_to(u'AGENDA', cmd)

        cls.generate_agenda_buffer(raw_agenda)

    @classmethod
    def list_next_week_for(cls, agenda_documents):
        raw_agenda = ORGMODE.agenda_manager.get_next_week_and_active_todo(
            agenda_documents)

        # if raw_agenda is empty, return directly
        if not raw_agenda:
            vim.command('echom "All caught-up. No agenda or active todo next week."')
            return

        # create buffer at bottom
        cmd = [u'setlocal filetype=orgagenda', ]
        cls._switch_to(u'AGENDA', cmd)

        cls.generate_agenda_buffer(raw_agenda)

    @classmethod
    def generate_agenda_buffer(cls, raw_agenda):
        # line2doc is a dic with the mapping:
        #     line in agenda buffer --> source document
        # It's easy to jump to the right document this way
        cls.line2doc = {}
        # format text for agenda
        last_date = None
        final_agenda = [u'Week Agenda:']
        for i, h in enumerate(raw_agenda):
            # insert date information for every new date (not datetime)
            active_date_no_time = h.active_date.date()
            if active_date_no_time != last_date:
                today = date.today()
                # insert additional "TODAY" string
                if active_date_no_time == today:
                    section = unicode(active_date_no_time) + u" TODAY"
                    today_row = len(final_agenda) + 1
                else:
                    section = unicode(active_date_no_time)
                final_agenda.append(section)

                # update last_date
                last_date = active_date_no_time

            formatted = cls.format_agenda_item(h)
            final_agenda.append(formatted)
            cls.line2doc[len(final_agenda)] = h

        # show agenda
        vim.current.buffer[:] = [u_encode(i) for i in final_agenda]
        vim.command(u_encode(u'setlocal nomodifiable  conceallevel=2 concealcursor=nc'))
        # try to jump to the position of today
        try:
            vim.command(u_encode(u'normal! %sgg<CR>' % today_row))
        except:
            pass

    @classmethod
    def format_agenda_item(cls, heading):
        bufname = cls.get_short_bufname(heading.document.bufnr)
        rescheduled_date = get_rescheduled_date(heading)
        tags = heading.get_all_tags()
        deadline = heading.get_parent_deadline()
        optional_columns = [
            tags and ':' + ':'.join(tags) + ':',
            rescheduled_date and '-> ' + unicode(rescheduled_date),
            deadline and "DEADLINE: " + unicode(deadline)]
        return u"  %(bufname)s (%(bufnr)d)  %(todo)s  %(timestr)s  %(title)s %(opt)s" % {
            'bufname': bufname,
            'bufnr': heading.document.bufnr,
            'todo': heading.todo,
            'timestr': heading.active_date.timestr(),
            'title': heading.title,
            'opt': ' '.join(c for c in optional_columns if c)
        }
    
    @classmethod
    def get_short_bufname(cls, bufnr):
        bufname = os.path.basename(vim.buffers[bufnr].name)
        return bufname[:-4] if bufname.endswith(u'.org') else bufname

    @classmethod
    def list_all_todos(cls, current_buffer=False):
        u""" List all todos in one buffer.

        Args:
            current_buffer (bool):
                False: all agenda files
                True: current org_file
        """
        if current_buffer:
            agenda_documents = vim.current.buffer.name
            loaded_agendafiles = cls._load_agendafiles([agenda_documents])
        else:
            loaded_agendafiles = cls._get_agendadocuments()
        if not loaded_agendafiles:
            return
        raw_agenda = ORGMODE.agenda_manager.get_todo(loaded_agendafiles)

        cls.line2doc = {}
        # create buffer at bottom
        cmd = [u'setlocal filetype=orgagenda']
        cls._switch_to(u'AGENDA', cmd)

        # format text of agenda
        final_agenda = []
        for i, h in enumerate(raw_agenda):
            tmp = u"%s %s" % (h.todo, h.title)
            final_agenda.append(tmp)
            cls.line2doc[len(final_agenda)] = h

        # show agenda
        vim.current.buffer[:] = [u_encode(i) for i in final_agenda]
        vim.command(u_encode(u'setlocal nomodifiable  conceallevel=2 concealcursor=nc'))

    @classmethod
    def list_timeline(cls):
        """
        List a timeline of the current buffer to get an overview of the
        current file.
        """
        raw_agenda = ORGMODE.agenda_manager.get_timestamped_items(
            [ORGMODE.get_document()])

        # create buffer at bottom
        cmd = [u'setlocal filetype=orgagenda']
        cls._switch_to(u'AGENDA', cmd)

        cls.line2doc = {}
        # format text of agenda
        final_agenda = []
        for i, h in enumerate(raw_agenda):
            tmp = fmt.format('{} {}', h.todo, h.title).lstrip().rstrip()
            final_agenda.append(tmp)
            cls.line2doc[len(final_agenda)] = h

        # show agenda
        vim.current.buffer[:] = [u_encode(i) for i in final_agenda]
        vim.command(u_encode(u'setlocal nomodifiable conceallevel=2 concealcursor=nc'))

    def register(self):
        u"""
        Registration of the plugin.

        Key bindings and other initialization should be done here.
        """
        add_cmd_mapping_menu(
            self,
            name=u"OrgAgendaTodo",
            function=u'%s ORGMODE.plugins[u"Agenda"].list_all_todos()' % VIM_PY_CALL,
            key_mapping=u'<localleader>cat',
            menu_desrc=u'Agenda for all TODOs'
        )
        add_cmd_mapping_menu(
            self,
            name=u"OrgBufferAgendaTodo",
            function=u'%s ORGMODE.plugins[u"Agenda"].list_all_todos(current_buffer=True)' % VIM_PY_CALL,
            key_mapping=u'<localleader>caT',
            menu_desrc=u'Agenda for all TODOs based on current buffer'
        )
        add_cmd_mapping_menu(
            self,
            name=u"OrgAgendaAll",
            function=u'%s ORGMODE.plugins[u"Agenda"].list_all_agenda()' % VIM_PY_CALL,
            key_mapping=u'<localleader>caw',
            menu_desrc=u'Agenda for entire time'
        )
        add_cmd_mapping_menu(
            self,
            name=u"OrgAgendaWeek",
            function=u'%s ORGMODE.plugins[u"Agenda"].list_next_week()' % VIM_PY_CALL,
            key_mapping=u'<localleader>caa',
            menu_desrc=u'Agenda for the week'
        )
        add_cmd_mapping_menu(
            self,
            name=u"OrgBufferAgendaWeek",
            function=u'%s ORGMODE.plugins[u"Agenda"].list_next_week_for_buffer()' % VIM_PY_CALL,
            key_mapping=u'<localleader>caA',
            menu_desrc=u'Agenda for the week based on current buffer'
        )
        add_cmd_mapping_menu(
            self,
            name=u'OrgAgendaTimeline',
            function=u'%s ORGMODE.plugins[u"Agenda"].list_timeline()' % VIM_PY_CALL,
            key_mapping=u'<localleader>caL',
            menu_desrc=u'Timeline for this buffer'
        )

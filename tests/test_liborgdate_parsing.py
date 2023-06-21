# -*- coding: utf-8 -*-


import sys
import unittest

sys.path.append(u'../ftplugin')
from orgmode.liborgmode.orgdate import get_orgdates
from orgmode.liborgmode.orgdate import OrgDate
from orgmode.liborgmode.orgdate import OrgDateTime
from orgmode.liborgmode.orgdate import OrgTimeRange

from orgmode.py3compat.unicode_compatibility import *

class OrgDateParsingTestCase(unittest.TestCase):
    u"""
    Tests the functionality of the parsing function of OrgDate.

    Mostly function get_orgdate().
    """

    def setUp(self):
        self.text = u'<2011-08-29 Mon>'
        self.textinactive = u'[2011-08-29 Mon]'

    def get_all_orgdates(self, text):
        return list(date[0] for date in get_orgdates(text))

    def get_single_orgdate(self, text):
        orgdates = self.get_all_orgdates(text)
        self.assertEqual(len(orgdates), 1)
        return orgdates[0]

    def test_get_orgdate_parsing_active(self):
        u"""
        get_orgdate should recognize all orgdates in a given text
        """
        result = self.get_single_orgdate(self.text)
        self.assertNotEqual(result, None)
        self.assertTrue(isinstance(result, OrgDate))
        self.assertTrue(isinstance(self.get_single_orgdate(u"<2011-08-30 Tue>"), OrgDate))
        self.assertEqual(self.get_single_orgdate(u"<2011-08-30 Tue>").year, 2011)
        self.assertEqual(self.get_single_orgdate(u"<2011-08-30 Tue>").month, 8)
        self.assertEqual(self.get_single_orgdate(u"<2011-08-30 Tue>").day, 30)
        self.assertTrue(self.get_single_orgdate(u"<2011-08-30 Tue>").active)

        datestr = u"This date <2011-08-30 Tue> is embedded"
        self.assertTrue(isinstance(self.get_single_orgdate(datestr), OrgDate))


    def test_get_orgdatetime_parsing_active(self):
        u"""
        get_orgdate should recognize all orgdatetimes in a given text
        """
        result = self.get_single_orgdate(u"<2011-09-12 Mon 10:20>")
        self.assertNotEqual(result, None)
        self.assertTrue(isinstance(result, OrgDateTime))
        self.assertEqual(result.year, 2011)
        self.assertEqual(result.month, 9)
        self.assertEqual(result.day, 12)
        self.assertEqual(result.hour, 10)
        self.assertEqual(result.minute, 20)
        self.assertTrue(result.active)

        result = self.get_single_orgdate(u"some datetime <2011-09-12 Mon 10:20> stuff")
        self.assertTrue(isinstance(result, OrgDateTime))


    def test_get_orgtimerange_parsing_active(self):
        u"""
        get_orgdate should recognize all orgtimeranges in a given text
        """
        daterangestr = u"<2011-09-12 Mon>--<2011-09-13 Tue>"
        result = self.get_single_orgdate(daterangestr)
        self.assertNotEqual(result, None)
        self.assertTrue(isinstance(result, OrgTimeRange))
        self.assertEqual(unicode(result), daterangestr)
        self.assertTrue(result.active)

        daterangestr = u"<2011-09-12 Mon 10:20>--<2011-09-13 Tue 13:20>"
        result = self.get_single_orgdate(daterangestr)
        self.assertNotEqual(result, None)
        self.assertTrue(isinstance(result, OrgTimeRange))
        self.assertEqual(unicode(result), daterangestr)
        self.assertTrue(result.active)

        daterangestr = u"<2011-09-12 Mon 10:20-13:20>"
        result = self.get_single_orgdate(daterangestr)
        self.assertNotEqual(result, None)
        self.assertTrue(isinstance(result, OrgTimeRange))
        self.assertEqual(unicode(result), daterangestr)
        self.assertTrue(result.active)

    def test_get_orgdate_parsing_inactive(self):
        u"""
        get_orgdate should recognize all inactive orgdates in a given text
        """
        result = self.get_single_orgdate(self.textinactive)
        self.assertNotEqual(result, None)
        self.assertTrue(isinstance(result, OrgDate))
        self.assertTrue(isinstance(self.get_single_orgdate(u"[2011-08-30 Tue]"), OrgDate))
        self.assertEqual(self.get_single_orgdate(u"[2011-08-30 Tue]").year, 2011)
        self.assertEqual(self.get_single_orgdate(u"[2011-08-30 Tue]").month, 8)
        self.assertEqual(self.get_single_orgdate(u"[2011-08-30 Tue]").day, 30)
        self.assertFalse(self.get_single_orgdate(u"[2011-08-30 Tue]").active)

        datestr = u"This date [2011-08-30 Tue] is embedded"
        self.assertTrue(isinstance(self.get_single_orgdate(datestr), OrgDate))

    def test_get_orgdatetime_parsing_passive(self):
        u"""
        get_orgdate should recognize all orgdatetimes in a given text
        """
        result = self.get_single_orgdate(u"[2011-09-12 Mon 10:20]")
        self.assertNotEqual(result, None)
        self.assertTrue(isinstance(result, OrgDateTime))
        self.assertEqual(result.year, 2011)
        self.assertEqual(result.month, 9)
        self.assertEqual(result.day, 12)
        self.assertEqual(result.hour, 10)
        self.assertEqual(result.minute, 20)
        self.assertFalse(result.active)

        result = self.get_single_orgdate(u"some datetime [2011-09-12 Mon 10:20] stuff")
        self.assertTrue(isinstance(result, OrgDateTime))

    def test_get_orgdate_parsing_with_list_of_texts(self):
        u"""
        get_orgdate should return the first date in the list.
        """
        datelist = [u"<2011-08-29 Mon>"]
        result = self.get_single_orgdate(datelist)
        self.assertNotEquals(result, None)
        self.assertTrue(isinstance(result, OrgDate))
        self.assertEqual(result.year, 2011)
        self.assertEqual(result.month, 8)
        self.assertEqual(result.day, 29)

        datelist = [u"<2011-08-29 Mon>",
                u"<2012-03-30 Fri>"]
        result = self.get_all_orgdates(datelist)
        self.assertTrue(isinstance(result[0], OrgDate))
        self.assertEqual(result[0].year, 2011)
        self.assertEqual(result[0].month, 8)
        self.assertEqual(result[0].day, 29)
        self.assertTrue(isinstance(result[1], OrgDate))
        self.assertEqual(result[1].year, 2012)
        self.assertEqual(result[1].month, 3)
        self.assertEqual(result[1].day, 30)

        datelist = [u"some <2011-08-29 Mon>text",
                u"<2012-03-30 Fri> is here"]
        result = self.get_all_orgdates(datelist)
        self.assertTrue(isinstance(result[0], OrgDate))
        self.assertEqual(result[0].year, 2011)
        self.assertEqual(result[0].month, 8)
        self.assertEqual(result[0].day, 29)
        self.assertTrue(isinstance(result[1], OrgDate))
        self.assertEqual(result[1].year, 2012)
        self.assertEqual(result[1].month, 3)
        self.assertEqual(result[1].day, 30)

        datelist = [u"here is no date",
                u"some <2011-08-29 Mon>text",
                u"<2012-03-30 Fri> is here"]
        result = self.get_all_orgdates(datelist)
        self.assertTrue(isinstance(result[0], OrgDate))
        self.assertEqual(result[0].year, 2011)
        self.assertEqual(result[0].month, 8)
        self.assertEqual(result[0].day, 29)
        self.assertTrue(isinstance(result[1], OrgDate))
        self.assertEqual(result[1].year, 2012)
        self.assertEqual(result[1].month, 3)
        self.assertEqual(result[1].day, 30)

        datelist = [u"here is no date",
                u"some <2011-08-29 Mon 20:10> text",
                u"<2012-03-30 Fri> is here"]
        result = self.get_all_orgdates(datelist)
        self.assertTrue(isinstance(result[0], OrgDateTime))
        self.assertEqual(result[0].year, 2011)
        self.assertEqual(result[0].month, 8)
        self.assertEqual(result[0].day, 29)
        self.assertEqual(result[0].hour, 20)
        self.assertEqual(result[0].minute, 10)
        self.assertTrue(isinstance(result[1], OrgDate))
        self.assertEqual(result[1].year, 2012)
        self.assertEqual(result[1].month, 3)
        self.assertEqual(result[1].day, 30)

    def test_get_orgdate_parsing_with_invalid_input(self):
        self.assertEquals(self.get_all_orgdates(u"NONSENSE"), [])
        self.assertEquals(self.get_all_orgdates(u"No D<2011- Date 08-29 Mon>"), [])
        self.assertEquals(self.get_all_orgdates(u"2011-08-r9 Mon]"), [])
        self.assertEquals(self.get_all_orgdates(u"<2011-08-29 Mon"), [])
        self.assertEquals(self.get_all_orgdates(u"<2011-08-29 Mon]"), [])
        self.assertEquals(self.get_all_orgdates(u"2011-08-29 Mon"), [])
        self.assertEquals(self.get_all_orgdates(u"2011-08-29"), [])
        self.assertEquals(self.get_all_orgdates(u"2011-08-29 mon"), [])
        self.assertEquals(self.get_all_orgdates(u"<2011-08-29 mon>"), [])

        self.assertEquals(self.get_all_orgdates(u"wrong date embedded <2011-08-29 mon>"), [])
        self.assertEquals(self.get_all_orgdates(u"wrong date <2011-08-29 mon>embedded "), [])

    def test_get_orgdate_parsing_with_invalid_dates(self):
        u"""
        Something like <2011-14-29 Mon> (invalid dates, they don't exist)
        should not be parsed
        """
        datestr = u"<2011-14-30 Tue>"
        self.assertEqual(self.get_all_orgdates(datestr), [])

        datestr = u"<2012-03-40 Tue>"
        self.assertEqual(self.get_all_orgdates(datestr), [])

        datestr = u"<2012-03-40 Tue 24:70>"
        self.assertEqual(self.get_all_orgdates(datestr), [])

    def test_get_orgdate_parsing_with_utf8(self):
        u"""
        get_orgdate should recognize all orgdates within a given utf-8 text
        """
        result = self.get_single_orgdate(u'<2016-05-07 Sáb>')
        self.assertNotEqual(result, None)
        self.assertTrue(isinstance(result, OrgDate))
        self.assertEqual(result.year, 2016)
        self.assertEqual(result.month, 5)
        self.assertEqual(result.day, 7)
        self.assertTrue(result.active)

        datestr = u"This date <2016-05-07 Sáb> is embedded"
        self.assertTrue(isinstance(self.get_single_orgdate(datestr), OrgDate))

        result = self.get_single_orgdate(u'[2016-05-07 Sáb]')
        self.assertFalse(result.active)

        datestr = u"This date [2016-05-07 Sáb] is embedded"
        self.assertTrue(isinstance(self.get_single_orgdate(datestr), OrgDate))

    def test_get_orgdatetime_parsing_with_utf8(self):
        u"""
        get_orgdate should recognize all orgdatetimes in a given utf-8 text
        """
        result = self.get_single_orgdate(u"<2016-05-07 Sáb 10:20>")
        self.assertNotEqual(result, None)
        self.assertTrue(isinstance(result, OrgDateTime))
        self.assertEqual(result.year, 2016)
        self.assertEqual(result.month, 5)
        self.assertEqual(result.day, 7)
        self.assertEqual(result.hour, 10)
        self.assertEqual(result.minute, 20)
        self.assertTrue(result.active)

        result = self.get_single_orgdate(u"some datetime <2016-05-07 Sáb 10:20> stuff")
        self.assertTrue(isinstance(result, OrgDateTime))

        result = self.get_single_orgdate(u"[2016-05-07 Sáb 10:20]")
        self.assertFalse(result.active)

        result = self.get_single_orgdate(u"some datetime [2016-05-07 Sáb 10:20] stuff")
        self.assertTrue(isinstance(result, OrgDateTime))



def suite():
    return unittest.TestLoader().loadTestsFromTestCase(OrgDateParsingTestCase)

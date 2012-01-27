# Case Conductor is a Test Case Management system.
# Copyright (C) 2011-12 Mozilla
#
# This file is part of Case Conductor.
#
# Case Conductor is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Case Conductor is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Case Conductor.  If not, see <http://www.gnu.org/licenses/>.
"""
Tests for Case/CaseVersion filtering.

"""
from mock import Mock

from django.utils.datastructures import MultiValueDict
from django.test import TestCase


from .... import factories as F



class CaseVersionFilterSetTest(TestCase):
    """Tests for CaseVersionFilterSet."""
    @property
    def CaseVersionFilterSet(self):
        """The class under test."""
        from cc.view.manage.cases.filters import CaseVersionFilterSet
        return CaseVersionFilterSet


    def test_filter_latest(self):
        """If productversion is not filtered on, filters by latest=True."""
        fs = self.CaseVersionFilterSet(MultiValueDict())

        qs = Mock()
        fs.filter(qs)

        qs.filter.assert_called_with(latest=True)


    def test_filtered_by_productversion(self):
        """If filtered by productversion, doesn't filter by latest=True."""
        pv = F.ProductVersionFactory.create()

        fs = self.CaseVersionFilterSet(
            MultiValueDict({"filter-productversion": [str(pv.id)]}))

        qs = Mock()
        qs2 = fs.filter(qs)

        qs.filter.assert_called_with(productversion__in=[pv.id])
        # no other filters intervening
        self.assertIs(qs2, qs.filter.return_value.distinct.return_value)
"""
Unit tests for :mod:`manwe.session`.
"""


import pytest
import varda
import varda.models

import utils


class TestSession(utils.TestEnvironment):
    def test_get_user(self):
        """
        Get a user.
        """
        admin_uri = self.uri_for_user(name='Administrator')
        assert self.session.user(admin_uri).name == 'Administrator'

    def test_create_sample(self):
        """
        Create a sample.
        """
        sample = self.session.create_sample('test sample', pool_size=5, public=True)
        assert sample.name == 'test sample'

        sample_uri = self.uri_for_sample(name='test sample')
        assert sample.uri == sample_uri

    def test_create_data_source(self):
        """
        Create a data source.
        """
        data_source = self.session.create_data_source('test data source', 'vcf', data='test_data')

        data_source_uri = self.uri_for_data_source(name='test data source')
        assert data_source.uri == data_source_uri

    def test_samples_by_user(self):
        """
        Filter sample collection by user.
        """
        a = varda.models.User('User A', 'a')
        b = varda.models.User('User B', 'b')

        samples_a = [varda.models.Sample(a, 'Sample A %d' % i)
                     for i in range(50)]
        samples_b = [varda.models.Sample(b, 'Sample B %d' % i)
                     for i in range(50)]

        varda.db.session.add_all(samples_a + samples_b)
        varda.db.session.commit()

        admin = self.session.user(self.uri_for_user(name='Administrator'))
        a = self.session.user(self.uri_for_user(name='User A'))
        b = self.session.user(self.uri_for_user(name='User B'))

        samples = self.session.samples()
        assert samples.size == 100

        samples_a = self.session.samples(user=a)
        assert samples_a.size == 50
        assert samples_a.user == a
        assert next(samples_a).user == a
        assert next(samples_a).name.startswith('Sample A ')

        samples_b = self.session.samples(user=b)
        assert samples_b.size == 50
        assert samples_b.user == b
        assert next(samples_b).user == b
        assert next(samples_b).name.startswith('Sample B ')

        samples_admin = self.session.samples(user=admin)
        assert samples_admin.size == 0
        assert samples_admin.user == admin
        with pytest.raises(StopIteration):
            next(samples_admin)

    def test_samples_by_groups(self):
        """
        Filter sample collection by groups.
        """
        admin = varda.models.User.query.filter_by(name='Administrator').one()
        a = varda.models.Group('Group A')
        b = varda.models.Group('Group B')

        varda.db.session.add(a)
        varda.db.session.add(b)
        varda.db.session.add_all(
            varda.models.Sample(admin, 'Sample A %d' % i, groups=[a])
            for i in range(20))
        varda.db.session.add_all(
            varda.models.Sample(admin, 'Sample B %d' % i, groups=[b])
            for i in range(20))
        varda.db.session.add_all(
            varda.models.Sample(admin, 'Sample AB %d' % i, groups=[a, b])
            for i in range(20))
        varda.db.session.commit()

        a = self.session.group(self.uri_for_group(name='Group A'))
        b = self.session.group(self.uri_for_group(name='Group B'))

        # All samples.
        samples = self.session.samples()
        assert samples.size == 60

        # Group A samples.
        samples_a = self.session.samples(groups=[a])
        assert samples_a.size == 40
        assert samples_a.groups == {a}
        sample = next(samples_a)
        assert any(g == a for g in sample.groups)
        assert sample.name.startswith('Sample A ') or sample.name.startswith('Sample AB ')

        # Group B samples.
        samples_b = self.session.samples(groups={b})
        assert samples_b.size == 40
        assert samples_b.groups == {b}
        sample = next(samples_b)
        assert any(g == b for g in sample.groups)
        assert sample.name.startswith('Sample B ') or sample.name.startswith('Sample AB ')

        # Group A and B samples.
        samples_ab = self.session.samples(groups=[a, b])
        assert samples_ab.size == 20
        assert samples_ab.groups == {a, b}
        sample = next(samples_ab)
        assert any(g == a for g in sample.groups)
        assert any(g == b for g in sample.groups)
        assert sample.name.startswith('Sample AB ')

    def test_variant_annotate(self):
        """
        Annotate a variant.
        """
        variant = self.session.create_variant('chr8', 800000, 'T', 'A')
        annotations = variant.annotate(queries={'GLOBAL': '*'})

        assert annotations == {'GLOBAL': {'coverage': 0,
                                          'frequency': 0,
                                          'frequency_het': 0,
                                          'frequency_hom': 0}}

    def test_variant_normalize(self):
        """
        Normalize a variant.
        """
        variant = self.session.create_variant('chr8', 800000, 'ATTTT', 'ATTTTT')

        assert variant.chromosome == '8'
        assert variant.position == 800001
        assert variant.reference == ''
        assert variant.observed == 'T'

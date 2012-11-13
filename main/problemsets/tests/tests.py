"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase
from c2g.models import Course, ProblemSet

class SimpleTestBase(TestCase):
    """
    A base class for test classes that need to log in to the system and
    switch to edit mode to ensure access to the correct data.

    TODO: If needed, parameterize each step so that some tests can log
          in only and stay in draft mode.
          Also provide configuration for the u/p (to allow student logins)
          Perhaps even take the path and parse it for the pre/suf
    """
    mode = 'draft'
    loginPath = '/%s/%s/preview_login/'
    userAgent = 'Mozilla/5.0'
    referer = 'http://testserver/%s/%s/preview/'

    # tried using __init__ to set these but there is something wonky with
    # the inheritance
    username = 'set-me-in-subclass'
    password = 'set-me-in-subclass'
    coursePrefix = 'set-me-in-subclass'
    courseSuffix = 'set-me-in-subclass'

    def setUp(self):
        # login
        resp = self.client.post((self.loginPath%(self.coursePrefix,
                                                 self.courseSuffix)),
                                {'username' : self.username,
                                 'password' : self.password},
                                follow=True)
        self.assertEqual(resp.status_code, 200)

        # switch to edit mode for full access
        resp = self.client.post('/switch_mode/',
                                {'course_prefix': self.coursePrefix,
                                 'course_suffix': self.courseSuffix,
                                 'to_mode': self.mode},
                                HTTP_USER_AGENT=self.userAgent,
                                HTTP_REFERER=(self.referer%(self.coursePrefix,
                                                            self.courseSuffix)),
                                follow=True)
        self.assertEqual(resp.status_code, 200)

class BasicDraftModeTest(SimpleTestBase):
    fixtures = ['pset_testdata.json']
    username = 'professor_0'
    password = 'class2go'
    coursePrefix = 'networking'
    courseSuffix = 'Fall2012'

    def test_fixture_loading(self):
        """
        Tests the fixture loaded correctly
        """
        numProblemSets = len(ProblemSet.objects.all())
        self.assertEqual(numProblemSets,4)

    def test_basic_pageAccess(self):
        """
        Tests that we can access the basic test problem set pages
        """

        # load the normal problem set page
        resp = self.client.get('/networking/Fall2012/problemsets/P2' )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue('pset_url' in resp.context)
        self.assertEqual(resp.context['pset_url'], '/networking/Fall2012/problemsets/P2/load_problem_set')

    def test_pset_load(self):
        """
        Test that we can load the actual problem set (?)
        """
        # load a page with just the problem set
        resp = self.client.get('/networking/Fall2012/problemsets/P2/load_problem_set' )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue('file_names' in resp.context)
        self.assertEqual(resp.context['file_names'][0], 'xx_P2_Lexical1')

    def test_load_all_psets(self):
        """
        Test the view all problemset page
        """
        resp = self.client.get('/networking/Fall2012/problemsets/' )
        self.assertEqual(resp.status_code, 200)

    def test_load_manage_exercises(self):
        """
        Test the loading of the manage problemset exercises page
        """
        resp = self.client.get('/networking/Fall2012/problemsets/P2/manage_exercise' )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context['exercises']), 2)

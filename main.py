#
# Insightly - Google App Engine Sample Code
# Brian McConnell <brian@insight.ly>
#
# This sample code for shows how to build webapp2 compatible apps that integrate with Insightly.
# This will run as-is on Google App Engine for Python, and should also run on any webapp2
# runtime environment, although you will need to replace the App Engine django templating tools
# with the Django installation. 
#
# With the Python SDK you can access all of the major object types in Insightly, including:
#
# * Contacts
# * Emails
# * Opportunities
# * orgainsations
# * Projects
# * Tasks
#
# This demo application includes a Bootstrap based sample website that enables prospective
# customers to fill out a web form, which then imports this information into the Insightly
# contact manager and tasks system. Some other hidden pages also demo how to read
# information out of Insightly, for example to display a list of tasks that are coming due. 
# 

import os
import string
import webapp2
import jinja2

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

import wsgiref.handlers

# import the required App Engine libraries, if you are hosting in a non-appengine environment
# you'll need to replace the Django templating engine
from google.appengine.api import memcache
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp import util

# import the Insightly SDK
from insightly import Insightly

from ggsys import GuardianInsightlyWrapper

import logging
from collections import defaultdict
from collections import OrderedDict

# your Insightly API key goes here
apikey = 'f01c8f69-bea1-4531-9f10-b38cc8a19bfc'

def load_page(page, data = None):
    """
    This helper function loads a Django template and merges data into it. The main.html file
    serves as a master template that child documents are merged into. 
    """
    if len(page) < 1: page = 'home'
    path = os.path.join(os.path.dirname(__file__), "main.html")
    if data is not None:
        if type(data) is dict:
            logging.info("Rendering path:" + path + " with data typed dict")
            return template.render(path, data)
    data = dict(
        page = page + '.html',
    )

    # logging.info("Rendering path:" + path + " with empty data collection")
    return template.render(path, data)
        
class RequestInformationHandler(webapp2.RequestHandler):
    """
    This request handler implements the request information form, and handles the POST submission
    when the form is submitted.
    
    It adds the user to Insightly contacts, and also creates a task to follow up with the user. 
    """
    def get(self):
        self.response.out.write(load_page('request_information'))
    def post(self):
        i = Insightly(apikey = apikey)
        contactinfos = list()

        if len(self.request.get('EMAIL')) > 0:
            contactinfo = dict(
                TYPE = 'EMAIL',
                DETAIL = self.request.get('EMAIL'),
            )
            contactinfos.append(contactinfo)
        if len(self.request.get('PHONE')) > 0:
            contactinfo = dict(
                TYPE = 'PHONE',
                DETAIL = self.request.get('PHONE'),
            )
            contactinfos.append(contactinfo)
        contact = dict(
            SALUTATION = self.request.get('SALUTATION'),
            FIRST_NAME = self.request.get('FIRST_NAME'),
            LAST_NAME = self.request.get('LAST_NAME'),
            CONTACTINFOS = contactinfos,
        )
        contact = i.addContact(contact)
        
        if self.request.get('addtask') == 'y':
            tasklinks = list()
            tl = dict(
                TASK_LINK_ID = 0,
                CONTACT_ID = contact['CONTACT_ID'],
            )
            tasklinks.append(tl)
            
            task = dict(
                Title = 'Follow up with ' + self.request.get('FIRST_NAME') + ' ' + self.request.get('LAST_NAME'),
                PRIORITY = 2,
                STATUS = 'NOT STARTED',
                COMPLETED = False,
                OWNER_USER_ID = i.owner_id,
                VISIBLE_TO = 'EVERYONE',
                PUBLICLY_VISIBLE = True,
                RESPONSIBLE_USER_ID = i.owner_id,
                TASKLINKS = tasklinks,
            )
            task = i.addTask(task)
        self.redirect('/thankyou')
            
class ProjectsHandler(webapp2.RequestHandler):
    """
    This hidden request handler displays up to 50 projects in an unordered list. 
    """
    def get(self):
        i = Insightly(apikey = apikey)
        projects = i.getProjects(top=50)
        if len(projects) > 0:
            self.response.out.write('<ul>')
            for p in projects:
                self.response.out.write('<li>' + str(p.get('PROJECT_NAME','')))
            self.response.out.write('</ul>')
        
class TasksHandler(webapp2.RequestHandler):
    """
    This is a simple request handler that displays a list of upcoming tasks. 
    """
    def get(self):
        i = Insightly(apikey = apikey)
        tasks = i.getTasks(top=25, orderby='DUE_DATE desc')
        if len(tasks) > 0:
            self.response.out.write('<ul>')
            for t in tasks:
                self.response.out.write('<li>' + t.get('Title','No title') + ' Due: ' + t.get('DUE_DATE','') + '</li>')
            self.response.out.write('</ul>')
            
class PageHandler(webapp2.RequestHandler):
    """
    This is a generic request handler that serves pages to the path /nnnn, where the file merged into the master template
    is nnnn.html (see requestinformation.html for an example)
    """
    def get(self, page=''):
        self.response.out.write(load_page(page))

class orgainsationsHandler(webapp2.RequestHandler):
    """
    This handler displays all of the orgainsations in an Insightly account
    """
    def get(self):
        i = Insightly(apikey = apikey)

        customFieldsList = i.getCustomFields()
        for cf in customFieldsList:
            if(str(cf.get('FIELD_NAME','')) == 'Classification'):
                classification_id = str(cf.get('CUSTOM_FIELD_ID'))

        organisations = i.getorgainsations()
        self.response.out.write('<ul>')
        for o in organisations:
            self.response.out.write('<li>' + str(o.get('ORGANISATION_NAME', '')) + ' - ')
            for cf in o.get('CUSTOMFIELDS'):
                if cf.get('CUSTOM_FIELD_ID') == classification_id:
                    self.response.out.write(str(cf.get('FIELD_VALUE')))
            self.response.out.write('</li>')
        self.response.out.write('</ul>')

class ReportHandler(webapp2.RequestHandler):
    """
    This handler displays all of the orgainsations in an Insightly account
    """
    def get(self):
        g = GuardianInsightlyWrapper()

        customFieldsList = g.getCustomFields()
        tasks = g.getTasks()
        organisations = g.getOrganisations()

        for cf in customFieldsList:
            if(str(cf.get('FIELD_NAME','')) == 'Classification'):
                classification_field_id = str(cf.get('CUSTOM_FIELD_ID'))

        # Decorate orgainsations with our custom field out of it's magical collection so that we can rely on it being there
        for o in organisations:
            if o['CUSTOMFIELDS'] is not None:
                for cf in o.get('CUSTOMFIELDS'):
                    if cf.get('CUSTOM_FIELD_ID') == classification_field_id:
                        o['CLASSIFICATION'] = cf.get('FIELD_VALUE')
                        # Also populate our organisation with any outstanding tasks
                if not o.has_key('CLASSIFICATION'):
                    o['CLASSIFICATION'] = 'Not Set'
            else:
                o['CLASSIFICATION'] = 'Not Set'

        org_idx_by_id = g.build_dict(organisations, 'ORGANISATION_ID')

        unallocated_tasks = []
        # Append all tasks to their organisations
        for t in tasks:
            if t['TASKLINKS'] is not None:
                for tl in t['TASKLINKS']:
                    if tl['ORGANISATION_ID'] is not None:
                        logging.info(tl['ORGANISATION_ID'])
                        if org_idx_by_id[tl['ORGANISATION_ID']] is not None:
                            # ID = org_idx_by_id[tl['ORGANISATION_ID']]['index']
                            if 'Tasks' in organisations[org_idx_by_id[tl['ORGANISATION_ID']]['index']]:
                                organisations[org_idx_by_id[tl['ORGANISATION_ID']]['index']]['Tasks'].append(t)
                            else:
                                organisations[org_idx_by_id[tl['ORGANISATION_ID']]['index']]['Tasks'] = []
                                organisations[org_idx_by_id[tl['ORGANISATION_ID']]['index']]['Tasks'].append(t)
                        else:
                            unallocated_tasks.append(t)
                            logging.info('Not Found')
            else:
                unallocated_tasks.append(t)

        # group our orgainsations by their classification
        orgs_by_class = {}
        for o in organisations:
            if not orgs_by_class.has_key(o['CLASSIFICATION']):
                orgs_by_class[o['CLASSIFICATION']] = []
            orgs_by_class[o['CLASSIFICATION']].append(o)
      
        logging.info(unallocated_tasks)

        template_values = {
            'page' : "report.html",
            'sorted_classification_list' : sorted(orgs_by_class, reverse=False),
            'orgs_by_class' : orgs_by_class,
            'unallocated_tasks': unallocated_tasks
        }
        
        #self.response.out.write(load_page('report', template_values))
        template = JINJA_ENVIRONMENT.get_template('report.html')
        self.response.write(template.render(template_values))

class CustomFieldHandler(webapp2.RequestHandler):
    """
    This handler lists the results of the dicts returned by the getCustomField api call
    """
    def get(self):
        i = Insightly(apikey = apikey)

        customFieldsList = i.getCustomFields()
        for cf in customFieldsList:
            if(str(cf.get('FIELD_NAME','')) == 'Classification'):
                classification_id = str(cf.get('CUSTOM_FIELD_ID'))

app = webapp2.WSGIApplication([
    ('/', RequestInformationHandler),
    ('/projects', ProjectsHandler),
    ('/orgainsations', orgainsationsHandler),
    ('/cf', CustomFieldHandler),
    ('/requestinformation', RequestInformationHandler),
    ('/tasks', TasksHandler),
    ('/report', ReportHandler),
    (r'/(.*)', PageHandler)
], debug=True)

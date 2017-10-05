# copyright 2015 Objectif Libre
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

#from decimal import *
import decimal
from django.utils.translation import ugettext_lazy as _
import json

from django import http
from horizon import exceptions
from horizon import views
from cloudkittydashboard.api import cloudkitty as api
from openstack_dashboard.dashboards.identity.users \
    import forms as project_forms
from openstack_dashboard.dashboards.identity.users \
    import tables as project_table
import dateutil.relativedelta
import simplejson as json
import pytz
import time
import sys
import datetime
from dateutil import tz

from openstack_dashboard import api as napi
from openstack_dashboard.api import keystone
from collections import OrderedDict

class IndexView(views.APIView):

    # A very simple class-based view...
    template_name = 'project/m1rating/index.html'

    def get_data(self, request, context, *args, **kwargs):
        services_mapping = {
            'compute':          'Compute', 
            'image':            'Image',
            'volume':           'Block Storage (Volume)', 
            'network.bw.in':    'Network Transfer (inbound)', 
            'network.bw.out':   'Network Transfer (outbound)', 
            'network.floating': 'Floating IP Addresses', 
            'cloudstorage':     'Object Storage (Swift)',
            'instance.addon':   'Compute Instance Add-On', 
            'tenant.addon':     'Project Add-On'
        }
        tenants = napi.keystone.tenant_list(self.request, request.user.id, marker = '', admin=False)
        services_mapping = OrderedDict(services_mapping)
        tenant = ''

        # Filter the current tenant
        for tenant_items in tenants: # Foreach tenant of the user
            if not isinstance(tenant_items, bool):
                for tenant_final in tenant_items:
                    if tenant_final.id == request.user.tenant_id:
                       tenant = tenant_final

        tenant_timezone = tenant.timezone if hasattr(tenant, 'timezone') else 'UTC'
        if hasattr(tenant, 'creation_date'):
             start_period_cloud  = tenant.creation_date
             if isinstance(start_period_cloud, unicode):
                 start_period_cloud = datetime.datetime.strptime(start_period_cloud, '%Y-%m-%d %H:%M:%S')
             else:
                 start_period_cloud = datetime.datetime.now() - dateutil.relativedelta.relativedelta(months=1)
        else:
            start_period_cloud = datetime.datetime.now() - dateutil.relativedelta.relativedelta(months=1)
                
        try:
            self.tenant_timezone = tenant_timezone
            now = datetime.datetime.now(pytz.timezone(self.tenant_timezone))
        except:
            self.tenant_timezone = 'UTC'
            now = datetime.datetime.now(pytz.timezone(self.tenant_timezone))

        start_time_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_date_week  = now - dateutil.relativedelta.relativedelta(days=7)
        start_date_week  = start_date_week.replace(hour=0, minute=0, second=0, microsecond=0)
        start_date_month = now - dateutil.relativedelta.relativedelta(months=1)
        start_date_month = start_date_month.replace(hour=0, minute=0, second=0, microsecond=0)

        # Add data to the context here...
        total = api.cloudkittyclient(request).reports.get_total(
                tenant_id = tenant.id, 
                begin = self.local2utc(start_time_today), 
                end= self.local2utc(now)) or 0.00
        total_dict = OrderedDict({})
        for item in services_mapping:
            totals = api.cloudkittyclient(request).reports.get_total(
                       tenant_id = request.user.tenant_id, 
                       service   = item, 
                       begin     = self.local2utc(start_time_today), 
                       end       = self.local2utc(now)) or 0.00
            total_dict[services_mapping[item]] = totals
     
        # GENERATING WEEK DATA 
        total_week = api.cloudkittyclient(request).reports.get_total(
                       tenant_id=request.user.tenant_id, 
                       begin=self.local2utc(start_date_week), 
                       end= self.local2utc(now)) or 0.00
        total_week_dict = {}
        total_week_dict = OrderedDict(total_week_dict)
        for item in services_mapping:
            totals_week = api.cloudkittyclient(request).reports.get_total(
                              tenant_id = request.user.tenant_id, 
                              service   = item, 
                              begin     = self.local2utc(start_date_week), 
                              end       = self.local2utc(now)) or 0.00
            total_week_dict[services_mapping[item]] = totals_week
    
        # GENERATING MONTHLY DATA
        total_month = api.cloudkittyclient(request).reports.get_total(
                          tenant_id = request.user.tenant_id, 
                          begin     = self.local2utc(start_date_month), 
                          end       = self.local2utc(now)) or 0.00
        total_month_dict = {}
        total_month_dict = OrderedDict(total_month_dict)
        for item in services_mapping:
            totals_month = api.cloudkittyclient(request).reports.get_total(
                               tenant_id = request.user.tenant_id, 
                               service   = item, 
                               begin     = self.local2utc(start_date_month), 
                               end       = self.local2utc(now)) or 0.00
            total_month_dict[services_mapping[item]] = totals_month


        # cloud resource section
        total_cloud = api.cloudkittyclient(request).reports.get_total(
                          tenant_id=request.user.tenant_id, 
                          begin=self.local2utc(start_period_cloud), 
                          end= self.local2utc(now)) or 0.00

        # cloud resources section    
        total_cloud_dict = {}
        total_cloud_dict = OrderedDict(total_cloud_dict)
        for item in services_mapping:
            totals_cloud = api.cloudkittyclient(request).reports.get_total(
                               tenant_id = request.user.tenant_id, 
                               service   = item, 
                               begin     = self.local2utc(start_period_cloud), 
                               end       = self.local2utc(now)) or 0.00
            total_cloud_dict[services_mapping[item]] = totals_cloud
       
        context['total_today'] = total
        context['start_period_today'] = start_time_today.strftime('%b %d %Y %H:%M')
        context['end_period'] = now.strftime('%b %d %Y %H:%M')
        context['total_dict'] = total_dict

        context['total_week'] = total_week
        context['start_period_week'] = start_date_week.strftime('%b %d %Y %H:%M')
        context['end_period'] = now.strftime('%b %d %Y %H:%M')
        context['total_week_dict'] = total_week_dict

        context['total_month'] = total_month
        context['start_period_month'] = start_date_month.strftime('%b %d %Y %H:%M')
        context['end_period'] = now.strftime('%b %d %Y %H:%M')
        context['total_month_dict'] = total_month_dict

        context['total_cloud'] = total_cloud
        context['start_period_cloud'] = start_period_cloud.strftime('%b %d %Y %H:%M')
        context['end_period'] = now.strftime('%b %d %Y %H:%M')
        context['total_cloud_dict'] = total_cloud_dict 
        context['time_zone'] = self.tenant_timezone

        return context

    # convert the local time to UTC
    def local2utc(self, dt):

        tenant_timezone = self.tenant_timezone
        from_zone = tz.gettz(tenant_timezone)
        to_zone = tz.gettz('UTC')
        local = dt.replace(tzinfo=from_zone)
        return local.astimezone(to_zone).replace(tzinfo = None)

def quote(request):
    pricing = "0"
    if request.is_ajax():
        if request.method == 'POST':
            json_data = json.loads(request.body)
            try:
                pricing = decimal.Decimal(api.cloudkittyclient(request)
                                          .quotations.quote(json_data))
                pricing = pricing.normalize().to_eng_string()
            except Exception:
                exceptions.handle(request,
                                  _('Unable to retrieve price.'))

    return http.HttpResponse(json.dumps(pricing),
                             content_type='application/json')

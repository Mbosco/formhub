import json

from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _

from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.decorators import action
from rest_framework import exceptions

from api import serializers as api_serializers
from api import mixins
from api import tools as utils

from utils.user_auth import check_and_set_form_by_id
from main.models import UserProfile

from odk_logger.models import XForm, Instance
from odk_viewer.models import ParsedInstance

from api.models import Project, OrganizationProfile, ProjectXForm, Team


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = api_serializers.UserSerializer
    lookup_field = 'username'

    def list(self, request, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        self.object_list = qs.filter(username=request.user.username)
        serializer = self.get_serializer(self.object_list, many=True)
        return Response(serializer.data)


class UserProfileViewSet(mixins.ObjectLookupMixin, viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = api_serializers.UserProfileSerializer
    lookup_field = 'user'

    def list(self, request, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        self.object_list = qs.filter(user__username=request.user.username)
        serializer = self.get_serializer(self.object_list, many=True)
        return Response(serializer.data)


class OrgProfileViewSet(mixins.ObjectLookupMixin, viewsets.ModelViewSet):
    queryset = OrganizationProfile.objects.all()
    serializer_class = api_serializers.OrganizationSerializer
    lookup_field = 'user'


class XFormViewSet(viewsets.ModelViewSet):
    queryset = XForm.objects.all()
    serializer_class = api_serializers.XFormSerializer

    def list(self, request, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        self.object_list = qs.filter(user=request.user)
        serializer = self.get_serializer(self.object_list, many=True)
        return Response(serializer.data)


class ProjectViewSet(mixins.MultiLookupMixin, viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = api_serializers.ProjectSerializer
    lookup_fields = ('owner', 'pk')
    lookup_field = 'owner'
    extra_lookup_fields = None

    def list(self, request, **kwargs):
        filter = {}
        if 'owner' in kwargs:
            filter['organization__username'] = kwargs['owner']
        filter['created_by'] = request.user
        qs = self.get_queryset()
        qs = self.filter_queryset(qs)
        self.object_list = qs.filter(**filter)
        serializer = self.get_serializer(self.object_list, many=True)
        return Response(serializer.data)

    @action(methods=['POST', 'GET'], extra_lookup_fields=['formid', ])
    def forms(self, request, **kwargs):
        project = get_object_or_404(
            Project, pk=kwargs.get('pk', None),
            organization__username=kwargs.get('owner', None))
        if request.method.upper() == 'POST':
            survey = utils.publish_project_xform(request, project)
            if isinstance(survey, XForm):
                serializer = api_serializers.XFormSerializer(
                    survey, context={'request': request})
                return Response(serializer.data, status=201)
            return Response(survey, status=400)
        filter = {'project': project}
        many = True
        if 'formid' in kwargs:
            many = False
            filter['xform__pk'] = int(kwargs.get('formid'))
        if many:
            qs = ProjectXForm.objects.filter(**filter)
            data = [px.xform for px in qs]
        else:
            qs = get_object_or_404(ProjectXForm, **filter)
            data = qs.xform
        serializer = api_serializers.XFormSerializer(
            data, many=many, context={'request': request})
        return Response(serializer.data)


class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.all()
    serializer_class = api_serializers.TeamSerializer
    lookup_fields = ('owner', 'pk')
    lookup_field = 'owner'
    extra_lookup_fields = None

    def get_object(self):
        filter = {
            'organization__username': self.kwargs['owner'],
            'pk': self.kwargs['pk']
        }
        qs = self.filter_queryset(self.get_queryset())
        return get_object_or_404(qs, **filter)

    def list(self, request, **kwargs):
        filter = {}
        if 'owner' in kwargs:
            filter['organization__username'] = kwargs['owner']
        if not filter:
            filter['user'] = request.user
        qs = self.filter_queryset(self.get_queryset())
        self.object_list = qs.filter(**filter)
        serializer = self.get_serializer(self.object_list, many=True)
        return Response(serializer.data)


class DataList(APIView):
    queryset = Instance.objects.all()

    def _get_formlist_data_points(self, request):
        xforms = []
        # list public points incase anonymous user
        if request.user.is_anonymous():
            xforms = XForm.public_forms().order_by('?')[:10]
        else:
            # list data points authenticated user has access to
            xforms = XForm.objects.filter(user=request.user)
        rs = {}
        for xform in xforms:
            point = {u"%s" % xform.id_string:
                     reverse("data-list", kwargs={"formid": xform.pk},
                             request=request)}
            rs.update(point)
        return rs

    def _get_form_data(self, xform, **kwargs):
        margs = {
            'username': xform.user.username,
            'id_string': xform.id_string,
            'query': kwargs.get('query', None),
            'fields': kwargs.get('fields', None),
            'sort': kwargs.get('sort', None)
        }
        cursor = ParsedInstance.query_mongo(**margs)
        records = list(record for record in cursor)
        return records

    def get(self, request, formid=None, dataid=None, **kwargs):
        data = None
        xform = None
        query = None
        if not formid and not dataid:
            data = self._get_formlist_data_points(request)
        if formid:
            xform = check_and_set_form_by_id(int(formid), request)
            if not xform:
                raise exceptions.PermissionDenied(
                    _("You do not have permission to "
                      "view data from this form."))
        if xform and dataid:
            query = json.dumps({'_id': int(dataid)})
        if xform:
            data = self._get_form_data(xform, query=query)
        return Response(data)
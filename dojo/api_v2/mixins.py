from django.db import DEFAULT_DB_ALIAS
from django.contrib.admin.utils import NestedObjects
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import action
from rest_framework import status
from rest_framework.authtoken.models import Token
from dojo.api_v2 import serializers
from dojo.models import Tool_Configuration, Tool_Type
from dojo.tool_config.factory import create_API
import itertools
import json


class DeletePreviewModelMixin:
    @extend_schema(
        methods=['GET'],
        responses={status.HTTP_200_OK: serializers.DeletePreviewSerializer(many=True)}
    )
    @swagger_auto_schema(
        method='get',
        responses={'default': serializers.DeletePreviewSerializer(many=True)}
    )
    @action(detail=True, methods=["get"], filter_backends=[], suffix='List')
    def delete_preview(self, request, pk=None):
        object = self.get_object()

        collector = NestedObjects(using=DEFAULT_DB_ALIAS)
        collector.collect([object])
        rels = collector.nested()

        def flatten(elem):
            if isinstance(elem, list):
                return itertools.chain.from_iterable(map(flatten, elem))
            else:
                return [elem]

        rels = [
            {
                "model": type(x).__name__,
                "id": x.id if hasattr(x, 'id') else None,
                "name": str(x) if not isinstance(x, Token) else "<APITokenIsHidden>"
            }
            for x in flatten(rels)
        ]

        page = self.paginate_queryset(rels)

        serializer = serializers.DeletePreviewSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class TestConnectionMixin:
    def dispatch(self, request, *args, **kwargs):
        if request.method in ['POST', 'PATCH', 'PUT']:
            request_body = json.loads(request.body)
            
            tool_type_id = request_body.get('tool_type')
            tool_type = Tool_Type.objects.get(id=int(tool_type_id))
    
            tool_configuration = Tool_Configuration(
                name=request_body.get('name'),
                description=request_body.get('description'),
                url=request_body.get('url'),
                tool_type=tool_type,
                authentication_type=request_body.get('authentication_type'),
                extras=request_body.get('extras'),
                username=request_body.get('username'),
                password=request_body.get('password'),
                auth_title=request_body.get('auth_title'),
                ssh=request_body.get('ssh'),
                api_key=request_body.get('api_key') 
            )

            try:
                api = create_API(tool_configuration)
                if api and hasattr(api, 'test_connection'):
                    result = api.test_connection()
            except Exception as e:
                data = {
                    'message': str(e)
                }
                return HttpResponse(status=422, content=json.dumps(data))

        return super().dispatch(request, *args, **kwargs)

# -*- coding:utf-8 -*-
__author__ = 'Wenhao Yin'

#from django.contrib.auth import authenticate
from django.views.decorators.csrf import csrf_exempt
from functools import wraps

from base64 import b64decode
from tokens import token_generator
from ajax import JsonResponseForbidden, JsonResponseUnauthorized


def token_required(view_func):
    """Decorator which ensures the user has provided a correct token."""

    @csrf_exempt
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        token = None
        basic_auth = request.META.get('HTTP_AUTHORIZATION')

        token = request.POST.get('token', request.GET.get('token'))

        # 如果没有token参数则通过HTTP_AUTHORIZATION里的信息验证,未测试待完善
        if not token and basic_auth:
            auth_method, auth_string = basic_auth.split(' ', 1)     # 以空格分隔一次

            if auth_method.lower() == 'basic':
                auth_string = b64decode(auth_string.strip())        # 去除两边空格
                user_id, token = auth_string.decode().split(':', 1)

        if not token:
            return JsonResponseForbidden("Must include 'token' parameters with request.")

        # user = authenticate(token=token)
        # if user:
        #     request.user = user     # 重要！！返回验证通过后的user
        #     return view_func(request, *args, **kwargs)

        user_id = token_generator.check_token(token)
        if user_id:
            request.user_id = user_id     # 重要！！返回验证通过后的user_id
            return view_func(request, *args, **kwargs)

        # 其它情况禁止访问
        return JsonResponseUnauthorized("Token did not authorized")
    return _wrapped_view
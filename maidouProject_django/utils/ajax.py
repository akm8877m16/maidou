# -*- coding:utf-8 -*-  
__author__ = 'Wenhao Yin'

from django.http import HttpResponse
"""JSON helper functions"""
try:
    import json as json
except ImportError:
    import json

# ensure_ascii 默认为True 结果为字符串, 如果设为False结果可能为unicode类型
def dumps(result = None, ensure_ascii = True):
    return json.dumps(result, ensure_ascii = ensure_ascii)

def loads(data):
    return json.loads(data)

# 先定义  data = {
#              'token': 'xxxxx',
#              'user_id': '1',
#           }
# JsonResponse(data)
def JsonResponse(data = '', status=200):
    """
    返回json格式成功响应
    """
    result = {
        'success': True,
        'msg': data,
    }
    #jsonResult = json.dumps(result, ensure_ascii = False)
    #return HttpResponse(jsonResult, content_type='application/json;charset=utf-8', status=status)
    return  result

# JsonError('错误提示消息')
def JsonError(error = '', status=200):
    """
    返回jsno格式错误响应
    """
    result = {
        'success': False,
        'msg': error
    }
    #jsonResult = json.dumps(result, ensure_ascii = False)
    #return HttpResponse(jsonResult, content_type='application/json;charset=utf-8', status=status)
    return  result

# 400 Bad Request 
# 因为错误的语法导致服务器无法理解请求信息。
def JsonResponseBadRequest(error):
    return JsonError(error, status=400)

# 401 Unauthorized 
# 如果请求需要用户验证。回送应该包含一个WWW-Authenticate头字段用来指明请求资源的权限。
def JsonResponseUnauthorized(error):
    return JsonError(error, status=401)

# 403 Forbidden 
# 服务器接受请求，但是被拒绝处理
def JsonResponseForbidden(error):
    return JsonError(error, status=403)

# 404 Not Found 
# 服务器无法找到任何匹配Request-URI的资源。
def JsonResponseNotFound(error):
    return JsonError(error, status=404)

# 405 Menthod Not Allowed 
# Request-Line 请求的方法不被允许通过指定的URI。
def JsonResponseNotAllowed(error):
    return JsonError(error, status=405)

def JsonResponseNotAcceptable(error):
    return JsonError(error, status=406)

# For backwards compatability purposes 
# ajax_ok = JsonResponse
# ajax_fail = JsonError

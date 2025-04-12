import json
import logging
import os
import re
import mimetypes
from wsgiref.util import FileWrapper

from django.http import JsonResponse, StreamingHttpResponse, HttpResponse
from django.shortcuts import render
from wxcloudrun.models import Counters


logger = logging.getLogger('log')


def index(request, _):
    """
    获取主页

     `` request `` 请求对象
    """
    # 检查视频文件是否存在
    from django.conf import settings
    video_path = os.path.join(settings.BASE_DIR, 'static', 'WeChat_20250412143759.mp4')
    video_exists = os.path.exists(video_path)
    
    context = {
        'video_exists': video_exists,
        'video_path': '/serve_video/'  # 修改为指向我们的视频服务视图
    }
    
    return render(request, 'index.html', context)


def serve_video(request):
    """
    提供视频文件，支持范围请求
    """
    from django.conf import settings
    
    video_path = os.path.join(settings.BASE_DIR, 'static', 'WeChat_20250412143759.mp4')
    
    if not os.path.exists(video_path):
        return HttpResponse("视频文件不存在", status=404)
    
    file_size = os.path.getsize(video_path)
    content_type = 'video/mp4'
    
    # 处理范围请求
    range_header = request.META.get('HTTP_RANGE', '').strip()
    range_match = re.match(r'bytes=(\d+)-(\d*)', range_header)
    
    if range_match:
        start = int(range_match.group(1))
        end = int(range_match.group(2)) if range_match.group(2) else file_size - 1
        
        if start >= file_size:
            return HttpResponse(status=416)  # 请求范围不满足
            
        # 确保范围有效
        end = min(end, file_size - 1)
        length = end - start + 1
        
        resp = StreamingHttpResponse(
            FileWrapper(open(video_path, 'rb'), chunk_size=8192),
            status=206,
            content_type=content_type
        )
        
        resp['Content-Length'] = str(length)
        resp['Content-Range'] = f'bytes {start}-{end}/{file_size}'
        resp['Accept-Ranges'] = 'bytes'
    else:
        # 完整文件请求
        resp = StreamingHttpResponse(
            FileWrapper(open(video_path, 'rb'), chunk_size=8192),
            content_type=content_type
        )
        resp['Content-Length'] = str(file_size)
        resp['Accept-Ranges'] = 'bytes'
    
    return resp


def counter(request, _):
    """
    获取当前计数

     `` request `` 请求对象
    """

    rsp = JsonResponse({'code': 0, 'errorMsg': ''}, json_dumps_params={'ensure_ascii': False})
    if request.method == 'GET' or request.method == 'get':
        rsp = get_count()
    elif request.method == 'POST' or request.method == 'post':
        rsp = update_count(request)
    else:
        rsp = JsonResponse({'code': -1, 'errorMsg': '请求方式错误'},
                            json_dumps_params={'ensure_ascii': False})
    logger.info('response result: {}'.format(rsp.content.decode('utf-8')))
    return rsp


def get_count():
    """
    获取当前计数
    """

    try:
        data = Counters.objects.get(id=1)
    except Counters.DoesNotExist:
        return JsonResponse({'code': 0, 'data': 0},
                    json_dumps_params={'ensure_ascii': False})
    return JsonResponse({'code': 0, 'data': data.count},
                        json_dumps_params={'ensure_ascii': False})


def update_count(request):
    """
    更新计数，自增或者清零

    `` request `` 请求对象
    """

    logger.info('update_count req: {}'.format(request.body))

    body_unicode = request.body.decode('utf-8')
    body = json.loads(body_unicode)

    if 'action' not in body:
        return JsonResponse({'code': -1, 'errorMsg': '缺少action参数'},
                            json_dumps_params={'ensure_ascii': False})

    if body['action'] == 'inc':
        try:
            data = Counters.objects.get(id=1)
        except Counters.DoesNotExist:
            data = Counters()
        data.id = 1
        data.count += 1
        data.save()
        return JsonResponse({'code': 0, "data": data.count},
                    json_dumps_params={'ensure_ascii': False})
    elif body['action'] == 'clear':
        try:
            data = Counters.objects.get(id=1)
            data.delete()
        except Counters.DoesNotExist:
            logger.info('record not exist')
        return JsonResponse({'code': 0, 'data': 0},
                    json_dumps_params={'ensure_ascii': False})
    else:
        return JsonResponse({'code': -1, 'errorMsg': 'action参数错误'},
                    json_dumps_params={'ensure_ascii': False})

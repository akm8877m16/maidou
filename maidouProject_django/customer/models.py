# -*- coding:utf-8 -*-
__author__ = 'Wenhao Yin'

from django.db import models
import hashlib
from django.core.cache import cache
from django.conf import settings
import datetime
from utils.tokens import token_generator
import redis
# Create your models here.

class UserControl(models.Model):
    user_name = models.CharField(max_length=50, unique=True, null=True)  # 用户名 默认phone number
    password = models.CharField(max_length=50)  # 密码
    phone = models.CharField(max_length=20, unique=True, null=True, blank=True)  # 手机
    token = models.CharField(unique=True, max_length=32)  # 授权令牌
    token_refresh_at = models.DateTimeField(auto_now_add=True)  # 授权令牌上一次更新时间
    last_login = models.DateTimeField(auto_now=True)  # 上次登入时间
    date_joined = models.DateTimeField(auto_now_add=True)  # 创建时间
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)

    def __str__(self):
        return self.phone

    # 是否授权(查找到对象就肯定授权了)
    def is_authenticated(self):
        return True

        # 密码加密函数

    def hashed_password(self, password=None):
        salt = 'hpy:'  # 加盐
        return hashlib.md5(salt + password).hexdigest()

        # 设置密码
    def set_password(self, password=None):
        self.password = self.hashed_password(password)

    # 检查密码匹配
    def check_password(self, password):
        if self.hashed_password(password) == self.password:
            return True
        return False

        # 检查授权令牌是否过期 True过期 False未过期

    def token_expired(self):
        if not self.r.exists('token:' + self.token):
            return True
        # 令牌是否过期
        TOKEN_TIMEOUT_SECONDS = getattr(settings, "TOKEN_TIMEOUT_SECONDS", None)
        if TOKEN_TIMEOUT_SECONDS == None:
            return False  # 无过期时间
        token_expired_at = self.token_refresh_at + datetime.timedelta(seconds=TOKEN_TIMEOUT_SECONDS)
        return token_expired_at <= datetime.datetime.now()

        # 强制刷新令牌

    def refreshToken(self):
        TOKEN_TIMEOUT_SECONDS = getattr(settings, "TOKEN_TIMEOUT_SECONDS", None)
        # 生成新的令牌
        token = token_generator.make_token(self)
        # 先更新缓存 redis缓存中实际存储的键是 1:token:xxxxx
        self.r.set('token:' + token, self.pk, ex=TOKEN_TIMEOUT_SECONDS)  # 缓存新的token,默认超时None,不超时
        # 删除旧的token
        self.r.delete('token:' + self.token)
        # 更新数据库中的值
        self.token = token
        self.token_refresh_at = datetime.datetime.now()

class Device(models.Model):
    user = models.ManyToManyField(UserControl)
    type = models.CharField(max_length=10)  #device type for future dev   1 单相 2 多相
    sn = models.CharField(max_length=30, unique=True)  #户号
    name = models.CharField(max_length=50, default='') #户名
    address = models.CharField(max_length=200, default='') #地址
    controlPass = models.CharField(max_length=10, default='') #控制密码

#控权限表，
class deviceControl(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    user = models.ForeignKey(UserControl, on_delete=models.CASCADE)
    right = models.IntegerField()  #1 owner  2 guest



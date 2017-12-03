# -*- coding:utf-8 -*-
__author__ = 'Wenhao Yin'

"""django.contrib.auth.tokens, but without using last_login in hash"""

import time
from django.utils import six
from django.utils.crypto import salted_hmac, get_random_string
from django.core.cache import cache

class PasswordResetTokenGenerator(object):
    """
    Strategy object used to generate and check tokens for the password
    reset mechanism.
    """
    key_salt = "hpy~!@$%"   # 加盐

    # 生成token令牌
    def make_token(self, user):
        """
        Returns a token that can be used for the given user.
        """
        timestamp = time.time()
        return self._make_token_with_timestamp(user, timestamp)

    # 检查缓存是否含有token令牌
    def check_token(self, token):
        """
        Check that a token is correct.
        """
        # user_id = self.r.get(token)
        user_id = cache.get('token:'+ token)
        return user_id

    def _make_token_with_timestamp(self, user, timestamp):
        # six.text_type 转成unicode类型
        value = (six.text_type(user.pk) + user.password + six.text_type(timestamp) + '-' + get_random_string(3))
        token = salted_hmac(self.key_salt, value).hexdigest()[::2]
        return token

# 实例化
token_generator = PasswordResetTokenGenerator()

# -*- coding:utf-8 -*-
__author__ = 'Wenhao Yin'
import re         #正则表达式(regular expression)模块

def isEmail(mailString):
    if re.match("[a-zA-Z0-9]+\@+[a-zA-Z0-9]+\.+[a-zA-Z]", mailString) != None:  #re.match(pattern, string)
        return True
    else:
        return False

def isMobilePhone(phoneString):
    if re.match("^0\d{2,3}\d{7,8}$|^1[358]\d{9}$|^147\d{8}", phoneString) != None:  #re.match(pattern, string)
        return True
    else:
        return False
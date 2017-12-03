# -*- coding:utf-8 -*-
from util.messageConst import CONST_DIC_ANALOG,CONST_DIC_POWER,CONST_DIC_ANALOG_RATIO,CONST_DIC_POWER_RATIO
from maidouTcp.logger import baseLogger

def showMessage(message):
    baseLogger.info(message)
    results = message.split(",")
    print results[0]
    print results[1]
    post = {}
    sn = results[0][2:]
    post["sn"] = sn
    data = results[1]
    dataArray = data.split(" ")
    messageType = dataArray[7]
    baseLogger.debug(messageType)
    realDataArray = dataArray[10:]

    startIndex = dataArray[8] * 256 + dataArray[9]
    baseLogger.debug(startIndex)
    if (messageType == 12):  # 模拟量
        dataLength = (dataArray[4] * 256 + dataArray[5] - 4) / 2
        for (k, v) in CONST_DIC_ANALOG.items():
            baseLogger.debug(k, ":  ", v)
            diff = startIndex - 1
            if ((v - diff) > dataLength):  # not in range
                continue
            else:
                index = v - diff - 1

                value = realDataArray[2 * index] * 256 + realDataArray[2 * index + 1]
                post[k] = value * CONST_DIC_ANALOG_RATIO[k]
                baseLogger.debug(k, ":  ", post[k])
    elif (messageType == 13):  # 电度
        dataLength = (dataArray[4] * 256 + dataArray[5] - 4) / 4
        for (k, v) in CONST_DIC_POWER.items():
            diff = startIndex - 1
            if ((v - diff) > dataLength):  # not in range
                continue
            else:
                index = v - diff - 1
                value = realDataArray[4 * index] * 16777216 + realDataArray[4 * index + 1] * 65536 + realDataArray[
                                                                                                         4 * index + 2] * 256 + \
                        realDataArray[4 * index + 3]
                post[k] = value * CONST_DIC_POWER_RATIO[k]
    elif (messageType == 14):  # event
        pass
    elif (messageType == 11):  # 断路器状态
        pass

# 主程序
if __name__ == '__main__':
    message = "E/wer2q34wfsfdsa,0, 0, 0, 0, 0, 52, 1, 12, 0, 1, 0, 255, 255, 255, 0, 3, 0, 4, 0, 229, 0, 6, 0, 7, 0, 8, 0, 9, 0, 10, 0, 11, 0, 12, 0, 13, 0, 14, 0, 15, 0, 16, 0, 17, 0, 18, 0, 19, 0, 20, 0, 21, 0, 22, 0, 23, 0, 24, 0, 25, 0, 26, 0, 27, 0, 28, 0, 29, 0, 30"
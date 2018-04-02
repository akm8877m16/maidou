# -*- coding:utf-8 -*-
# 主程序
if __name__ == '__main__':
    #message = "E/wer2q34wfsfdsa,0, 0, 0, 0, 0, 52, 1, 12, 0, 1, 0, 255, 255, 255, 0, 3, 0, 4, 0, 229, 0, 6, 0, 7, 0, 8, 0, 9, 0, 10, 0, 11, 0, 12, 0, 13, 0, 14, 0, 15, 0, 16, 0, 17, 0, 18, 0, 19, 0, 20, 0, 21, 0, 22, 0, 23, 0, 24, 0, 25, 0, 26, 0, 27, 0, 28, 0, 29, 0, 30"
    sn = "AAAAAAAACCDDFF"
    snToBytes = []
    message = [0xaa, 0xaa]
    for i in range(0, len(sn)):
        single = ord(sn[i])
        print sn[i]
        print ord(sn[i])
        print type(single)
        snToBytes.append(ord(sn[i]))
    print snToBytes

    print type(snToBytes[0])
    dataString = "".join(map(chr, snToBytes))
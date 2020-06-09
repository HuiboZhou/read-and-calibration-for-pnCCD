#!/usr/bin/env python
from collections import Counter
import numpy as np
# import matplotlib.pyplot as plt
import gc
import binascii
import logging

initial_file_name='test.dat'


"""
# 将源文件进行拆分，文件太大，占用大量内存
# 拆分过程中将二进制流转成十六进制文本数据
"""
# 将源文件进行分隔处理
# 将源文件的二进制数据转成16进制，分文件保存
print("开始拆分文件")

hex_file_list=[]
file_count=0
with open(initial_file_name,'rb') as inf:    
    while True:
        # 每次读取16M数据保存        
        a=inf.read(1024*1024*16)
        if not a:
            break
        # 创建新文件
        file_name='hex_'+str(file_count)+'.dat'
        with open(file_name,'w') as of:
            # 将二进制数据转成16进制数据，并写入文件
            of.write(str(binascii.b2a_hex(a)))
        # 保存文件名称
        hex_file_list.append(file_name)
        print("生成文件"+file_name)
        # 清理内存
        del a
        del file_name
        gc.collect()

        file_count+=1

"""
# 根据数据块头信息，将文本信息拆分成行，每行一个完成的数据块
"""
print("开始拆分数据块")
# 标记数据块头
header='eb9055aa66'
# 总数据块数量
total_row_count=0
# 16进制数据文件名称列表
hex_row_file_list=[]
# 每个文件的数据块数量
file_row_count=0

end_content=""
# 依次处理每个文件。必须依次处理
for file in hex_file_list:
    index=0
    head_position=0
    
    with open(file,'r') as inf:
        hex_row_file_name="row_"+file
        # 读取一个文件，写入一个文件
        with open(hex_row_file_name,'w') as of:
            file_row_count=0
            # 每次读取整个文件内容
            file_content=inf.read()

            # 如果上次读取的数据有部分残留，记录在end_content变量中，添加到本次文件内容前头
            # 初始文件内容开头有b'标记，末尾有'标记，需要删除
            hex_content=end_content+file_content[2:-1]
            temp_hex_content=hex_content

            # 开始从文本中查找数据块头
            # 因为每个文件内容大小16m,因此可以确定文件中肯定存在数据块头
            # 所以此处不需要判断index是否为-1
            index=temp_hex_content.find(header)

            # 找到第一个数据块头之后，将下标给于head_position，
            # 再找下一个数据块头
            head_position=index
            index=temp_hex_content.find(header,head_position+1)

            # 如果能找到下一个数据块头，进行数据写入
            while (index != -1):
                of.write(temp_hex_content[head_position:index])
                of.write('\n')
                file_row_count+=1
                # 继续找新的数据块头
                head_position=index
                index=temp_hex_content.find(header,head_position+1)
            
            # 数据全部找完，将该文件的剩余内容传给end_content
            # 在处理下一个文件内容时使用     
            end_content=""
            end_content=temp_hex_content[head_position:]
    
    hex_row_file_list.append(hex_row_file_name)
    print("文件"+file+"处理完毕，数据写入文件"+hex_row_file_name+"，共"+str(file_row_count)+"行")

"""
# 这里从文本中读取数据块头部信息，验证帧的是否连续
# 数据帧正常格式长度：98304*18+1080+18+2+12+40=1770624个二进制
# 十六进制长度：1770624/4=442656
"""
# frame -> 帧
# 记录行信息的信息，包括数据块内的帧号，数据块的长度等
# 每个itme的格式：file_name+row_no:{'frame_no':frame_no,'length':length}

# hex_row_file_list=['row_hex_0.dat','row_hex_1.dat','row_hex_2.dat','row_hex_3.dat','row_hex_4.dat','row_hex_5.dat','row_hex_6.dat','row_hex_7.dat',
# 'row_hex_8.dat','row_hex_9.dat','row_hex_10.dat','row_hex_11.dat','row_hex_12.dat']
# hex_row_file_list=['row_hex_0.dat']
print("汇总所有行中数据块信息")
data_frame_info={}
row_count=0
for file in hex_row_file_list:
    with open(file,'r') as inf:
        line_no=0
        for line in inf.readlines():
            frame_no=int(line[10:13],16)
            length=len(line)
            # CRC码使用下面的语句处理
            crc=line[13:18]
            # 有效数据
            effect_data=line[288:]
            data_frame_info[file+":"+str(line_no)]={"frame_no":frame_no,"length":length,"crc":crc,"effect_data":effect_data}
            line_no+=1
            row_count+=1
    print("文件"+file+"处理完毕，共处理"+str(line_no)+"行")
print("所有数据块信息整理完毕，共"+str(row_count)+"个数据块")

print("检查帧号信息")
# 生成帧编号上升序列
frame_list=[v["frame_no"] for v in data_frame_info.values()]
frame_list.sort()
min_frame=min(frame_list)
max_frame=max(frame_list)
order_frame_list=frame_list.sort()



# 检测真编号之间的差值
frame_diff_list=[frame_list[i+1]-frame_list[i] for i in range(len(frame_list)-2)]
# 取出现最多的差值记为正常差值
normal_frame_diff=Counter(frame_diff_list).most_common(1)
diff=normal_frame_diff[0][0]

# 找到所有缺失的帧
lost_frame=[]
# 正常帧序列
normal_frame=[]
for i in range(max_frame-min_frame+1):
    normal_frame.append(min_frame+i*int(diff))
    if(min_frame+i*int(diff) not in frame_list):
        lost_frame.append(min_frame+i*int(diff))

print("帧数："+str(row_count)+",最小帧："+str(min_frame)+", 最大帧："+str(max_frame)+", 帧号间隔："+str(diff))

if(len(lost_frame)>0):
    print("以下数据帧缺失："+','.join(lost_frame))
else:
    print("数据帧无缺失")

# 找到错误编号的帧
# 正常帧序列号
error_frame=[]
for f in frame_list:
    if (f not in normal_frame):
        error_frame.append(f)
if(len(error_frame)>0):
    print("以下帧号错误："+','.join([str(e) for e in error_frame]))
else:
    print("不存在异常帧号")


# 检测帧长度，正常帧长度:442657
# 注意：生成帧数据最后有一个换行符（\n），因此，长度会多一个字符
# 查询出现次数最多的长度作为正常数据帧长度
error_length_frame={}
frame_length_list=[v["length"] for v in data_frame_info.values()]
common_frame_length=Counter(frame_length_list).most_common(1)
normal_frame_length=common_frame_length[0][0]

for key,value in data_frame_info.items():
    if(value["length"]!=normal_frame_length):
        error_length_frame[key]=value

if(len(error_length_frame)>0):
    print("以下帧数据长度错误：")
    for key,value in error_length_frame.items():
        print("文件"+key.split(":")[0]+"第"+str(key.split(":")[1])+"行，帧号"+str(value["frame_no"]))
else:
    print("所有帧长度正常，每帧数据长度为"+str(normal_frame_length))


# 通过词典方法，将十六进制字符串转成二进制字符串
def hex2bin(hex):
    """
    :param hex 十六进制字符串
    """
    hex2bin_dict={
        '0':'0000',
        '1':'0001',
        '2':'0010',
        '3':'0011',
        '4':'0100',
        '5':'0101',
        '6':'0110',
        '7':'0111',
        '8':'1000',
        '9':'1001',
        'a':'1010',
        'b':'1011',
        'c':'1100',
        'd':'1101',
        'e':'1110',
        'f':'1111',
    }
    bin=""
    for c in hex:
        if c in hex2bin_dict.keys():
            bin+=hex2bin_dict[c]
        else:
            pass

    return bin

# 将六进制字符串转成十进制数字之后保存至文件
# 文件名称位dec_effect_data.dat
# 文件中每行数据格式：{frame_no:[dec_data1,dec_data2,...]}
# 每个文件75行，代表75个有效数据
print("将有效数据转成十进制数据保存至文件")
frame_count=0
dec_frame_list=[]
file_count=0
for key,value in data_frame_info.items():
    bin_effect_data=hex2bin(value["effect_data"])
    dec_data_list=[]
    for c in range(98304-1):
        bin_data=bin_effect_data[c*18:(c+1)*18]
        dec_data_list.append(int(bin_data,2))
    dec_frame_list.append({value['frame_no']:dec_data_list})
    frame_count+=1

    # 每75条有效数据保存至一个文件
    if(frame_count==75):
        with open('dec_effect_data_'+str(file_count)+'.dat','w') as of:
            for dec_frame in dec_frame_list:
                of.write(str(dec_frame))
                of.write('\n')
        print('75条十进制有效数据保存至文件'+'dec_effect_data_'+str(file_count)+'.dat')
        frame_count=0
        dec_data_list=[]
        file_count+=1
        gc.collect()

        
# 将最后剩余一部分数据写入新的文件
with open('dec_effect_data_'+str(file_count)+'.dat','w') as of:
    for dec_frame in dec_frame_list:
        of.write(str(dec_frame))
        of.write('\n')
print('75条十进制有效数据保存至文件'+'dec_effect_data_'+str(file_count)+'.dat')

exit(0)

# 两个二进制字符串异或操作函数
# def xor(bin_a,bin_b):
#     # 如果两个二进制字符串的长度不一致，短的字符串左侧补0
#     length=len(bin_a) if len(bin_a)>=len(bin_b) else len(bin_b)
#     if(len(bin_a)<length):
#         bin_a.rjust(length,'0')
#     elif(len(bin_b)<length):
#         bin_b.rjust(length,'0')

#     result=[]
#     for i in range(length):
#         if(bin_a[i]==bin_b[i]):
#             result.append('0')
#         else:
#             result.append('1')

#     return ''.join(result)

# 
def crc(bin_a,bin_b):
    """
    :param bin_a 被除数
    :param bin_b 除数
    """

    # 现在被除数右侧补充为除数长度减一个0
    # 作为被除数整体
    bin_dided=bin_a.ljust(len(bin_a)+len(bin_b)-1,'0')

    len_bin_b=len(bin_b)
    len_bin_dided=len(bin_dided)
    result=''
    count=0

    # 将下标定义到除数长度减一
    # 这里的下标为被除数整体的下标
    index=len_bin_b-1
    # divided为实际执行过程中的被除数
    # 将原被除数中左侧截取与被除数长度相等的部分作为最初被除数，
    # 给予divided
    dividend=bin_dided[0:len_bin_b] 
    # 循环计算至下标到被除数整体的末尾
    while index<len_bin_dided-1:
        # 检查当前被除数缺少多少个二进制字符
        len_diff=18-len(dividend)
        
        if(len_diff>0):
            if(index+len_diff<=len_bin_dided-1):
                # 被除数整体有足够的二进制字符可以使用
                # 从被除数整体中当前下标位置向后查相应数量的二进制字符
                # 添到被除数的右侧末尾
                dividend=dividend+bin_dided[index:index+len_diff]
                # 被除数添加二进制字符之后
                # 被除数整体的下标也要相应的向后移动相应的位数
                index+=len_diff
            else:
                # 如果被除数整体没有足够的二进制字符可以添加到被除数，
                # 直接将被除数整体从当前下标至右侧末尾的全部二进制字符串
                # 添加到被除数右侧末尾
                dividend=dividend+bin_dided[index:]
                # 被除数的下标置为末尾
                index=len_bin_dided-1

        # dividend=xor(dividend,bin_b)
        # 将二进制字符串转成十进制数字之后进行异或操作
        # 注意返回值转成二进制字符串之后，第一位总是1，长度小于等参与异或操作的二进制字符串的最大长度
        dividend=bin(int(dividend,2)^int(bin_b,2))[2:]

    # 将最终CRC数值左侧补0，至18位后返回
    return dividend.rjust(18,'0')


# 有效数据的CRC计算方法
def effect_crc(effect_data):
    '''
    :param effect_data 十六进制有效数据
    '''

    # 将十六进制数据转为二进制
    bin_effect_data=hex2bin(effect_data)

    # 有效数据的crc生成函数x^18+x^4+x^3+1
    bin_divisor='100000000000011001'
    c=0
    for c in range(98304-1):
        # 每次取二进制有效数据18bit数据
        # 计算其CRC,并将该CRC结果作为下一次计算的除数
        # 依次循环处理
        bin_xor=crc(bin_effect_data[c*18:(c+1)*18],bin_divisor)
        bin_divisor=bin_xor

    # 将最终结果通过左侧补0的方式补全20位，
    # 生成十六进制数据
    full_bin_xor=bin_xor.rjust(20,'0')
    return hex(int(full_bin_xor,2))[2:]


# 从数据列表中抽取CRC与对应的有效数据进行判断
error_crc={}
for key,value in data_frame_info.items():
    # print("crc:"+value["crc"]+"------->effect:"+effect_crc(effect_data))
    if(value["crc"]!=effect_crc(value["effect_data"])):
        error_crc[key]=value
if(len(error_crc)>0):
    print("以下帧数据CRC校验未通过：")
    for key,value in error_crc.items():
        print("文件"+key.split(":")[0]+"第"+str(key.split(":")[1])+"行，帧号"+str(value["frame_no"]))
else:
    print("所有数据帧CRC验证通过")

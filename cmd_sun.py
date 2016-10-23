#!/usr/bin/env python
# coding:utf-8
# Author: Sun Yang
# version 1.0.0

import configparser
import os
import optparse
import paramiko
from gevent import monkey; monkey.patch_all()
import gevent


BASE_DIR = os.path.dirname((os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR,'data')
GET_DIR = os.path.join(BASE_DIR,'get_file')

ip_dic = {}
group_dic = {}

pool_dic = {}
pool_list = []

PORT = 22
USER = 'root'
# 默认的put文件传递到其他服务器的/tmp下
PUT_PATH = '/tmp'



def config_dic(mode=None,file_name="ip"):
    conf = configparser.ConfigParser()
    conf.read(os.path.join(DATA_DIR, file_name), encoding='utf-8')
    sections = conf.sections()
    if mode == None:
        for i in sections:
            p_dic = {}
            kvs = conf.items(i)
            p_dic[kvs[0][0]] = kvs[0][1]
            ip_dic[i] = p_dic
            # print(i,p_dic)
    elif mode == "group":
        for i in sections:
            g_dic = {}
            kvs = conf.items(i)
            g_list = kvs[0][1].split(',')
            g_dic[kvs[0][0]] = g_list
            group_dic[i] = g_dic
    check_conf()


def check_conf():
    num = 0
    for key,val in group_dic.items():
        for i in val['hosts']:
            if i not in ip_dic:
                print("%s主机组中的 %s主机在ip文件内不存在。请检查！"%(key,i))
                num += 1
    if num !=0:
        exit()

# 获取配置文件的信息，写为字典
config_dic()
config_dic(mode='group',file_name='group')



parser = optparse.OptionParser('usage '+'-H<host,host...or all> -G<group name> -L<group or hosts list> '
                                               '--get<filename>'
                                               '--put<filename> --cmd<system command>')
parser.add_option('-H',dest='host',type='string',help='需要执行的服务器ip地址多个逗号隔开')
parser.add_option('-L',dest='group_host_list',type='string',help='查看主机组和主机信息')
parser.add_option('-G',dest='group',type='string',help='需要执行的组的名称')
parser.add_option('--get',dest='get_file',type='string',help='需要下载的文件')
parser.add_option('--put',dest='put_file',type='string',help='需要上传的文件')
parser.add_option('--cmd',dest='command',type='string',help='需要执行的命令')

(options,args) = parser.parse_args()
if options.group_host_list == None:
    if options.host == None and options.group == None:
        print("-H 与 -G 两者必须有一个 请查看帮助  -help")
        exit(0)
    elif options.host != None and options.group != None:
        print("-H 与 -G 两者只能有一个 请查看帮助  -help")
        exit(0)
    elif options.get_file == None and options.put_file == None and options.command == None:
        print('--get --put --cmd 必须有一个')
        exit(0)
    elif options.get_file != None and options.put_file != None:
        print('--get --put --cmd 只能有一个')
        exit(0)
    elif options.get_file != None and options.command != None:
        print('--get --put --cmd 只能有一个')
        exit(0)
    elif options.put_file != None and options.command != None:
        print('--get --put --cmd 只能有一个')
        exit(0)
elif options.group_host_list == 'hosts':
    for ip_list in ip_dic.keys():
        print(ip_list)
elif options.group_host_list == 'group':
    for group_list in group_dic.keys():
        print(group_list,group_dic[group_list]['hosts'])


def sun_cmd(ip, port, user, passwd, command):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip, port, user, passwd)
    stdin,stdout,stderr = ssh.exec_command(command)
    gevent.sleep()

    err = stderr.readline()
    out = stdout.read()
    if "" != err:
        print("########################### %s\ncommand: "%ip + command + " exec failed!\nERROR :%s\n"%err)
        # print("command: " + command + " exec failed!\nERROR :" + err)
    else:
        print("########################### %s\n%s\n"%(ip, str(out, encoding='utf8')))



def sun_put(ip, port, user, passwd, localpath, remotepath):
    client = paramiko.Transport((ip, port))
    client.connect(username=user, password=passwd)
    sftp = paramiko.SFTPClient.from_transport(client)
    try:
        sftp.put(localpath, remotepath)
        print("########################### %s\n%s 文件上传完毕"%(ip,localpath))
    except Exception:
        print("########################### %s\n请查看服务器/tmp下是否有相同文件名的目录！"%ip)
    client.close()


def sun_get(ip, port, user, passwd, localpath, remotepath):
    client = paramiko.Transport((ip, port))
    client.connect(username = user, password = passwd)
    sftp = paramiko.SFTPClient.from_transport(client)
    try:
        sftp.get(remotepath, localpath)
        print("########################### %s\n%s 文件下载完毕"%(ip,localpath))
    except:
        print("########################### %s\n远程需要get的文件不存在！"%ip)
        os.remove(localpath)
    client.close()





####################################################### Logic code


if options.host != None and options.command != None:
    if options.host == 'all':
        for host_ip in ip_dic.keys():
            pool_list.append(gevent.spawn(sun_cmd, host_ip, PORT, USER, ip_dic[host_ip]['passwd'], options.command))
        gevent.joinall(pool_list)
    else:
        num = 0
        ip_list = options.host.split(',')
        for i in ip_list:
            if i not in ip_dic:
                print("%s data/ip 配置文件内没有找到此条记录！请添加"%i)
                num +=1
        if num != 0:
            exit(0)
        for host_ip in ip_list:
            pool_list.append(gevent.spawn(sun_cmd,host_ip,PORT,USER,ip_dic[host_ip]['passwd'],options.command))
        gevent.joinall(pool_list)
elif options.group != None and options.command != None:
    if options.group not in group_dic:
        print("输入的组名有误，请-L group 查看组信息后再执行！")
        exit()
    for host_ip in group_dic[options.group]['hosts']:
        pool_list.append(gevent.spawn(sun_cmd, host_ip, PORT, USER, ip_dic[host_ip]['passwd'], options.command))
    gevent.joinall(pool_list)
elif options.host != None and options.put_file != None:
    # sun_put('192.168.2.141', 22, 'root', 'hYu6M2+qroy', 'F:\\config.ini', '/tmp/a/a')
    if options.host == 'all':
        for host_ip in ip_dic.keys():
            pool_list.append(gevent.spawn(sun_put, host_ip, PORT, USER, ip_dic[host_ip]['passwd'], options.put_file,
                                          os.path.join(PUT_PATH, os.path.split(options.put_file)[-1])))
            gevent.joinall(pool_list)
    else:
        num = 0
        ip_list = options.host.split(',')
        for i in ip_list:
            if i not in ip_dic:
                print("%s data/ip 配置文件内没有找到此条记录！请添加"%i)
                num +=1
        if num != 0:
            exit(0)
        for host_ip in ip_list:
            pool_list.append(gevent.spawn(sun_put,host_ip,PORT,USER,ip_dic[host_ip]['passwd'],options.put_file,
                                          os.path.join(PUT_PATH,os.path.split(options.put_file)[-1])))
        gevent.joinall(pool_list)

elif options.group != None and options.put_file != None:
    if options.group not in group_dic:
        print("输入的组名有误，请-L group 查看组信息后再执行！")
        exit()
    for host_ip in group_dic[options.group]['hosts']:
        pool_list.append(gevent.spawn(sun_put, host_ip, PORT, USER, ip_dic[host_ip]['passwd'], options.put_file,
                                      os.path.join(PUT_PATH,os.path.split(options.put_file)[-1])))
    gevent.joinall(pool_list)

elif options.host != None and options.get_file != None:
    if options.host == 'all':
        for host_ip in ip_dic.keys():
            get_file_path = os.path.join(GET_DIR,host_ip)
            if not os.path.isdir(get_file_path):
                os.mkdir(get_file_path)
            pool_list.append(gevent.spawn(sun_get, host_ip, PORT, USER, ip_dic[host_ip]['passwd'],
                                          os.path.join(get_file_path, os.path.split(options.get_file)[-1]),
                                          options.get_file))
        gevent.joinall(pool_list)
    else:
        num = 0
        ip_list = options.host.split(',')
        for i in ip_list:
            if i not in ip_dic:
                print("%s data/ip 配置文件内没有找到此条记录！请添加"%i)
                num +=1
        if num != 0:
            exit(0)
        for host_ip in ip_list:
            get_file_path = os.path.join(GET_DIR,host_ip)
            if not os.path.isdir(get_file_path):
                os.mkdir(get_file_path)
            pool_list.append(gevent.spawn(sun_get,host_ip,PORT,USER,ip_dic[host_ip]['passwd'],
                                          os.path.join(get_file_path,os.path.split(options.get_file)[-1]),options.get_file))
        gevent.joinall(pool_list)
elif options.group != None and options.get_file != None:
    if options.group not in group_dic:
        print("输入的组名有误，请-L group 查看组信息后再执行！")
        exit()
    for host_ip in group_dic[options.group]['hosts']:
        get_file_path = os.path.join(GET_DIR,host_ip)
        if not os.path.isdir(get_file_path):
            os.mkdir(get_file_path)
        pool_list.append(gevent.spawn(sun_get,host_ip,PORT,USER,ip_dic[host_ip]['passwd'],
                                      os.path.join(get_file_path,os.path.split(options.get_file)[-1]),options.get_file))
    gevent.joinall(pool_list)
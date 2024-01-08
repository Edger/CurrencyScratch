#! /usr/bin/env/ python
# -*- coding:UTF-8 -*-
# Author: Zhu Huaren

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox, filedialog
from tkinter import scrolledtext  # 导入滚动文本框的库
from tkcalendar import Calendar
import requests
from lxml import etree
import xlrd
from xlutils.copy import copy
import xlwt
from datetime import datetime
import os
import time
import random
import threading

# 设置请求头模拟浏览器行为
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}

# 控制查询过程的标志
is_fetching = False
fetch_thread = None

# 检查文件是否存在，如果不存在则创建
def initialize_excel(start_date, end_date, currency):
    excel_file = '{}兑人民币_{}~{}.xls'.format(currency, start_date, end_date)
    
    if not os.path.exists(excel_file):
        workbook = xlwt.Workbook()  # 创建一个新的工作簿
        worksheet = workbook.add_sheet('Sheet1')  # 添加一个工作表
        worksheet.write(0, 0, '货币名称')
        worksheet.write(0, 1, '现汇买入价')
        worksheet.write(0, 2, '现钞买入价')
        worksheet.write(0, 3, '现汇卖出价')
        worksheet.write(0, 4, '现钞卖出价')
        worksheet.write(0, 5, '中行折算价')
        worksheet.write(0, 6, '发布时间')
        workbook.save(excel_file)

    if not os.path.exists(excel_file):
        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet('Sheet1')
        titles = ['货币名称', '现汇买入价', '现钞买入价', '现汇卖出价', '现钞卖出价', '中行折算价', '发布时间']
        for col, title in enumerate(titles):
            worksheet.write(0, col, title)
        workbook.save(excel_file)

def parse_timeYmdhms(time_str):
    return datetime.strptime(time_str.strip(), '%Y.%m.%d %H:%M:%S')

def parse_timeYmd(time_str):
    return datetime.strptime(time_str.strip(), '%Y-%m-%d')

# 用于将字符串转换为浮点数的辅助函数
def to_float(s):
    try:
        return float(s)
    except ValueError:
        return 0  # 或者你可以选择返回None或者其他合适的值

# row = 1  # 从第二行开始写入数据

def fetch_data(start_date, end_date, currency):
    global is_fetching

    initialize_excel(start_date, end_date, currency)
    row = 1
    end_date_1030_fetched = False  # 标记是否获取到了end_date对应日期的10:30的汇率
    page = 1  # 从第一页开始抓取

    output_text.after(0, insert_data, '查询日期：{}～{}'.format(start_date, end_date))                 

    while is_fetching:
        # 如果 is_fetching 变为 False，停止查询操作
        if not is_fetching:
            break

        try:
            print('第{}页爬取开始...'.format(page))
            output_text.after(0, insert_data, '第 {} 页查询开始...'.format(page))                

            form_data = {
                'erectDate': start_date,
                'nothing': end_date,
                'pjname': currency,
                'page': page,
            }
            url = 'https://srh.bankofchina.com/search/whpj/search_cn.jsp'
            res = requests.post(url=url, data=form_data, headers=headers)
            html = etree.HTML(res.text)

            # 尝试获取当前页面的所有汇率记录的日期
            record_dates = html.xpath('//tr[position()>1]/td[7]/text()')
            # print('record_dates = {}'.format(record_dates))

            # 检查是否有数据
            if not record_dates:
                print('not record_dates = true')
                if end_date_1030_fetched:
                    # 查询结束或被中断时，重置按钮状态
                    submit_button.after(0, stop_fetch)
                    break  # 如果已经获取到所需日期的10:30记录且当前页面为空，正常结束循环
                else:
                    messagebox.showerror("错误", "无法获取到指定日期的汇率数据。")
                    # 查询结束或被中断时，重置按钮状态
                    submit_button.after(0, stop_fetch)
                    break  # 如果还没有获取到指定日期的10:30记录且当前页面为空，异常结束循环

            # 打开工作表并进行初始化，避免每次循环时打开和保存
            excel_file = '{}兑人民币_{}~{}.xls'.format(currency, start_date, end_date)
            workbook = xlrd.open_workbook(excel_file)
            workbook_copy = copy(workbook)
            worksheet = workbook_copy.get_sheet(0)

            for j in range(2, 22):
                date = html.xpath('//tr[{}]/td[7]/text()'.format(j))
                date_text = ''.join(date).strip()
                # 检查时间是否为10:30:00
                if date_text.endswith('10:30:00'):
                    if parse_timeYmdhms(date_text).date() == parse_timeYmd(start_date).date():
                        # print('date_text = {}'.format(parse_timeYmdhms(date_text).date()))
                        # print('end_date = {}'.format(parse_timeYmd(end_date).date()))
                        end_date_1030_fetched = True
                        # print('end_date_1030_fetched = {}'.format(end_date_1030_fetched))
                    m_n = html.xpath('//tr[{}]/td[1]/text()'.format(j))
                    s_e_p = html.xpath('//tr[{}]/td[2]/text()'.format(j))
                    c_p = html.xpath('//tr[{}]/td[3]/text()'.format(j))
                    s_e_sp = html.xpath('//tr[{}]/td[4]/text()'.format(j))
                    c_s = html.xpath('//tr[{}]/td[5]/text()'.format(j))
                    bank_count_p = html.xpath('//tr[{}]/td[6]/text()'.format(j))

                    # 使用 strip() 方法去除每个字符串元素的首尾空格
                    # 需要确保列表不为空，并且取列表的第一个元素（通常这些xpath返回的是单个字符串的列表）
                    data = '{} {} {} {} {} {} {}'.format(
                        m_n[0].strip() if m_n else '',
                        s_e_p[0].strip() if s_e_p else '',
                        c_p[0].strip() if c_p else '',
                        s_e_sp[0].strip() if s_e_sp else '',
                        c_s[0].strip() if c_s else '',
                        bank_count_p[0].strip() if bank_count_p else '',
                        date_text.strip() if date_text else ''
                    ) 
                    output_text.after(0, insert_data, data)                  

                    # 将数据写入工作表
                    worksheet.write(row, 0, ''.join(m_n).strip())
                    worksheet.write(row, 1, to_float(''.join(s_e_p).strip()))
                    worksheet.write(row, 2, to_float(''.join(c_p).strip()))
                    worksheet.write(row, 3, to_float(''.join(s_e_sp).strip()))
                    worksheet.write(row, 4, to_float(''.join(c_s).strip()))
                    worksheet.write(row, 5, to_float(''.join(bank_count_p).strip())) 
                    worksheet.write(row, 6, ''.join(date).strip())
                    
                    row += 1  # 只有写入数据后才递增行号

            # 循环结束后保存工作表
            workbook_copy.save(excel_file)
            output_text.after(0, insert_data, '第 {} 页查询完成...'.format(page))

            # 判断是否已经获取到结束日期的10:30数据
            if end_date_1030_fetched:
                print('已获取到开始日期的 10:30 数据，退出循环。')
                output_text.after(0, insert_data, '已获取到开始日期的 10:30 数据, 停止查询')
                # 查询结束或被中断时，重置按钮状态
                submit_button.after(0, stop_fetch)
                break
            
            # 随机暂停 1 到 3 秒
            time.sleep(random.uniform(1, 5))

            page += 1  # 准备获取下一页的数据
        
        except Exception as e:
            messagebox.showerror("错误", "在爬取数据时发生了异常：{}".format(e))
            # 查询结束或被中断时，重置按钮状态
            submit_button.after(0, stop_fetch)
            break  # 发生异常，结束循环

    # 爬取完成后开始处理数据
    # 读取数据
    workbook = xlrd.open_workbook(excel_file)
    worksheet = workbook.sheet_by_index(0)
    data = []
    for i in range(1, worksheet.nrows):
        row_data = worksheet.row_values(i)
        # 去除空格
        row_data[6] = row_data[6].strip()
        data.append(row_data)

    # 去除重复并排序
    # 注意这里我们使用了一个字典来确保同一天的数据只保留一个
    data_dict = {parse_timeYmdhms(row[6]).date(): row for row in data}
    unique_data = list(data_dict.values())

    sorted_data = sorted(unique_data, key=lambda x: parse_timeYmdhms(x[6]))  # 按时间排序

    # 写入新的Excel文件中
    new_workbook = xlwt.Workbook()
    new_worksheet = new_workbook.add_sheet('Sheet1')

    # 写入标题行
    titles = ['货币名称', '现汇买入价', '现钞买入价', '现汇卖出价', '现钞卖出价', '中行折算价', '发布时间']
    for col, title in enumerate(titles):
        new_worksheet.write(0, col, title)

    # 写入去重并排序后的数据
    for i, row_data in enumerate(sorted_data, start=1):
        for j, value in enumerate(row_data):
            new_worksheet.write(i, j, value)

    # 保存新的Excel文件
    sorted_excel_file = '{}兑人民币_{}~{}_sorted.xls'.format(currency, start_date, end_date)
    new_workbook.save(sorted_excel_file)
    print('数据排序和去重完成，已保存到文件 {}'.format(sorted_excel_file))
    output_text.after(0, insert_data, '数据排序和去重完成，已保存到文件【{}】'.format(sorted_excel_file))

# 创建图形界面
root = tk.Tk()
root.title("外币兑人民币汇率查询工具")

style = ttk.Style(root)
style.theme_use('clam')

# 创建一个容器帧来横向居中所有内容
container_frame = tk.Frame(root)
container_frame.pack()

# 开始日期选择器容器
start_frame = tk.Frame(container_frame)
start_frame.pack(side=tk.LEFT, padx=10)  # side=tk.LEFT 用于横向并排，padx用于添加水平间距

# 开始日期标签
label_start = tk.Label(start_frame, text="开始日期:")
label_start.pack(anchor="center")

# 开始日期日历控件
cal_start = Calendar(
    start_frame, 
    selectmode='day', 
    year=datetime.now().year, 
    month=datetime.now().month, 
    day=datetime.now().day, 
    showweeknumbers=False,
    firstweekday='sunday'
    )
cal_start.pack(pady=(0, 10))  # pady用于在日历控件下方添加一些空间

# 结束日期选择器容器
end_frame = tk.Frame(container_frame)
end_frame.pack(side=tk.LEFT, padx=10)  # 同上

# 结束日期标签
label_end = tk.Label(end_frame, text="结束日期:")
label_end.pack(anchor="center")

# 结束日期日历控件
cal_end = Calendar(
    end_frame, 
    selectmode='day', 
    year=datetime.now().year, 
    month=datetime.now().month, 
    day=datetime.now().day, 
    showweeknumbers=False,
    firstweekday='sunday'
    )
cal_end.pack(pady=(0, 10))

# 货币名称输入
label_currency = tk.Label(root, text="外币名称:")
label_currency.pack(pady=(10, 0))
entry_currency = tk.Entry(root)
entry_currency.pack(pady=(0, 10))

# 提交按钮的回调函数
def start_fetch():
    global is_fetching, fetch_thread
    is_fetching = True
    submit_button.config(text="停止查询", command=stop_fetch, fg="red")
    
    # 将日期从 "YYYY/M/D" 格式转换为 "YYYY-MM-DD" 格式
    start_date_str = cal_start.get_date()
    end_date_str = cal_end.get_date()
    
    # 此处处理单个数字月份和日期，例如将 "2024/1/8" 转换为 "2024-01-08"
    start_date = datetime.strptime(start_date_str, "%Y/%m/%d").strftime("%Y-%m-%d")
    end_date = datetime.strptime(end_date_str, "%Y/%m/%d").strftime("%Y-%m-%d")
    
    currency = entry_currency.get()
    print('开始时间: {}, 结束时间: {}'.format(start_date, end_date))
    
    if datetime.strptime(start_date, "%Y-%m-%d") > datetime.strptime(end_date, "%Y-%m-%d"):
        messagebox.showerror("错误", "开始日期必须早于结束日期。")
        return
    
    # 运行爬取数据的函数
    # 创建并启动一个线程来运行耗时的操作
    threading.Thread(target=fetch_data, args=(start_date, end_date, currency)).start()
    # fetch_data(start_date, end_date, currency)

# 停止查询的函数
def stop_fetch():
    global is_fetching
    is_fetching = False
    submit_button.config(text="开始查询", command=start_fetch, fg="black")

# 初始状态为开始查询
submit_button = tk.Button(root, text="开始查询", command=start_fetch)
submit_button.pack()

# 输出框
output_frame = tk.Frame(root)
output_frame.pack(pady=10)

output_text = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, height=30, width=100)
output_text.pack()

# 当需要向GUI组件插入数据时，需要使用线程安全的方法
def insert_data(data):
    if output_text:
        output_text.insert(tk.END, data + '\n')  # 将数据插入到输出框
        output_text.see(tk.END)          # 滚动到最新的一条数据

# 运行主循环前最大化窗口
# root.state('zoomed')

# 运行主循环
root.mainloop()

#!/bin/bash

# 检查是否提供了足够的参数
if [ "$#" -lt 2 ]; then
  echo "用法: $0 <IP地址> <协议类型: tcp/udp>"
  exit 1
fi

# 获取用户提供的IP地址和协议类型
ip_address="$1"
protocol="$2"

# 检查协议类型是否为tcp或udp
if [ "$protocol" != "tcp" ] && [ "$protocol" != "udp" ]; then
  echo "无效的协议类型。请使用 'tcp' 或 'udp'。"
  exit 1
fi

# 使用nmap扫描指定的IP地址和协议类型
echo "开始对 $ip_address 进行nmap端口扫描..."

if [ "$protocol" == "tcp" ]; then
  echo "* 正在执行tcp协议的端口扫描探测..."
  echo "sudo nmap -min-rate 10000 -p- \"$ip_address\" "-oG" \"$ip_address\"-tcp-braker-allports"
  echo ""
  sudo nmap -min-rate 10000 -p- "$ip_address" -oG "$ip_address"-tcp-braker-allports
  nmap_port_result=$(grep -oE '([0-9]+)/open' "$ip_address"-tcp-braker-allports | awk -F/ '{print $1}' | tr '\n' ',')
  echo "* 正在对开放的端口进行TCP全连接式版本探测和系统版本以及漏洞探测..."
  echo "sudo nmap -sT -sV -sC -O -p\"$nmap_port_result\" \"$ip_address\""
  echo ""
  sudo nmap -sT -sV -sC -O -p"$nmap_port_result" "$ip_address"

elif [ "$protocol" == "udp" ]; then
  echo "* 正在执行udp协议的端口扫描探测..."
  echo "sudo nmap -min-rate 10000 -p- -sU \"$ip_address\" "-oG" \"$ip_address\"-udp-braker-allports"
  echo ""
  sudo nmap -min-rate 10000 -p- -sU "$ip_address" -oG "$ip_address"-udp-braker-allports
  nmap_port_result=$(grep -oE '([0-9]+)/open' "$ip_address"-udp-braker-allports | awk -F/ '{print $1}' | tr '\n' ',')
  echo "* 正在对开放的端口进行udp式版本探测和系统版本探测..."
  echo "sudo nmap -sV -sU -sC -O -p\"$nmap_port_result\" \"$ip_address\""
  echo ""
  sudo nmap -sV -sU -sC -O -p"$nmap_port_result" "$ip_address"

fi
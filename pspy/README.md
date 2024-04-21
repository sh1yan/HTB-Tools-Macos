# [![img](https://github.com/DominicBreuker/pspy/raw/master/images/logo.svg)](https://github.com/DominicBreuker/pspy/blob/master/images/logo.svg)[pspy - 非特权 Linux 进程监听](https://github.com/DominicBreuker/pspy#pspy---unprivileged-linux-process-snooping)

[![去报告卡](https://camo.githubusercontent.com/5ffe39791a9c1a40662e06e373b0ba72e160854491ad6e7b87a19a0c87d3b204/68747470733a2f2f676f7265706f7274636172642e636f6d2f62616467652f6769746875622e636f6d2f446f6d696e6963427265756b65722f70737079)](https://goreportcard.com/report/github.com/DominicBreuker/pspy) [![可维护性](https://camo.githubusercontent.com/0b4272d14f3e3e06d1b1d92f07079a1e1d2c187f1278649e74f6427dfa53d367/68747470733a2f2f6170692e636f6465636c696d6174652e636f6d2f76312f6261646765732f32333332386232353439613736616131316464352f6d61696e7461696e6162696c697479)](https://codeclimate.com/github/DominicBreuker/pspy/maintainability) [![测试覆盖率](https://camo.githubusercontent.com/10647b8ba6b179d7288500f932070a28f856ea32bf42b6cac283de9921057a3a/68747470733a2f2f6170692e636f6465636c696d6174652e636f6d2f76312f6261646765732f32333332386232353439613736616131316464352f746573745f636f766572616765)](https://codeclimate.com/github/DominicBreuker/pspy/test_coverage) [![循环CI](https://camo.githubusercontent.com/d285222c93cd6a8aa0847de747be4a0f9ef56660f3b883fbdc8348ef0b76aadf/68747470733a2f2f636972636c6563692e636f6d2f67682f446f6d696e6963427265756b65722f707370792e7376673f7374796c653d737667)](https://circleci.com/gh/DominicBreuker/pspy)

pspy 是一个命令行工具，旨在无需 root 权限即可窥探进程。它允许您在执行时查看其他用户运行的命令、cron 作业等。非常适合在 CTF 中枚举 Linux 系统。也很高兴向您的同事展示为什么在命令行上将秘密作为参数传递是一个坏主意。

该工具从 procfs 扫描中收集信息。放置在文件系统选定部分的 Inotify 观察程序会触发这些扫描以捕获短暂的进程。

## [入门](https://github.com/DominicBreuker/pspy#getting-started)

### [下载](https://github.com/DominicBreuker/pspy#download)

将该工具安装到您要检查的 Linux 计算机上。首先获取二进制文件。在此处下载已发布的二进制文件：

- 32位大静态版本：`pspy32` [下载](https://github.com/DominicBreuker/pspy/releases/download/v1.2.1/pspy32)
- 64 位大静态版本：`pspy64` [下载](https://github.com/DominicBreuker/pspy/releases/download/v1.2.1/pspy64)
- 32位小版本：`pspy32s` [下载](https://github.com/DominicBreuker/pspy/releases/download/v1.2.1/pspy32s)
- 64位小版本：`pspy64s` [下载](https://github.com/DominicBreuker/pspy/releases/download/v1.2.1/pspy64s)

静态编译的文件应该可以在任何 Linux 系统上运行，但相当大（~4MB）。如果大小是一个问题，请尝试依赖于 libc 并使用 UPX 压缩的较小版本（~1MB）。

### [建造](https://github.com/DominicBreuker/pspy#build)

使用系统上安装的 Go 或运行基于 Docker 的构建过程来创建版本。对于后者，请确保安装了 Docker，然后运行`make build-build-image`以构建 Docker 映像，然后用`make build`它构建二进制文件。

您可以跑步`pspy --help`来了解旗帜及其含义。总结如下：

- -p：启用将命令打印到标准输出（默认启用）
- -f：启用将文件系统事件打印到标准输出（默认情况下禁用）
- -r：使用 Inotify 监视的目录列表。pspy 将递归地监视所有子目录（默认情况下，监视 /usr、/tmp、/etc、/home、/var 和 /opt）。
- -d：使用 Inotify 监视的目录列表。pspy 将仅监视这些目录，而不是子目录（默认为空）。
- -i：procfs 扫描之间的时间间隔（以毫秒为单位）。pspy 会定期扫描新进程，无论 Inotify 事件如何，以防万一未收到某些事件。
- -c：以不同颜色打印命令。文件系统事件不再着色，命令根据进程 UID 具有不同的颜色。
- --debug：打印详细的错误消息，否则这些消息将被隐藏。

默认设置应该适合大多数应用程序。观察内部文件`/usr`是最重要的，因为许多工具将访问其中的库。

一些更复杂的例子：

```
# print both commands and file system events and scan procfs every 1000 ms (=1sec)
./pspy64 -pf -i 1000 

# place watchers recursively in two directories and non-recursively into a third
./pspy64 -r /path/to/first/recursive/dir -r /path/to/second/recursive/dir -d /path/to/the/non-recursive/dir

# disable printing discovered commands but enable file system events
./pspy64 -p=false -f
```



### [例子](https://github.com/DominicBreuker/pspy#examples)

### [Cron 作业观看](https://github.com/DominicBreuker/pspy#cron-job-watching)

要查看该工具的运行情况，只需克隆存储库并运行`make example`（需要 Docker）。众所周知，将密码作为命令行参数传递是不安全的，可以使用示例来演示它。该命令启动一个 Debian 容器，其中由 root 运行的秘密 cron 作业每分钟更改一次用户密码。pspy 以用户 myuser 的身份在前台运行，并扫描进程。您应该看到与此类似的输出：

```
~/pspy (master) $ make example
[...]
docker run -it --rm local/pspy-example:latest
[+] cron started
[+] Running as user uid=1000(myuser) gid=1000(myuser) groups=1000(myuser),27(sudo)
[+] Starting pspy now...
Watching recursively    : [/usr /tmp /etc /home /var /opt] (6)
Watching non-recursively: [] (0)
Printing: processes=true file-system events=false
2018/02/18 21:00:03 Inotify watcher limit: 524288 (/proc/sys/fs/inotify/max_user_watches)
2018/02/18 21:00:03 Inotify watchers set up: Watching 1030 directories - watching now
2018/02/18 21:00:03 CMD: UID=0    PID=9      | cron -f
2018/02/18 21:00:03 CMD: UID=0    PID=7      | sudo cron -f
2018/02/18 21:00:03 CMD: UID=1000 PID=14     | pspy
2018/02/18 21:00:03 CMD: UID=1000 PID=1      | /bin/bash /entrypoint.sh
2018/02/18 21:01:01 CMD: UID=0    PID=20     | CRON -f
2018/02/18 21:01:01 CMD: UID=0    PID=21     | CRON -f
2018/02/18 21:01:01 CMD: UID=0    PID=22     | python3 /root/scripts/password_reset.py
2018/02/18 21:01:01 CMD: UID=0    PID=25     |
2018/02/18 21:01:01 CMD: UID=???  PID=24     | ???
2018/02/18 21:01:01 CMD: UID=0    PID=23     | /bin/sh -c /bin/echo -e "KI5PZQ2ZPWQXJKEL\nKI5PZQ2ZPWQXJKEL" | passwd myuser
2018/02/18 21:01:01 CMD: UID=0    PID=26     | /usr/sbin/sendmail -i -FCronDaemon -B8BITMIME -oem root
2018/02/18 21:01:01 CMD: UID=101  PID=27     |
2018/02/18 21:01:01 CMD: UID=8    PID=28     | /usr/sbin/exim4 -Mc 1enW4z-00000Q-Mk
```



首先，pspy 打印所有当前正在运行的进程，每个进程都有 PID、UID 和命令行。当 pspy 检测到新进程时，它会在此日志中添加一行。在此示例中，您发现一个 PID 23 的进程似乎更改了 myuser 的密码。这是 root private crontab 中使用的 Python 脚本的结果`/var/spool/cron/crontabs/root`，该脚本执行此 shell 命令（检查[crontab](https://github.com/DominicBreuker/pspy/blob/master/docker/var/spool/cron/crontabs/root)和[script](https://github.com/DominicBreuker/pspy/blob/master/docker/root/scripts/password_reset.py)）。请注意，myuser 既看不到 crontab，也看不到 Python 脚本。使用 pspy，它仍然可以看到命令。

### [来自 Hack The Box 的 CTF 示例](https://github.com/DominicBreuker/pspy#ctf-example-from-hack-the-box)

[下面是Hack The Box](https://www.hackthebox.eu/)中的怪物史莱克机器的示例。在本次 CTF 挑战中，任务是利用隐藏的 cron 作业来更改文件夹中所有文件的所有权。该漏洞是通配符与 chmod 的不安全使用（感兴趣的读者可以了解[详细信息）。](https://www.defensecode.com/public/DefenseCode_Unix_WildCards_Gone_Wild.txt)找到并利用它需要大量的猜测。不过，使用 pspy，很容易找到并分析 cron 作业：

[![动画演示 gif](https://github.com/DominicBreuker/pspy/raw/master/images/demo.gif)](https://github.com/DominicBreuker/pspy/blob/master/images/demo.gif)

## [怎么运行的](https://github.com/DominicBreuker/pspy#how-it-works)

存在一些工具可以列出 Linux 系统上执行的所有进程，包括那些已完成的进程。例如有[forkstat](http://smackerelofopinion.blogspot.de/2014/03/forkstat-new-tool-to-trace-process.html)。它从内核接收有关进程相关事件（例如 fork 和 exec）的通知。

这些工具需要 root 权限，但这不应给您带来错误的安全感。没有什么可以阻止您窥探 Linux 系统上运行的进程。只要进程正在运行，procfs 中的大量信息都是可见的。唯一的问题是您必须在生命周期很短的时间内捕获短暂的进程。在无限循环中扫描`/proc`目录中的新 PID 可以达到目的，但会消耗大量 CPU。

一种更隐蔽的方法是使用以下技巧。进程倾向于访问文件，例如 中的库`/usr`、临时文件`/tmp`、日志文件等`/var`。使用[inotify](http://man7.org/linux/man-pages/man7/inotify.7.html) API，您可以在创建、修改、删除、访问这些文件时收到通知。Linux 不需要特权用户对于此 API，因为许多无辜的应用程序都需要它（例如向您显示最新文件资源管理器的文本编辑器）。因此，虽然非 root 用户无法直接监视进程，但他们可以监视进程对文件系统的影响。

我们可以使用文件系统事件作为扫描的触发器`/proc`，希望我们能够足够快地捕获进程。这就是 pspy 的作用。无法保证您不会错过任何一个，但在我的实验中，机会似乎很大。一般来说，进程运行的时间越长，捕获它们的机会就越大。

# [杂项](https://github.com/DominicBreuker/pspy#misc)

徽标：“作者：Creative Tail [CC BY 4.0 ( http://creativecommons.org/licenses/by/4.0 )]，来自 Wikimedia Commons”（[链接](https://commons.wikimedia.org/wiki/File%3ACreative-Tail-People-spy.svg)）
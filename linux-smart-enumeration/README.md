首先，一些有用的单行文字；）

```
wget "https://github.com/diego-treitos/linux-smart-enumeration/releases/latest/download/lse.sh" -O lse.sh;chmod 700 lse.sh
```

```
curl "https://github.com/diego-treitos/linux-smart-enumeration/releases/latest/download/lse.sh" -Lo lse.sh;chmod 700 lse.sh
```

请注意，从版本开始，`2.10`您可以*使用该标志将脚本提供*给其他主机`-S`！

# linux 智能枚举

用于渗透测试和 CTF 的 Linux 枚举工具

该项目的灵感来自https://github.com/rebootuser/LinEnum并使用了它的许多测试。

与 LinEnum 不同，`lse`它尝试从隐私的角度根据信息的重要性逐步公开信息。

## 它是什么？

该shell脚本将显示本地Linux系统安全的相关信息，有助于提权。

从版本**2.0**开始，它*主要兼容* **POSIX**并使用`shellcheck`和进行测试`posh`。

它还可以**监视进程以发现重复的程序执行**。它在执行所有其他测试时进行监控，以便您节省一些时间。默认情况下，它会监视 1 分钟，但您可以通过参数选择监视时间`-p`。

它有 3 个详细级别，因此您可以控制看到的信息量。

在默认级别，您应该看到系统中非常重要的安全缺陷。级别`1`( `./lse.sh -l1`) 显示有趣的信息，可以帮助您了解隐私。级别`2`( `./lse.sh -l2`) 将仅转储它收集的有关系统的所有信息。

默认情况下，它会问你一些问题：主要是当前用户密码（如果你知道的话；），这样它就可以做一些额外的测试。

## 如何使用它？

这个想法是逐渐获取信息。

首先你应该像执行它一样`./lse.sh`。如果你看到一些绿色`yes!`，你可能已经有了一些可以使用的好东西。

如果没有，您应该尝试`level 1`使用详细信息`./lse.sh -l1`，您会看到更多有趣的信息。

如果这没有帮助，`level 2`将使用 转储您可以收集到的有关该服务的所有内容`./lse.sh -l2`。在这种情况下，您可能会发现使用`./lse.sh -l2 | less -r`.

您还可以通过传递参数来选择要执行的测试`-s`。使用它您可以选择要执行的特定测试或部分。例如，`./lse.sh -l2 -s usr010,net,pro`将执行测试以及和`usr010`部分中的所有测试。`net``pro`

```
Use: ./lse.sh [options]

 OPTIONS
  -c           Disable color
  -i           Non interactive mode
  -h           This help
  -l LEVEL     Output verbosity level
                 0: Show highly important results. (default)
                 1: Show interesting results.
                 2: Show all gathered information.
  -s SELECTION Comma separated list of sections or tests to run. Available
               sections:
                 usr: User related tests.
                 sud: Sudo related tests.
                 fst: File system related tests.
                 sys: System related tests.
                 sec: Security measures related tests.
                 ret: Recurren tasks (cron, timers) related tests.
                 net: Network related tests.
                 srv: Services related tests.
                 pro: Processes related tests.
                 sof: Software related tests.
                 ctn: Container (docker, lxc) related tests.
                 cve: CVE related tests.
               Specific tests can be used with their IDs (i.e.: usr020,sud)
  -e PATHS     Comma separated list of paths to exclude. This allows you
               to do faster scans at the cost of completeness
  -p SECONDS   Time that the process monitor will spend watching for
               processes. A value of 0 will disable any watch (default: 60)
  -S           Serve the lse.sh script in this host so it can be retrieved
               from a remote host.
```

## 漂亮吗？

### 使用演示

也可在[webm 视频中找到](https://raw.githubusercontent.com/diego-treitos/linux-smart-enumeration/master/screenshots/lse.webm)

[![伦敦证券交易所演示](https://github.com/diego-treitos/linux-smart-enumeration/raw/master/screenshots/lse.gif)](https://github.com/diego-treitos/linux-smart-enumeration/raw/master/screenshots/lse.gif)

### 0级（默认）输出样本

[![伦敦证券交易所0级](https://raw.githubusercontent.com/diego-treitos/linux-smart-enumeration/master/screenshots/lse_level0.png)](https://raw.githubusercontent.com/diego-treitos/linux-smart-enumeration/master/screenshots/lse_level0.png)

### 1 级详细输出示例

[![伦敦证券交易所1级](https://raw.githubusercontent.com/diego-treitos/linux-smart-enumeration/master/screenshots/lse_level1.png)](https://raw.githubusercontent.com/diego-treitos/linux-smart-enumeration/master/screenshots/lse_level1.png)

### 2 级详细输出示例

[![伦敦证券交易所二级](https://raw.githubusercontent.com/diego-treitos/linux-smart-enumeration/master/screenshots/lse_level2.png)](https://raw.githubusercontent.com/diego-treitos/linux-smart-enumeration/master/screenshots/lse_level2.png)

## 例子

直接执行单线

```
bash <(wget -q -O - "https://github.com/diego-treitos/linux-smart-enumeration/releases/latest/download/lse.sh") -l2 -i
```

```
bash <(curl -s "https://github.com/diego-treitos/linux-smart-enumeration/releases/latest/download/lse.sh") -l1 -i
```

## 给我买瓶啤酒

如果这个脚本有用，请随时给我买瓶啤酒`:)`

**₿**：`1DNBZRAzP6WVnTeBPoYvnDtjxnS1S8Gnxk`

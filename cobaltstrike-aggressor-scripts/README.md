# Cobalt Strike Aggressor 脚本



## 介绍

这是我担任 Locked Shields 2021 红队成员期间开发和测试的 Cobalt Strike Aggressor 脚本集合。



## 初始访问

[初始访问](https://attack.mitre.org/tactics/TA0001/)包括使用各种进入向量在网络内获得初始立足点的技术。

- `initial-access-cmd/initial-access-cmd.cna`：
  - **Certutil Web Delivery（自定义）**：提供 CMD 单行命令，通过 Certutil 交付自定义可执行文件
  - **Certutil Web Delivery（无阶段）**：提供 CMD 单行命令，通过 Certutil 传递无阶段 Cobalt Strike 有效载荷
  - **Bitsadmin Web Delivery（无阶段）**：提供 CMD 单行命令，通过 Bitsadmin 传递无阶段 Cobalt Strike 有效载荷
  - **Regsvr32 Web 交付（无阶段）**：提供 CMD 单行命令，通过 Regsvr32 交付无阶段 Cobalt Strike 有效载荷
  - **MSHTA Web 交付（无阶段）**：提供 CMD 单行命令，通过 MSHTA 交付无阶段 Cobalt Strike 有效载荷
  - **Rundll32 Web Delivery（无阶段）**：提供 CMD 单行命令，通过 Rundll32 传递无阶段 Cobalt Strike 有效载荷
- `initial-access-powershell/initial-access-powershell.cna`：
  - **纯 Powershell Web 交付（无阶段）**：提供 PowerShell 单行代码来（在内存中）传递无阶段的 Cobalt Strike PoweShell 有效载荷
  - **Artifact Powershell Web Delivery（无阶段）**：提供 PowerShell 单行程序来传递（内存中）嵌入无阶段 Cobalt Strike 有效载荷的 PowerShell 脚本
- `initial-access-python/initial-access-python.cna`：
  - **Python 2 Web 交付**：提供 Python 2 单行代码来传递无阶段的 Cobalt Strike 有效载荷（它假定 Python 2 的路径如下：*c:\Python27\pythonw.exe*）
  - **Python 3 Web Delivery**：提供 Python 3.9 单行代码来传递无阶段 Cobalt Strike 有效载荷（它假定 Python 3.9 的路径如下：*C:\Python39\pythonw.exe*）



## 持久性

[持久性](https://attack.mitre.org/tactics/TA0003/)包括攻击者用来在系统重启、更改凭据和其他可能切断其访问的中断情况下保持对系统的访问的技术。

- ```
  persistence-sharpersist/persistence-sharpersist.cna
  ```

  ：

  - *** 启动文件夹（上传可执行文件）[重新启动]**：通过将可执行文件上传到启动文件夹来为所有用户安装持久性[需要管理员权限]
  - **启动文件夹（上传可执行文件）[重新启动]**：通过将可执行文件上传到启动文件夹来为当前用户安装持久性
  - *** Windows 服务（Powershell 命令）[重启]**：通过创建启动 PowerShell 命令的 Windows 服务为所有用户安装持久性 [需要管理员权限]
  - *** Windows 服务（上传可执行文件）[重启]**：通过上传可执行文件并创建启动它的 Windows 服务来为所有用户安装持久性 [需要管理员权限]
  - *** 计划任务（Powershell 命令）[登录/每小时]**：通过创建启动 PowerShell 命令的计划任务为所有用户安装持久性 [需要管理员权限]
  - *** 计划任务（上传可执行文件）[登录/每小时]**：通过上传可执行文件并创建启动它的计划任务来为所有用户安装持久性[需要管理员权限]
  - **计划任务（Powershell 命令）[登录/每小时]**：通过创建启动 PowerShell 命令的计划任务来为当前用户安装持久性
  - **计划任务（上传可执行文件）[登录/每小时]**：通过上传可执行文件并创建启动它的计划任务来为当前用户安装持久性
  - *** 注册表（Powershell 命令）[登录]**：通过向自动运行注册表项添加 PowerShell 命令来为所有用户安装持久性 [需要管理员权限]
  - *** 注册表（上传可执行文件）[登录]**：通过上传可执行文件并将其添加到自动运行注册表项来为所有用户安装持久性[需要管理员权限]
  - **注册表（Powershell 命令）[登录]**：通过向自动运行注册表项添加 PowerShell 命令来为当前用户安装持久性 [需要管理员权限]
  - **注册表（上传可执行文件）[登录]**：通过上传可执行文件并将其添加到自动运行注册表项来为当前用户安装持久性
  - *** 粘滞键 (CMD)**：在执行粘滞键或其他辅助工具（例如，讲述人、放大镜）时启动 CMD 提示
  - *** 粘滞键（信标）**：当粘滞键或其他辅助工具（例如，讲述人、放大镜）执行时，启动 Cobalt Strike 信标



## 防御规避

[防御规避](https://attack.mitre.org/tactics/TA0005/)是指攻击者在攻击过程中用来规避检测的技术。用于规避防御的技术包括卸载/禁用安全软件，或混淆/加密数据和脚本。

- `evasion-disable-defender/evasion-disable-defender.cna`：
  - *** 禁用 AV/防火墙**：禁用 Windows Defender [需要管理员权限]
  - *** 添加排除（自动）**：自动将路径和可执行文件列表添加到 Windows Defender 排除项 [需要管理员权限]
  - *** 添加排除项（自定义）**：向 Windows Defender 排除项添加自定义路径和可执行文件 [需要管理员权限]
  - *** 添加排除项（扩展）**：向 Windows Defender 排除项添加自定义文件扩展名 [需要管理员权限]
  - *** 删除定义**：删除 Windows Defender 定义 [需要管理员权限]
- `evasion-disable-edr/evasion-disable-edr.cna`
  - *** 杀死 EDR**：尝试自动杀死所有 EDR/AV [需要管理员权限]
  - *** 终止 EDR（自定义）**：尝试终止自定义 EDR/AV [需要管理员权限]
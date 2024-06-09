# 索伦之眼



SauronEye 是一款搜索工具，旨在帮助红队查找包含特定关键字的文件。

**特征**：

- 搜索多个（网络）驱动器
- 搜索文件内容
- 搜索 Microsoft Office 文件的内容 ( `.doc`, `.docx`, `.xls`, `.xlsx`)
- `.xls`在旧的 2003和`.doc`文件中查找 VBA 宏
- 多线程搜索多个驱动器以提高性能
- 支持搜索关键字的正则表达式
- 与 Cobalt Strike 兼容`execute-assembly`

速度也相当快，不到一分钟就可以处理 50k 个文件，总计 1.3 TB 的网络驱动器（使用实际文件过滤器）。搜索`C:\`（在廉价的 SATA SSD 上）大约需要 15 秒。

### 使用示例



```
C:\>SauronEye.exe -d C:\Users\vincent\Desktop\ --filetypes .txt .doc .docx .xls --contents --keywords password pass* -v`

         === SauronEye ===

Directories to search: C:\Users\vincent\Desktop\
For file types: .txt, .doc, .docx, .xls
Containing: wacht, pass
Search contents: True
Search Office 2003 files for VBA: True
Max file size: 1000 KB
Search Program Files directories: False
Searching in parallel: C:\Users\vincent\Desktop\
[+] C:\Users\vincent\Desktop\test\wachtwoord - Copy (2).txt
[+] C:\Users\vincent\Desktop\test\wachtwoord - Copy (3).txt
[+] C:\Users\vincent\Desktop\test\wachtwoord - Copy.txt
[+] C:\Users\vincent\Desktop\test\wachtwoord.txt
[+] C:\Users\vincent\Desktop\pass.txt
[*] Done searching file system, now searching contents
[+] C:\Users\vincent\Desktop\pass.txt
         ...the admin password=admin123...

[+] C:\Users\vincent\Desktop\test.docx:
         ...this is a testPassword = "welkom12...


 Done. Time elapsed = 00:00:01.6656911
```



搜索多个目录，包括网络驱动器：

```
SauronEye.exe --directories C:\ \\SOMENETWORKDRIVE\C$ --filetypes .txt .bat .docx .conf --contents --keywords password pass*
```

包含空间的搜索路径和共享：

```
SauronEye.exe -d "C:\Users\user\Path with a space" -d "\\SOME NETWORK DRIVE\C$" --filetypes .txt --keywords password pass*
C:\>SauronEye.exe --help

         === SauronEye ===

Usage: SauronEye.exe [OPTIONS]+ argument
Search directories for files containing specific keywords.

Options:
  -d, --directories=VALUE    Directories to search
  -f, --filetypes=VALUE      Filetypes to search for/in
  -k, --keywords=VALUE       Keywords to search for
  -c, --contents             Search file contents
  -m, --maxfilesize=VALUE    Max file size to search contents in, in kilobytes
  -b, --beforedate=VALUE     Filter files last modified before this date,
                                format: yyyy-MM-dd
  -a, --afterdate=VALUE      Filter files last modified after this date,
                                format: yyyy-MM-dd
  -s, --systemdirs           Search in filesystem directories %APPDATA% and %
                               WINDOWS%
  -v, --vbamacrocheck        Check if 2003 Office files (*.doc and *.xls)
                               contain a VBA macro
  -h, --help                 Show help
```



### 笔记



SauronEye 不搜索`%WINDIR%`和`%APPDATA%`。使用`--systemdirs`标志搜索 的内容`Program Files*`。SauronEye 依赖于 .NET 4.7.2 才可用的功能，因此需要 >= .NET 4.7.2 才能运行。
# username-anarchy



- 版本：0.5（2016 年 10 月）| 我修改了里面的一个变量使用，将所有的 `File.exists?` 替换为 `File.exist?`了。
- 作者：urbanadventurer（安德鲁·霍顿）
- 主页：http://www.morningstarsecurity.com/research/username-anarchy
- 来源：https://github.com/urbanadventurer/username-anarchy/

## 描述



渗透测试时生成用户名的工具。*用户名是密码暴力破解问题的一半。*

当用户名基于用户名时，这对于用户帐户/密码暴力猜测和用户名枚举非常有用。通过在大量用户帐户中尝试一些弱密码，可以避免用户帐户锁定阈值。

可以通过多种方法识别用户名：

- 从 LinkedIn、Facebook 和其他社交网络中抓取员工姓名。
- 从 PDF、Word、Excel 等文档类型中提取元数据。这可以使用 FOCA 来执行。

还包括来自论坛的常见别名或自行选择的用户名。

## 特征



- 用户名格式的插件架构
- 格式字符串样式用户名格式定义
- 替补。例如，当仅知道名字首字母和姓氏时（LinkedIn 会像这样列出用户），它将尝试所有可能的名字
- 来自 Familypedia 和 PublicProfiler 的常见名字和姓氏的国家数据库
- 拥有 Facebook 通用名字和姓氏列表

## 附加功能



- 常见论坛用户名，按受欢迎程度排序

## 用法



用户名 Anarchy 是一个命令行工具。

```
	 ___ ____                                                        
	|   |    \ ______  ____ _______   ____  _____     __ __    ____  
	|   :    //  ___/_/    \\_  __ \ /    \ \__  \   /  :  \ _/    \
	'   .   / \___ \ \   o_/ |  | \/|   :  \ /  o \ |  . .  \\   o_/ 
	 \_____/ /______) \_____)|__|   |___:  /(______)|__: :  / \_____)
	       _____                         \/       .__     \/      
	      /     \    ____  _____  _______   ____  |  |__  ___.__.   
	     /   o   \  /    \ \__  \ \_  __ \_/ ___\ |  |  \(   :  |   
	    /    .    \|   .  \ /  o \ |  | \/\  \___ |   .  \\___  |   
	    \____:__  /|___:__/(______)|__|    \_____)|___:__//_____|   
	            \/                                                  
	Usage: ./username-anarchy [OPTIONS]... [firstname|first last|first middle last]
	Author: Andrew Horton (urbanadventurer). Version: 0.5

	Names:
	 -i, --input-file FILE     Input list of names. Can be SPACE, CSV or TAB delimited.
	                           Defaults to firstname, lastname. Valid column headings are:
	                           firstinitial, firstname, lastinitial, lastname,
	                           middleinitial, middlename.
	 -a, --auto                Automatically generate names from a country/list
	 -c, --country COUNTRY     COUNTRY can be one of the following datasets:
	                           PublicProfiler:
	                           argentina, austria, belgium, canada, china,
	                           denmark, france, germany, hungary, india, ireland,
	                           italy, luxembourg, netherlands, newzealand, norway,
	                           poland, serbia, slovenia, spain, sweden,
	                           switzerland, uk, us
	                           Other:
	                           Facebook - uses the Facebook top 10,000 names
	     --given-names FILE    Dictionary of given names
	     --family-names FILE   Dictionary of family names
	 -s, --substitute STATE    Control name substitutions
	                           Valid values are 'on' and 'off'. Default: off
	                           Can substitute any part of a name not available
	 -m, --max-sub NUM         Limit quantity of substitutions per plugin.
	                           Default: -1 (Unlimited)

	Username format:
	 -l, --list-formats        List format plugins
	 -f, --select-format LIST  Select format plugins by name. Comma delimited list
	 -r, --recognise USERNAME  Recognise which format is in use for a username.
	                           This uses the Facebook dataset. Use verbose mode to
	                           show progress.
	 -F, --format FORMAT       Define the user format using either format string or
	                           ABK format. See README.md for format details.

	Output:
	 -@, --suffix BOOL         Suffix. e.g. @example.com
	                           Default: None
	 -C BOOL,                  Case insensitive usernames.
	     --case-insensitive    Default: True (All lower case)

	Miscellaneous:
	 -v, --verbose             Display plugin format comments in output and displays
	                           last name searches in plugin format recogniser
	 -h, --help
```



## 用法示例



### 您知道用户名，但不知道用户名格式



```
./username-anarchy anna key
anna
annakey
anna.key
annakey
annak
a.key
akey
kanna
k.anna
...
```



### 您知道用户名格式和用户名称



```
./username-anarchy --input-file ./test-names.txt  --select-format first.last
andrew.horton
jim.vongrippenvud
peter.otoole
```



### 你知道服务器在法国



请注意，当您未指定任何输入名称时，需要 -a 或 --auto。

```
./username-anarchy --country france --auto
martin
bernard
thomas
durand
richard
robert
petit
moreau
dubois
simon
martinsmith
martinjohnson
...
```



### 列出用户名格式插件



```
./username-anarchy --list-formats
Plugin name         	Example
--------------------------------------------------------------------------------
first               	anna
firstlast           	annakey
first.last          	anna.key
firstlast[8]        	annakey
firstl              	annak
f.last              	a.key
flast               	akey
lfirst              	kanna
l.first             	k.anna
lastf               	keya
last                	key
last.f              	key.a
last.first          	key.anna
FLast               	AKey
first1              	anna0,anna1,anna2
fl                  	ak
fmlast              	abkey
firstmiddlelast     	annaboomkey
fml                 	abk
FL                  	AK
FirstLast           	AnnaKey
First.Last          	Anna.Key
Last                	Key
FML                 	ABK
```



### 自动识别使用的用户名格式



```
./username-anarchy --recognise j.smith
Recognising j.smith. This can take a while.
Username format j.smith recognised. Plugin name: f.last
```



## 输入文件



要为多个用户帐户生成用户名，您必须在文本文件中提供名称。这可以是 TAB 或 CSV 分隔的。

### 实施例1



```
Firstname,Lastname
Andrew,Horton
Jim, von Grippenvud
Peter,O'Toole
```



### 实施例2



LinkedIn 经常显示名字和姓氏首字母

```
firstname,lastinitial
andrew,h
foo,b
```



### 实施例3



混合名称集

```
firstname,firstinitial,middleinitial,lastname,lastinitial
andrew,,,horton,
jim,,,,v
,p,,o'toole,
```



## 自定义插件



### 命令行插件



使用 ABK 或格式字符串格式定义自定义插件格式。使用 -F 或 --format 指定用户名格式

#### 实施例1



```
./username-anarchy -F "v-annakey" andrew horton
v-andrewhorton
```



#### 实施例2



```
./username-anarchy -F "v-%f%l" -a -C poland
v-nowaksmith
v-nowakjohnson
v-nowakjones
v-nowakwilliams
v-nowakbrown
v-nowaklee
v-nowakkhan
v-nowaksingh
v-nowakkumar
v-nowakmiller
...
```



### 编写插件



您可以通过在 format-plugins.rb 中定义插件来将插件添加到用户名无政府状态

此示例使用 ABK 格式。

```
Plugin.define "last.first" do
	def generate(n)
		n.format_anna("key.anna")
	end
end
```



此示例使用格式字符串格式。

```
Plugin.define "first" do
	def generate(n)
		n.format("%f")
	end
end
```



### 格式化字符串



Username Anarchy 提供了一种使用格式字符串定义用户名格式的方法。

- %F - 名字
- %M - 中间名
- %L - 姓氏
- %f - 名字
- %m - 中间名
- %l - 姓氏
- %if - 第一个首字母
- %im - 中间名首字母
- %il - 最后一个首字母
- %iF - 第一个首字母
- %iM - 中间名首字母
- %iL - 最后一个首字母
- %D - 数字范围 0..9
- %DD - 数字范围 00..99

### ABK格式



Username Anarchy 提供了一种使用 ABK 格式定义用户名格式的方法，ABK 格式可转换为格式字符串。

- 安娜 - %F
- 繁荣 - %M
- 关键 - %L
- 安娜-%f
- 繁荣 - %m
- 关键 - %l
- A-%iF
- B-%iM
- K-%iL
- 一个 - %如果
- b - %im
- k - %il

## 论坛用户名



论坛名称文件夹包含：

- common-forum-names.csv - 包含论坛名称及其出现频率的 CSV 文件
- common-forum-names-top10k.txt - 前 10,000 个论坛名称
- common-forum-names.txt - 1,774,313 个论坛名称
- phpbb-scraper.rb - PHPbb 论坛上用户名的网络抓取工具

## 名称资源



### 名称



- http://worldnames.publicprofiler.org/SearchArea.aspx一些常见的国家/地区。排名前 10 位的姓氏和名字
- https://secure.wikimedia.org/wikipedia/en/wiki/List_of_most_popular_given_names
- http://www.babynamefacts.com/popularnames/countries.php?country=NZD每个国家/地区前 100 个婴儿名字
- https://secure.wikimedia.org/wikipedia/en/wiki/List_of_most_common_surnames_in_Oceania

### 名称解析：



- https://secure.wikimedia.org/wikipedia/en/wiki/Capitalization
- http://cpansearch.perl.org/src/KIMRYAN/Lingua-EN-NameParse-1.28/lib/Lingua/EN/NameParse.pm
- http://search.cpan.org/~summer/Lingua-EN-NameCase/NameCase.pm

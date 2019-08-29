# TinyUrl-Service
短网址系统就是把一个长网址转成短网址的服务

### 1.场景和限制
 使用场景：提供短网址服务为公司其他各业务服务
 - 功能：一个长网址转成短网址并存储；根据短网址还原长 url
 - 要求短网址的后缀**不超过**7位(大小写字母和数字)
 - 估计峰值假设插入请求数量级：数百；查询请求数量级：数千
 
### 2.数据存储设计
  根据需求设计数据存储方式
- 使用Mysql即可满足
- 需要的字段有哪些？根据需求来看实际上只需要 ID、存储生成之后的短网址、原网址、创建时间这四个字段就可以满足需求。
-  Mysql 数据表
```
    id | token(索引) | url(原网址) | created_at
```
-  token:不存储整个短网址，希望前边的主机名可以随意的去替换
- 如何根据查询设计索引？只有一个需求就是根据短网址还原原网址，直接给token加上索引就可以。

### 3.算法实现设计
   短网址生成算法有哪些？对比优缺点选择适合业务的方法
- **两个 API：`long2short_url` 把长的url转换成短网址，`short2long_url` 根据短网址查询出长网址**
- **常用算法：hash 算法截取； 自增序列算法**
- **对比多钟算法，采取自增序列算法实现**

短网址生成算法：
  `CHARS=“abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789”`
   对每个长网址从字符集里面生成一个不超过7位长度的一个短网址token  

① md5摘要算法：接收任意长度的字节然后生成一个定长的字符，经常用在下载文件的时候会与md5校验值用来检查文件是不是修改了。
```
>>> import hashlib
>>> url = 'http://mirrors.163.com/.help/CentOS7-Base-163.repo'
>>> hashlib.md5(url.encode())              # 对url使用摘要算法得到的值
<md5 HASH object @ 0x000002BE328342D8>
>>> hashlib.md5(url.encode()).hexdigest()  # 转化成一个16进制串
'60dc55352afeb63b4d91a75c9c4ff287'
>>> len(hashlib.md5(url.encode()).hexdigest())
32                                         # 是一个定长的32位字符串
```
因为我们需要一个不超过7位的字符串而md5摘要算法是32位的。可能会想到截断只取前7个字符。但是有个问题可能**会有一定概率的冲突**。一旦有冲突就需要在插入时候去数据库检查一下是不是有冲突。实际上这样在高并发的插入场景下是特别不友好的。

② 把对应的每个ID给它生成一个不重复的短网址token。
- 字符集CHARS特点：从小a到小z，大A到大Z，0到9，一共26+26+10=62个。
- 一共七个位置每个位置有62种选项，62**7是一个非常大的数字，万亿规模的数字，对短网址token来说有万亿规模肯定就够用了
- **字符集类似于62进制的数字**。对于二进制数字来说它的可选项是0,1；十六进制 0-9 a-f 。
- 可以把自增ID十进制把它转换成字符集这种62进制的，十进制 -> 62进制，这样就实现十进制的ID跟六十二进制数字的一个映射。这里并不是严格的62进制的数字，不过从0到61每个位置上都有一个字符与之对应。
  
**现在就知道如何来解决这个问题了，就是根据自增的ID来去给每个长网址生成一个62进制的短网址。**
- 如何把十进制的ID转换成62进制的短网址？
    - 进制换换 10进制 ->2进制   不断取余，倒序输出
```
>>> bin(10)             # 将10进制转换成2进制
  '0b1010' 
>>> help(divmod)        # 查看divmod函数使用
Help on built-in function divmod in module builtins:
divmod(x, y, /)
    Return the tuple (x//y, x%y).  Invariant: div*y + mod == x.
>>> divmod(10, 2)       # 返回一个tuple，一个是整除的商，x对y取模求余数
(5, 0)
```
- 10进制转换成2进制函数实现
```
def mybin(num):       # 10进制 -> 2进制
     if num == 0:
        return 0
    res = []          # 保存2进制串的列表
    while num:
        num, rem = divmod(num, 2)
        res.append(str(rem))
    return ''.join(reversed(res))  # 倒序输出转换成字符串
    
print(mybin(10))     # 输出结果：1010
```
- 10进制到62进制串的转化（递增序列算法）
```
CHARS="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
def encode(num):
    if num == 0:
        return CHARS[0]
    res = []
    while num:
        num, rem = divmod(num, len(CHARS))
        res.append(CHARS[rem])
    return ''.join(reversed(res))

print(encode(62))  # 输出结果：ba
```
 自增 id 问题？**数据库只有在插入时候才会有自增ID，所以这里还需要一个全局计数器，用来生成自增ID**，这样就可以根据ID生成62进制串。使用` Redis incr`可以非常容易实现一个计数器。
 
###  4.生成短网址的过程

- request -> redis incr的值 index -> encode(index) -> save mysql
    - 如果一个请求(request)过来时候，先去Redis 拿到 incr 值比如叫index, 然后把index转换成index串。最后把得到的值存储到数据库里面。

### 5.短网址服务的编码实现
- 搭建环境
    - 首先需要你安装MySQL数据库，只安装服务器端就行，安装的时候可以选择。
    - 安装Redis 非关系型数据库
    - 接下来是一些需要的Python插件的安装：
```
# 安装flask
(python3) C:\Users\allar\system_design>pip install -i https://pypi.doubanio.com/simple/ --trusted-host pypi.doubanio.com flask

# 安装flask_mysqldb
(python3) C:\Users\allar\system_design>pip install flask_mysqldb

# 安装flask_redis
(python3) C:\Users\allar\system_design>pip install flask-redis

# 安装requests
(python3) C:\Users\allar\system_design>pip install requests
```
-  在数据库里面创建一个 short_url 表
```
CREATE TABLE short_url (
    id bigint unsigned NOT NULL AUTO_INCREMENT,
    token varchar(10),
    url varchar(2048),
    created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_token` (`token`)
);
```
- 使用 Flask 框架演示本系统实现
    - 代码里实现了短网址生成算法
    - 数据库使用 Mysql
    - 计数器使用 Redis


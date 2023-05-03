# opq-onebotV11
opq simple onebot adapter


用法 python ob.py

很轻，很清凉🍦

记得修改py文件，ws://127.0.0.1:20004 这一行，是opq要连接的onebotv11应用端

site = web.TCPSite(runner, "127.0.0.1", 30004)

30004是你的opq指定-wsserver ws://127.0.0.1:30004/ws地址

OPQBot.exe -port 8086 -token 你的opqtoken -wsserver ws://127.0.0.1:30004/ws

opq搭建指南

https://73s2swxb4k.apifox.cn/doc-2200981

暂时只针对早苗进行了测试，对其他ob11应用端还要再进行一些测试

(早苗的ob实现和标准略有不同，api多出了bot_qq字段，且没有echo)

(nb和koishi似乎都可以，请使用obV2.py）

(trss-yunzai需要实现array格式上报，请使用obv3.py)

接入早苗的指南，

1，首先部署好opq，到opq群(位于搭建指南)获得token，留意群内bot的私聊

2，修改ob.py 将 ws_url_b = "ws://127.0.0.1:20004" 改为早苗服务器地址(obv2可以改为本地的nonebot、koishi地址)

【公用sanae地址，ws://sanae.youngmoe.com:200xx】【xx替换成1-50】比如【ws://sanae.youngmoe.com:20005】

3，python ob.py 运行adapter，缺少依赖就pip安装 pip install 缺少的依赖名

4，OPQBot.exe -port 8086 -token 你的opqtoken -wsserver ws://127.0.0.1:30004/ws【ob里面默认是使用30004端口，这里对应】

5，群里发 早苗on。应该可以用早苗了🍉

https://www.yuque.com/km57bt/hlhnxg

早苗的文档地址↑

3个版本具体区别，

ob（string格式上报，接受string格式调用）

obv2（string格式上报，接收array格式调用）

obv3（array格式上报，接收array格式调用）

yunzai测试了，可以用，koishi也测了下，也能用

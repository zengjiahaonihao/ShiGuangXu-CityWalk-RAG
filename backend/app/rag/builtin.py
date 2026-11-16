"""内置人文库：随项目自带的全国名城古街文史档案 + 专题通识。

说明：
- CITY_PROFILES 用于首页陈列、知识库分区与路线生成的城市快选；
- image 对应 frontend/public 下的图片路径（带城市名的为专属图，region-* 为区域氛围图）；
- doc 对应内置人文库目录下的 Markdown 文件名；
- 所有配图均取自 Pexels 免费商用图库，为氛围示意，非对应街区实拍。
"""
from __future__ import annotations

import json

from .. import config

# 城市档案：用于首页陈列 / 知识库分区 / 路线生成
CITY_PROFILES: list[dict] = [
    # ---------------- 华东 ----------------
    {
        "id": "quanzhou", "city": "泉州", "district": "福建 · 鲤城", "region": "华东",
        "title": "西街 · 开元寺", "subtitle": "半城烟火半城仙",
        "summary": "1300 年的老街，红砖厝与南洋骑楼夹道；中段一座唐代佛寺，寺里两座宋代石塔是全城最高的地標。",
        "tags": ["海丝", "红砖厝", "燕尾脊", "宋元石塔", "骑楼"],
        "highlights": ["开元寺与东西塔", "西街红砖厝", "中山路骑楼", "府文庙", "蟳埔蚵壳厝"],
        "image": "/cities/quanzhou.webp",
        "doc": "泉州-西街与开元寺.md",
        "walk": "半日 · 约 3 公里",
        "credit": "Pexels 免费商用 · 氛围示意",
    },
    {
        "id": "fuzhou", "city": "福州", "district": "福建 · 鼓楼", "region": "华东",
        "title": "三坊七巷", "subtitle": "明清古建筑博物馆",
        "summary": "西晋末年成形的里坊街区，白墙瓦屋、曲线马鞍墙；走出上百位影响中国近现代史的人物。",
        "tags": ["里坊制", "马鞍墙", "名人故居", "水榭戏台"],
        "highlights": ["衣锦坊水榭戏台", "郎官巷严复故居", "杨桥巷林觉民·冰心故居", "光禄吟台"],
        "image": "/cities/fuzhou.webp",
        "doc": "福州-三坊七巷.md",
        "walk": "半日 · 约 2.5 公里",
        "credit": "Pexels 免费商用 · 氛围示意",
    },
    {
        "id": "suzhou", "city": "苏州", "district": "江苏 · 姑苏", "region": "华东",
        "title": "平江路", "subtitle": "一条平江路，半座姑苏城",
        "summary": "1606 米傍河小路，完整保存着南宋《平江图》里的水陆并行、河街相邻双棋盘格局。",
        "tags": ["双棋盘", "粉墙黛瓦", "昆曲评弹", "宋构石桥"],
        "highlights": ["平江河十七桥", "中张家巷昆曲评弹博物馆", "《平江图》碑亭", "耦园"],
        "image": "/cities/suzhou.webp",
        "doc": "苏州-平江路.md",
        "walk": "半日 · 约 2 公里",
        "credit": "Pexels 免费商用 · 氛围示意",
    },
    {
        "id": "shanghai", "city": "上海", "district": "上海 · 徐汇/黄浦", "region": "华东",
        "title": "武康路 · 石库门", "subtitle": "一条武康路，半部近代史",
        "summary": "1183 米的梧桐小马路上立着 30 余处名人旧居；弄堂深处的石库门，把江南天井锁进了红砖门框。",
        "tags": ["石库门", "弄堂", "Art Deco", "外滩万国建筑"],
        "highlights": ["武康大楼", "巴金故居", "新天地与张园", "外滩建筑群", "豫园与老城厢"],
        "image": "/cities/shanghai.webp",
        "doc": "上海-武康路与石库门.md",
        "walk": "一日 · 约 6 公里",
        "credit": "Pexels 免费商用 · 区域氛围示意",
    },
    {
        "id": "nanjing", "city": "南京", "district": "江苏 · 鼓楼/秦淮", "region": "华东",
        "title": "颐和路 · 老城南", "subtitle": "梧桐下的民国，城墙下的市井",
        "summary": "颐和路公馆区藏两百余处民国建筑与十余国使馆旧址；城南门东门西，还留着明代的手工业与秦淮灯会。",
        "tags": ["民国建筑", "明城墙", "秦淮灯会", "云锦"],
        "highlights": ["颐和路公馆区", "中华门瓮城与藏兵洞", "门东三条营", "甘熙宅第", "秦淮河"],
        "image": "/cities/nanjing.webp",
        "doc": "南京-颐和路与老城南.md",
        "walk": "一日 · 约 5 公里",
        "credit": "Pexels 免费商用 · 区域氛围示意",
    },
    {
        "id": "hangzhou", "city": "杭州", "district": "浙江 · 上城", "region": "华东",
        "title": "南宋御街 · 清河坊", "subtitle": "一条街叠着三个朝代",
        "summary": "中山中路地下叠压着南宋香糕砖、元明石板、清民青石三层路面；街侧的胡庆余堂挂着戒欺匾。",
        "tags": ["南宋御街", "西湖", "老字号", "中药文化"],
        "highlights": ["南宋御街遗址", "胡庆余堂中药博物馆", "河坊街与大井巷", "吴山城隍阁", "西湖十景"],
        "image": "/cities/hangzhou.webp",
        "doc": "杭州-南宋御街与清河坊.md",
        "walk": "半日 · 约 3 公里",
        "credit": "Pexels 免费商用 · 区域氛围示意",
    },
    {
        "id": "yangzhou", "city": "扬州", "district": "江苏 · 广陵", "region": "华东",
        "title": "东关街", "subtitle": "运河码头与盐商园林",
        "summary": "1122 米老街，一头拴着运河的码头，一头系着个园——四季假山用四堆石头把一年过完了。",
        "tags": ["大运河", "盐商", "个园四季假山", "淮扬菜"],
        "highlights": ["东关街与东门遗址", "个园", "汪氏小苑", "瘦西湖", "富春茶社"],
        "image": "/cities/yangzhou.webp",
        "doc": "扬州-东关街.md",
        "walk": "一日 · 约 4 公里",
        "credit": "Pexels 免费商用 · 区域氛围示意",
    },
    {
        "id": "shaoxing", "city": "绍兴", "district": "浙江 · 越城", "region": "华东",
        "title": "书圣故里 · 仓桥直街", "subtitle": "一座没有围墙的博物馆",
        "summary": "从戒珠寺的墨池到题扇桥，王羲之的足迹与鲁迅的三味书屋，都在同一片台门与河埠之间。",
        "tags": ["水乡", "台门", "八字桥", "黄酒"],
        "highlights": ["书圣故里与墨池", "题扇桥与躲婆弄", "仓桥直街", "八字桥", "鲁迅故里三味书屋"],
        "image": "/cities/shaoxing.webp",
        "doc": "绍兴-书圣故里与仓桥直街.md",
        "walk": "一日 · 约 4 公里",
        "credit": "Pexels 免费商用 · 区域氛围示意",
    },
    {
        "id": "huizhou", "city": "徽州", "district": "安徽 · 黄山", "region": "华东",
        "title": "屯溪老街 · 西递宏村", "subtitle": "粉墙黛瓦马头墙",
        "summary": "1273 米的屯溪老街是活着的明清街市；西递宏村以牛形水系与三雕，成为中国最早列入世遗的古村落。",
        "tags": ["徽派建筑", "马头墙", "天井四水归堂", "徽州三雕"],
        "highlights": ["屯溪老街", "西递胡文光牌坊", "宏村月沼与南湖", "承志堂", "水口园林"],
        "image": "/cities/huizhou.webp",
        "doc": "徽州-屯溪老街与西递宏村.md",
        "walk": "二日 · 约 8 公里",
        "credit": "Pexels 免费商用 · 区域氛围示意",
    },
    {
        "id": "jingdezhen", "city": "景德镇", "district": "江西 · 珠山", "region": "华东",
        "title": "御窑厂 · 三闾庙", "subtitle": "一座靠一门手艺活了千年",
        "summary": "洪武二年设御窑厂，五百余年间百选一二——不合格的官窑瓷一律打碎深埋，六百年后被挖了出来。",
        "tags": ["御窑厂", "青花", "七十二道工序", "高岭土"],
        "highlights": ["御窑厂遗址与掩埋坑", "御窑博物馆", "三闾庙古码头", "陶溪川", "陶瓷博物馆"],
        "image": "/cities/jingdezhen.webp",
        "doc": "景德镇-御窑厂与三闾庙.md",
        "walk": "一日 · 约 4 公里",
        "credit": "Pexels 免费商用 · 区域氛围示意",
    },
    {
        "id": "xiamen", "city": "厦门", "district": "福建 · 思明", "region": "华东",
        "title": "鼓浪屿", "subtitle": "1.88 平方公里的世界",
        "summary": "13 国领事馆与华侨别墅挤在一座小岛上，红砖与柱廊混搭出厦门装饰风格，2017 年列入世界遗产。",
        "tags": ["世界遗产", "华侨别墅", "Amoy Deco", "钢琴之岛"],
        "highlights": ["八卦楼与风琴博物馆", "菽庄花园与钢琴博物馆", "海天堂构", "日光岩", "协和礼拜堂"],
        "image": "/cities/xiamen.webp",
        "doc": "厦门-鼓浪屿.md",
        "walk": "一日 · 约 5 公里",
        "credit": "Pexels 免费商用 · 区域氛围示意",
    },
    # ---------------- 华南 ----------------
    {
        "id": "haikou", "city": "海口", "district": "海南 · 龙华", "region": "华南",
        "title": "骑楼老街", "subtitle": "南洋归侨盖的一座城",
        "summary": "4.4 公里骑楼长廊，巴洛克风洞墙下挂着中式砖雕；中国首批十大历史文化名街之一。",
        "tags": ["骑楼", "巴洛克女儿墙", "侨乡", "南洋风格"],
        "highlights": ["中山路骑楼群", "得胜沙路", "博爱路最早骑楼", "海口钟楼", "天后宫"],
        "image": "/cities/haikou.webp",
        "doc": "海口-骑楼老街.md",
        "walk": "半日 · 约 2 公里",
        "credit": "Pexels 免费商用 · 氛围示意",
    },
    {
        "id": "chaozhou", "city": "潮州", "district": "广东 · 湘桥", "region": "华南",
        "title": "牌坊街", "subtitle": "坊之多而知风化之美",
        "summary": "1948 米中轴线上 23 座石牌坊与南洋骑楼并肩而立，连接 51 条古街巷。",
        "tags": ["石牌坊", "骑楼", "工夫茶", "潮州木雕"],
        "highlights": ["状元坊", "四狮亭", "义兴甲民居街区", "广济桥", "己略黄公祠"],
        "image": "/cities/chaozhou.webp",
        "doc": "潮州-牌坊街.md",
        "walk": "半日 · 约 2.5 公里",
        "credit": "Pexels 免费商用 · 氛围示意",
    },
    {
        "id": "guangzhou", "city": "广州", "district": "广东 · 荔湾", "region": "华南",
        "title": "西关永庆坊 · 沙面", "subtitle": "趟栊门里的日子，榕树下的近代史",
        "summary": "西关大屋的三件头门、满洲窗与麻石街；沙面岛上 150 余座欧洲建筑，是中国的万国建筑群之一。",
        "tags": ["西关大屋", "趟栊门", "满洲窗", "沙面租界"],
        "highlights": ["陈家祠七绝装饰", "永庆坊与八和会馆", "恩宁路骑楼", "沙面建筑群", "十三行"],
        "image": "/cities/guangzhou.webp",
        "doc": "广州-西关永庆坊与沙面.md",
        "walk": "一日 · 约 5 公里",
        "credit": "Pexels 免费商用 · 区域氛围示意",
    },
    {
        "id": "macao", "city": "中国澳门", "district": "中国澳门特别行政区", "region": "华南",
        "title": "历史城区", "subtitle": "四百年的中西相遇",
        "summary": "25 幢历史建筑构成世界遗产：大三巴牌坊上刻着汉字箴言，议事亭前地铺着葡式碎石路。",
        "tags": ["世界遗产", "葡式碎石路", "中西合璧", "土生葡菜"],
        "highlights": ["大三巴牌坊", "妈阁庙", "议事亭前地", "郑家大屋", "岗顶剧院"],
        "image": "/cities/macao.webp",
        "doc": "中国澳门-历史城区.md",
        "walk": "一日 · 约 4 公里",
        "credit": "Pexels 免费商用 · 区域氛围示意",
    },
    # ---------------- 华中 ----------------
    {
        "id": "wuhan", "city": "武汉", "district": "湖北 · 武昌/江汉", "region": "华中",
        "title": "昙华林 · 汉口里分", "subtitle": "两江三镇，各有各的老",
        "summary": "昙华林一条街上教堂、佛寺、教会学堂并列；汉口的里分是武汉版的石库门，藏着近代中国的市井。",
        "tags": ["里分", "租界建筑", "江汉关", "过早"],
        "highlights": ["昙华林与文华书院", "江汉关大楼", "咸安坊与江汉村", "黎黄陂路", "黄鹤楼"],
        "image": "/cities/wuhan.webp",
        "doc": "武汉-昙华林与汉口里分.md",
        "walk": "一日 · 约 6 公里",
        "credit": "Pexels 免费商用 · 区域氛围示意",
    },
    {
        "id": "changsha", "city": "长沙", "district": "湖南 · 天心", "region": "华中",
        "title": "太平街", "subtitle": "长沙古城唯一的原版",
        "summary": "375 米主街加五条支巷，是长沙古城格局里唯一完整保存的鱼骨街巷；街内的贾谊故居是中国最老的名人故居之一。",
        "tags": ["鱼骨街巷", "贾谊故居", "湘剧", "火宫殿"],
        "highlights": ["贾谊故居与太傅井", "乾益升粮栈", "金线街与孚嘉巷", "岳麓书院", "火宫殿"],
        "image": "/cities/changsha.webp",
        "doc": "长沙-太平街.md",
        "walk": "半日 · 约 2.5 公里",
        "credit": "Pexels 免费商用 · 区域氛围示意",
    },
    {
        "id": "luoyang", "city": "洛阳", "district": "河南 · 老城/洛龙", "region": "华中",
        "title": "老城 · 丽景门 · 龙门", "subtitle": "十三朝古都，五都荟洛",
        "summary": "金元老城的十字街上飘着水席味；城南 13 公里，卢舍那大佛用一千三百年看你一眼。",
        "tags": ["十三朝古都", "隋唐洛阳城", "龙门石窟", "牡丹"],
        "highlights": ["龙门石窟奉先寺", "丽景门与老城十字街", "明堂天堂与应天门", "定鼎门遗址", "白马寺"],
        "image": "/cities/luoyang.webp",
        "doc": "洛阳-老城与龙门.md",
        "walk": "二日 · 约 8 公里",
        "credit": "Pexels 免费商用 · 区域氛围示意",
    },
    # ---------------- 华北 ----------------
    {
        "id": "pingyao", "city": "平遥", "district": "山西 · 晋中", "region": "华北",
        "title": "明清古城", "subtitle": "中国第一家票号的诞生地",
        "summary": "6.4 公里城墙围住一座龟城，四大街八小街七十二巷；日昇昌在此开创汇通天下。",
        "tags": ["世界遗产", "晋商", "票号", "城墙", "单坡房"],
        "highlights": ["日昇昌票号", "古城墙 72 敌楼", "南大街明清街", "县衙", "双林寺彩塑"],
        "image": "/cities/pingyao.webp",
        "doc": "平遥-明清古城.md",
        "walk": "一日 · 约 5 公里",
        "credit": "Pexels 免费商用 · 氛围示意",
    },
    {
        "id": "beijing", "city": "北京", "district": "北京 · 东城/西城", "region": "华北",
        "title": "胡同 · 中轴线", "subtitle": "7.8 公里的中国秩序",
        "summary": "永定门到钟鼓楼 7.8 公里的中轴线，2024 年列入世界遗产；两侧的胡同与四合院是它的毛细血管。",
        "tags": ["中轴线", "胡同", "四合院", "京剧"],
        "highlights": ["故宫与景山", "钟鼓楼", "南锣鼓巷鱼骨胡同", "什刹海与恭王府", "宣南会馆"],
        "image": "/cities/beijing.webp",
        "doc": "北京-胡同与中轴线.md",
        "walk": "一日 · 约 6 公里",
        "credit": "Pexels 免费商用 · 区域氛围示意",
    },
    {
        "id": "tianjin", "city": "天津", "district": "天津 · 和平", "region": "华北",
        "title": "五大道 · 意风区", "subtitle": "九国租界，九种风格",
        "summary": "五大道两千余栋小洋楼与意风区的马可波罗广场——一座城市同时有过九套建筑规范。",
        "tags": ["九国租界", "小洋楼", "意式建筑", "杨柳青年画"],
        "highlights": ["五大道与民园", "庆王府", "意风区马可波罗广场", "梁启超饮冰室", "古文化街天后宫"],
        "image": "/cities/tianjin.webp",
        "doc": "天津-五大道与意风区.md",
        "walk": "一日 · 约 5 公里",
        "credit": "Pexels 免费商用 · 区域氛围示意",
    },
    {
        "id": "datong", "city": "大同", "district": "山西 · 平城", "region": "华北",
        "title": "古城 · 云冈", "subtitle": "三代京华，两朝重镇",
        "summary": "北魏在此建都 97 年，把五位皇帝凿成了昙曜五窟的大佛；辽金的华严寺藏着海内孤品天宫壁藏。",
        "tags": ["北魏平城", "云冈石窟", "辽金木构", "边镇"],
        "highlights": ["云冈昙曜五窟", "华严寺薄伽教藏殿", "善化寺", "九龙壁", "悬空寺"],
        "image": "/cities/datong.webp",
        "doc": "大同-古城与云冈.md",
        "walk": "二日 · 约 7 公里",
        "credit": "Pexels 免费商用 · 区域氛围示意",
    },
    # ---------------- 西南 ----------------
    {
        "id": "chengdu", "city": "成都", "district": "四川 · 青羊", "region": "西南",
        "title": "宽窄巷子 · 少城", "subtitle": "一座城中的满城",
        "summary": "清代八旗驻防的少城留下鱼骨状长顺街；宽窄井三条巷子，是川西穿斗四合院最后的完整样本。",
        "tags": ["少城满城", "川西民居", "穿斗构架", "茶馆"],
        "highlights": ["宽巷子恺庐", "窄巷子与白夜", "井巷子砖墙", "人民公园鹤鸣茶社", "文殊院"],
        "image": "/cities/chengdu.webp",
        "doc": "成都-宽窄巷子与少城.md",
        "walk": "半日 · 约 3 公里",
        "credit": "Pexels 免费商用 · 区域氛围示意",
    },
    {
        "id": "chongqing", "city": "重庆", "district": "重庆 · 沙坪坝/渝中", "region": "西南",
        "title": "磁器口 · 十八梯", "subtitle": "房子骑在坡上，坡挂在江边",
        "summary": "山城的梯道、缆车与吊脚楼——嘉陵江边的千年码头，与连接上下半城的数百级石阶。",
        "tags": ["山地城市", "码头", "吊脚楼", "陪都"],
        "highlights": ["磁器口正街与宝轮寺", "十八梯", "白象街开埠老街", "湖广会馆", "洪崖洞"],
        "image": "/cities/chongqing.webp",
        "doc": "重庆-磁器口与十八梯.md",
        "walk": "一日 · 约 5 公里",
        "credit": "Pexels 免费商用 · 区域氛围示意",
    },
    {
        "id": "lijiang", "city": "丽江", "district": "云南 · 古城区", "region": "西南",
        "title": "丽江古城", "subtitle": "家家门前流水",
        "summary": "不筑城墙的世遗古城：玉龙雪山的水分三河穿城，三眼井把饮用、洗菜、洗衣排成了三级。",
        "tags": ["世界遗产", "纳西族", "三眼井", "东巴文"],
        "highlights": ["四方街", "木府", "三眼井与水圳", "大石桥", "白沙壁画"],
        "image": "/cities/lijiang.webp",
        "doc": "丽江-古城.md",
        "walk": "一日 · 约 4 公里",
        "credit": "Pexels 免费商用 · 区域氛围示意",
    },
    {
        "id": "lasa", "city": "拉萨", "district": "西藏 · 城关区", "region": "西南",
        "title": "八廓街", "subtitle": "先有寺，后有城",
        "summary": "一条转经道围成一座城：囊廓、八廓、林廓三重同心，顺时针走了一千三百年。",
        "tags": ["世界遗产", "转经道", "藏式碉房", "唐卡"],
        "highlights": ["大昭寺与唐蕃会盟碑", "布达拉宫", "八廓街转经", "罗布林卡", "哲蚌寺"],
        "image": "/cities/lasa.webp",
        "doc": "拉萨-八廓街.md",
        "walk": "一日 · 约 4 公里",
        "credit": "Pexels 免费商用 · 区域氛围示意",
    },
    # ---------------- 西北 ----------------
    {
        "id": "xian", "city": "西安", "district": "陕西 · 碑林/莲湖", "region": "西北",
        "title": "明城墙 · 书院门 · 回坊", "subtitle": "13.74 公里围住唐长安的骨架",
        "summary": "中国现存最大的古代城垣；墙下有碑林与关中书院，回坊里是千年蕃坊传下来的生活。",
        "tags": ["明城墙", "碑林", "回坊", "丝路"],
        "highlights": ["明城墙与瓮城", "西安碑林", "书院门与关中书院", "化觉巷清真大寺", "大雁塔"],
        "image": "/cities/xian.webp",
        "doc": "西安-明城墙书院门与回坊.md",
        "walk": "一日 · 约 6 公里",
        "credit": "Pexels 免费商用 · 区域氛围示意",
    },
    {
        "id": "dunhuang", "city": "敦煌", "district": "甘肃 · 敦煌", "region": "西北",
        "title": "莫高窟", "subtitle": "崖壁上的千年美术馆",
        "summary": "735 座洞窟、4.5 万平方米壁画，从 366 年凿到元代；藏经洞的门一开，就是二十世纪最痛的考古发现。",
        "tags": ["世界遗产", "石窟寺", "飞天", "藏经洞"],
        "highlights": ["莫高窟洞窟与九层楼", "数字展示中心", "鸣沙山月牙泉", "玉门关遗址", "阳关"],
        "image": "/cities/dunhuang.webp",
        "doc": "敦煌-莫高窟.md",
        "walk": "一日 · 约 3 公里",
        "credit": "Pexels 免费商用 · 区域氛围示意",
    },
    {
        "id": "kashi", "city": "喀什", "district": "新疆 · 喀什", "region": "西北",
        "title": "喀什老城", "subtitle": "土墙里的中亚",
        "summary": "中国现存规模最大、保存最完整的生土建筑群：过街楼在巷子上借空，阿以旺天窗把光引到屋子中央。",
        "tags": ["生土建筑", "过街楼", "巴扎", "木卡姆"],
        "highlights": ["艾提尕尔清真寺", "老城巷道与过街楼", "高台民居土陶人家", "花盆巴扎", "香妃墓"],
        "image": "/cities/kashi.webp",
        "doc": "喀什-老城.md",
        "walk": "一日 · 约 4 公里",
        "credit": "Pexels 免费商用 · 区域氛围示意",
    },
    # ---------------- 东北 ----------------
    {
        "id": "haerbin", "city": "哈尔滨", "district": "黑龙江 · 道里", "region": "东北",
        "title": "中央大街", "subtitle": "一块面包石，一条铁路城",
        "summary": "中东铁路造出的一座城：1450 米面包石街上立着 71 栋欧陆建筑，道外还有中华巴洛克。",
        "tags": ["中东铁路", "面包石", "拜占庭", "中华巴洛克"],
        "highlights": ["中央大街与马迭尔宾馆", "圣索菲亚教堂", "靖宇街中华巴洛克", "防洪纪念塔", "松花江"],
        "image": "/cities/haerbin.webp",
        "doc": "哈尔滨-中央大街.md",
        "walk": "一日 · 约 5 公里",
        "credit": "Pexels 免费商用 · 区域氛围示意",
    },
]

# 专题通识（不属任一城市，但参与检索）
GENERAL_DOCS = [
    {
        "doc": "中国老街建筑语汇通识.md",
        "city": "",
        "title": "中国老街建筑语汇通识",
        "subtitle": "骑楼 / 马鞍墙 / 燕尾脊 / 牌坊 / 双棋盘……",
        "image": "",
    },
    {
        "doc": "通识-中国传统民居类型图谱.md",
        "city": "",
        "title": "中国传统民居类型图谱",
        "subtitle": "合院 / 窑洞 / 吊脚楼 / 土楼 / 碉房 / 一颗印……",
        "image": "",
    },
    {
        "doc": "通识-中国古代都城营建.md",
        "city": "",
        "title": "中国古代都城营建",
        "subtitle": "从里坊制到街巷制，中轴线与城墙体系",
        "image": "",
    },
    {
        "doc": "通识-中国非物质文化遗产概览.md",
        "city": "",
        "title": "中国非物质文化遗产概览",
        "subtitle": "十大门类与 Citywalk 里的非遗",
        "image": "",
    },
    {
        "doc": "通识-线性文化遗产.md",
        "city": "",
        "title": "线性文化遗产：运河、丝路与茶马古道",
        "subtitle": "一条路如何串起一串城",
        "image": "",
    },
    {
        "doc": "通识-中国古桥与园林.md",
        "city": "",
        "title": "中国古桥与园林",
        "subtitle": "梁桥拱桥索桥廊桥 · 叠山理水与借景框景",
        "image": "",
    },
    {
        "doc": "通识-历史文化名城与街区保护.md",
        "city": "",
        "title": "历史文化名城与街区保护制度",
        "subtitle": "三层体系、四条原则与四种更新模式",
        "image": "",
    },
]

CITY_BY_DOC = {c["doc"]: c for c in CITY_PROFILES}

# ---------------------------------------------------------------- 坐标
_coords_cache: dict | None = None


def spot_coords() -> dict:
    """主要看点的 WGS84 坐标（网页导出/build_coords.py 生成，缺失时返回空表）。"""
    global _coords_cache  # noqa: PLW0603
    if _coords_cache is None:
        path = config.DATA_DIR / "spot_coords.json"
        try:
            _coords_cache = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _coords_cache = {}
    return _coords_cache


def city_coords(city_id: str) -> dict:
    """{ center: [lng, lat] | None, spots: [{name, lat, lng}] }"""
    entry = spot_coords().get(city_id) or {}
    return {
        "center": entry.get("center"),
        "spots": entry.get("spots") or [],
    }



def builtin_dir():
    return config.BUILTIN_DIR


def builtin_entries() -> list[dict]:
    """列出所有应入库的内置文件条目。"""
    entries = []
    for profile in CITY_PROFILES:
        entries.append({**profile, "category": "老街史料", "origin": "builtin"})
    for g in GENERAL_DOCS:
        entries.append({**g, "category": "古建筑", "origin": "builtin", "id": "general"})
    return entries


# ---------------------------------------------------------------- 详情正文
_sec_cache: dict[str, list[dict]] = {}


def _clean(line: str) -> str:
    import re as _re

    s = line.strip()
    s = _re.sub(r"^[-*]\s+", "", s)
    s = s.replace("**", "")
    s = _re.sub(r"\[\d+\]", "", s)          # 去掉 [1][2] 引用标号
    s = _re.sub(r"\s{2,}", " ", s)
    return s.strip()


def city_sections(city_id: str) -> list[dict]:
    """把某城的 Markdown 档案拆成 [{h, items}]，供详情页渲染。"""
    if city_id in _sec_cache:
        return _sec_cache[city_id]
    profile = next((p for p in CITY_PROFILES if p["id"] == city_id), None)
    if not profile:
        return []
    path = builtin_dir() / profile["doc"]
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []

    sections: list[dict] = []
    cur = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("## "):
            cur = {"h": line[3:].strip(), "items": []}
            sections.append(cur)
        elif line.startswith("# ") or line.startswith(">") or line.strip() in ("", "---"):
            continue
        elif cur is not None:
            s = _clean(line)
            if len(s) >= 4 and (not cur["items"] or cur["items"][-1] != s):
                cur["items"].append(s)

    # 去掉空小节，限制每节条目数，页面才不会被撑得失控
    out = [{"h": s["h"], "items": s["items"][:6]} for s in sections if s["items"]]
    _sec_cache[city_id] = out
    return out

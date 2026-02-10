import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
# 引入核心库，如果环境没配好，这里就会报错
try:
    from lunar_python import Solar
except ImportError:
    Solar = None

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class PaipanRequest(BaseModel):
    year: int
    month: int
    day: int
    hour: int
    minute: int = 0
    gender: str = "男"

class ZiWeiEngine:
    def __init__(self):
        self.ZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
        self.GAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
        self.NAYIN = {
            "甲子":4,"乙丑":4,"丙寅":6,"丁卯":6,"戊辰":5,"己巳":5,"庚午":5,"辛未":5,"壬申":4,"癸酉":4,
            "甲戌":6,"乙亥":6,"丙子":2,"丁丑":2,"戊寅":5,"己卯":5,"庚辰":4,"辛巳":4,"壬午":5,"癸未":3,
            "甲申":2,"乙酉":2,"丙戌":5,"丁亥":5,"戊子":6,"己丑":6,"庚寅":5,"辛卯":5,"壬辰":2,"癸巳":2,
            "甲午":4,"乙未":4,"丙申":6,"丁酉":6,"戊戌":5,"己亥":5,"庚子":5,"辛丑":5,"壬寅":4,"癸卯":4,
            "甲辰":6,"乙巳":6,"丙午":2,"丁未":2,"戊申":5,"己酉":5,"庚戌":4,"辛亥":4,"壬子":5,"癸丑":5,
            "甲寅":2,"乙卯":2,"丙辰":5,"丁巳":5,"戊午":6,"己未":6,"庚申":5,"辛酉":5,"壬戌":2,"癸亥":2
        }
        self.SIHUA = {"甲":"廉破武阳","乙":"机梁紫阴","丙":"同机昌廉","丁":"阴同机巨","戊":"贪阴右机",
                      "己":"武贪梁曲","庚":"阳武阴同","辛":"巨阳曲昌","壬":"梁紫左武","癸":"破巨阴贪"}

    def get_ziwei_idx(self, bureau, day):
        for x in range(bureau):
            if (day + x) % bureau == 0:
                q = (day + x) // bureau
                base = (2 + q - 1) % 12
                return (base - x) % 12 if x % 2 != 0 else (base + x) % 12
        return 2

    def get_stars(self, m_idx, h_idx, y_zhi, y_gan, bureau, day):
        # 基础星曜计算
        zw_idx = self.get_ziwei_idx(bureau, day)
        tf_idx = (4 - zw_idx) % 12
        stars = {z: [] for z in self.ZHI}
        
        # 主星
        for n, o in [("紫微",0),("天机",1),("太阳",3),("武曲",4),("天同",5),("廉贞",8)]:
            stars[self.ZHI[(zw_idx-o)%12]].append(n)
        for n, o in [("天府",0),("太阴",1),("贪狼",2),("巨门",3),("天相",4),("天梁",5),("七杀",6),("破军",10)]:
            stars[self.ZHI[(tf_idx+o)%12]].append(n)
            
        # 辅星
        stars[self.ZHI[(10 - h_idx) % 12]].append("文昌")
        stars[self.ZHI[(4 + h_idx) % 12]].append("文曲")
        stars[self.ZHI[(4 + m_idx - 1) % 12]].append("左辅")
        stars[self.ZHI[(10 - (m_idx - 1)) % 12]].append("右弼")
        
        ky = {"甲":["丑","未"], "乙":["子","申"], "丙":["亥","酉"], "丁":["亥","酉"],"戊":["丑","未"], "己":["子","申"], "庚":["丑","未"], "辛":["午","寅"],"壬":["卯","巳"], "癸":["卯","巳"]}.get(y_gan, [])
        if ky: stars[ky[0]].append("天魁"); stars[ky[1]].append("天钺")
        
        lu_map = {"甲":"寅","乙":"卯","丙":"巳","丁":"午","戊":"巳","己":"午","庚":"申","辛":"酉","壬":"亥","癸":"子"}
        if y_gan in lu_map:
            l_idx = self.ZHI.index(lu_map[y_gan])
            stars[self.ZHI[l_idx]].append("禄存")
            stars[self.ZHI[(l_idx+1)%12]].append("擎羊")
            stars[self.ZHI[(l_idx-1)%12]].append("陀罗")
            
        return stars

    def calculate(self, y_gz, m_idx, day, h_idx, gender):
        y_gan, y_zhi = y_gz[0], y_gz[1]
        ming_idx = (2 + (m_idx - 1) - h_idx) % 12
        shen_idx = (2 + (m_idx - 1) + h_idx) % 12
        
        start_gan_idx = ((self.GAN.index(y_gan) % 5) * 2 + 2) % 10
        stems = {self.ZHI[(2+i)%12]: self.GAN[(start_gan_idx+i)%10] for i in range(12)}
        
        ming_gz = stems[self.ZHI[ming_idx]] + self.ZHI[ming_idx]
        bureau = self.NAYIN.get(ming_gz, 3)
        
        stars = self.get_stars(m_idx, h_idx, y_zhi, y_gan, bureau, day)
        
        p_names = ["命宫","兄弟","夫妻","子女","财帛","疾厄","迁移","交友","官禄","田宅","福德","父母"]
        is_yang = y_gan in "甲丙戊庚壬"
        direction = 1 if (is_yang and gender=="男") or (not is_yang and gender=="女") else -1
        
        sihua = self.SIHUA.get(y_gan, "")
        s_map = {"禄":sihua[0],"权":sihua[1],"科":sihua[2],"忌":sihua[3]} if sihua else {}
        
        res = {}
        for i, name in enumerate(p_names):
            curr = (ming_idx - i) % 12
            zhi = self.ZHI[curr]
            gan = stems[zhi]
            
            s_list = stars[zhi]
            fmt = []
            for s in s_list:
                tag = ""
                for k,v in s_map.items():
                    if v==s: tag=f"({k})"
                fmt.append(f"{s}{tag}")
            
            step = i if direction == 1 else (12 - i) % 12
            age = bureau + step * 10
            
            tags = []
            if gan == y_gan: tags.append("【来因】")
            if curr == shen_idx: tags.append("【身宫】")
            
            res[name] = {
                "干支": f"{gan}{zhi}",
                "星曜": fmt if fmt else ["【空宫】"],
                "大限": f"{age}-{age+9}",
                "标注": " ".join(tags)
            }
            
        return {"局数": f"{bureau}局", "核心": {"命宫": self.ZHI[ming_idx]}, "数据": res}

engine = ZiWeiEngine()

@app.post("/api/calc")
async def calc(req: PaipanRequest):
    # 终极兜底：检查库是否安装
    if Solar is None:
        return {"error": "Dependencies missing", "message": "lunar-python not installed"}

    try:
        s = Solar.fromYmdHms(req.year, req.month, req.day, req.hour, req.minute, 0)
        l = s.getLunar()
        
        # 1. 获取干支 (使用八字接口，最稳)
        bazi = l.getEightChar()
        y_gz = bazi.getYear()
        m_gz = bazi.getMonth()
        d_gz = bazi.getDay()
        
        # 2. 计算月份索引 (节气月逻辑)
        # 寅=1, 卯=2...
        m_zhi = m_gz[1]
        m_idx = (engine.ZHI.index(m_zhi) - 2) % 12 + 1
        
        # 3. 闰月霸权
        if l.getMonth() < 0: m_idx = abs(l.getMonth())
        
        h_idx = engine.ZHI.index(l.getTimeZhi())
        
        data = engine.calculate(y_gz, m_idx, l.getDay(), h_idx, req.gender)
        
        # 4. 返回完整结构
        return {
            "meta": {
                "公历": s.toYmdHms(),
                "农历": f"{l.getYear()}年{l.getMonth()}月{l.getDay()}日",
                "干支": f"{y_gz} {m_gz} {d_gz}"
            },
            "chart": data,
            "result": data
        }
        
    except Exception as e:
        # 万一报错，返回 JSON 而不是 500
        return {
            "error": True,
            "message": str(e),
            "meta": {"干支": "系统 维护 中"},
            "result": {}
        }

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from lunar_python import Solar

app = FastAPI(title="钦天门紫微斗数API (节气定轴修正版)")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class PaipanRequest(BaseModel):
    year: int; month: int; day: int; hour: int; minute: int = 0; gender: str = "男"

class ZiWeiEngine:
    def __init__(self):
        self.ZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
        self.GAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
        # 纳音定局
        self.NAYIN = {"甲子":4,"乙丑":4,"丙寅":6,"丁卯":6,"戊辰":5,"己巳":5,"庚午":5,"辛未":5,"壬申":4,"癸酉":4,
                      "甲戌":6,"乙亥":6,"丙子":2,"丁丑":2,"戊寅":5,"己卯":5,"庚辰":4,"辛巳":4,"壬午":5,"癸未":3,
                      "甲申":2,"乙酉":2,"丙戌":5,"丁亥":5,"戊子":6,"己丑":6,"庚寅":5,"辛卯":5,"壬辰":2,"癸巳":2,
                      "甲午":4,"乙未":4,"丙申":6,"丁酉":6,"戊戌":5,"己亥":5,"庚子":5,"辛丑":5,"壬寅":4,"癸卯":4,
                      "甲辰":6,"乙巳":6,"丙午":2,"丁未":2,"戊申":5,"己酉":5,"庚戌":4,"辛亥":4,"壬子":5,"癸丑":5,
                      "甲寅":2,"乙卯":2,"丙辰":5,"丁巳":5,"戊午":6,"己未":6,"庚申":5,"辛酉":5,"壬戌":2,"癸亥":2}
        self.SIHUA = {"甲":"廉破武阳","乙":"机梁紫阴","丙":"同机昌廉","丁":"阴同机巨","戊":"贪阴右机",
                      "己":"武贪梁曲","庚":"阳武阴同","辛":"巨阳曲昌","壬":"梁紫左武","癸":"破巨阴贪"}

    def get_ziwei_idx(self, bureau, day):
        q, r = divmod(day, bureau)
        if r == 0: return (2 + q - 1) % 12
        add = bureau - r
        base = (2 + q) % 12
        return (base - add) % 12 if add % 2 != 0 else (base + add) % 12

    def calculate(self, y_gan, month_idx, day, h_idx, gender):
        # 命身宫 (寅2起)
        m_idx = (2 + (month_idx - 1) - h_idx) % 12
        s_idx = (2 + (month_idx - 1) + h_idx) % 12
        
        # 宫干 (五虎遁)
        start_gan = ((self.GAN.index(y_gan) % 5) * 2 + 2) % 10
        stems = {self.ZHI[(2+i)%12]: self.GAN[(start_gan+i)%10] for i in range(12)}
        
        # 五行局 (纳音)
        ming_gz = stems[self.ZHI[m_idx]] + self.ZHI[m_idx]
        bureau = self.NAYIN.get(ming_gz, 3)
        
        # 安星
        zw_idx = self.get_ziwei_idx(bureau, day)
        tf_idx = (4 - zw_idx) % 12
        stars = {z: [] for z in self.ZHI}
        
        for n, o in [("紫微",0),("天机",1),("太阳",3),("武曲",4),("天同",5),("廉贞",8)]:
            stars[self.ZHI[(zw_idx-o)%12]].append(n)
        for n, o in [("天府",0),("太阴",1),("贪狼",2),("巨门",3),("天相",4),("天梁",5),("七杀",6),("破军",10)]:
            stars[self.ZHI[(tf_idx+o)%12]].append(n)
            
        # 顺逆大限
        direction = 1 if (y_gan in "甲丙戊庚壬") == (gender == "男") else -1
        
        p_names = ["命宫","兄弟","夫妻","子女","财帛","疾厄","迁移","交友","官禄","田宅","福德","父母"]
        res = {}
        for i, name in enumerate(p_names):
            curr = (m_idx - i) % 12
            zhi = self.ZHI[curr]
            gan = stems[zhi]
            step = (curr - m_idx) % 12 if direction == 1 else (m_idx - curr) % 12
            age = bureau + step * 10
            tags = []
            if gan == y_gan: tags.append("【来因】")
            if curr == s_idx: tags.append("【身宫】")
            res[name] = {"宫位":f"{gan}{zhi}","星曜":stars[zhi],"大限":f"{age}-{age+9}","标注":" ".join(tags)}
            
        return {"局数":f"{bureau}局","命盘":res}

engine = ZiWeiEngine()

@app.post("/api/calc")
def calc(req: PaipanRequest):
    s = Solar.fromYmdHms(req.year, req.month, req.day, req.hour, req.minute, 0)
    l = s.getLunar()
    # 核心修正：使用干支月索引 (寅=1, 卯=2, 辰=3...)
    m_pillar = l.getMonthInGanZhi() # 如 "丙辰"
    m_idx = engine.ZHI.index(m_pillar[1]) + 1
    if m_idx < 1: m_idx = 1 # 兜底逻辑
    
    data = engine.calculate(l.getYearGan(), m_idx, l.getDay(), engine.ZHI.index(l.getTimeZhi()), req.gender)
    return {"meta": {"公历": s.toYmdHms(), "干支": f"{l.getYearInGanZhi()} {m_pillar} {l.getDayInGanZhi()}"}, "result": data}
